"""
Investigation how to get sync grammar to relate sentences to highlights
"""

import txt2txtgen
import txt2txtgen.config.Config as Config


#from parse import POSTagger, PhraseDependencyTree
#from nlputils import NltkUtils
#from features import ExtractFeatures
#from utils import ListFiles
#from tasks import CNNAssessmentFiles, BBCCaptionFilelist, DUC04Filelist
#from summarize import WriteHighlights
#from features.FeatureList import *
#from nlputils import TfIdf
#from nlputils.TfIdf import CorpusFreqDist
#from features import ExtractFeatures, ExtractPhraseFeatures
#from config import Shelves
#import summarize.IP
#from tasks import CNNCaptionsFilelist

import nltk.probability
import cPickle as pickle
from operator import attrgetter
import sys, os, codecs
import shelve

LIMIT_MATCHING_RULES = True
LIMIT_MATCHING_RULES_COUNT = 5
LIMIT_MATCHING_TOP_RULE_COUNT = 5
LIMIT_RULE_DEPTH = 40





from SyncTreeGrammar import SyncGrammarRule, NoGrammarPathError
from QGCore import *
from QGDefs import *
import morph


def createQSGParaphrase( syncGrammarRules, rootPhraseTree ):
    """
    Creates a paraphrase of rootPhraseTree, based on rules.
    Returns the paraphrase, which may contain CHOICE nodes.
    """
    raise DeprecationWarning, "should go through createParaphraseTree()"
    paraphrases = _findMatchingRulesForChildRecursive( syncGrammarRules, rootPhraseTree, 0 )
    assert len(paraphrases)==1, "Even the root has created more than one paraphrase"
    rootParaphrase, rootParaphraseRuleCount, identicalFlag = paraphrases[0] # get only paraphrase
    return rootParaphrase
    

def createParaphraseTree(srcPhraseTree, rule, allRules, level, rewrite_only_if_necessary=False):
    """
    Create a paraphrase
    Rewrite the phrase tree according to the srcSync and targetSync rule.
    Returns a PhraseDependencyTree
    """

    # stop handling of very deep rules
    # instead, make a copy of the tree, with no further choice nodes or rules applied
    if level>LIMIT_RULE_DEPTH:
        if PRINT_DEBUG_PARAPHRASE: 
            print "Making plain copy of src, at level", level
            print srcPhraseTree.tag()
            print rule
            print rule._target.tag()
        if not rule._target.tag()==srcPhraseTree.tag():
            raise NoGrammarPathError,"Cannot produce straight copy with %s -> %s" % (srcPhraseTree.tag(),rule._target.tag())
        return srcPhraseTree.copy(deep=True)
    
    # special handling for choice nodes
    if isinstance(srcPhraseTree, PhraseTreeChoice):
        return createParaphraseTreeFromChoice(srcPhraseTree, allRules,level)
        
    srcSync = rule._source
    targetSync = rule._target
    assert rule.matchesSource(srcPhraseTree), "Sync grammar not suitable for this phrase tree node"
    assert isinstance(srcPhraseTree, PhraseDependencyTree.PhraseDependencyTree), "Cannot create a paraphrase tree from %s" % srcPhraseTree
    assert not srcPhraseTree.isLeaf(), "Rule called on leaf"
    if isinstance(srcPhraseTree, PhraseTreeChoice):
        assert srcPhraseTree.tag()==PhraseTreeChoice.TAG, "Misnamed choice node %s" % srcPhraseTree
    assert not isinstance(srcPhraseTree, PhraseTreeChoice), "Trying to paraphrase an already existing choice \n%s" % srcPhraseTree

    targetPhraseTree = PhraseDependencyTree.PhraseDependencyTree("( %s )"% targetSync.tag())
    targetPhraseTree.copyAttributes(srcPhraseTree)
    
    if PRINT_DEBUG_PARAPHRASE: 
        print "Source phrs tree: ", srcPhraseTree
        print "Source sync tree: ", srcSync
        print "Target sync tree: ", targetSync
        
    if PRINT_DEBUG_PARAPHRASE:
        print "In createParaphraseTree, before working through children"
        print "Created target phrase ", targetPhraseTree.leaves(), targetPhraseTree.tag(),targetPhraseTree.dep(), " with wordpos ", targetPhraseTree._wordPos
        print "...from source phrase ", srcPhraseTree.leaves(), srcPhraseTree.tag(), srcPhraseTree.dep(), " with wordpos ", srcPhraseTree._wordPos
        if len(targetPhraseTree)>0:
            tdbg = targetPhraseTree[0]
            print "and...", tdbg.treepos, tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
        print 
        
    if PRINT_DEBUG_PARAPHRASE: print "targetSync = ", targetSync
    
    
    _createParaphraseTreeChildren(srcSync, targetSync, srcPhraseTree, targetPhraseTree, allRules, level, rewrite_only_if_necessary=rewrite_only_if_necessary)
    
    if PRINT_DEBUG_PARAPHRASE:
        print "Created target phrase ", targetPhraseTree.leaves(), targetPhraseTree.dep(), " with wordpos ", targetPhraseTree._wordPos
        print "...from source phrase ", srcPhraseTree.leaves(), srcPhraseTree.dep(), " with wordpos ", srcPhraseTree._wordPos
        
        if len(targetPhraseTree)>0:
            tdbg = targetPhraseTree[0]
            print "and...", tdbg.treeposition(), tdbg.leaves(), tdbg._wordPos, tdbg.dep(), "\tInd:",tdbg.isIndependentPhrase()
        print 
        
    return targetPhraseTree



def _createParaphraseTreeChildren(srcSync, targetSync, srcPhraseTree, targetPhraseTree, allRules, level, rewrite_only_if_necessary=False):
    for ch in targetSync.children():
        if PRINT_DEBUG_PARAPHRASE:
            print "First go: child=", ch, " at linked pos ",ch._linknum,"\t\t",
            try:
                print "Links to ", srcSync.findLink(ch._linknum, srcPhraseTree)
            except LookupError:
                print "No link"
        try:
            position = srcSync.findLink(ch._linknum, srcPhraseTree)
            if PRINT_DEBUG_PARAPHRASE: print "Target ", ch, "at", ch._linknum, "\t\tlinked to source ", position
            if srcPhraseTree[position].isLeaf():
                try:
                    copiedNode = morph.morph_tree(srcPhraseTree[position], ch)
                except (ValueError, AttributeError):
                    # can get here if we don't know the lemma of the node, e.g. if it is taken from another QTSG rule
                    # just do deep copy and don't apply any more rules
                    copiedNode = srcPhraseTree[position].copy(deep=True)
                    # print "Leaf copy. Original: ", srcPhraseTree[position], "\tCopied ", copiedNode
                
                targetPhraseTree.append(copiedNode)
            else:
                if PRINT_DEBUG_PARAPHRASE:
                    print "Link number: ", ch._linknum
                    print "Linked to position: ", position
                    print "srcPhraseTree: ", srcPhraseTree[position]
                # TODO: may need to apply another rule here if transform is required
                copiedNodeList = _findMatchingRulesForChildRecursive( allRules, srcPhraseTree[position], level+1, targetTreeNode=ch, rewrite_only_if_necessary=rewrite_only_if_necessary )
                # print "*** tree copy. Original wordPos", srcPhraseTree[position]._wordPos, srcPhraseTree[position].isFixed(), " Copied ", copiedNodeList[0][0]._wordPos
                assert len(copiedNodeList)>0, "No paraphrase generated"
                
                # Get all the leaf positions in this paraphrase
                # May need special function to just get the fixed node positions
                for paraphrase, count, identical, rule in copiedNodeList:
                    newPosList=[]
                    for ch in paraphrase:
                        if not ch.isIndependentPhrase(): # was ch.isFixed()
                            newPosList.extend(ch._wordPos)
                    paraphrase._wordPos = newPosList
                    
                    if PRINT_DEBUG_PARAPHRASE:
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
            if PRINT_DEBUG_PARAPHRASE: 
                print "Unlinked child (%s %s)" % (ch._node, ch._text)
                print "Number of children:", len(ch.children()), ch.hasChildren()
            
            if ch.hasChildren():
                parseString = "(%s)" % (ch._node)
                targetChild = PhraseDependencyTree.PhraseDependencyTree(parseString)
                targetChild._rel = ch._dep
                targetChild._fixed = True
                if PRINT_DEBUG_PARAPHRASE: print "Current target:", targetChild
                _createParaphraseTreeChildren(srcSync, ch, srcPhraseTree, targetChild, allRules, level+1, rewrite_only_if_necessary=rewrite_only_if_necessary)
                if PRINT_DEBUG_PARAPHRASE: print "Target child after paraphrase:", targetChild
                targetPhraseTree.append(targetChild)
                
            else:
                assert ch._text is not None, "Unlinked target phrase has no structure and no text"
                parseString = "(%s %s)" % (ch._node, ch._text)
                fixedTextChild = PhraseDependencyTree.PhraseDependencyTree(parseString)
                fixedTextChild._rel = ch._dep
                fixedTextChild._fixed = True
                # fixedTextChild._wordPos = [-1] # a dummy value to get the word count correct
                fixedTextChild._wordPos = [] # need to find another way to add up length of phrase
                
                # for paraphrase rules PPDBSyncTreeText, copy across word token information as this contains position information if nothing else
                # TODO: need to handle other types of rules, by exception?
                if PRINT_DEBUG_PARAPHRASE:
                    print "paraphrased word: linking to source token information"
                    print type(ch), ch, ch.word_alignment()
                    print srcPhraseTree
                
                # get token information of src node
                try:
                    leaf_nodes = srcPhraseTree.leaf_nodes_in_order()
                    src_token = leaf_nodes[ch.word_alignment()].token()
                    # create new token information for tgt child, with index and text 
                    this_token = ParaphrasedTokenInfo(ch._text, ch._node, src_token.index)
                    fixedTextChild.storeSingleTokenInfo(this_token)
                except TypeError:
                    # no word alignment information for this leaf
                    pass
                
                targetPhraseTree.append(fixedTextChild)

    

class ParaphrasedTokenInfo():
    '''
    Same structure as parse.TokenInfo
    Access methods for individual tokens. 
    '''
    def __init__(self, word, pos, index):
        self.word = word
        self.lemma = word
        self.POS = pos
        self.index = index



def createParaphraseTreeFromChoice(srcPhraseTree, allRules, level):
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
        targetChParaphrases = createParaphraseTree( ch, dupRule, allRules, level+1)
        childrenForTarget.append( targetChParaphrases )
        
    assert len(childrenForTarget) == len(srcPhraseTree.counts()), \
        "Not got the correct number of children (%d) and counts (%d)" \
        % (len(childrenForTarget),len(srcPhraseTree.counts()))
    choiceList = zip(childrenForTarget, srcPhraseTree.counts(), srcPhraseTree.identicals())
    targetPhraseTree = PhraseTreeChoice.create(choiceList)
    
    return targetPhraseTree



def _debug_checkChoiceTags(tree):
    if isinstance(tree, PhraseTreeChoice):
        assert tree.tag() == PhraseTreeChoice.TAG, "Tag not correctly set up %s - %s" % (tree.tag(), tree.treepos)
    
    if not tree.isLeaf():
        for ch in tree:
            _debug_checkChoiceTags(ch)
    return True
    



    


def _findMatchingRulesForChildRecursive( rules, phraseTree, level, rewrite_only_if_necessary=False, targetTreeNode=None ):
    """
    Just to get this working
    useOriginal: if True, the source sentence is a valid paraphrase
    """

    if PRINT_DEBUG and targetTreeNode: print "Target node: ", targetTreeNode, "\t\tSource node: ", phraseTree.tag(), phraseTree.dep()
    useOriginal=True
    if targetTreeNode:
        if not (phraseTree.tag() == targetTreeNode.tag() ):
            #and phraseTree.dep() == targetTreeNode.dep() ): # TODO: want to consolidate use of dep()
            #raise SystemExit, "Can't use paraphrase transformation" 
            useOriginal=False
       
    matchingRules = [ r for r in rules if r is not None and r.isSuitable(phraseTree, targetTreeNode) ]
    if PRINT_INFO: 
        print "INFO_rules\tsrc tag %s\ttgt tag %s \t%d rules\t%d instances" % (phraseTree.tag(), targetTreeNode.tag(), len(matchingRules), sum([r.count() for r in matchingRules])),
        print "\t", level, "\t", phraseTree.treeposition()
        for r in rules:
            print r.isSuitable(phraseTree, targetTreeNode)

    if rewrite_only_if_necessary:
        if useOriginal:
            # just original
            matchingRules = []
        else: # original not possible, need to rewrite
            matchingRules = matchingRules[:1] # just the first one for now
            pass # TODO: not sure if we should cut down matchingRules
        
    if LIMIT_MATCHING_RULES:
        # cut out low-count rules if there are a lot of them
        if len(matchingRules)>LIMIT_MATCHING_RULES_COUNT:
            sortedMatchingRules = sorted( matchingRules, key=SyncGrammarRule.count, reverse=True )
            if False and phraseTree.tag()=="S": # print out the list
                print "All matching rules, sorted into frequency order"
                for r in sortedMatchingRules:
                    print r.count(), "\t\t", r
                    if r._target.tag()=="SP":
                        raise SystemExit,"SP rule found"
                
            # Get more rules for the very top node, and fewer below
            if phraseTree.dep()=="TOP" and phraseTree.tag()=="S" and len(matchingRules)>LIMIT_MATCHING_TOP_RULE_COUNT:
                matchingRules = sortedMatchingRules[:LIMIT_MATCHING_TOP_RULE_COUNT]
            else:
                matchingRules = sortedMatchingRules[:LIMIT_MATCHING_RULES_COUNT]
                        
    if PRINT_DEBUG and True:
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
            if PRINT_DEBUG: print "Creating duplication rule\t\tCurrent text: ", nodeText(phraseTree)
            dupRule = SyncGrammarRule.createDuplicationRule(phraseTree)
            matchingRules.append(dupRule)
    
    possibleParaphraseTrees = []
    identicalRuleUsed = False
    for r in matchingRules:
        if r.isIdentical(): identicalRuleUsed = True
        
        try:
            if PRINT_DEBUG: print "Creating paraphrase from rule: ", r
            paraphraseTree = createParaphraseTree(phraseTree, r, rules, level, rewrite_only_if_necessary=rewrite_only_if_necessary )
            # if PRINT_DEBUG: print "Paraphrase:\n", paraphraseTree,"\n\n"
            # if r._target.tag()=="SP": raise SystemExit, "Debugging SP rule"
            possibleParaphraseTrees.append((paraphraseTree, r.count(), r.isIdentical(), r))
        except NoGrammarPathError, e:
            pass # try next rule
        
    if len(possibleParaphraseTrees)==0:
        raise NoGrammarPathError, "No rules available"
    
    return possibleParaphraseTrees


def locateSentenceSplits(tree):
    """
    Return a list of tree positions where the 
    sentence can be split into smaller sentences.
    """
    assert isinstance(tree,PhraseDependencyTree.PhraseDependencyTree), "Unexpected type"
    l = []
    if tree.tag()=="SP":
        for ch in tree:
            l.append(ch)
    for ch in tree:
        if not ch.isLeaf(): 
            l.extend(locateSentenceSplits(ch))
    return l
    
    


