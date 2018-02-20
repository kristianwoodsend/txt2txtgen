"""
A grammar for learning how to split sentences into shorter ones.
The assumption of this grammar is that a source node both contributes
to the target node and also generates a separate, stand-alone sentence.

If the rule is working well, then this will ideally split the phrases of this node
neatly between the target node and the second sentence.
"""

from QGDefs import *
from QGCore import *
from SyncTreeGrammar import *
import QGParaphrase
import SyncTreeGrammar
import info

import txt2txtgen.features.ExtractPhraseFeatures
from txt2txtgen.features.FeatureList import *
import txt2txtgen.utils.FeatureCache
from txt2txtgen.formats.ParsedArticle import WikiSplitSentenceArticle

from operator import attrgetter


LIMIT_SENTENCE_SPLITTING_DEPTH = 4
LIMIT_SENTENCE_SPLITTING_RULE_COUNT = 1

# ------------------------------------------------------
# ------- Paraphrase generation functions
def createSplitSet(doc, splitRules, singleSTRules, singleLexQGRuleset, singleCompressionQGRuleset):
    if PRINT_DEBUG_SPLIT: print "In createSplitSet"
    if PRINT_DEBUG_SPLIT_INDICATIONS:
        indicationcount = 0 
    splits = []
    for s in doc.sentences():
        if PRINT_DEBUG_SPLIT_INDICATIONS: 
            indicationcount+=1; print indicationcount, 
            if indicationcount%10 == 0: print
        if PRINT_DEBUG_SPLIT: print "... working on sentence: ", s.tokenString()
        try:
            sTree = s.parseTree()
            topNode, sentenceSplitList = _sentenceSplitParaphrase(sTree, splitRules, singleSTRules, singleLexQGRuleset, singleCompressionQGRuleset, 0)
            sentenceSplitList.append(SentenceSplitPair(None,sTree,0,None))
            if PRINT_DEBUG_SPLIT: 
                print "... created split set"
                print "topNode"
                print topNode
                print
                print "sTree"
                print sTree
                # raise SystemExit, "paraphrased first sentence"
        
            if len(sentenceSplitList)>1:
                orderedSentences = orderSplitSentences(sentenceSplitList)
                splits.append(orderedSentences)
            else:
                pass
                splits.append(sentenceSplitList)
                # splits.append((SentenceSplitPair(None,sTree,0,None),))
        except IndexError: # something wrong with the parse of this sentence
            pass
            splits.append(None)
            if PRINT_DEBUG_SPLIT: print " ... Failed to parse properly"
    if PRINT_DEBUG_SPLIT_INDICATIONS: print
    return splits
    
    
def createSplitDoc(doc, splits, sentenceFeatures):
    sList, phrList, sFeatures, phrFeatures, mainAuxList = _featuresForSplits(doc, splits, sentenceFeatures)
    splitDoc = WikiSplitSentenceArticle(doc, doc._task, sList, phrList)
    featuresDict = txt2txtgen.utils.FeatureCache.NoStorageCacheEntry()
    featuresDict[kSentenceFeatureList] = sFeatures
    featuresDict[kPhraseFeatureList]=phrFeatures
    featuresDict[kMainAuxSentencesList]=mainAuxList
    return splitDoc, featuresDict


def _featuresForSplits(doc, splits, sentenceFeatures):
    newSentenceFeatures = []
    fullSentences = []
    fullSentenceFeatures = []
    fullPhrases = []
    fullPhraseFeatures = []
    task = doc.task()
    
    sCount = 0
    for s_i, split in enumerate(splits): # one split per sentence
        if split is None: continue # sentence that didn't parse and split successfully
        for i,sp in enumerate(split): # sub-sentences
            sentence = sp.aux()
            # print i,": ",nodeText(sentence)
            sf = sentenceFeatures[s_i]
            # phrases = features.ExtractPhraseFeatures.phraseList((sentence,), sentenceNums=(sCount,)) # wrong sentence for bigrams
            phrases = txt2txtgen.features.ExtractPhraseFeatures.phraseList((sentence,), sentenceNums=(s_i,))
            # print "Number of phrases:", len(phrases)
            phrFeatures = [ task.storePhraseFeatures(phr,doc,{}) for phr in phrases ]
            for ph in phrases: ph._sentenceIndex = sCount # correct sentence number back to the one in the expanded document
            
            # add in sentence features
            for phrF in phrFeatures: phrF.update(sf)
            
            # don't need this check --- not reliable, as text-identical sentences are being matched
            # assert sentence not in fullSentences, "Sentence %d already in list" % sCount
            if False and sentence in fullSentences: 
                print "Sentence %d already in list" % sCount
                sp.info()
                
            fullSentences.append(sentence)
            sp.setSIndex(sCount)
            fullSentenceFeatures.append(sf)
            fullPhrases.extend(phrases)
            fullPhraseFeatures.extend(phrFeatures)
            sCount += 1
            
            
    for j, ph_node in enumerate(fullPhrases):
            ph_node.tree().setPhrIndex(j)

    # link together split sentences
    # do this after phrases have been numbered
    mainAuxList = getMainPhraseAuxSentenceList(splits)

    if False:
        for i,s in enumerate(fullSentences):
            print i, nodeText(s)
            
        for ph, f in zip(fullPhrases,fullPhraseFeatures):
            print ph.text()
            print f
    
    return fullSentences, fullPhrases, fullSentenceFeatures, fullPhraseFeatures, mainAuxList


def getMainPhraseAuxSentenceList(splits):
    mainAuxList = []
    #for i,s in enumerate(fullSentences): print i,nodeText(s)
    # print "Trying to link split sentences together"
    for s_i, split in enumerate(splits): # one split per sentence
        if split is None: continue # sentence that didn't parse and split OK
        for i,sp in enumerate(split): # sub-sentences
            # print i, "Recorded sentence index:", sp.sIndex()
            if not sp.main(): continue
            indexAux = sp.sIndex()
            mainPhraseNumber = sp.main().phrIndex()
            mainAuxList.append((mainPhraseNumber,indexAux))
            
            # debugging
            if False:
                print "Main phrase ", mainPhraseNumber, "in sentence ", s_i,
                print " is linked to sentence", indexAux, "-" , 
                # this is what needs to be recorded, and then written out for the IP
                # main phrases, linked sentence number
                print ": (%d, %d)" % (mainPhraseNumber,indexAux)
    # print "Final main-aux list:", mainAuxList
            
    return mainAuxList
    

def _sentenceSplitParaphrase(ph, splitRuleset, singleSTRuleset, singleLexQGRuleset, singleCompressionQGRuleset, level):
    """
    Apply sentence-splitting rules to this phrase node.
    
    Returns a paraphrased version of this node ph
    """
    if DEBUG_SENTENCE_SPLIT:
        print "--------------_sentenceSplitParaphrase(level %d)----------------" % level
        print "Currently: ", ph.treeposition(), ph.tag(), nodeText(ph) # , "with ruleset size %d"%len(ruleset)
    
    if ph.isLeaf(): return None, []
    assert not ph.isLeaf(), "_sentenceSplitParaphrase(): Trying to apply paraphrase to leaf"
    
    # stop handling of very deep rules
    # instead, make a copy of the tree, with no further choice nodes or rules applied
    if level>LIMIT_SENTENCE_SPLITTING_DEPTH:
        if DEBUG_SENTENCE_SPLIT: 
            print "LIMIT_SENTENCE_SPLITTING_DEPTH exceeded, so jumping splitting methods"
        # raise SystemExit, "LIMIT_SENTENCE_SPLITTING_DEPTH exceeded, so jumping splitting methods"
        suitableRulesCounts = []
        sentenceSplitList = []
    else:
        sentenceSplitList = []
        dupRule = SyncGrammarRule.createDuplicationRule(ph)
        # print "Duplication rule:", dupRule.count(), dupRule
        if DEBUG_SENTENCE_SPLIT: 
            print "current phrase:", ph
            print "Number of rules in ruleset: ", len(splitRuleset)
        suitableRulesCounts = [ (r.count(),r) for r in splitRuleset if r.isSuitable(ph,None) and r.count()>1]
        suitableRulesCounts.sort(reverse=True)

        # cut down list of suitable rules
        if LIMIT_SENTENCE_SPLITTING_RULE_COUNT > 0:
            suitableRulesCounts = suitableRulesCounts[:LIMIT_SENTENCE_SPLITTING_RULE_COUNT]
            
        
    
    if DEBUG_SENTENCE_SPLIT:
        print "List of suitable rules:"
        for rc,r in suitableRulesCounts: 
            print r
        print "----------------------------"
    
    choiceList = []
    if len(suitableRulesCounts):
        for rc,r in suitableRulesCounts: 
            try:
                if DEBUG_SENTENCE_SPLIT:
                    print "\n---------------------"
                    print "Suitable rule (count %d) for %s:"%(rc, nodeText(ph))
                    print r
                    print
                
                    print "applying to s2:",r._sent2Rule
                # TODO: LIMIT_RULE_DEPTH-1
                para2 = QGParaphrase.createParaphraseTree(ph, r._sent2Rule, singleSTRuleset, QGParaphrase.LIMIT_RULE_DEPTH-2)
                para2copy = [ (i,ch) for (i,ch) in enumerate(para2) if not ch.isLeaf()]
                para2SentenceSplitInfo = None
                for (i,ch) in para2copy:
                    if DEBUG_SENTENCE_SPLIT: print "para2copy:",i, ch.tag()
                    para_ch, para2SentenceSplitInfo = _sentenceSplitParaphrase(ch, splitRuleset, singleSTRuleset, singleLexQGRuleset, singleCompressionQGRuleset, level+1)
                    # para_ch = None # TODO: sort out recursive applying split sentence rules to repeated elements
                    if para_ch:
                        # print "Trying to replace with paraphrase"
                        para2[i] = para_ch
                if DEBUG_SENTENCE_SPLIT:
                    print "Para2:", nodeText(para2)
                    print "Full:", nodeText(ph.root())
                # put ROOT above para2
                treeRoot = PhraseDependencyTree.PhraseDependencyTree("(ROOT)")
                treeRoot._rel="TOP"
                treeRoot.append(para2)
                # print "tree root:", treeRoot
                para2 = treeRoot
                # raise SystemExit,"Completed 1 sentence para2"
                
                if DEBUG_SENTENCE_SPLIT: print "applying to s1:",r._sent1Rule
                
                # TODO: need to generate paraphrase with as few changes as possible
                # use depth LIMIT_RULE_DEPTH, but then if a change of constituent is needed, LIMIT_RULE_DEPTH-2
                para1SentenceSplitInfo = []
                para1 = QGParaphrase.createParaphraseTree(ph, r._sent1Rule, singleSTRuleset, QGParaphrase.LIMIT_RULE_DEPTH-2)
                para1copy = [ (i,ch) for (i,ch) in enumerate(para1) if not ch.isLeaf()]
                for (i,ch) in para1copy:
                    # print "para1copy:",i, ch.tag()
                    para_ch, para1SentenceSplitInfo = _sentenceSplitParaphrase(ch, splitRuleset, singleSTRuleset, singleLexQGRuleset, singleCompressionQGRuleset, level+1)
                    if para_ch:
                        # print "Trying to replace with paraphrase"
                        para1[i] = para_ch
                if DEBUG_SENTENCE_SPLIT: print "Para1:", nodeText(para1)
                
                # raise SystemExit,"Completed 1 sentence para1"
                
                # successfully created split sentences from this rule
                choiceList.append(SentenceSplitPair(para1, para2, r.count(), r.auxAfter()))
                sentenceSplitList.extend(para1SentenceSplitInfo)
                if para2SentenceSplitInfo: # TODO: sometimes this is not set properly, need to find out why 
                    sentenceSplitList.extend(para2SentenceSplitInfo)
                if DEBUG_SENTENCE_SPLIT or DEBUG_SENTENCE_SPLIT_RESULT: 
                    print "Resulting sentences:"
                    print nodeText(ph), " --> ", nodeText(para1)
                    print nodeText(para2)
                    print para2
                    print "From rule:"
                    print r
                    print "-----------------------------"
                    # raise SystemExit,"Completed 1 sentence"
                # break # maybe one successful rule is enough
                    
            except NoGrammarPathError,e:
                # abandon this rule, as we cannot create a whole sentence
                if DEBUG_SENTENCE_SPLIT: print "NoGrammarPathError: ", e
                pass
                
                
    if len(choiceList)>0:
        assert len(choiceList)>0,"Not enough choices"
        sentenceSplitList.extend(choiceList)
        choices = [ (ch.main(),ch.count(),False) for ch in choiceList ]
        choices.append((QGParaphrase.createParaphraseTree( ph, dupRule, singleSTRuleset, 0),dupRule.count(), True))
        if DEBUG_SENTENCE_SPLIT: 
            for (p1,count,_identical) in choices: print p1.tag(), p1.parent(), nodeText(p1)
        newPh = PhraseTreeChoice.create(choices)                
    else:
        if DEBUG_SENTENCE_SPLIT: print "No suitable sentence splitting rules"
        lexSubChoices = doSingleSRuleParaphrases(ph, singleLexQGRuleset, lexical=True)
        compressionChoices = doSingleSRuleParaphrases(ph, singleCompressionQGRuleset, lexical=False)
        if len(lexSubChoices):
            # sentenceSplitList = []
            if DEBUG_SENTENCE_SPLIT: print "Applying lexical substitutions"
            newPh = PhraseTreeChoice.create(lexSubChoices)
            
            if DEBUG_SENTENCE_SPLIT: 
                print "Choice tree created from lexical rules:"
                print newPh
                print newPh.pprint()
                print "lexSubChoices:", lexSubChoices
                
        elif len(compressionChoices):
            if DEBUG_SENTENCE_SPLIT: print "Applying compression substitutions"
            newPh = PhraseTreeChoice.create(compressionChoices)
                        
            if isinstance(newPh, PhraseTreeChoice):
                # apply sentence splitting to children of each choice
                for choice in newPh:
                    phCopy = [ (i,ch) for (i,ch) in enumerate(choice) if not ch.isLeaf()]
                    for (i,ch) in phCopy:
                        # print "Working on ", i
                        para_ch, chSentenceSplitList = _sentenceSplitParaphrase(ch, splitRuleset, singleSTRuleset, singleLexQGRuleset, singleCompressionQGRuleset, level+1)
                        if para_ch:
                            choice[i] = para_ch
                        sentenceSplitList.extend(chSentenceSplitList)
                        
            else:
                newPh = None
                        
        else:
            newPh = None
            
        if newPh is None:
            phCopy = [ (i,ch) for (i,ch) in enumerate(ph) if not ch.isLeaf()]
            for (i,ch) in phCopy:
                # print "phCopy:",i, ch.tag()
                # no sentence splitting has been applied, so keep sentence split level = level
                para_ch, chSentenceSplitList = _sentenceSplitParaphrase(ch, splitRuleset, singleSTRuleset, singleLexQGRuleset, singleCompressionQGRuleset, level)
                if para_ch:
                # print "Trying to replace with paraphrase"
                    ph[i] = para_ch
                sentenceSplitList.extend(chSentenceSplitList)
                #print "para_ch:", para_ch
            newPh = None
        
        
    return newPh, sentenceSplitList



def doSingleSRuleParaphrases(ph, singleSRuleset, lexical=True):
    """
    Look for single rules, we assume lexical substitutions, that can be applied to ph
    without invoking sentence splitting.
    lexical=True: only word substitution rules are used
    lexical=False: only compression rules are used
    """
    if PRINT_DEBUG_PARAPHRASE: print "In doSingleSRuleParaphrases: node ", ph.tag(), " text: ", nodeText(ph)
    # raise SystemExit,"doSingleSRuleParaphrases"
    SINGLE_RULE_MULTIPLE = 1
    SINGLE_RULE_LEXICAL_DUPLICATE_RULE_COUNT = 1.5
    LIMIT_SINGLE_RULE_NUMBER = 4
    if lexical:
        appRules = [ r for r in singleSRuleset if r.isSuitable(ph, ph) and r.isSubstitution(contentWords=True)]
    else:
        appRules = [ r for r in singleSRuleset if r.isSuitable(ph, ph)]
        
    appRules.sort(key=attrgetter('_count'), reverse=True)
    if LIMIT_SINGLE_RULE_NUMBER > 0:
        # limit the number of rules that we will apply
        appRules = appRules[:LIMIT_SINGLE_RULE_NUMBER]

    if PRINT_DEBUG_PARAPHRASE: print "In doSingleSRuleParaphrases: got %d appRules" % len(appRules)

    if PRINT_DEBUG_PARAPHRASE:
        if len(appRules):
            print "Number of lexical substitution rules available:", len(appRules)
            for r in appRules:
                print r.count(), r
        else:
            print "No lexical substitution rules available"    
            
    choices=[]
    for r in appRules:
        try:
            targetPhraseTree = r.applyRule(ph)
            if PRINT_DEBUG_PARAPHRASE: print "target tree created locally:\n", targetPhraseTree
        except NotImplementedError:
            targetPhraseTree = PhraseDependencyTree.PhraseDependencyTree("( %s )"% r._target.tag()) # was ph.tag())
            targetPhraseTree.copyAttributes(ph)
            _singleRuleCreateParaphraseTreeChildren(r._source, r._target, ph, targetPhraseTree)
            if PRINT_DEBUG_PARAPHRASE: print "target tree created:\n", targetPhraseTree
        choices.append((targetPhraseTree, SINGLE_RULE_MULTIPLE*r.count(), False ))

    if len(choices)>0:
        # add in copy of original
        noParaCopy = ph.copy(deep=True)
        choices.append((noParaCopy, SINGLE_RULE_MULTIPLE*SINGLE_RULE_LEXICAL_DUPLICATE_RULE_COUNT, True))
        
    return choices

    
    
def _singleRuleCreateParaphraseTreeChildren(srcSync, targetSync, srcPhraseTree, targetPhraseTree):
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
            
            # just do deep copy and don't apply any more rules
            copiedNode = srcPhraseTree[position].copy(deep=True)
            # print "Leaf copy. Original wordPos", srcPhraseTree[position]._wordPos, " Copied ", copiedNode._wordPos, srcPhraseTree[position].isFixed()
            targetPhraseTree.append(copiedNode)
                    
        except LookupError, _e:
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
                _singleRuleCreateParaphraseTreeChildren(srcSync, ch, srcPhraseTree, targetChild)
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
                targetPhraseTree.append(fixedTextChild)
        
    

class SentenceSplitPair(object):
    def __init__(self, mainNode, auxSentence, count, after):
        self._mainNode = mainNode
        self._auxSentence = auxSentence
        self._count = count
        self._after = after
        self._mainLink = None
        self._sIndexAux = None # final sentence index of the auxilliary sentence
        
    def count(self): return self._count
    def main(self):  return self._mainNode
    def aux(self): return self._auxSentence
    def mainRoot(self):
        if self._mainNode:
            return self.main().root()
        else:
            return None
    def after(self): return self._after
    def setMainLink(self,link): self._mainLink = link
    def getMainLink(self): return self._mainLink
    def setSIndex(self, i): self._sIndexAux=i
    def sIndex(self): return self._sIndexAux
    def info(self):
        print nodeText(self.aux())
        if self.main():
            print "depends on ", self.main().treeposition(), nodeText(self.main())
    

def orderSplitSentences(splits):
    """
    Return SentenceSplitPair objects in order
    """
    # print "orderSplitSentences"
    
    # find root of set of sentences
    srootlist = [ sp for sp in splits if not sp.main() ]
    assert len(srootlist)==1, "Cannot find the root of split sentence tree"
    if DEBUG_SENTENCE_SPLIT: print "sroot - found ", len(srootlist)
    sroot = srootlist[0]
    if DEBUG_SENTENCE_SPLIT: print nodeText(sroot.aux())
    
    ordered = [sroot.aux()]
    fullOrderedInfo=[sroot]
    
    endlessLoopCounter = 0
    while len(fullOrderedInfo) < len(splits) and endlessLoopCounter<len(splits):
        endlessLoopCounter += 1
        for sp in splits:
            try:
                # if sp.aux() in ordered: continue # already added
                index_id(ordered, sp.aux())
                continue # already added
            except StopIteration:
                rt = sp.mainRoot()

                try:
                    i = index_id(ordered, rt)
                except StopIteration:
                    continue # skip this until root has been included
                
                link = fullOrderedInfo[i]
                sp.setMainLink(link)
                if DEBUG_SENTENCE_SPLIT: 
                    print "--- Adding:"
                    sp.info()
                    for i,s in enumerate(ordered): print i, nodeText(s)
                try:
                    # assert sp.aux() not in ordered, "Aux sentence already seen"
                    index_id(ordered, sp.aux())
                    assert True, "Aux sentence already seen"
                except StopIteration:
                    pass
                
                if sp.after():
                    ordered.insert(i+1,sp.aux())
                    fullOrderedInfo.insert(i+1,sp)
                else:
                    ordered.insert(i,sp.aux())
                    fullOrderedInfo.insert(i,sp)
    
    
    if DEBUG_SENTENCE_SPLIT: 
        print "Original splits:", len(splits)
        print "Ordered splits: ", len(fullOrderedInfo)
        if False and not endlessLoopCounter<len(splits): # maybe this is OK
            print "\nFull list of main sentences:"
            for sp in splits: 
                if sp.mainRoot(): print nodeText(sp.mainRoot())
                else: print "<None>" 
                
            raise SystemExit, "ordering split sentences"
    
    if False: # print the output
        for i,sp in enumerate(fullOrderedInfo):
            print i,": ",nodeText(sp.aux())
            if sp.main():
                print "needs ", 
                print fullOrderedInfo.index(sp.getMainLink()),  
                # print sp.getMainLink(),  
                print "at position", sp.main().treeposition(),":\t",nodeText(sp.main())
            print "-----------------"
    return fullOrderedInfo
    




# -----------------------------------------------------


def doDoc(doc_pair, linenums):
    """
    Find paraphrases in file f and return
    a list of sync grammar rules
    """
    assert isinstance(doc_pair, txt2txtgen.formats.BaseArticle.BasePairedArticle), "Expecting document type to be BasePairedArticle"
    
    fullResultsList = []
    fullSingleResultsList = []
    
    src_doc =  doc_pair.get_source()
    tgt_doc = doc_pair.get_target()

    matchlist1 = align.align_nodes_multisentence_no_corefs(src_doc.parse_info(), tgt_doc.parse_info(), linenums)
    matchlist2 = align.align_nodes_multisentence_corefs(src_doc.parse_info(), tgt_doc.parse_info(), linenums)
    
    matchlist = matchlist1 + matchlist2
    
    # info.printAllMatchListInfo( matchlist )

    lineSPairs = txt2txtgen.tasks.QGTestSetup.difflistSentencePairs(linenums)
    for (src_linenums, tgt_linenums) in lineSPairs.items():
        if len(tgt_linenums) < 2: continue
        
        # TODO: iterate through all the tgt_linenums
        
        srctree = src_doc.sentence(src_linenums)
        tgt1tree = tgt_doc.sentence(tgt_linenums[0])
        tgt2tree = tgt_doc.sentence(tgt_linenums[1])
        spl_list, single_list = txt2txtgen.qtsg.SplitSentences.syncGrammarSentenceSplit( srctree, tgt1tree, tgt2tree, matchlist )
        
        # TODO: get this to work better; currently not splitting successfully
        
        fullResultsList.extend(spl_list)
        fullSingleResultsList.extend(single_list)
    
    return fullResultsList, fullSingleResultsList

    


def syncGrammarSentenceSplit( src, tgt1, tgt2, matchlist ):
    """
    Learn a grammar where the source tree can be transformed into the target tree.
    The assumption of this grammar is that the source tree node will feature
    in the target tree node as a related constituent,
    but at the same time the source node can be transformed into a second,
    stand-alone sentence.
    
    We try both tgtTree1 and tgtTree2 as the main sentence, and the other as the satellite sentence.
    """
    
    srcTree = src.parseTree()
    tgtTree1 = tgt1.parseTree()
    tgtTree2 = tgt2.parseTree()
    
    # we are expecting tgtSepSentenceTree to be a separately parsed sentence
    assert tgtTree1.tag()=="ROOT", "tgtTree1 not root of tree"
    assert tgtTree2.tag()=="ROOT", "tgtTree2 not root of tree"
    assert len(tgtTree1)>0, "tgtTree1 has no children"
    assert len(tgtTree2)>0, "tgtTree2 has no children"

    # split match list into sentences    
    mlT1 = [(ms, mt) for (ms, mt) in matchlist if mt.root() is tgtTree1.root() ]
    mlT2 = [(ms, mt) for (ms, mt) in matchlist if mt.root() is tgtTree2.root() ]
    
    # handle case where sentence splits neatly into two
    
    addCommonAncestorMatch(mlT1, mlT2, srcTree[0], tgtTree1[0], tgtTree2[0])
    
    splitSentenceQGResults, singleSentenceQGResults = _splitSentenceRules(mlT1, mlT2, tgtTree2[0], True)
    sp2, sg2 = _splitSentenceRules(mlT2, mlT1, tgtTree1[0], False)
    splitSentenceQGResults.extend(sp2)
    singleSentenceQGResults.extend(sg2)
    return splitSentenceQGResults, singleSentenceQGResults
    
    
def addCommonAncestorMatch(mlT1, mlT2, src, tgt1, tgt2):
    # cover case where srcTree neatly splits, and the split is above mlT1 and T2
    setT1 = set( ms.treeposition() for (ms, _mt) in mlT1 )
    setT2 = set( ms.treeposition() for (ms, _mt) in mlT2 )
    
    commonAncestorsLinks = set((commonAncestorPositions(p1,p2) for p1 in setT1 for p2 in setT2))
    if len(commonAncestorsLinks)==1 and not commonAncestorsLinks <= setT1 and not commonAncestorsLinks <= setT2:
        # add in a link to this common ancestor
        ca_pos = commonAncestorsLinks.pop()
        mlT1.append( (src.root()[ca_pos],tgt1) )
        mlT2.append( (src.root()[ca_pos],tgt2) )


def identifySplitPoints(mlT1, mlT2):
    pass
    setT1 = set( ms.treeposition() for (ms, _mt) in mlT1 if ms.has_content() )
    setT2 = set( ms.treeposition() for (ms, _mt) in mlT2 if ms.has_content() )
    commonAncestorsLinks = set((commonAncestorPositions(p1,p2) for p1 in setT1 for p2 in setT2))
    splitNodes = [ ca for ca in commonAncestorsLinks if isSplitNode(ca, setT1, setT2 ) ]
    if PRINT_DEBUG_SPLIT: 
        print "commonAncestorsLinks:", commonAncestorsLinks
        print "splitNodes:", splitNodes
    return splitNodes


def isSplitNode( n, s1Nodes, s2Nodes ):
    """
    Expecting position tuples
    """
    descendents1 = set([ d for d in s1Nodes if _isDescendent(d, n) ])
    descendents2 = set([ d for d in s2Nodes if _isDescendent(d, n) ])
    if True and PRINT_DEBUG_SPLIT: 
        print 
        print n
        print "d1:", descendents1
        print "d2:", descendents2
        print "&:", descendents1 & descendents2
        print "^:", descendents1 ^ descendents2
        print "|:", descendents1 | descendents2
    if len(descendents1)>0 and len(descendents2)>0 and len(descendents1&descendents2)==0:
        return True # clean split
    else:
        return False
    
    


def _splitSentenceRules(matchListT1, matchListT2, tgtSepSentenceTree, sepSentenceAfter):
    splitSentenceQGResults=[]
    singleSentenceQGResults=[]
    splitNodes = identifySplitPoints(matchListT1, matchListT2)
    # extend splitNodes to include parents
    for m in matchListT1+matchListT2:
        if m[0].treeposition() in splitNodes: continue 
        for s in splitNodes:
            if _isDescendent(s, m[0].treeposition()):
                splitNodes.append(m[0].treeposition())
                # print m[0].treeposition(), "---", s
                
    # nodes creating the target separate sentence
    sepSentenceMatchesT2 = [(ms,mt) for (ms,mt) in matchListT2 if ms.treeposition() in splitNodes and mt is tgtSepSentenceTree]
    for (ms2, mt2) in sepSentenceMatchesT2:
        syncSrc2, syncTgt2 = extract_grammar_at_node( matchListT2, ms2, mt2 )
        # find matching node for first target tree
        sepSentenceMatchesT1 = [(ms1, mt1) for (ms1, mt1) in matchListT1 if ms1 is ms2]
        for (ms1, mt1) in sepSentenceMatchesT1:
            try:
                syncSrc1, syncTgt1 = extract_grammar_at_node( matchListT1, ms1, mt1 )
                _splitSentenceTest(syncSrc1, syncSrc2, ms1, ms2)
                splitSentenceQGResults.append( ( syncSrc1, syncTgt1, syncSrc2, syncTgt2, sepSentenceAfter ) )
            except (ValueError, AttributeError), e:
                if PRINT_DEBUG_SYNC: 
                    print "Sync tree pair discarded"
                    print e
                pass
        
    
    # TODO: learn how to convert single sentence to ST, embedding ST ( S () )
    
    return splitSentenceQGResults, singleSentenceQGResults

    

def _splitSentenceTest(syncSrc1, syncSrc2, phrasetree1, phrasetree2):
    """
    Do the rules tell us anything about how to split the sentence?
    """
    src1LinkPos = set([ tuple(syncSrc1.findLink(l, phrasetree1)) for l in syncSrc1.links() ])
    src2LinkPos = set([ tuple(syncSrc2.findLink(l, phrasetree2)) for l in syncSrc2.links() ])
    if PRINT_DEBUG_SPLIT: print "Set1 links:",src1LinkPos,"\t\tSet2 links:",src2LinkPos
    # Allow T1 to contain nothing new if it contributes to the current sentence
    # but T2 must have new information.
    # if len(src1LinkPos-src2LinkPos)==0: raise ValueError, "No separate information in tgt1"
    if len(src2LinkPos-src1LinkPos)==0: raise ValueError, "No separate information in tgt2"
    
    # don't allow VP to be common between the two trees
    commonPos = src2LinkPos&src1LinkPos
    for l in syncSrc1.links():
        link = syncSrc1.findLink(l, phrasetree1)
        if tuple(link) in src2LinkPos:
            # a common link
            # print link
            ch = syncSrc1.get(link)
            if ch.tag()=="VP": raise ValueError, "Common VP node"



def _removeTwoSentenceCommonNode(syncSrc1, syncSrc2, matchListT1, matchListT2, prefix):
    """
    Identify and remove a node that appears to be in both of the target sentences,
    and is also a currently active link
    """
    raise DeprecationWarning, "Now finding split points before individual pairs"
    # a useful rule splits the node into tgt1 and tgt2,
    # with information on how to structure both
    src1LinkPos = set([ tuple(syncSrc1.findLink(l)) for l in syncSrc1.links() ])
    src2LinkPos = set([ tuple(syncSrc2.findLink(l)) for l in syncSrc2.links() ])
    if PRINT_DEBUG_SPLIT: print "Set1 links:",src1LinkPos,"\t\tSet2 links:",src2LinkPos
    
    
    commonAncestorsLinks = set((commonAncestorPositions(p1,p2) for p1 in src1LinkPos for p2 in src2LinkPos))
    if PRINT_DEBUG_SPLIT: 
        print "commonAncestorsLinks:", commonAncestorsLinks
    
    # not sure if I need this test. It might be enough to get a clean split
    # if len(src1LinkPos-src2LinkPos)==0: raise ValueError, "No separate information in tgt1"
    # if len(src2LinkPos-src1LinkPos)==0: raise ValueError, "No separate information in tgt2"
    if len(src1LinkPos-src2LinkPos)==0 or len(src2LinkPos-src1LinkPos)==0:
        print "Rule contains nothing to split the sentences"
        linksToRemove = [ prefix+l for l in (commonAncestorsLinks) ]
        print "linksToRemove:",linksToRemove
        refMatchListT1 = [ (ms,mt) for (ms,mt) in matchListT1 if ms.treeposition() not in linksToRemove ]
        refMatchListT2 = [ (ms,mt) for (ms,mt) in matchListT2 if ms.treeposition() not in linksToRemove ]
        raise SystemExit,"common nodes"
        return refMatchListT1, refMatchListT2, False
    
    ancestorsIn1 = commonAncestorsLinks&src1LinkPos
    ancestorsIn2 = commonAncestorsLinks&src2LinkPos
    
    crossAncestors1 = [ a for a in ancestorsIn1 for d in src2LinkPos if _isDirectDescendent(d, a) ]
    crossAncestors2 = [ a for a in ancestorsIn2 for d in src1LinkPos if _isDirectDescendent(d, a) ]
    if PRINT_DEBUG_SPLIT: 
        print "crossAncestors1:", crossAncestors1
        print "crossAncestors2:", crossAncestors2
    
    if len(crossAncestors1)==0 and len(crossAncestors2)==0:
        # print "Nothing to change"
        return matchListT1, matchListT2, True
        
    # remove the common ancestor nodes
    linksToRemove = [ prefix+l for l in (crossAncestors1+crossAncestors2) ]
    if PRINT_DEBUG_SPLIT: print "linksToRemove:",linksToRemove
    refMatchListT1 = [ (ms,mt) for (ms,mt) in matchListT1 if ms.treeposition() not in linksToRemove ]
    refMatchListT2 = [ (ms,mt) for (ms,mt) in matchListT2 if ms.treeposition() not in linksToRemove ]

    if PRINT_DEBUG_SPLIT: 
        print "\nAfter removing common ancestor nodes,\nrefMatchListT1:"
        printAllMatchListInfo(refMatchListT1)
        print "refMatchListT2:"
        printAllMatchListInfo(refMatchListT2)
        raise SystemExit,"common nodes"
    return refMatchListT1, refMatchListT2, False


def _identifyTwoSentenceNodes(matchListT1, matchListT2):
    """
    Identify the source nodes that link to both target sentences,
    and remove them from the match lists
    """
    raise DeprecationWarning, "This method fails if words are repeated in the two parts of the sentence"
    l1 = set(ms.treeposition() for (ms,mt) in matchListT1)
    l2 = set(ms.treeposition() for (ms,mt) in matchListT2)
    l_common = l1&l2
    if True:
        print "l1:",l1
        print "l2:",l2
        print "int:",l1&l2
        
    if True: # SPIKE: don't use intersecting sets, but set of common ancestors
        print "\n\SPIKE"
        ancestors = set(commonAncestor(ms1, ms2) for (ms1,_mt1) in matchListT1 for (ms2,_mt2) in matchListT2)
        print "Set: ", ancestors
        ancestors.remove((0,))
        print "Set without root: ", ancestors
        l_common = ancestors
    
    # find nodes just above the split
    # these need to be removed from the match lists
    l_above_split=[]
    for l in l_common:
        below1 = set( bl for bl in l1 if _isDirectDescendent(bl, l) )
        below2 = set( bl for bl in l2 if _isDirectDescendent(bl, l) )
        if len(below1 ^ below2)>0:
            l_above_split.append(l)
    for l in l_common:
        for l2 in l_above_split:
            if _isDescendent(l2,l):
                l_above_split.append(l)
    print "\n-------\nNodes above split point:", l_above_split
    
    refMatchListT1 = [ (ms,mt) for (ms,mt) in matchListT1 if ms.treeposition() not in l_above_split ]
    refMatchListT2 = [ (ms,mt) for (ms,mt) in matchListT2 if ms.treeposition() not in l_above_split ]
    
    print "refMatchListT1:"
    printAllMatchListInfo(refMatchListT1)
    print "refMatchListT2:"
    printAllMatchListInfo(refMatchListT2)

    return refMatchListT1, refMatchListT2



def _isDirectDescendent(d, a):
    if len(d)>len(a)+1: return False
    else: return _isDescendent(d, a)

def _isDescendent(d, a):
    """
    Return True if d is a descendent of a
    """
    assert type(d)==tuple, "expecting a tuple giving position"
    assert type(a)==tuple, "expecting a tuple giving position"
    if len(d)<=len(a): return False
    for i in range(len(a)):
        if not d[i]==a[i]: return False
    return True
    
    

def _singleSentenceRules(matchList, tgt):
    """
    Learn how to create the target using matchList links
    """
    raise DeprecationWarning, "_singleSentenceRules() is not used --- SyncGrammar functions used instead"
    # Generate sync grammar rule for each pair of linked nodes 
    singleSentenceQGResults=[]
    sentenceTopmatchList = [ (ms,mt) for (ms,mt) in matchList if mt==tgt ]
    
    print "\n\nIn singleSentenceRules"
    print "Match list for single sentence"
    print tgt.tag(), nodeText(tgt)
    printAllMatchListInfo(matchList)
    
    print "\nMatch list for top level"
    printAllMatchListInfo(sentenceTopmatchList)
    
    for (ph1,ph2) in sentenceTopmatchList:
        try:
            syncSrc, syncTgt = _createLinksAndSyncPair(ph1,ph2,matchList)
            singleSentenceQGResults.append( ( syncSrc, syncTgt ) )
        except ValueError, e:
            if PRINT_DEBUG_SYNC: 
                print "Sync tree pair discarded"
                print e
            pass

    return singleSentenceQGResults


def _createLinksAndSyncPair(srcPh, tgtPh, matchList):
    """
    Identifies the links for this pair of phrases,
    and calls _createSyncPair().
    Raises ValueError if a sync pair cannot be created
    """
    if (srcPh.isLeaf() or tgtPh.isLeaf()): 
        raise ValueError, "Leaf nodes"
        
    if PRINT_DEBUG_SPLIT:
        print "\n----------------------\nCreating single-sentence rule:"
        print "src: ", nodeText(srcPh)
        print "tgt: ", nodeText(tgtPh)
        
    links = linkMatchingNodes(srcPh, tgtPh, matchList, includeDestRoot=True)
    if len(links)==0: 
        raise ValueError, "No links between sync-ed pair"
        
    if PRINT_DEBUG_SPLIT:
        print "Input match list:"
        printAllMatchListInfo(links)
        
    # if either _createSyncPair call fails, it raises ValueError 
    syncSrc, syncTgt = _createSyncPair(srcPh,tgtPh,links)
    
    # We have created a rule for both this phrase and a second sentence
    syncTgt.checkAllLinked()
    # check that all links in tree 2 are to be found in tree 1
    assert set(syncTgt.links()).issubset(set(syncSrc.links())), "Not all target links are present"
    
    if PRINT_RULE_APPLICATION:
        r1 = SyncGrammarRule(syncSrc, syncTgt)
        print "\nRule: \t", r1
        print "Learnt from:\t", nodeText(srcPh), "\t", nodeText(tgtPh)

    return syncSrc, syncTgt
    

def _createSyncPair(srcPh, tgtPh, matchList):
    """
    Create a sync grammar trees to describe the transformation
    from src to tgt, using the links provided.
    """
    if PRINT_DEBUG_SPLIT: 
        print "Trying to create sync pair from"
        print "src: ", nodeText(srcPh)
        print "tgt: ", nodeText(tgtPh)
    try:
        synctree1, synctree2 = SyncTreeGrammar._makeContractedSyncGrammarForPhrase(srcPh, tgtPh, matchList)
        if PRINT_DEBUG_SPLIT: print "Contracted rule created successfully"
        
    except ValueError:
        try:
            links = linkMatchingNodes(srcPh, tgtPh, matchList, includeDestRoot=False)
            links = removeDuplicatedLinksToTargets(links)
            if len(links)==0: raise ValueError,"No linked nodes"
            synctree1, synctree2 = SyncTreeGrammar._makeSyncGrammarForPhrase(srcPh, tgtPh, links)
            
            # Force all tree pairs to share the same set of links
            refinedLinks = SyncTreeGrammar._sharedLinkSubset(links, synctree1, synctree2)
            if PRINT_DEBUG_SPLIT:
                print "Source tree links:", synctree1.links()
                # print "Refined links:", refinedLinks
                printAllMatchListInfo(refinedLinks)
            synctree1, synctree2 = SyncTreeGrammar._makeSyncGrammarForPhrase(srcPh, tgtPh, refinedLinks)
            
            if PRINT_DEBUG_SPLIT:
                print "\n------\nAfter refining links:"
                print "Src:", synctree1
                print "Tgt:", synctree2

            # check that all links in tree 2 are to be found in tree 1
            if not set(synctree2.links()).issubset(set(synctree1.links())):
                refinedLinks = _linkSubset(links, synctree1, synctree2)
                synctree1, synctree2 = SyncTreeGrammar._makeSyncGrammarForPhrase(srcPh, ph2, refinedLinks)
                
            if not set(synctree2.links()).issubset(set(synctree1.links())):
                raise ValueError, "Cannot explain all target links"
                
            assert synctree1.matches(srcPh), "Match failure"
            assert synctree2.matches(tgtPh), "Match failure"
        except ValueError, e:
            if PRINT_DEBUG_SPLIT:
                print "Sync tree pair discarded"
                print e
            raise # exit the function here if no rule created
    assert synctree1, "No synctree1 created"
    assert synctree2, "No synctree2 created"
    if PRINT_DEBUG_SPLIT:
        print "Sync tree pair created successfully"
        print "Src:", synctree1
        print "Tgt:", synctree2
    return synctree1, synctree2



def removeDuplicateQtsgRules( sgItems, oldSyncGrammarDict = [] ):
    """
    Create a list of SyncGrammarRule from elements of the rules:
    src and tgt pairs, for main and aux sentences.
    
    Each rule should appear only once, with a count of 
    instances found in the training data
    """    
    syncGrammarDict = dict() # temporary store
    
    # copy across old ruleset
    for r in oldSyncGrammarDict:
        k = r.key()
        syncGrammarDict[k] = r
        
    for (s1, t1, s2, t2, satAfter) in sgItems:
        r = SplitSentenceRule(s1, t1, s2, t2, satAfter)
        k = r.key() # need string representation, not actual object
        if False: print k; print
        
        if k in syncGrammarDict: 
            syncGrammarDict[k].inc()
            if False and PRINT_DEBUG: print k, "already in dictionary ", syncGrammarDict[k].count()
        else:
            syncGrammarDict[k] = r
    return syncGrammarDict.values()


def printRuleSetInfo( rules ):
    print "Count of rules: \t\t", len(rules)
    
    
QSGSplitRulesPickleFile = "splitrules.pickle"
def saveQSGRules( rules, task, filename=QSGSplitRulesPickleFile ):
    SyncTreeGrammar.saveQSGRules(rules, task, filename=filename)
    
def loadQSGRules(task, filename=QSGSplitRulesPickleFile):
    return SyncTreeGrammar.loadQSGRules(task,filename=filename)


def printRuleSet( resultsList, minCount=2, sort=True ):
    """ Print out a set of rules, involving rule objects """
    if sort:
        resultsList.sort(key=attrgetter('_count'), reverse=True)
    for r in resultsList:
        if r.count() < minCount: continue
        print r.count(), "\t\t",
        if r.auxAfter(): print "after main"
        else: print "before main"
        print "\t",r._sent1Rule
        print "\t",r._sent2Rule
        print


class SplitSentenceRule(object):
    """
    A rule relates a source SyncGrammarTree to a pair of target SyncGrammarTree.
    Main refers to the tree that forms part of the target sentence.
    Aux refers to a separate sentence tree, also generated from the source.
    """
    def __init__(self, s1, t1, s2, t2, satAfter, count=1):
        self._count = count
        self._sent1Rule = SyncGrammarRule(s1,t1)
        self._sent2Rule = SyncGrammarRule(s2,t2)
        
        # does t2 come before or after the main sentence
        self._satelliteAfter = satAfter


    def isSuitable( self, srcTree, targetTreeNode=None ):
        return self._sent1Rule.isSuitable(srcTree, targetTreeNode) \
            and self._sent2Rule.isSuitable(srcTree, None) 

    def __str__(self):
        s = str(self._sent1Rule) + "\n" + str(self._sent2Rule)
        s += "\n" + str(self.count()) + "\tAfter:"+str(self._satelliteAfter)
        return s

    def key(self):
        """
        Returns a string representation that can be used 
        as a dictionary lookup
        """
        k1 = self._sent1Rule.key()
        k2 = self._sent2Rule.key()
        return k1 + "\n" + k2 + ";" + str(self._satelliteAfter)
        
    def inc(self, extra=1):
        """
        Increment the counter for the number of times this rule
        is seen during training.
        """
        self._count += extra


    def count(self):
        """
        Return the number of times this rule has been
        seen during training
        """
        return self._count

    def auxAfter(self):
        return self._satelliteAfter
    
    def introducesContent(self):
        """
        Returns True if children in the target tree
        will be inserted by the grammar, rather
        than coming from the source tree
        """
        return self._sent1Rule.introducesContent() or self._sent2Rule.introducesContent()

    

## {{{ http://code.activestate.com/recipes/576426/ (r2)
def index_id(a_list, elem):
    """
    Return the index of an item elem in the list, using identity rather than equality
    """
    return (index for index, item in enumerate(a_list) if item is elem).next()
## end of http://code.activestate.com/recipes/576426/ }}}
        
