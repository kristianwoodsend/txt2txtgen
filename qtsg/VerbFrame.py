"""
Investigation how to get sync grammar to relate sentences to highlights
"""


from config import Config
from parse import POSTagger, PhraseDependencyTree
from nlputils import NltkUtils
from features import ExtractFeatures
from utils import ListFiles
from tasks import CNNAssessmentFiles, BBCCaptionFilelist, DUC04Filelist
from summarize import WriteHighlights
from features.FeatureList import *
from nlputils import TfIdf
from nlputils.TfIdf import CorpusFreqDist
import nltk.probability
import cPickle as pickle
import sys, os, codecs

PRINT_DEBUG = True
PRINT_INFO = False
PRINT_RULE_APPLICATION = True


# todo: sort out parsing and caching
# dpParser = POSTagger.StanfordDependencyParser()
# pennParser = POSTagger.StanfordPennParser()
graphvizDir = Config.GRAPHVIZ_DIR
FORMAT="ps"
GRAPHVIZ_EXTRA = False
MIN_PHRASE_SIZE = PhraseDependencyTree.PhraseDependencyTree.USE_CONSTITUENCY_STRUCTURE




def investigateVerbFrame():
    
    verbDict = createVerbFrameRules()
    #printVerbDict(verbDict)
    
    #raise SystemExit
    
    
    SENTENCE_PHRASE_TAGS = ( 'S', 'SBAR', 'VP' )
              
    print
    labelsPresent = True
    fileCount = 0
    ExtractFeatures.setFeaturesCache()
    for f in CNNAssessmentFiles.filelistIter():
        try:
            featuresDict = ExtractFeatures.extractFeaturesOfFile(f, labelsPresent=labelsPresent)
            fileCount += 1
        except KeyError: continue
        sentences = featuresDict[kSentences]
        highlights = featuresDict[kHiligLhtSentences]
    
        print "Applying rules to sentences in %s:" % f
        for s in highlights+sentences:
            #applyVerbFrameRuleToSentence(s, verbDict)
            sTree = createTree(s)
            para = createVFParaphraseTree(sTree, verbDict)
            
            print "\n\nFinal paraphrase:"
            print para
                    

def applyVerbFrameRuleToSentence(s, verbDict):
    """
    Find rules that can apply to this sentence, and print out available contractions
    """
    sTree = createTree(s)
    phraseList = sTree.getPhrases()
    for (ph,tok) in phraseList:
        try:
            if ph.isLeaf(): continue
            appliedRulesList = applyVerbFrameRulesToPhrase(ph, verbDict) 
            phraseDeps = set([VerbFrameRule.encodeChild(ch) for ch in ph])
        
            if PRINT_DEBUG: 
                # just for debug really
                verbText = _joinVerbListIntoText(_findVerbsInPhrase(ph))
                print "\nOriginal: ", nodeText(ph)
                print "Consolidated rule list for %s: " % verbText, appliedRulesList
            
            createChoiceNodeFromRules(ph, appliedRulesList)
            
        except AttributeError:
            # no verb or rule to apply
            print "Cannot apply any rule to ", nodeText(ph)
            pass


def createVFParaphraseTree(srcPhraseTree, verbDict):
    """
    Create a paraphrase using verb frame rules.
    Applies all applicable rules to this and child nodes in the phrase tree.
    Returns a PhraseDependencyTree copy of srcPhraseTree.
    """
    assert not srcPhraseTree.isLeaf(), "Rule called on leaf"

    targetPhraseTree = POSTagger.PhraseDependencyTree("( %s )"%srcPhraseTree.node)
    targetPhraseTree.copyAttributes(srcPhraseTree)
    paraphrasedChildren = []
    
    for ch in srcPhraseTree:
        if ch.isLeaf():
            # just do deep copy and don't apply any more rules
            copiedNode = ch.copy(deep=True)
            paraphrasedChildren.append(copiedNode)
        else:
            chPara = createVFParaphraseTree(ch, verbDict)
            paraphrasedChildren.append(chPara)

    if False:
        print "After createVFParaphraseTree(), children:"
        for ch in paraphrasedChildren:
            print ch
    
    # apply verb frame rules to the set of children
    try:
        ruleList = applyVerbFrameRulesToPhrase(srcPhraseTree, verbDict)
        assert len(ruleList)>0, "No rules at all"
        if len(ruleList)==1:
            if ruleList[0][0]==[]:
                # rule just says use original, so jump to straight copy
                raise AttributeError, "No modification rules provided"
            else:
                # rule is modification, so also allow option of original tree
                ruleList.append(([],1))
        choiceList = [] # the list of option nodes and rule counts
        for delDepList, count in ruleList:
            # print count, delDepList
            optionNode = POSTagger.PhraseDependencyTree("( %s )"%srcPhraseTree.node)
            optionNode.copyAttributes(srcPhraseTree)
            for ch in paraphrasedChildren:
                if VerbFrameRule.encodeChild(ch) not in delDepList:
                    copy = ch.copy(deep=True)
                    optionNode.append(copy)
            choiceList.append( (optionNode, count) )
        targetPhraseTree = PhraseTreeChoice.create(choiceList)

    except AttributeError:
        # just make a copy of the original node
        for ch in paraphrasedChildren:
            targetPhraseTree.append(ch)
        
    #raise NotImplementedError, "createVFParaphraseTree() not done yet"
    
    # check that the target phrase tree seems OK
    if isinstance(targetPhraseTree, PhraseTreeChoice):
        #print targetPhraseTree.tag()
        #print targetPhraseTree
        assert targetPhraseTree.tag()==PhraseTreeChoice.TAG, "Misnamed choice node"
    _debug_checkChoiceTags(targetPhraseTree)
        
    return targetPhraseTree

def applyVerbFrameRulesToPhrase(ph, verbDict):
    """
    Applies all applicable rules to the phrase ph.
    Returns a list of (child nodes for deletion, rule count).
    Consolidates rule counts where the rules give the same list of deletion.
    """
    KEEP_DEPS = ['fixed','aux','auxpass','neg']
    applicableRules = findMatchingVerbRules(ph,verbDict)

    # we want to consolidate rules that give the same output
    appliedRuleEncChildToDelete = []
    appliedRuleEncChildToDeleteCount = []
        
    if not applicableRules:
        print "\nOriginal: ", nodeText(ph)
        print "No rules at all"
        return None
        
    for r in applicableRules: 
        #printPhraseTreeStructure(copiedPhrase)
        childTypesToDelete = [VerbFrameRule.encodeChild(ch) \
            for ch in ph if ch.dep() not in KEEP_DEPS \
            and VerbFrameRule.encodeChild(ch) not in r._deps]


        if PRINT_DEBUG: print "Child types ready for deletion: ", childTypesToDelete

        foundEquivalentRule = False
        for i in range(len(appliedRuleEncChildToDelete)):
            if appliedRuleEncChildToDelete[i] == childTypesToDelete: # equivalent rule
                appliedRuleEncChildToDeleteCount[i] += r.count()
                foundEquivalentRule = True
                break
        if not foundEquivalentRule:
            appliedRuleEncChildToDelete.append(childTypesToDelete)
            appliedRuleEncChildToDeleteCount.append(r.count())

    consolidatedList = zip(appliedRuleEncChildToDelete, appliedRuleEncChildToDeleteCount)
    return consolidatedList
    
                    
def createChoiceNodeFromRules(ph, appliedRulesList):
    """
    Apply the rules and create a CHOICE node from the possibilities
    """
    assert appliedRulesList, "No appliedRulesList has been provided"
    if len(appliedRulesList)<=1:
        # not enough rules to make a choice
        raise AttributeError, "Only %d rules in appliedRulesList, not enough for a choice" % len(appliedRulesList)
        
    print "Equivalent rule set:"
    for chForDeletion, count in appliedRulesList:
        print  count,"\t\t", chForDeletion
        
    if False: # we need to create a set of choice nodes here, one for each consol rule
        # copy phrase here to apply rule
        copiedPhrase = ph.copy(deep=True)
        copiedPhrase._rel = ph._rel
        for i, ch in enumerate(ph):
            copiedPhrase[i]._rel = ph[i]._rel
        
        # We need to do the deletion after the marking loop, or children are skipped
        for ch in childrenToDelete:
            copiedPhrase.remove(ch)
            #print "Deleted:", nodeText(ch), "because dep ", ch.dep()
        
        print r._count, "\t", nodeText(copiedPhrase), "\t from rule", r 
    
    

    
def createVerbFrameRules():
    """
    Creates the verb frame rules dictionary from the working directory of files.
    """
    try:
        verbDict = loadVerbFrameRules()
    except IOError:
        ExtractFeatures.buildCorpusFreqDist()
        ExtractFeatures.setFeaturesCache()    
        directory = Config.TRAINING_DOCS_DIR
        filePattern = '*.doc.txt'
        labelsPresent = False
        allFiles = ListFiles.listAllFiles( filePattern, directory )
        fileCount=0
        FILE_COUNT_LIMIT = 5000
        verbDict = {}
        
        for f in allFiles:
            if (fileCount > FILE_COUNT_LIMIT): break
            print "(%d)\tProcessing file %s" % (fileCount, f)
            try:
                featuresDict = ExtractFeatures.extractFeaturesOfFile(f, labelsPresent=labelsPresent)
                fileCount += 1
            except KeyError: continue
            sentences = featuresDict[kSentences]
            highlights = featuresDict[kHilightSentences]
        
            for s in highlights+sentences:
                try:
                    extractVerbFrameRulesFromSentence(s, verbDict)
                except ValueError, e:
                    print "Sentence parse failure: ", e
                    pass
        
        if PRINT_INFO: print "\nNumber of files processed: ", fileCount 
        saveVerbFrameRules(verbDict)
        
    return verbDict

def consolidateVerbFrameRules(verbDict):
    """
    Consolidates the verb frame rules dictionary.
    Rules that are equivalent according to matchesRule() are combined.
    """
    consolidatedDict = {}
    for k in verbDict:
        verbRuleSet = verbDict[k]
        consolidatedList = []
        for rule in verbRuleSet:
            #print rule, "\t\t\t\t", rule._count
            matchingRules = [ r for r in consolidatedList if rule.matchesRule(r) ] # NB need to re-evaluate consoldatedList each time
            if len(matchingRules)>0:
                assert len(matchingRules) == 1, "There is now more than one consolidated rule"
                consRule = matchingRules[0]
                consRule.inc(rule._count)
                #print "Combined rules for ", k, "\t count ", consRule._count
            else:
                # add this new rule in
                consolidatedList.append(rule)

        consolidatedDict[k] = consolidatedList
        if PRINT_DEBUG:
            print "Original number of rules for ", k, "\t\t", len(verbRuleSet)
            print "Consolidated #  of rules for ", k, "\t\t", len(consolidatedList)
            print
        
    return consolidatedDict
    


def extractVerbFrameRulesFromSentence(s, verbDict):
    """
    Processes text sentence s, and extracts verb frame rules.
    Rules are added to verbDict
    """
    if PRINT_DEBUG: print "Original: ", s
    sTree = createTree(s)
    phList = sTree.getPhrases()
    for (ph,tok) in phList:
        try:
            verbListText, verbFrameRule = generateVerbFrameRule(ph) 
            if PRINT_DEBUG: print "Verb: ", verbListText, "\t\t", verbFrameRule
            addVerbFrameRule(verbListText, verbFrameRule, verbDict)
            # _checkDodgyRuleDebug(verbListText, verbFrameRule)
        except AttributeError: pass
        except ValueError, e: print e; pass


def addVerbFrameRule( verbText, verbRule, verbRuleDict ):
    """
    Adds the verb rule to the dictionary of rules.
    If an identical rule already exists, the counter for the rule is incremented
    """
    if verbText not in verbRuleDict: 
        verbRuleDict[verbText] = [] 
    thisVerbEntry = verbRuleDict[verbText]
    if verbRule in thisVerbEntry:
        originalRule = thisVerbEntry[thisVerbEntry.index(verbRule)]
        originalRule.inc()
    else:
        thisVerbEntry.append(verbRule)
    

def generateVerbFrameRule(ph):
    """
    Generates a verb frame rule for this phrase
    Returns verb as text, verb frame rule
    Raises AttributeError if there is no verb present
    """
    if ph.isLeaf(): raise AttributeError, "Leaf, not a phrase"
    verbText = _joinVerbListIntoText(_findVerbsInPhrase(ph)) # let any AttributeError go up stack
    return verbText, VerbFrameRule(verbText,ph)
    
    

def _checkDodgyRuleDebug(verbListText, verbFrameRule):
    """
    Check this rule and stop the program if this is the rule we want to debug.
    For debugging only.
    """
    if verbListText=="is" \
        and ph.tag()=="S" \
        and ph.dep()=="ccomp" \
        and str(verbFrameRule).count("( fixed ccomp nsubj )")>0:
        print
        print verbFrameRule
        print "Phrase: ", nodeText(ph)
        print "Sentence: ", s
        printPhraseTreeStructure(ph)
        print "Phrase structure:"
        print ph
        raise SystemExit, "Found dodgy rule"

def printVerbDict(verbDict):
    """
    Print out some information on the rule set for all verbs
    """
    print "Printing out rule dictionary"
    for k in verbDict:
        thisVerbRuleSet = verbDict[k]
        for rule in thisVerbRuleSet:
            print rule, "\t\t\t\t", rule._count
        print
    print "Number of verb frames identified: ", len(verbDict)

    # print out a particular rule set
    if False:
        print
        key = "is"
        print key, ":"
        thisVerbRuleSet = verbDict[key]
        for rule in thisVerbRuleSet:
            print rule, "\t\t\t\t", rule._count
        print "Number of rules: ", len(thisVerbRuleSet)


def _findVerbsInPhrase(ph):
    """
    Finds the verb tokens in this phrase
    Returns list of verb tokens
    Raises AttributeError if there is no verb present in the phrase at all
    """
    assert not ph.isLeaf(), "Leaf node, not a phrase"
    verbList = []
    for ch in ph:
        if ch.tag().startswith("VB") and not \
            (ch.dep()=="amod" or ch.dep().startswith("aux")):
            verbList.append(NltkUtils.stem(nodeText(ch)))
    if len(verbList)==0:
        raise AttributeError, "No verbs present in %s" % nodeText(ph)
    return verbList



def _findVerbDependencyLabelsInPhrase(ph, verbDepList):
    """
    A debug routine.
    Finds the list of verb dependency labels in this phrase.
    Just to make sure we've got them all covered.
    """
    verbList = []
    for ch in ph:
        if ch.tag().startswith("VB") and not ch.dep()=="amod":
            verbList.append(NltkUtils.stem(nodeText(ch)))
            verbDepList.append(ch.dep())
    originalVerbList = _findVerbsInPhrase(ph)
    assert _joinVerbListIntoText(verbList) == _joinVerbListIntoText(originalVerbList), \
        "Verb list not the same as the original"


def _joinVerbListIntoText(verbList):
    """ Combines the verbs in verbList into a single string and returns it.
    """
    return " ".join(verbList)


def findMatchingVerbRules(phrase, verbDict):
    """
    Finds and returns any rules in verbDict that match the phrase.
    """
    matchingRules = []
    try:
        verbText = _joinVerbListIntoText(_findVerbsInPhrase(phrase))
        thisVerb = verbDict[verbText]
        for rule in thisVerb:
            if rule.matches(phrase): matchingRules.append(rule)
    except KeyError:
        if PRINT_DEBUG: print "Cannot find verb %s" % verbText
        pass
    
    if len(matchingRules)==0:
        raise AttributeError, "No rules available for %s" % verbText
    return matchingRules





def investigatePickledResults():
    """
    Read in pickled sync grammar and do some investigations
    """
    syncGrammar = loadQSGRules()
    print "Sync grammar generation completed"
    #printResultsListInfo( syncGrammar )
    print 
    
    syncGrammarRules = [ SyncGrammarRule(n1,n2) for (n1,n2) in syncGrammar ]
    print "Sync Grammar rules length: ", len(syncGrammarRules)
    modificationRules = [r for r in syncGrammarRules
        if not r.isIdentical()]
    print "Modified rules: ", len(modificationRules)
    
    # how many rules involve a simple deletion
    testRule = modificationRules[6]
    print testRule
    print "Is identical:", testRule.isIdentical()
    print "Is partOfSpeechChange:", testRule.partOfSpeechChange()
    print "Is depLabelChange:", testRule.depLabelChange()
    print "Has containsDeletions:", testRule.containsDeletions()
    print "Deleted nodes:", [n._node for n in testRule.deletedNodes()]
    print "Is reordered:", testRule.isReordered()
    
    
    
    
    """
    Try to find rule that will help to resolve:
    Original:   the rest of the way
    5 Identical rule
    Paraphrase:  of the way rest
    1 NP/dobj -> ( DT/det#0 NN/fixed#2 PP/prep_of#1 )       NP/dobj -> ( QP/num#1 NN/fixed#2 )
    """
    if False:
        for r in modificationRules:
            if r._source._node=="NP" and r._target._node=="NP"\
            and str(r).count(",/fixed#0 NP/appos#0 ,/fixed#0")>0:
            #if r._source._node=="NP" and r._source._dep=="prep_of" and\
            #    r._target._node=="NP" and r._target._dep=="poss":
                print r
        raise SystemExit, "Located matching rules"
    
    
    print "\n\nInvestigating deletions: "
    delOnlyRules = [ r for r in modificationRules 
        if r.containsDeletions() and not r.isReordered() ]
    #for r in delOnlyRules: print r
    print "\nNumber of deletion only rules: ", len(delOnlyRules)
    fdist = nltk.probability.FreqDist()
    for r in delOnlyRules:
        delNodes = r.deletedNodes()
        for n in delNodes: fdist.inc(n._node)
    print "Tags deleted:"
    for (k,v) in fdist.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*v/fdist.N())
        
    tagChangeOnly = [ r for r in modificationRules 
        if r.partOfSpeechChange() and 
        not r.containsDeletions() and 
        not r.isReordered() and
        not r.containsInsertions() ]
    print "\n\nNumber of modification rules involving only tag change", len(tagChangeOnly) 
    fdist = nltk.probability.FreqDist((r._source._node,r._target._node) for r in tagChangeOnly)
    for (k,v) in fdist.iteritems(): print k, '\t', v, \
        "\t%8.1f %%" % (100.0*v/fdist.N())
        
    # transform in POS involving some change
    posChange = [ r for r in modificationRules 
        if r.partOfSpeechChange() and 
        (r.containsDeletions() or r.isReordered() or r.containsInsertions() ) ]
    print "\n\nNumber of modification rules changing POS involving some change", len(posChange) 
    fdist = nltk.probability.FreqDist((r._source._node,r._target._node) for r in posChange)
    for (k,v) in fdist.iteritems(): print k, '\t', v, \
        "\t%8.1f %%" % (100.0*v/fdist.N())
    
    print "\n\nCount rules instances: which appear more than once"
    fdist = nltk.probability.FreqDist(str(r) for r in syncGrammarRules )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break

    print "\n\nCount instances of true modification: which appear more than once"
    someRealChange = [ r for r in modificationRules
        if (r.containsDeletions() or r.isReordered() or r.containsInsertions() ) ]
    fdist = nltk.probability.FreqDist(str(r) for r in someRealChange )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break

    print "\n\nCount unique rules of modification which involve just deletions"
    someRealChange = [ r for r in modificationRules
        if r.containsDeletions() and not (r.isReordered() or r.containsInsertions()) ]
    fdist = nltk.probability.FreqDist(str(r) for r in someRealChange )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break

    print "\n\nCount instances of POS modification: which appear more than once"
    fdist = nltk.probability.FreqDist(str(r) for r in posChange )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break
        
        
def investigatePickledResultsRuleSet():
    """
    Read in pickled sync grammar and do some investigations
    using the set of rules, counted into groups
    """
    syncGrammarRules = loadQSGRules()
    print "Sync Grammar rules length: ", len(syncGrammarRules)
    
    # print stats for rule set
    fdist = nltk.probability.FreqDist()
    fdistCount = nltk.probability.FreqDist()
    fdistDups = nltk.probability.FreqDist()
    fdistDels = nltk.probability.FreqDist()
    fdistIns = nltk.probability.FreqDist()
    fdistReorder = nltk.probability.FreqDist()
    for r in syncGrammarRules: 
        fdist.inc(r._source.tag())
        fdistCount.inc(r._source.tag(), r.count())
        if r.isIdentical(): fdistDups.inc(r._source.tag())
        if r.deletedNodes(): fdistDels.inc(r._source.tag())
        if r.containsInsertions(): fdistIns.inc(r._source.tag())
        if r.isReordered(): fdistReorder.inc(r._source.tag())
        
    print "Source parent tag for rule:\t\t\tBy count:"
    for (k,v) in fdist.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*v/fdist.N()),\
        "\t\t", fdistCount[k],\
        "\t%8.1f %%" % (100.0*fdistCount[k]/fdistCount.N())
    
    print "\nNo-change rules:"
    for (k,v) in fdistDups.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistDups[k]/fdistDups.N()),\
        "\t%8.1f %%" % (100.0*fdistDups[k]/fdist[k])

    print "\nDeleted nodes rules:"
    for (k,v) in fdistDels.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistDels[k]/fdistDels.N()),\
        "\t%8.1f %%" % (100.0*fdistDels[k]/fdist[k])

    print "\nInserted nodes rules:"
    for (k,v) in fdistIns.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistIns[k]/fdistIns.N()),\
        "\t%8.1f %%" % (100.0*fdistIns[k]/fdist[k])

    print "\nReordered nodes rules:"
    for (k,v) in fdistReorder.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistReorder[k]/fdistReorder.N()),\
        "\t%8.1f %%" % (100.0*fdistReorder[k]/fdist[k])
        
def investigateParaphrasing():
    """
    Try to write out some sentences using the paraphrase rules
    """
    print "In investigateParaphrasing"
    
    ExtractFeatures.buildCorpusFreqDist()
    ExtractFeatures.setFeaturesCache()    
    directory = Config.TRAINING_DOCS_DIR
    filePattern = '*.doc.txt'
    labelsPresent=True
    allFiles = ListFiles.listAllFiles( filePattern, directory )
    fileCount=0
    sentenceCount=0
    targetFileCount=4
    targetSentenceCount=9
    
    print "Getting rules"
    syncGrammarRules = createQSGFromDirectory()
    print "Sync Grammar rules length: ", len(syncGrammarRules)
    
    for f in allFiles:
        fileCount += 1
        #if not fileCount == targetFileCount: continue
        if fileCount>150: break
        print "Processing (%d): " % fileCount, f
        featuresDict = ExtractFeatures.extractFeaturesOfFile(f, labelsPresent=labelsPresent)
        sentences = featuresDict[kSentences]
        highlights = featuresDict[kHilightSentences]
        hiTrees = [ createTree(h) for h in highlights ]
        print "Number of sentences: ", len(sentences), "\tNumber of highlights: ", len(highlights)
        for s in sentences:
            sentenceCount += 1
            #if not sentenceCount==targetSentenceCount: continue
            print "Working on: ", s
            sTree = createTree(s)
            #print sTree
            paraphrases = _findMatchingRulesForChildRecursive( syncGrammarRules, sTree )
            assert len(paraphrases)==1, "Even the root has created more than one paraphrase"
            
            #print
            p = paraphrases[0][0]
            #print p
            selectShortestParaphrase(p)
            pTxt = " ".join(p.leaves())
            print "INFO_comprn\t%d\t%d\t%f" % (len(pTxt), len(s.strip()), 1.0*len(pTxt)/len(s.strip())) 
            if len(pTxt)<len(s.strip()):
                print 
                print "Original:    ", s
                print "Paraphrases: ", pTxt
                #print pTxt
                #print "Shortened from %d to %d" % (len(s), len(pTxt)) 
            else:
                print
                # print "Unchanged:    ", s.strip()
                pass
                
        #raise SystemExit, "All done" 

from itertools import count, izip
def selectShortestParaphrase(p):
    if p.isLeaf(): return
    else:
        for ch in p:
            selectShortestParaphrase(ch)
    if isinstance(p, PhraseTreeChoice): 
        #print "PhraseTreeChoice found"
        lengths = map(lambda ch: len(ch.leaves()), p)
        #print "lengths:", lengths
        
        minvalue, minindex = min(izip(lengths, count()))
        maxvalue, maxindex = max(izip(lengths, count()))
        mostvalue, mostindex = max(izip(p.counts(), count()))
        #print "Min length:  ", minvalue, minindex
        #print "Most likely: ", mostvalue, mostindex
        p.setChoice(minindex)
    return
    


def createQSGParaphrase( syncGrammarRules, rootPhraseTree ):
    """
    Creates a paraphrase of rootPhraseTree, based on rules.
    Returns the paraphrase, which may contain CHOICE nodes.
    """
    paraphrases = _findMatchingRulesForChildRecursive( syncGrammarRules, rootPhraseTree )
    assert len(paraphrases)==1, "Even the root has created more than one paraphrase"
    rootParaphrase, rootParaphraseRuleCount = paraphrases[0] # get only paraphrase
    return rootParaphrase
    

def _findMatchingRulesForChildRecursive( rules, phraseTree, targetTreeNode=None ):
    """
    Just to get this working
    useOriginal: if True, the source sentence is a valid paraphrase
    """

    if PRINT_DEBUG and targetTreeNode: print "Target node: ", targetTreeNode
    useOriginal=True
    if targetTreeNode:
        if not (phraseTree.tag() == targetTreeNode.tag() ):
            #and phraseTree.dep() == targetTreeNode.dep() ): # TODO: want to consolidate use of dep()
            #raise SystemExit, "Can't use paraphrase transformation" 
            useOriginal=False
       
    matchingRules = [ r for r in rules if r.isSuitable(phraseTree, targetTreeNode) ]
    if PRINT_INFO: 
        print "INFO_rules\ttag %s\t%d rules\t%d instances" % (phraseTree.tag(),len(matchingRules), sum([r.count() for r in matchingRules]) )
        
    if PRINT_DEBUG:
        print "Current text: ", nodeText(phraseTree), "\tStructure: ", 
        printPhraseTreeStructure(phraseTree)
        #print phraseTree.pprint(margin=200)
        for r in matchingRules:
            print "Identified matching (dup=%s) rule (%dx): " % (r.isIdentical(),r.count()), r

    if useOriginal: 
        # check if matchingRules already as r.isIdentical()
        # if not, add a identical rule with count 0
        tmpRuleList = [ r for r in matchingRules if r.isIdentical() ]
        if len(tmpRuleList)==0:
            dupRule = SyncGrammarRule.createDuplicationRule(phraseTree)
            matchingRules.append(dupRule)
    
    possibleParaphraseTrees = []
    identicalRuleUsed = False
    for r in matchingRules:
        if r.isIdentical(): identicalRuleUsed = True
        
        try:
            paraphraseTree = createParaphraseTree(phraseTree, r, rules )
            possibleParaphraseTrees.append((paraphraseTree, r.count()))
        except NoGrammarPathError, e:
            pass # try next rule
        
    if len(possibleParaphraseTrees)==0:
        raise NoGrammarPathError, "No rules available"
    
    return possibleParaphraseTrees



def investigateFile( f, labelsPresent ):
    """
    Find paraphrases in file f and return
    a list of sync grammar rules
    """
    fullResultsList = []
    print "Processing file: ", f
    featuresDict = ExtractFeatures.extractFeaturesOfFile(f, labelsPresent=labelsPresent)
    sentences = featuresDict[kSentences]
    # highlights = featuresDict[kHilightSentences]
    highlights = ( featuresDict[kTitle], )
    print "Highlights: ", highlights
    hiTrees = [ createTree(h) for h in highlights ]
    print "Number of sentences: ", len(sentences), "\tNumber of highlights: ", len(highlights)
    
    # skip long files for now, just get some results
    if (len(sentences)>100): return []
    
    for s in sentences:
        try:
            sTree = createTree(s)
            for hi in hiTrees:
                results = syncGrammar( sTree, hi )
                fullResultsList.extend(results)
        except cPickle.UnpicklingError:
            # abandon this sentence, something wrong with parse look-up
            pass
    return fullResultsList

    

def nodeText(node):
    return " ".join(node.leaves())
    
def nodePhraseText(node):
    leaves = node.root.leaves()
    words = [leaves[i] for i in node._wordPos]
    return " ".join(words)
    
    
def topLevelPhrasesMatch(m):
    """
    Returns true if the two phrases have the same top level constituency
    """
    ph1, ph2 = m
    e1 = ph1.tag()[0]
    e2 = ph2.tag()[0]
    print "Phrase match\t%s\t-> %s\t%s\t-> %s" % (ph1.tag(), e1, ph1.tag(), e2), (e1==e2)
    if e1==e2: 
        return True
    elif e1=='V' and e2=='S':
        print "Letting this through"
        return True
    else: 
        return False
    
    
def syncGrammar( tree1, tree2 ):     
    if PRINT_DEBUG: print "Sentence: ", tree1.leaves()
    if PRINT_DEBUG: print "Highlight: ", tree2.leaves()
    phraseListTxt1 = tree1.getPhrases()
    phraseListHi1 = tree2.getPhrases()
    
    if PRINT_DEBUG:
        print "\nPhrase 1 nodes:"
        printAllPhraseInfo(phraseListTxt1)
        print "\nPhrase 2 nodes:"
        printAllPhraseInfo(phraseListHi1)
    
    matchList = []
    matchListNoStopList = []
    # Match phrases based on word content
    # Phrase contains tree and toks; phrase=ph.tree(), toks=ph.leaves()
    for phrase1 in phraseListTxt1:
        ph1 = phrase1.tree()
        for phrase2 in phraseListHi1:
            ph2 = phrase2.tree()
            if phrasesMatch(phrase1, phrase2): matchList.append((ph1,ph2))
            if phrasesMatch(phrase1, phrase2, stoplist=False): matchListNoStopList.append((ph1,ph2))
            
    # Link parent nodes together as well
    # including stop words
    matchList.extend(linkParentNodes(matchList, matchListNoStopList))

    # Link child nodes that may not be independent phrases
    # but which do have identical word content
    # Working with highlights rather than sentences
    # as it's more important to match all the phrases of the highlight
    # nodesAlreadyMatched = [ n2 for (n1,n2) in matchList ] 
    for (ph1, ph2) in matchList:
        if ph1.isLeaf() or ph2.isLeaf(): continue
        matchList.extend(linkIdenticalNodes(ph1,ph2,matchList))
        matchList.extend(linkIdenticalWords(ph1,ph2,matchList))
        
    if PRINT_DEBUG: printAllMatchListInfo(matchList)
    
    # Remove any rules that involve a change to top level phrase type
    # We think that the only rules worth learning keep the 
    # top level phrase element the same
    matchListRefined = [ m for m in matchList if topLevelPhrasesMatch(m) ]
    matchList = matchListRefined
    if PRINT_DEBUG:
        print
        print "After refining matchList so top levels match"
        printAllMatchListInfo(matchList)
        
            
    # Modifications in children of node?
    syncGrammarResults=[]
    if PRINT_DEBUG: print "\n\nLooking at deletions, insertions at node"
    for (ph1,ph2) in matchList:
        if (ph1.isLeaf() or ph2.isLeaf()): continue
        
        # if not nodeText(ph1)=="was going from the airport in Long Beach , California , to the Brown Field airport in San Diego": continue
        
        if True or PRINT_DEBUG: 
            print
            print "Phrase 1:", nodeText(ph1)
            print "Phrase 2:", nodeText(ph2)
        
        # tree underneath both nodes
        links = linkMatchingNodes(ph1, ph2, matchList)
        
        if PRINT_DEBUG:
            print
            print "List of matching nodes:"
            for l in links: print nodeText(l[0]), " --- ", nodeText(l[1])
        
        if False: # this was false, shouldn't find anything we haven't already got
            beforeNodeMatchingLinks = len(links)
            print "Before linking identical nodes: ", len(links)
            for l in links: print l
            print
            links.extend(linkIdenticalNodes(ph1, ph2, matchList))
            links.extend(linkIdenticalWords(ph1, ph2, matchList))
            if PRINT_DEBUG: print "After linking identical nodes: ", len(links)
            assert len(links)==beforeNodeMatchingLinks, "Found some extra links"
        
        # if single words are linked, then len(links)==0
        # we don't want this behaviour as it teaches us nothing about paraphrasing
        #assert len(links)>0, "Nothing linking underneath the tree:\n%s\n%s" %(nodeText(ph1),nodeText(ph2))
        if len(links)==0: continue
        try:
            try:
                assessSyncTreeQuality(ph1, ph2, links)
                synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,links,0)
                synctree2 = SyncGrammarTree.createFromPhraseTree(ph2,links,1, includeUnlinkedText=True)
            except ValueError:
                if PRINT_DEBUG: print "*** starting second pass with substitutions"
                assessSyncTreeQuality(ph1, ph2, links, maxSubstitutions=3) # If >0, allow unlinked text in source tree
                synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,links,0, includeUnlinkedText=True)
                synctree2 = SyncGrammarTree.createFromPhraseTree(ph2,links,1, includeUnlinkedText=True)
                if PRINT_DEBUG: print "*** second pass with substitutions completed"
                
            assert synctree1.matches(ph1), "Match failure"
            assert synctree2.matches(ph2), "Match failure"
            synctree2.checkAllLinked()
            
            if PRINT_DEBUG:
                print
                print "List of matching nodes:"
                for l in links: print l[0].treepos, nodeText(l[0]), " --- ", l[1].treepos, nodeText(l[1])
                print
                print "Rule:\t", synctree1, "\t", synctree2
                
            
            # check that all links in tree 2 are to be found in tree 1
            assert set(synctree2.links()).issubset(set(synctree1.links())), "Not all target links are present"
            
            syncGrammarResults.append( ( synctree1, synctree2 ) )

            if False: # print out the rules and examples
                # print "synctree1 is type", type(synctree1)
                print "Rule:\t", synctree1, "\t", synctree2
                print "Text:\t", nodeText(ph1), "\t", nodeText(ph2)
                # print "E.g.:\t", ph1, "\t;\t", ph2
                print
            if PRINT_RULE_APPLICATION:
                r = SyncGrammarRule(synctree1,synctree2)
                print "\nRule: \t", r
                print "Learnt from:\t", nodeText(ph1), "\t", nodeText(ph2)
                try:
                    paraphraseTree = createParaphraseTree(ph1, r, [] )
                    print "Applying rule to original phrase:"
                    print nodeText(ph1), "\t-->\t", nodeText(paraphraseTree)
                    # print paraphraseTree
                except NoGrammarPathError:
                    print "Cannot apply grammar rule to ", nodeText(ph1)
        except ValueError:
            if PRINT_DEBUG: print "Sync tree pair discarded"
            pass
        # raise SystemExit
            
        if False: graphvizTreePair(ph1, ph2, matchList)
        
    return syncGrammarResults


def graphvizTreePair(ph1, ph2, matchList):
    f = Config.GRAPHVIZ_DIR + "sync1.ps"
    txt=[]
    leafList=[]
    txtStart="digraph G { orientation=landscape;"
    # txtStart+='\ngraph [rankdir=TB, nodesep=0.25, ranksep=0.05, size="3,5!"];'
    txtEnd="}"
    txt.append(txtStart)
    txt.append("subgraph cluster_ph1 {  rankdir=TB;")
    PhraseDependencyTree.NODE_PREFIX = "S"
    txt.extend(PhraseDependencyTree._makeGraphvizDiagramFromTree( ph1, leafList ))
    txt.append("}")
    txt.append("subgraph cluster_ph2 {  rankdir=BT;")
    PhraseDependencyTree.NODE_PREFIX = "H"
    txt.extend(PhraseDependencyTree._makeGraphvizDiagramFromTree( ph2, leafList ))
    txt.append("}")
    for (m1,m2) in matchList:
        PhraseDependencyTree.NODE_PREFIX = "S"
        pos1 = PhraseDependencyTree.treePos(m1)
        PhraseDependencyTree.NODE_PREFIX = "H"
        pos2 = PhraseDependencyTree.treePos(m2)
        print "%s -- %s;" % (pos1,pos2)
        txt.append("%s -> %s [direction=both, style=dashed];" % (pos1,pos2))
    
    txt.append(txtEnd)
    PhraseDependencyTree.makeGraphvizDiagram( f, txt )
    #print txt
    



def findPartialMatches( matchList, highlightPhrases ):
    """
    try to find if highlight nodes have been partially matched to more than one original
    This method is not currently being used
    """
    for (ph2,tok2) in highlightPhrases:
        multipleNodeMatches = [ n1 for (n1,n2) in matchList if n2==ph2 ] 
        if (len(multipleNodeMatches)>1):
            print "Got more than one match"
            print nodeText(ph2)
            for n1 in multipleNodeMatches: 
                print nodeText(n1),
                print "Parent links as well? ", n1.parent in multipleNodeMatches
                if (n1.parent in multipleNodeMatches):
                    print "Parent: ", n1.parent
            print
            # TODO:
            # use the parent that matches
            # incorporate phrases from children in it
            # find a way to describe these rules
            # find a way to give to describeSyncTrees
    #raise SystemExit


def identifyDeletionsAtNode(n1, n2, matchList):
    l1 = len(n1)
    l2 = len(n2)
    assert l1 >= l2, "Insertions present rather than deletions"
    if (l1 > l2):
        print "Deletion occurred"
        print nodeText(n1), l1, nodeText(n2), l2 
        print "Original: ", n1
        print "Highlight: ", n2
        
        print "Children of original:"
        
        for ch1 in n1:
            print ch1, ch1.node
            try:
                findInMatchList(ch1,matchList)
            except ValueError:
                pass
        raise SystemExit, "Finished identifyDeletionsAtNode"
    
# this is probably of no use by itself
def getChildPOSList( treeNode ):
    return [ ch.node for ch in treeNode ]
    
    
def findInMatchList(node, matchList, offset=0):
    if PRINT_DEBUG: print "Trying to find a match for ", nodeText(node), "using offset ", offset
    foundMatches = []
    
    # identify all possible matches
    for match in matchList:
        # print "Possible match: ", match
        if node == match[offset]:
            if PRINT_DEBUG: print "Found one match: ", nodeText(match[0]), " --- ", nodeText(match[1])
            foundMatches.append(match)
    
    if True:
        # Try supplying all matches, and 
        # leave identifying the best match until later
        if len(foundMatches)==0: 
            if PRINT_DEBUG: print "No match found"
            raise ValueError, "No match found"
        else:
            return foundMatches
        
    # old version:
    
    if len(foundMatches)==0: 
        if PRINT_DEBUG: print "No match found"
        raise ValueError, "No match found"
    elif len(foundMatches)==1: return foundMatches[0] # only one found
    
    # need to find the best match
    # TODO: work out how to do this
    # currently choosing highest node
    matchedOffset = 0
    if offset==0: matchedOffset=1
    bestMatch = None
    bestMatchPositionLength = sys.maxint 
    for f in foundMatches:
        if len(f[matchedOffset].treeposition) < bestMatchPositionLength:
            bestMatch = f
            bestMatchPositionLength = len(bestMatch[matchedOffset].treeposition)
            if PRINT_DEBUG: print "Best match of multiple matches so far: ", nodeText(bestMatch[matchedOffset])
            #raise LookupError, "Where next?"
    return bestMatch
            
            
            
def makeListOfSourceNodes(srcTree, depth):
    """
    Makes a list of all source nodes in srcTree, up to depth.
    """
    if depth <= 0: return []
    srcNodeList = [ ch for ch in srcTree ]
    for ch in srcTree:
        if ch.isLeaf(): continue
        elif ch.dep() == PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT: 
            srcNodeList.extend(makeListOfSourceNodes(ch,depth))
        else: 
            srcNodeList.extend(makeListOfSourceNodes(ch,depth-1))
    return srcNodeList
    
    
    
def linkMatchingNodes(srcTree, destTree, matchList):
    """
    Returns a subset of the matchList 
    so that every child of destTree is linked (if possible)
    to children or grandchildren of srcTree
    """
    srcNodeList = makeListOfSourceNodes(srcTree,2)
    if PRINT_DEBUG:
        print "In linkMatchingNodes, results of makeListOfSourceNodes():" 
        for ch in srcNodeList:
            print ch.treeposition, nodeText(ch)
        print

    # refine the full match list to include
    # only those nodes in srcTree
    refinedMatchList = [ m for m in matchList if m[0] in srcNodeList ]

    destNodeList = makeListOfSourceNodes(destTree,2)
    matchNodeList = []
    for ch in destNodeList:
        if PRINT_DEBUG: print "Finding match for ", nodeText(ch)
        try:
            match = findInMatchList(ch, refinedMatchList, offset=1)
            # matchNodeList.append( (match[0],match[1]) )
            # matchNodeList.append( match ) # if guaranteed of only one match
            matchNodeList.extend( match ) # for list of matches
        except ValueError:
            pass
        
    # remove duplicated nodes from src and dest matches, so that
    # there can only be 1-1 matches
    matchedSrcNodes = set()
    matchedDstNodes = set()
    matchNodeListNoDuplicates = []
    for m in matchNodeList:
        if m[0].treepos not in matchedSrcNodes and m[1].treepos not in matchedDstNodes:
            matchedSrcNodes.add(m[0].treepos)
            matchedDstNodes.add(m[1].treepos)
            matchNodeListNoDuplicates.append(m)
    
    if PRINT_DEBUG:
        print
        print "In linkMatchingNodes, results of refinedMatchList:" 
        for m in refinedMatchList:
            print m[0].treepos, nodeText(m[0]), " --- ", m[1].treepos, nodeText(m[1])
        print "\nIn linkMatchingNodes, results of matchNodeList:" 
        for m in matchNodeList:
            print m[0].treepos, nodeText(m[0]), " --- ", m[1].treepos, nodeText(m[1])
        print
        print "\nIn linkMatchingNodes, results of matchNodeListNoDuplicates:" 
        for m in matchNodeListNoDuplicates:
            print m[0].treepos, nodeText(m[0]), " --- ", m[1].treepos, nodeText(m[1])
        print
        
        #if nodeText(srcTree)=="Some countries , including Britain and France ,":
        #    raise SystemExit,"Enough for now"
            
    return matchNodeListNoDuplicates


def linkIdenticalNodes(n1, n2, matchList):
    """
    Matches nodes in the two trees that are exactly equivalent.
    @return Pair of matched nodes
    """
    ch1List = [ (ch,repr(ch)) for ch in n1]
    ch2List = [ (ch,repr(ch)) for ch in n2]
    matching = [ (ch1,ch2) for (ch1,txt1) in ch1List for (ch2,txt2) in ch2List 
        if txt1==txt2 and (ch1,ch2) not in matchList ]
    return matching
                
def linkIdenticalWords(n1, n2, matchList):
    """
    Matches nodes in the two trees where the words match, even if the node labels do not.
    Using wordsMatch which includes stemming.
    @return Pair of matched nodes
    """
    assert not n1.isLeaf(), "Original sentence node is a single leaf"
    assert not n2.isLeaf(), "Highlight sentence node is a single leaf"
    ch1List = [ (ch,nodeText(ch)) for ch in n1]
    ch2List = [ (ch,nodeText(ch)) for ch in n2]
    if False and PRINT_DEBUG:
        print "ch1"
        for ch in ch1List: print ch[1] 
        print "ch2"
        for ch in ch2List: print ch[1] 
    matching = [ (ch1,ch2) for (ch1,txt1) in ch1List for (ch2,txt2) in ch2List 
        if (ch1,ch2) not in matchList and wordsMatch(txt1,txt2) ]
    return matching
                
                
def linkParentNodes(matchList, matchListNoStopList, maxDepth = 1):
    """
    Considers pairs of matched nodes in the match list.
    If two nodes have the same parent, then this parent
    is matched to the ancestor of the corresponding
    highlight nodes.
    """
    matchingParentNodes=[]
    if PRINT_DEBUG: print "\nInvestigating node distances"
    for i, (s1, h1) in enumerate(matchListNoStopList):
        for (s2, h2) in matchListNoStopList[i+1:]:
            d = nodeDistance(s1, s2)
            if d<=maxDepth:
                ca1 = s1.root[commonAncestor(s1, s2)]
                ca2 = h1.root[commonAncestor(h1, h2)]
                if (ca1,ca2) in matchList: continue
                if (ca1,ca2) in matchingParentNodes: continue
                if PRINT_DEBUG: 
                    print
                    print "Original:  ", nodeText(s1), " --- ", nodeText(s2), d
                    print "Highlight: ", nodeText(h1), " --- ", nodeText(h2), nodeDistance(h1,h2)
                    print "Ancestors in match list? ", (ca1,ca2) in matchList
                    print "Original parent phrase: ", nodeText(ca1)
                    print "Highlight parent phrase:", nodeText(ca2)
                
                matchingParentNodes.append( (ca1, ca2) )
    return matchingParentNodes



SUBSTITUTE_TOKENS = ['.',',',':',';','``',"''",'RB','TO','CC','EX']
def assessSyncTreeQuality(ph1, ph2, links, maxSubstitutions=0):
    """
    Assess quality sync tree,
    and raise ValueError if we don't want to keep this rule.
    Returns the number of word substitutions that will be required 
    """
    substitutionsSoFar=0
    linkedPh2 = [ l2 for (l1,l2) in links ]
    # good tree: must have all links for children in highlight
    for ch in ph2:
        if ch in linkedPh2: continue
        elif not ch.isLeaf() and ch.node in SUBSTITUTE_TOKENS: continue
        elif substitutionsSoFar < maxSubstitutions: 
            if ch.isLeaf():
                substitutionsSoFar += len(ch.leaves())
            else:
                substitutionsSoFar += assessSyncTreeQuality(ph1, ch, links, maxSubstitutions=maxSubstitutions-substitutionsSoFar)
                # for gch in ch:
                #    print "Need to count unlinked child: ", gch
                #    # if isinstance(gch, PhraseDependencyTree.PhraseDependencyTree) and not gch.isLeaf():
        else:
            if PRINT_DEBUG: 
                print "******** to be discarded: %s *********" % nodeText(ch)
            print "Match discarded after ", substitutionsSoFar, "substitutions"
            raise ValueError, "Rule tree quality too low"
    return substitutionsSoFar
    
    
def describeSyncTrees(ph1, ph2, links):
    """
    Describe the grammar structure of the subtree at ph1, 
    the subtreee at ph2,
    and the links between them
    @return: Possibly a string, or a more complex tree structure
    """
    s1 = describeTreeWithLinks(ph1, links, offset=0)
    s2 = describeTreeWithLinks(ph2, links, offset=1)
    if PRINT_DEBUG: print "Original:  ", s1
    if PRINT_DEBUG: print "Highlight: ", s2
    return (s1, s2)
    
def describeTreeWithLinks(tree, links, offset=0):
    # print "Top level node: ", tree.node
    linkedNodes = [l[offset] for l in links]
    s = "%s/%s -> " % (tree.node, tree._rel)
    for ch in tree:
        linkPos = 0
        if ch in linkedNodes: linkPos = linkedNodes.index(ch)+1
        s += "%s/%s#%d " % (ch.node, ch._rel, linkPos)
        
        # link grandchildren
        linkedGrandChildren = [gch for gch in ch if gch in linkedNodes]
        if len(linkedGrandChildren)>0: 
            s += "[ "
            for gch in ch:
                linkPos = 0
                if gch in linkedGrandChildren: 
                    linkPos = linkedNodes.index(gch)+1
                s += "%s/%s#%d " % (gch.node, gch._rel, linkPos)
            s += "] "
    return s

def describeTreeProductions(tree, links, offset=0):
    """
    Write out the PCFG node productions
    """
    s = "%s ->" % tree.node
    for ch in tree:
        s += " %s" % ch.node
    return s

def equivalentNodes( n1, n2 ):
    return n1.__repr__() == n2.__repr__()


def nodeDistance(n1, n2):
    ca = commonAncestor( n1, n2)
    root = n1.root
    n1pos = n1.treeposition
    n2pos = n2.treeposition
    
    if False and PRINT_DEBUG:
        print
        print "ca.treeposition: ", ca, n1.root[ca].tag(), n1.root[ca].dep(), n1.root[ca].leaves()
        print "n1.treeposition: ", n1.treeposition, n1.tag(), n1.dep(), n1.leaves()
        print "n2.treeposition: ", n2.treeposition
    
    # Don't count tree layers marked "fixed"
    # We want dependency depth, not phrase structure depth
    n1depth = len(n1pos)-len(ca)
    for i in range( len(ca), len(n1pos) ):
        if root[n1pos[:i+1]].dep() == PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT:
            n1depth -= 1
        
    n2depth = len(n2pos)-len(ca)
    for i in range( len(ca), len(n2pos) ):
        if root[n2pos[:i+1]].dep() == PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT:
            n2depth -= 1

    distance = max(n1depth,n2depth)
    return distance


def commonAncestor(n1, n2): 
    """ 
    @return: The tree position of the lowest descendant of this 
    tree that dominates the two nodes. 
    """ 
    assert n1.root == n2.root, "Unrelated nodes"
    
    # Find the tree positions of the start & end leaves, and 
    # take the longest common subsequence. 
    start_treepos = n1.treeposition
    end_treepos = n2.treeposition
    
    # Find the first index where they mismatch: 
    for i in range(len(start_treepos)): 
        if i == len(end_treepos) or start_treepos[i] != end_treepos[i]: 
            return start_treepos[:i] 
    return start_treepos         


def createParserTreeDiagrams(sl_ca):
    for i, s in enumerate(sl_ca):
        tree = createTree( s )
        fc=graphvizDir + "dc%d.%s" % (i,FORMAT) 
        # print tree
        PhraseDependencyTree.makeGraphvizDiagramFromTree(fc,tree[0])


        phraseList = tree.getPhrases()
        print "Independent phrase list:"
        for i in phraseList:
            print i[0].node, i[0]._rel, i[0]._wordPos, i[1]
            # ExtractPhraseFeatures.processPhrase(i[1])





def createTree( s, doc=None, min_phrase_size=MIN_PHRASE_SIZE ):
        assert not doc==None, "No document, don't know which parser cache to use"
        pennParser = POSTagger.StanfordPennParser(doc)
        dpParser = POSTagger.StanfordDependencyParser(doc)
        tree = pennParser.parse(s) 
        dg=dpParser.parseToDepGraph(s)
        #dotTxt = dg.createGraphviz()
        #fdg=graphvizDir + "dg%d.%s" % (i,FORMAT)  
        #PhraseDependencyTree.makeGraphvizDiagram(fdg, dotTxt)
        
        tree.addDependencies(dg)
        #fdl=graphvizDir + "dgl%d.%s" % (i,FORMAT)  
        # print tree
        #PhraseDependencyTree.makeGraphvizDiagramFromTree(fdl,tree[0])
                
        
        if PRINT_DEBUG: print "Marking independent phrases: ", min_phrase_size
        tree.markIndependentPhrase(min_phrase_size)
        # tree.collapseFixedLinks()
        #tree.collapseIntoPhrases()
        #tree.collapseFixedLinks()
        return tree




MATCH_STOP_TAGS = set(('.',',','IN','DT','TO'))
def phrasesMatch( n1, n2, stoplist=True ):
    """
    Returns True if the phrases match.
    Currently removes case information and looks for identity match.
    TODO: cope with lists of words, remove stop words and check content words
    """
    assert type(n1)==PhraseDependencyTree.Phrase, "Phrase not correct type"
    assert type(n2)==PhraseDependencyTree.Phrase, "Phrase not correct type"
    tree1 = n1.tree()
    tree2 = n2.tree()
    tok1List = [tree1.root.pos()[i] for i in tree1._wordPos]
    tok2List = [tree2.root.pos()[i] for i in tree2._wordPos]
    for (t1,tag1) in tok1List:
        if stoplist and (tag1 in MATCH_STOP_TAGS): continue
        for (t2,tag2) in tok2List:
            if wordsMatch(t1,t2):
                # print t1, " matches ", t2 
                return True
    return False

def wordsMatch( w1, w2 ):
    return NltkUtils.stem(w1)==NltkUtils.stem(w2)

def printPhraseTreeStructure( phraseTree ):
    print "%s/%s" % (phraseTree.tag(), phraseTree.dep()), 
    print "(",
    for ch in phraseTree:
        print "%s/%s" % (ch.tag(), ch.dep()), 
    print ")"
    
def printAllPhraseInfo( phraseList ):
    for node in phraseList: 
        print node.tree().tag(), "/", node.tree().dep(), node.leaves()

def printAllMatchListInfo( matchList ):
    print "\nMatch list:"
    for (ph1,ph2) in matchList: 
        print nodeText(ph1), " --- ", nodeText(ph2)
    print

def printRulesAndExamples( resultsList ):
    raise NotImplementedError, "Not working with just sync trees"
    for r in resultsList:
        (ph1, st1, ph2, st2, links) = r
        #if "#0" in st2: print "***** Avoid this one:" # Some #0 are OK, if we learn the word to be inserted
        if nodeText(ph1)==nodeText(ph2): continue # don't print out identical phrases, although we might want them for statistics later
        if st1==st2: continue # no transform, even though some child phrase changed
        print nodeText(ph1), "\t", nodeText(ph2)
        print st1, "\t", st2
        print
    
def printRules( resultsList ):
    """ We expect a list of source and target trees """
    for (rs,rt) in resultsList:
        print rs, "\t", rt
        
def printRuleSet( resultsList ):
    """ Print out a set of rules, involving rule objects """
    for r in resultsList:
        print r
    
def printResultsListInfo( fullResultsList ):
    print "Count of rules: \t\t", len(fullResultsList)
    modificationRules = [(n1,n2) for (n1,n2) in fullResultsList
        if not str(n1)==str(n2)]
    #for (n1,st1,n2,st2) in modificationRules: print st1,st2
    print "Count of modification rules: \t", len(modificationRules)
    print "Count of no-change rules: \t", len(fullResultsList)-len(modificationRules)
    
    print "\nPCFG synchronized phrases:"
    fdist = nltk.probability.FreqDist((n1._node,n2._node) for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    print "\nPCFG synchronized phrases, modifications only:"
    fdist = nltk.probability.FreqDist((n1._node,n2._node) for (n1,n2) in modificationRules)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    # stop here for now
    return
    
    print "\nDep parser synchronized phrases:"
    fdist = nltk.probability.FreqDist((n1._dep,n2._dep) for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    print "\nPCFG productions for all rules:"
    fdist = nltk.probability.FreqDist(
        (n1.productions()[0],n2.productions()[0]) 
        for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v

    print "\nPCFG productions for modification rules:"
    fdist = nltk.probability.FreqDist(
        (n1.productions()[0],n2.productions()[0]) 
        for (n1,n2) in modificationRules)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v

    print "\nPCFG productions for modification rules using my production code:"
    fdist = nltk.probability.FreqDist(
        (describeTreeProductions(n1,[]),describeTreeProductions(n2,[]))
        for (n1,n2) in modificationRules)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v

    print "\nPCFG productions for full rules using my production code:"
    fdist = nltk.probability.FreqDist(
        (describeTreeProductions(n1,[]),describeTreeProductions(n2,[]))
        for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v



def _removeDuplicateQSGRules( syncGrammarPairs ):
    """
    Create a list of SyncGrammarRule from pairs of trees.
    Each rule should appear only once, with a count of 
    instances found in the training data
    """    
    syncGrammarDict = dict() # temporary store
    for (n1,n2) in syncGrammarPairs:
        r = SyncGrammarRule(n1,n2)
        k = r.key() # need string representation, not actual object
        if k in syncGrammarDict: 
            syncGrammarDict[k].inc()
            if False and PRINT_DEBUG: print k, "already in dictionary ", syncGrammarDict[k].count()
        else:
            syncGrammarDict[k] = r
    return syncGrammarDict.values()


QSGRulesPickleFile = Config.SHELF_BASE_DIR + "syncrules.pickle"
#QSGRulesPickleFile = Config.SHELF_BASE_DIR + "syncrules-gromit500.pickle"
def saveQSGRules( rules ):
    _pickleRules( rules, QSGRulesPickleFile )
    
def loadQSGRules():
    return _unpickleRules(QSGRulesPickleFile)

VerbFrameRulesPickleFile = Config.SHELF_BASE_DIR + "verbframerules.pickle"
#VerbFrameRulesPickleFile = Config.SHELF_BASE_DIR + "verbframerules_consolidated.pickle"
def saveVerbFrameRules( rules ):
    _pickleRules( rules, VerbFrameRulesPickleFile )
def loadVerbFrameRules():
    return _unpickleRules(VerbFrameRulesPickleFile)

def _pickleRules( rules, filename ):
    """
    Save as pickle file for later analysis
    """
    pkl_file = open(filename, 'w')
    print "Saving to: ", filename
    pickle.dump(rules, pkl_file)
    pkl_file.flush()
    pkl_file.close()
    
def _unpickleRules(filename):
    """
    Read in rules from pickle file
    """
    print "Loading rules from: ", filename
    pkl_file = open(filename, 'r')
    rules = pickle.load(pkl_file)
    pkl_file.close()
    return rules




def createQSGFromDirectory():
    """
    Creates the quasi sync grammar rules.
    Will load the pickled ruleset if present.
    Otherwise it will create a new ruleset from the working directory.
    """
    try:
        qsgRules = loadQSGRules()
    except IOError:
        ExtractFeatures.buildCorpusFreqDist()
        ExtractFeatures.setFeaturesCache()
        # normal dirs
        # directory = Config.TRAINING_DOCS_DIR
        # filePattern = '*.doc.txt'

        # duc 03
        directory = Config.DUC03_OUTPUT_DIR
        filePattern = '*'
        fileCount=0
        FILE_COUNT_LIMIT = 5000
        qsgRulesFullSet=[]

        allFiles = ListFiles.listAllFiles( filePattern, directory )
        for f in allFiles:
            try:
                if (fileCount > FILE_COUNT_LIMIT): break
                print "(%d)\tProcessing file %s" % (fileCount, f)
                results = investigateFile( f, True )
                printRules(results)
                # printRulesAndExamples(results)
                qsgRulesFullSet.extend(results)
                fileCount += 1
            except KeyError: 
                continue
        
        qsgRules = _removeDuplicateQSGRules(qsgRulesFullSet)
        print "\n\n====================================\n"
        print "All sentences are now processed, #rules",len(qsgRulesFullSet)
        printRuleSet(qsgRules)
        # save results for working on later
        saveQSGRules(qsgRules)
        
    if False: # print out information
        print "Sync grammar generation completed"
        printResultsListInfo( qsgRules )
    return qsgRules
    


def createParaphraseTree(srcPhraseTree, rule, allRules):
    """
    Create a paraphrase
    Rewrite the phrase tree according to the srcSync and targetSync rule.
    Returns a PhraseDependencyTree
    """
    
    # special handling for choice nodes
    if isinstance(srcPhraseTree, PhraseTreeChoice):
        return createParaphraseTreeFromChoice(srcPhraseTree, allRules)
        
    srcSync = rule._source
    targetSync = rule._target
    assert srcSync.matches(srcPhraseTree), "Sync grammar not suitable for this phrase tree node"
    assert isinstance(srcPhraseTree, PhraseDependencyTree.PhraseDependencyTree), "Cannot create a paraphrase tree from %s" % srcPhraseTree
    assert not srcPhraseTree.isLeaf(), "Rule called on leaf"
    if isinstance(srcPhraseTree, PhraseTreeChoice):
        assert srcPhraseTree.tag()==PhraseTreeChoice.TAG, "Misnamed choice node %s" % srcPhraseTree
    assert not isinstance(srcPhraseTree, PhraseTreeChoice), "Trying to paraphrase an already existing choice \n%s" % srcPhraseTree

    targetPhraseTree = PhraseDependencyTree.PhraseDependencyTree("( %s )"%srcPhraseTree.node)
    targetPhraseTree.copyAttributes(srcPhraseTree)
    
    if PRINT_DEBUG: 
        print "Source phrs tree: ", srcPhraseTree
        print "Source sync tree: ", srcSync
        print "Target sync tree: ", targetSync
        
    if PRINT_DEBUG:
        print "In createParaphraseTree, before working through children"
        print "Created target phrase ", targetPhraseTree.leaves(), targetPhraseTree.tag(),targetPhraseTree.dep(), " with wordpos ", targetPhraseTree._wordPos
        print "...from source phrase ", srcPhraseTree.leaves(), srcPhraseTree.tag(), srcPhraseTree.dep(), " with wordpos ", srcPhraseTree._wordPos
        if len(targetPhraseTree)>0:
            tdbg = targetPhraseTree[0]
            print "and...", tdbg.treepos, tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
        print 
        
    if PRINT_DEBUG: print "targetSync = ", targetSync
    
    
    _createParaphraseTreeChildren(srcSync, targetSync, srcPhraseTree, targetPhraseTree, allRules)
    
    if PRINT_DEBUG:
        print "Created target phrase ", targetPhraseTree.leaves(), targetPhraseTree.dep(), " with wordpos ", targetPhraseTree._wordPos
        print "...from source phrase ", srcPhraseTree.leaves(), srcPhraseTree.dep(), " with wordpos ", srcPhraseTree._wordPos
        
        if len(targetPhraseTree)>0:
            tdbg = targetPhraseTree[0]
            print "and...", tdbg.treepos, tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
        print 
        
    return targetPhraseTree



def _createParaphraseTreeChildren(srcSync, targetSync, srcPhraseTree, targetPhraseTree, allRules):
    for ch in targetSync.children():
        if PRINT_DEBUG:
            print "First go: child=", ch, " at linked pos ",ch._linknum,"\t\t",
            try:
                print "Links to ", srcSync.findLink(ch._linknum)
            except LookupError:
                print "No link"
        try:
            position = srcSync.findLink(ch._linknum)
            if PRINT_DEBUG: print "Target ", ch, "at", ch._linknum, "\t\tlinked to source ", position
            if srcPhraseTree[position].isLeaf():
                # just do deep copy and don't apply any more rules
                copiedNode = srcPhraseTree[position].copy(deep=True)
                # print "Leaf copy. Original wordPos", srcPhraseTree[position]._wordPos, " Copied ", copiedNode._wordPos, srcPhraseTree[position].isFixed()
                targetPhraseTree.append(copiedNode)
            else:
                if PRINT_DEBUG:
                    print "Link number: ", ch._linknum
                    print "Linked to position: ", position
                    print "srcPhraseTree: ", srcPhraseTree[position]
                # TODO: may need to apply another rule here if transform is required
                copiedNodeList = _findMatchingRulesForChildRecursive( allRules, srcPhraseTree[position], ch )
                # print "*** tree copy. Original wordPos", srcPhraseTree[position]._wordPos, srcPhraseTree[position].isFixed(), " Copied ", copiedNodeList[0][0]._wordPos
                assert len(copiedNodeList)>0, "No paraphrase generated"
                
                # Get all the leaf positions in this paraphrase
                # May need special function to just get the fixed node positions
                for paraphrase, count in copiedNodeList:
                    if False and PRINT_DEBUG:
                        print "\n\nParaphrase: "
                        print paraphrase.tag(), paraphrase.dep(), paraphrase._wordPos, paraphrase
                        for chDbg in paraphrase: print chDbg.tag(), chDbg.dep(), "Fxd",chDbg.isFixed(), " Ind",chDbg.isIndependentPhrase()
                        srcDbg = srcPhraseTree[position]
                        print "of source: ", srcDbg.tag(), srcDbg.dep(), srcDbg._wordPos, srcDbg
                        for chDbg in srcDbg: print chDbg.tag(), chDbg.dep(), "Fxd",chDbg.isFixed(), " Ind",chDbg.isIndependentPhrase()
                    newPosList=[]
                    for ch in paraphrase:
                        if not ch.isIndependentPhrase(): # was ch.isFixed()
                            newPosList.extend(ch._wordPos)
                    paraphrase._wordPos = newPosList
                    
                    if PRINT_DEBUG:
                        print "Paraphrase: ", paraphrase.leaves(), paraphrase.dep(), "\twordpos:", paraphrase._wordPos
                        print paraphrase
                        print
                    
                if len(copiedNodeList)==1:
                    # just put in single choice
                    targetPhraseTree.append(copiedNodeList[0][0])
                    assert targetPhraseTree[-1]._indPhrase==srcPhraseTree[position]._indPhrase, "Independent phrase flag not copied"
                else:
                    node = PhraseTreeChoice.create(copiedNodeList)
                    targetPhraseTree.append(node)

        except LookupError, e:
            # Add in the text from the target sync grammar
            if PRINT_DEBUG: 
                print "Unlinked child (%s %s)" % (ch._node, ch._text)
                print "Number of children:", len(ch.children()), ch.hasChildren()
            
            if ch.hasChildren():
                parseString = "(%s)" % (ch._node)
                targetChild = PhraseDependencyTree.PhraseDependencyTree(parseString)
                targetChild._rel = ch._dep
                targetChild._fixed = True
                if PRINT_DEBUG: print "Current target:", targetChild
                _createParaphraseTreeChildren(srcSync, ch, srcPhraseTree, targetChild, allRules)
                if PRINT_DEBUG: print "Target child after paraphrase:", targetChild
                targetPhraseTree.append(targetChild)
                
            else:
                assert ch._text is not None, "Unlinked target phrase has no structure and no text"
                parseString = "(%s %s)" % (ch._node, ch._text)
                fixedTextChild = PhraseDependencyTree.PhraseDependencyTree(parseString)
                fixedTextChild._rel = ch._dep
                fixedTextChild._fixed = True
                fixedTextChild._wordPos = [-1] # a dummy value to get the word count correct
                targetPhraseTree.append(fixedTextChild)
    


def createParaphraseTreeFromChoice(srcPhraseTree, allRules):
    """
    Create a paraphrase from a PhraseTreeChoice tree.
    There are no rewrites.
    Instead, we just make a copy of all children, allowing rewrite rules further down.
    Returns a PhraseDependencyTree
    """
    assert isinstance(srcPhraseTree, PhraseTreeChoice), "Cannot create a paraphrase choice tree from %s" % srcPhraseTree
    assert srcPhraseTree.tag() == PhraseTreeChoice.TAG, "Tag not correctly set up %s" % srcPhraseTree.tag()

    # create copies of children
    childrenForTarget = []
    for ch in srcPhraseTree:
        dupRule = SyncGrammarRule.createDuplicationRule(ch)
        targetChParaphrases = createParaphraseTree( ch, dupRule, allRules)
        childrenForTarget.append( targetChParaphrases )
        
    assert len(childrenForTarget) == len(srcPhraseTree.counts()), \
        "Not got the correct number of children (%d) and counts (%d)" \
        % (len(childrenForTarget),len(srcPhraseTree.counts()))
    choiceList = zip(childrenForTarget, srcPhraseTree.counts())
    targetPhraseTree = PhraseTreeChoice.create(choiceList)
    
    return targetPhraseTree



class VerbFrameRule(object):
    """
    A rule describes the mandatory dependency elements
    in a sentence, as seen somewhere in the corpus.
    """
    
    # The dependency types where we need to match the words as well
    DEP_WORD_MATCH_LIST = [ 'aux', 'auxpass', 'prt' ]

    def __init__(self, verbToken, sourceTree, count=1):
        """
        Initialise this rule, based on the verb word and the phrase tree where it occurs
        """
        assert not sourceTree.isLeaf(), \
            "Trying to make verb frame from phrase with no dependents"
        self._nodeTag = sourceTree.tag()
        self._nodeDep = sourceTree.dep()
        self._verb = verbToken
        deplist = []
        for ch in sourceTree:
            deplist.append( self.encodeChild(ch) )
        self._deps = set(deplist)
        self._count = count

    def __str__(self):
        """
        String representation of this rule
        """
        s = self._verb + "\t"
        s += self._nodeTag + "/" + self._nodeDep + " ( "
        for d in self._deps:
            s += d + " "
        s += ") "
        return s

    def __eq__(self, other):
        if PRINT_DEBUG:
            print "This: ", str(self)
            print "Other: ", str(other)
        if (    self._nodeTag == other._nodeTag
            and self._nodeDep == other._nodeDep
            and self._deps == other._deps ):
            return True
        return False
    
    def matchesRule(self, other):
        """
        This mirrors the matches() method, where we ignore the dep of the rule
        """
        if PRINT_DEBUG:
            print "This: ", str(self)
            print "Other: ", str(other)
        if (    self._nodeTag == other._nodeTag
            and self._deps == other._deps ):
            return True
        return False
    
    def inc(self, extra=1):
        """
        Increments the number of times this rule has been seen.
        """
        self._count += extra

    def count(self):
        """
        Returns the number of times this rule has been seen.
        """
        return self._count
        
    @classmethod    
    def encodeChild(cls, ch):
        """
        Returns a representation of a child node as a string
        """
        if ch.dep() in cls.DEP_WORD_MATCH_LIST:
            if nodeText(ch).count(" ")>0: raise ValueError, "%s is not a single word" % nodeText(ch)
            s = "%s/%s/%s" % (ch.tag(), ch.dep(), nodeText(ch))
        else:
            s = "%s/%s" % (ch.tag(), ch.dep())
        return s
    
        
        
    def matches(self, phraseTree):
        """
        Checks if this rule can be applied to the phrase tree.
        The phrase must have all the dependencies in the rule,
        but others can be present.
        """
        # Don't use dep for now
        #if not (self._nodeTag == phraseTree.tag()
        #    and self._nodeDep == phraseTree.dep()):
        #    return False
        
        if not (self._nodeTag == phraseTree.tag()): 
            return False
            
        for dep in self._deps:
            matchingDepInPhrase = False
            for ch in phraseTree:
                if self.encodeChild(ch) == dep:
                    matchingDepInPhrase = True
                    break
            if not matchingDepInPhrase:
                if PRINT_DEBUG: print "Cannot find matching ", dep
                return False
        return True
        

def _debug_checkChoiceTags(tree):
    if isinstance(tree, PhraseTreeChoice):
        assert tree.tag() == PhraseTreeChoice.TAG, "Tag not correctly set up %s - %s" % (tree.tag(), tree.treepos)
    
    if not tree.isLeaf():
        for ch in tree:
            _debug_checkChoiceTags(ch)
    return True
    

from features import ExtractFeatures, ExtractPhraseFeatures
import shelve
from config import Shelves
import summarize.IP
from tasks import CNNCaptionsFilelist

def investigateMakingIPHighlight():
    print "Getting QSG rules"
    syncGrammarRules = createQSGFromDirectory()

    ExtractFeatures.buildCorpusFreqDist()
    ExtractFeatures.setFeaturesCache()
    svmCache = shelve.open(Shelves.SVM)
    label = 3

    if False: # for CNN highlights
        labelsPresent = True
        svm = svmCache["Phrase"]
        # make sure phrase tfidf set is being used
        print "Getting verb frame rules"
        verbDict = createVerbFrameRules()

    elif True: # for CNN captions
        svm = svmCache["CNN captions, phrases"] # trained on training set using overlap, phrase-based
        labelsPresent = False
        # make sure phrase tfidf set is being used
        verbDict = {} # to make the runtime shorter, not load verb templates for now
        # verbDict = createVerbFrameRules()
        
    elif False: # for DUC04 headlines
        svm = svmCache["DUC03, headlines, phrases, all"] # trained on DUC03
        labelsPresent = False
        # make sure phrase tfidf set is being used
        verbDict = {} # to make the runtime shorter, not load verb templates for now


        
    #for testFile in CNNAssessmentFiles.filelistIter():
    print "Starting on file list"
    #for testFile in CNNCaptionsFilelist.filelistIter():
    for testFile in BBCCaptionFilelist.filelist():
    #for testFile in DUC04Filelist.filelist():
        # skip this file if it has already been processed
        if False:
            if os.path.exists(Config.HLIGHTS_OUTPUT_DIR + os.path.basename(testFile)):
                print Config.HLIGHTS_OUTPUT_DIR + os.path.basename(testFile)
                print "Already done this file"
                continue

    
            
        try:
            print "Current file: ", testFile
            filePhraseList = []
            fileSentenceTrees = []
            filefd = ExtractFeatures.extractFeaturesOfFile(testFile, labelsPresent)
            topWords=filefd[kTfidfTopWords]
            taggedTitle=filefd[kTaggedTitle]
                  
            print "Number of sentences: ", filefd[kSentenceCount]
            for i in range(filefd[kSentenceCount]):
                # if not i==10: continue
                sTxt = filefd[kSentences][i]
                sfd  = filefd[kSentenceFeatureList][i]
                if PRINT_DEBUG: print "Original sentence:", sTxt
                
                tree = createTree(sTxt, min_phrase_size=POSTagger.PhraseDependencyTree.USE_CONSTITUENCY_STRUCTURE)
                #tree = ExtractPhraseFeatures.makePhraseTree(sTxt, min_phrase_size=POSTagger.PhraseDependencyTree.USE_CONSTITUENCY_STRUCTURE)
                if PRINT_DEBUG: print "Trees created"
                
                # Apply verb frames
                if False:
                    tree = createVFParaphraseTree(tree, verbDict)
                    assert _debug_checkChoiceTags(tree), "Contains wrongly tagged PhraseTreeChoice nodes\n%s" % tree
                    
                # Apply QSG rules
                if True:
                    rootParaphrase = createQSGParaphrase( syncGrammarRules, tree )
                    assert _debug_checkChoiceTags(tree), "Contains wrongly tagged PhraseTreeChoice nodes\n%s" % tree
                else:
                    rootParaphrase = tree
                    
                fileSentenceTrees.append(rootParaphrase)
                
                if PRINT_DEBUG: print "paraphrase: ", rootParaphrase
                if False: # debug why wordpos has extra entries
                    print "After createQSGParaphrase()"
                    tdbg = rootParaphrase
                    print "***: ", tdbg.treepos, tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
                    tdbg = rootParaphrase[0]
                    print "***: ", tdbg.treepos, tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
                    tdbg = rootParaphrase[0,0]
                    print "***: ", tdbg.treepos, tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
                    print 
                    raise NotImplementedError, "Need to get ph_node._wordPos sorted (get rid of duplicates, indep children)"
                    
                    
                # Process each phrase to get scores and features
                phraseList = rootParaphrase.getPhrases()
                #print "\nPhrases from paraphrase tree", len(phraseList)
                for (ph_node, ph_txt) in phraseList:
                    ph_fd={}
                    ph_tokenPos = ph_node._wordPos # it's complicated. wordPos can look up words previously in sentence, but doesn't describe the length of the phrase any more
                    if PRINT_DEBUG: print "***: ", ph_node.leaves(), ph_tokenPos, ph_node.dep(), "\tInd:",ph_node.isIndependentPhrase()
                    notIndepLeaves = [ l for ch in ph_node if isinstance(ch,nltk.tree.Tree) and not ch.isIndependentPhrase() for l in ch.leaves()]
                    if PRINT_DEBUG:
                        print ph_node
                        print "~IN: ", notIndepLeaves 
                        print 
                    if PRINT_DEBUG: print "Processing phrase"
                    ExtractPhraseFeatures.processPhrase(ph_fd, sTxt, sfd, ph_tokenPos, topWords, taggedTitle)
                    if PRINT_DEBUG: print "Processing image tags"
                    ExtractPhraseFeatures.processPhraseImageTags( ph_fd, filefd[kImageTags], ph_tokenPos, sTxt )
                    #ExtractPhraseFeatures.processPhraseImageTagsWnSim( ph_fd, filefd[kImageTags], ph_tokenPos, sTxt )
                    ph_fd[KPhWordCount] = len(notIndepLeaves) # _wordPos does not include QSG added words 
                    filePhraseList.append((ph_fd, sfd, label, ph_txt, ph_node, i))
                        
            print "Top words: ", topWords
            for j, (ph_fd, sfd, label, ph_txt, ph_node, i) in enumerate(filePhraseList):
                  ph_node.setPhrIndex(j)
                  assert j==ph_node.phrIndex(), "Node indexing gone wrong"
                  
            filefd[kPhraseFeatureList] = filePhraseList
            filefd[kSentenceTrees]     = fileSentenceTrees
            IP.writeDataForPhraseSummary(filefd, svm)
            
            #raise NotImplementedError, "Ready to solve IP model"
            
            try:
                solution = IP.solveIP(Config.IP_MODEL)
            except Warning: # problem is infeasible
                print "Problem is infeasible"
                continue # for now, move on to the next file with no output
                    
            xList = IP._getValuesFromSolution( 'x', len(filePhraseList), solution )
            sList = IP._getValuesFromSolution( 's_used', filefd[kSentenceCount], solution )
            if False:
                print "xList: ", xList
                print "sList: ", sList
                # print solution
            keepPhraseNodes = [ filePhraseList[i][4] \
                for i in range(len(filePhraseList)) \
                if (xList[i]) ]
            sentences=filefd[kSentences]
            trees=filefd[kSentenceTrees]
                
            if False:
                print "\n\n"
                print "phrase nodes to keep: "
                for p in keepPhraseNodes: 
                    print nodeText(p)
                    
                    
            print "\n\n"
            print "Original sentences: "
            for i in range(len(sList)):
                if sList[i]==1: print sentences[i]
                
            try:
                highlights = IP.assembleHighlightsFromPhraseTrees( filePhraseList, trees, sentences, xList, sList )
                #except RuntimeError:
            except ValueError:
                continue # quit with this file
                
            print "Number of highlights created: ", len(highlights)
            for h in highlights: 
                print h

            # raise NotImplementedError, "Ready to write output to file"

            if False: # for CNN highlights
                OUTPUT_HIGHLIGHTS_DIR = Config._DATA_BASE_DIR + 'assessment-files/QSG/27/'
                assert testFile.startswith(CNNAssessmentFiles.RAW_FILES_DIRECTORY), "File not where I thought"
                outputFile = testFile.replace(CNNAssessmentFiles.RAW_FILES_DIRECTORY, OUTPUT_HIGHLIGHTS_DIR)
                outputFile = outputFile.replace(".doc.txt", ".hlights.txt")
            elif False: # for CNN captions
                OUTPUT_HIGHLIGHTS_DIR = Config.HLIGHTS_OUTPUT_DIR
                assert testFile.startswith(Config.TRAINING_DOCS_DIR), "File not where I thought"
                outputFile = testFile.replace(Config.TRAINING_DOCS_DIR, OUTPUT_HIGHLIGHTS_DIR)
                if os.path.exists(outputFile):
                    print "Already done this file"
                    continue
            elif True: # for BBC highlights
                OUTPUT_HIGHLIGHTS_DIR = Config.BBCCorpusCaptions_DIR + 'QSG-output/6/'
                assert testFile.startswith(BBCCaptionFilelist.TOK_DIR), "File not where I thought"
                outputFile = testFile.replace(BBCCaptionFilelist.TOK_DIR, OUTPUT_HIGHLIGHTS_DIR)
                if os.path.exists(outputFile):
                    print "Already done this file"
                    continue
            elif False: # for DUC04 highlights
                # combine into single line
                if len(highlights)>1:
                    combHighlights=[]
                    for h in highlights[:-1]:
                        hs = h.strip()
                        if hs[-1]=='.':
                            print "Found final full stop"
                            hs = hs[:-1]
                        combHighlights.append(hs)
                    combHighlights.append(highlights[-1]) # add final sentence
                    singleSentence = "; ".join(combHighlights)
                    # print "Single sentence: ", singleSentence
                    # put single sentence back in highlights
                    highlights = [ singleSentence, ]
                OUTPUT_HIGHLIGHTS_DIR = Config.DUC04_OUTPUT_DIR + 'QSG-12/'
                assert testFile.startswith(DUC04Filelist.TOK_DIR), "File not where I thought"
                outputFile = testFile.replace(DUC04Filelist.TOK_DIR, OUTPUT_HIGHLIGHTS_DIR)
                if os.path.exists(outputFile):
                    print "Already done this file"
                    continue

            WriteHighlights.writeHighlightsToFile( highlights, outputFile )
        except IndexError, e:
            print "Problem with mapping dependencies onto trees here"
            print e
            raise SystemExit
        except UnicodeDecodeError, e:
            print "Problem with file codec", e
        except KeyError, e:
            print "Skipping file not in cache.", e
    
                    
    
    
def concatOutputFiles():
    """
    Collect the output files and concatenate them so we can compare the various models.
    """
    inputBaseDir = Config._DATA_BASE_DIR + 'assessment-files/QSG/'
    outputDir = Config._DATA_BASE_DIR + 'assessment-files/QSG/concat/'
    inputDirList = ( ('../highlights','Original CNN highlights'),
                     ('1','Hand-written dependency rules; longer highlights (28, 75)'),
                     ('2','Verb templates; longer highlights (28, 75)'),
                     ('3','Verb templates with handwritten parent dep rules; longer highlights (28, 75)'),
                     ('4','Quasi sync grammar; longer highlights (28, 75)'),
                     ('5','Quasi sync grammar with handwritten dep rules; longer highlights (28, 75)'),
                     ('6','Quasi sync grammar and verb templates; longer highlights (28, 75)'),
                     ('7','QSG, verb templates and parent dep rules; longer highlights (28, 75)'),
                     ('21','Hand-written dependency rules; medium highlights (25, 65)'),
                     ('22','Verb templates; medium highlights (25, 65)'),
                     ('23','Verb templates with handwritten parent dep rules; medium highlights (25, 65)'),
                     ('24','Quasi sync grammar; medium highlights (25, 65)'),
                     ('25','Quasi sync grammar with handwritten dep rules; medium highlights (25, 65)'),
                     ('26','Quasi sync grammar and verb templates; medium highlights (25, 65)'),
                     ('27','QSG, verb templates and parent dep rules; medium highlights (25, 65)'),
                     ('11','Hand-written dependency rules; short highlights (20, 60)'),
                     ('12','Verb templates; short highlights (20, 60)'),
                     ('13','Verb templates with handwritten parent dep rules; short highlights (20, 60)'),
                     ('14','Quasi sync grammar; short highlights (20, 60)'),
                     ('15','Quasi sync grammar with handwritten dep rules; short highlights (20, 60)'),
                     ('16','Quasi sync grammar and verb templates; short highlights (20, 60)'),
                     ('17','QSG, verb templates and parent dep rules; short highlights (20, 60)'),
                     )
    for f_orig in CNNAssessmentFiles.filelistIter():
        output = []
        f_name = os.path.basename(f_orig)
        f_name = f_name.replace(".doc.txt", ".hlights.txt")
        print "f_name: ", f_name
        outputFile = outputDir + f_name
        assert not os.path.exists(outputFile), "Output file %s already exists" % outputFile
        
        output.append("Document %s\n\n" % f_name)

        for d, description in inputDirList:
            inputDir = inputBaseDir+d+'/'
            f_in = inputDir + os.path.basename(f_name)
            
            output.append("Model %s: %s\n" % (d,description))
            if os.path.exists(f_in):
                print "Found highlight file", f_in
                fh_in = codecs.open(f_in, 'r','iso-8859-1')
                lines = fh_in.readlines()
                output.extend(lines)
                fh_in.close()
            else:
                output.append("[Highlights couldn't be generated]\n")
                
            output.append("\n")
            
            
        WriteHighlights.writeHighlightsToFile( output, outputFile )        




def concatCaptionOutputFiles():
        """
        Collect the output files and concatenate them so we can compare the various models.
        TODO: fit this in with concatOutputFiles()
        """
        if False: # CNN captions
            inputBaseDir = Config.CNNCorpusCaptions_DIR + 'output/'
            outputDir = Config.HLIGHTS_OUTPUT_DIR
            inputDirList = ( ('../caption','CNN'),
                         ('7','Dep'),
                         ('9','QSG'),
                         ('8','Q+D'))
            outputFile = Config.CNNCorpusCaptions_DIR + "output/concat.txt"
        elif True: # BBC captions
            inputBaseDir = '/disk/scratch/summarisation/BBCCaptions/QSG-output/'
            inputDirList = ( ('../test/cap','BBC'),
                             ('../out-s-best','B1S'),
                             ('../out-s-btag','B1T'),
                             ('../yansong','Yan'),
                             ('4','Dep'),
                             ('5','QSG'),
                             ('6','Q+D'))
            outputFile = '/disk/scratch/summarisation/BBCCaptions/QSG-output/concat4.txt'
        elif False: # DUC04 headlines
            inputBaseDir = '/disk/scratch/summarisation/DUC-04/output/'
            inputDirList = ( ('l1','Ld1'),
                             ('QSG-12','Dep'),
                             ('QSG-11','QSG'),
                             ('QSG-10','Q+D'))
            outputFile = '/disk/scratch/summarisation/DUC-04/output/concat.txt'

        output = []
        assert not os.path.exists(outputFile), "Output file %s already exists" % outputFile
        #for f_orig in CNNCaptionsFilelist.filelistIter():
        #for f_orig in BBCCaptionFilelist.filelist():
        for f_orig in BBCCaptionFilelist.humanEvalFilelist():
        #for f_orig in DUC04Filelist.filelist():

            f_name = os.path.basename(f_orig)
            print "f_name: ", f_name

            output.append("Document %s\n" % f_name)
            for d, description in inputDirList:
                inputDir = inputBaseDir+d+'/'
                f_in = inputDir + os.path.basename(f_name)
                if d=="../caption":
                    f_in = f_in.replace(".doc.txt", ".caption.txt")
                elif d=="../test/cap":
                    f_in = f_in.replace(".doc.txt", ".txt")


                output.append("%s: " % description)
                if os.path.exists(f_in):
                    print "Found highlight file", f_in
                    fh_in = codecs.open(f_in, 'r','iso-8859-1')
                    lines = fh_in.readlines()
                    output.extend(lines)
                    fh_in.close()
                else:
                    print "Didn't find highlights file", f_in
                    output.append("[Highlights couldn't be generated]\n")
            output.append("\n")
                    
                    
        WriteHighlights.writeHighlightsToFile( output, outputFile )

                   


                                                                                                            
if __name__=="__main__":
    investigate()
    #createQSGFromDirectory()
    #investigatePickledResults()
    #investigatePickledResultsRuleSet()
    #investigateParaphrasing()
    #investigateVerbFrame()
    #createVerbFrameRules()
    #createQSGFromDirectory()    
    #investigateMakingIPHighlight()
    #concatOutputFiles()
    #concatCaptionOutputFiles()
    

