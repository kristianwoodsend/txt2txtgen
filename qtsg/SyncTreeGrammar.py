"""
Investigation how to get sync grammar to relate sentences to highlights
"""


import txt2txtgen.config.Config as Config
import txt2txtgen


import nltk.probability
import cPickle as pickle

from itertools import count, izip
import sys, os

from QGDefs import *
from QGCore import *
from info import printAllMatchListInfo
import align


# The depth of the source tree that we will consider linking in a rule
SOURCE_NODE_DEPTH = 5
TARGET_NODE_DEPTH = 5
                    



    
def investigateDoc(doc_pair, linenums=None):
    """
    Find paraphrases in file f and return
    a list of sync grammar rules
    """
    assert isinstance(doc_pair, txt2txtgen.formats.BaseArticle.BasePairedArticle), "Expecting document type to be BasePairedArticle"

    src_doc =  doc_pair.get_source()
    tgt_doc = doc_pair.get_target()
    matchlist1 = align.align_nodes_multisentence_no_corefs(src_doc.parse_info(), tgt_doc.parse_info(), linenums)
    grammar1 = extract_grammar(matchlist1)
    matchlist2 = align.align_nodes_multisentence_corefs(src_doc.parse_info(), tgt_doc.parse_info(), linenums)
    grammar2 = extract_grammar(matchlist2)
    return (grammar1+grammar2)
    
    
def investigateDoc_with_linenumbering(d, linenums):
    """
    Find paraphrases in file f and return
    a list of sync grammar rules.
    Use line-numbering to reduce the search space
    """
    matchlist1 = align.align_nodes_multisentence_no_corefs(d.parse_info(), d.getSimpleArticle().parse_info(), linenums)
    grammar1 = extract_grammar(matchlist1)
    matchlist2 = align.align_nodes_multisentence_corefs(d.parse_info(), d.getSimpleArticle().parse_info(), linenums)
    grammar2 = extract_grammar(matchlist2)
    return (grammar1+grammar2)



def investigateTreesAndAlignments(d, srcSIndex, tgtSIndex):
    """
    Return the parse trees and word alignments for this
    pair of source sentence and target sentence indices
    """
    src  = d.sentence(srcSIndex)
    tgt = d.highlight(tgtSIndex)
    
    # get matchList, and trim so it is only leaf nodes
    matchList = align.align_nodes(src, tgt)
    matchList2 = [ (s,t) for (s,t) in matchList if s.isLeaf() and t.isLeaf() ]
    
    leafAlignments = [ (s.token().index, t.token().index) for (s,t) in matchList2 ]
    return src, tgt, leafAlignments



def extract_grammar( matchlist ):     
    rules=[]
    for (ph1,ph2) in matchlist:
        ( synctree1, synctree2 ) = extract_grammar_at_node( matchlist, ph1, ph2 )
        if synctree1 is not None and synctree2 is not None:
            rules.append(( synctree1, synctree2 ))
    return rules
        
        
        
def extract_grammar_at_node( matchlist, ph1, ph2 ):     
    """
    Extract a quasi-sync tree substitution grammar from these pairs of matched nodes
    """
    synctree1=None
    synctree2=None
    
    if (ph1.isLeaf() or ph2.isLeaf()): return ( synctree1, synctree2 )

    if PRINT_DEBUG_SYNC:
        print "\n----------------------\nTrying to create rule:"
        print "src: ", nodeText(ph1)
        print "tgt: ", nodeText(ph2)

    try:
        # possibly a contraction of the levels in the source tree would also be successful
        links = link_subtree_nodes(ph1, ph2, matchlist, includeDestRoot=True)
        if len(links)==0: return ( synctree1, synctree2 )
        if PRINT_DEBUG_SYNC and PRINT_MATCH_LIST:
            print "Input match list for possible contracted rule:"
            printAllMatchListInfo(links)

        synctree1, synctree2 = _makeContractedSyncGrammarForPhrase(ph1, ph2, links)
        if PRINT_DEBUG_SYNC: print "Contracted rule created successfully"
    except ValueError:
        try:
            links = link_subtree_nodes(ph1, ph2, matchlist, includeDestRoot=False)
            if len(links)==0: return ( synctree1, synctree2 )
            synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, links)
            
            # Force all tree pairs to share the same set of links
            refinedLinks = _sharedLinkSubset(links, synctree1, synctree2)
            if PRINT_DEBUG_SYNC and PRINT_MATCH_LIST:
                print "Source tree links:", synctree1.links()
                print "Refined links:"
                printAllMatchListInfo(refinedLinks)
            synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, refinedLinks)
            
            if PRINT_DEBUG_SYNC and PRINT_MATCH_LIST:
                print "\n------\nAfter refining links:"
                print synctree1
                print synctree2

            # check that all links in tree 2 are to be found in tree 1
            if not set(synctree2.links()).issubset(set(synctree1.links())):
                refinedLinks = _linkSubset(links, synctree1, synctree2)
                synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, refinedLinks)
                
            if not set(synctree2.links()).issubset(set(synctree1.links())):
                raise ValueError, "Cannot explain all target links"
                
            assert synctree1.matches(ph1), "Match failure"
            assert synctree2.matches(ph2), "Match failure"
        except ValueError, e:
            if PRINT_DEBUG_SYNC: 
                print "Sync tree pair discarded"
                print e
            synctree1=None
            synctree2=None
            pass
        
    try:
        if synctree1 and synctree2:
            changed = synctree2.removeMultipleLinks()
            synctree2.checkAllLinked(single=True)
            # check that all links in tree 2 are to be found in tree 1
            assert set(synctree2.links()).issubset(set(synctree1.links())), "Not all target links are present"
            
            if changed:
                # we should be able to make a full set of links without the multiple links
                refinedLinks = _sharedLinkSubset(links, synctree1, synctree2)
                synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, refinedLinks)
                if PRINT_DEBUG_SYNC: # sometimes this is not working
                    print "refined to remove multiple links"
                    print synctree1
                    print synctree2
                    assert set(synctree2.links()).issubset(set(synctree1.links())), "Not all target links are present"
                if not set(synctree2.links()).issubset(set(synctree1.links())):
                    raise ValueError, "Cannot get clean rule after removing multiple links"
                    
            
            
            
            if PRINT_DEBUG:
                print
                print "List of matching nodes:"
                for l in links: print l[0].treeposition(), nodeText(l[0]), " --- ", l[1].treeposition(), nodeText(l[1])
                print
                print "Rule:\t", synctree1, "\t", synctree2
                
            if PRINT_DEBUG_SYNC: # print out the rules and examples
                # print "synctree1 is type", type(synctree1)
                print "Rule:\t", synctree1, "\t", synctree2
                print "Text:\t", nodeText(ph1), "\t", nodeText(ph2)
                # print "E.g.:\t", ph1, "\t;\t", ph2
                print
            if PRINT_RULE_APPLICATION:
                r = SyncGrammarRule(synctree1,synctree2)
                if not r.isIdentical():
                    print "\nRule: \t", r
                    print "Learnt from:\t", nodeText(ph1), "\t", nodeText(ph2)
                    print "Source phrase tree:"
                    print ph1
                    print "Target phrase tree:"
                    print ph2
                    print "--------------------------------------------"
                
            # raise SystemExit
    except ValueError, e:
        if PRINT_DEBUG_SYNC: 
            print "Sync tree pair discarded"
            print e
        synctree1=None
        synctree2=None
        pass
            
    return ( synctree1, synctree2 )

    
    
def syncGrammar( tree1, tree2 ):     
    """
    N.B. This originally allowed an initialMatchList to be passed in, 
    to allow QTSG to be used with other alignment mechanisms,
    but the default initialMatchList=[] is causing problems, as it is the same reference every time.
    could change to initialMatchList=None, then if not initialMatchList: initialMatchList=[] to create a new reference
    """
    raise DeprecationWarning, "Should use syncGrammar(), where linking has been separated from grammar extraction"
    # TODO: separate the matching and the QTSG rule functions
    
    initialMatchList = []
    assert len(initialMatchList)==0, "Still got a match list from before"
    if PRINT_DEBUG: print "Sentence: ", tree1.leaves()
    if PRINT_DEBUG: print "Highlight: ", tree2.leaves()
    matchList = _createPhraseMatchList(tree1, tree2, initialMatchList, doEquivNodes=True)
    
    
    # Modifications in children of node?
    # Generate sync grammar rule for each pair of linked nodes 
    syncGrammarResults=[]
    if PRINT_DEBUG: print "\n\nLooking at deletions, insertions at node"
    for (ph1,ph2) in matchList:
        if (ph1.isLeaf() or ph2.isLeaf()): continue
        
        # if not nodeText(ph1)=="was going from the airport in Long Beach , California , to the Brown Field airport in San Diego": continue
        
        if PRINT_DEBUG_SYNC:
            print "\n----------------------\nTrying to create rule:"
            print "src: ", nodeText(ph1)
            print "tgt: ", nodeText(ph2)
        
        # if single words are linked, then len(links)==0
        # we don't want this behaviour as it teaches us nothing about paraphrasing
        #assert len(links)>0, "Nothing linking underneath the tree:\n%s\n%s" %(nodeText(ph1),nodeText(ph2))
        
        synctree1=None
        synctree2=None
        try:
            # possibly a contraction of the levels in the source tree would also be successful
            links = linkMatchingNodes(ph1, ph2, matchList, includeDestRoot=True)
            if len(links)==0: continue
            if PRINT_DEBUG_SYNC and PRINT_MATCH_LIST:
                print "Input match list:"
                printAllMatchListInfo(links)
                
                
                
            synctree1, synctree2 = _makeContractedSyncGrammarForPhrase(ph1, ph2, links)
            if PRINT_DEBUG_SYNC: print "Contracted rule created successfully"
            
        except ValueError:
            try:
                links = linkMatchingNodes(ph1, ph2, matchList, includeDestRoot=False)
                if len(links)==0: continue
                synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, links)
                
                # Force all tree pairs to share the same set of links
                refinedLinks = _sharedLinkSubset(links, synctree1, synctree2)
                if PRINT_DEBUG_SYNC and PRINT_MATCH_LIST:
                    print "Source tree links:", synctree1.links()
                    print "Refined links:"
                    printAllMatchListInfo(refinedLinks)
                synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, refinedLinks)
                
                if PRINT_DEBUG_SYNC and PRINT_MATCH_LIST:
                    print "\n------\nAfter refining links:"
                    print synctree1
                    print synctree2
    
                # check that all links in tree 2 are to be found in tree 1
                if not set(synctree2.links()).issubset(set(synctree1.links())):
                    refinedLinks = _linkSubset(links, synctree1, synctree2)
                    synctree1, synctree2 = _makeSyncGrammarForPhrase(ph1, ph2, refinedLinks)
                    
                if not set(synctree2.links()).issubset(set(synctree1.links())):
                    raise ValueError, "Cannot explain all target links"
                    
                assert synctree1.matches(ph1), "Match failure"
                assert synctree2.matches(ph2), "Match failure"
            except ValueError, e:
                if PRINT_DEBUG_SYNC: 
                    print "Sync tree pair discarded"
                    print e
                synctree1=None
                synctree2=None
                pass
            
        try:
            if synctree1 and synctree2:
                synctree2.removeMultipleLinks()
                synctree2.checkAllLinked(single=True)
                # check that all links in tree 2 are to be found in tree 1
                assert set(synctree2.links()).issubset(set(synctree1.links())), "Not all target links are present"
                
                
                
                if PRINT_DEBUG:
                    print
                    print "List of matching nodes:"
                    for l in links: print l[0].treeposition(), nodeText(l[0]), " --- ", l[1].treeposition(), nodeText(l[1])
                    print
                    print "Rule:\t", synctree1, "\t", synctree2
                    
                
                
                syncGrammarResults.append( ( synctree1, synctree2 ) )
    
                if PRINT_DEBUG_SYNC: # print out the rules and examples
                    # print "synctree1 is type", type(synctree1)
                    print "Rule:\t", synctree1, "\t", synctree2
                    print "Text:\t", nodeText(ph1), "\t", nodeText(ph2)
                    # print "E.g.:\t", ph1, "\t;\t", ph2
                    print
                if PRINT_RULE_APPLICATION:
                    r = SyncGrammarRule(synctree1,synctree2)
                    if not r.isIdentical():
                        print "\nRule: \t", r
                        print "Learnt from:\t", nodeText(ph1), "\t", nodeText(ph2)
                        print "Source phrase tree:"
                        print ph1
                        print "Target phrase tree:"
                        print ph2
                        print
                        print "Whole source sentence:"
                        print tree1
                        print "Whole target sentence:"
                        print tree2
                        print "--------------------------------------------"
                    
                # raise SystemExit
        except ValueError, e:
            if PRINT_DEBUG_SYNC: 
                print "Sync tree pair discarded"
                print e
            synctree1=None
            synctree2=None
            pass
            
        
    return syncGrammarResults



def link_subtree_nodes(src, tgt, matchlist, includeDestRoot=False):
    """
    Returns a subset of the matchlist 
    so that every child of destTree is linked (if possible)
    to children or grandchildren of srcTree
    """
    
    if PRINT_DEBUG_LINKING: 
        print "Link set for :" , src.treeposition(), "---", tgt.treeposition()
        pass
        for m in matchlist:
            if m[0].isDescendent(src): print m[0].treeposition(), nodeText(m[0])
    
    refML = [ m for m in matchlist if m[0].isDescendent(src) and m[1].isDescendent(tgt) ]
    if includeDestRoot:
        refML.extend([ m for m in matchlist if m[0].isDescendent(src) and m[1] is tgt])
    if PRINT_DEBUG_LINKING: printAllMatchListInfo(refML)
    return refML
    


def _makeSyncGrammarForPhrase(ph1, ph2, links):
    """
    Creates a pair of sync grammar trees for ph1 and ph2.
    Raises ValueError if the trees cannot be synchronized
    """
    handle_unlinked_content = SyncGrammarTree.NO_UNLINKED_CONTENT # need to allow links, even if we discard these rules later
    
    if PRINT_DEBUG: print "Starting _makeSyncGrammarForPhrase() on ", ph1.treeposition(), nodeText(ph1), "---", ph2.treeposition(), nodeText(ph2) 
    try:
        # first attempt: explain all target from links, no substitutions allowed
        if PRINT_DEBUG: print "*** starting first pass assessSyncTreeQuality(), no substitutions"
        assessSyncTreeQuality(ph1, links, linkOffset=0, substituteUnlinked=True, maxSubstitutions=0)
        assessSyncTreeQuality(ph2, links, linkOffset=1)
        synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,links,0, includeUnlinkedText=handle_unlinked_content)
        synctree2 = SyncGrammarTree.createFromPhraseTree(ph2,links,1, includeUnlinkedText=handle_unlinked_content)
        
        # don't use assessSyncRuleQuality, as it is unable to spot stop-words
        #assessSyncRuleQuality(synctree1, maxSubstitutions=0)
        #assessSyncRuleQuality(synctree2, maxSubstitutions=0)
    except ValueError, e:
        # second pass: make substitutions in source and target trees
        if PRINT_DEBUG: print "*** starting second pass assessSyncTreeQuality() with substitutions"; print e
        try:
            MAX_SUB = 5
            assessSyncTreeQuality(ph1, links, linkOffset=0, substituteUnlinked=True, maxSubstitutions=MAX_SUB)
            assessSyncTreeQuality(ph2, links, linkOffset=1, substituteUnlinked=True, maxSubstitutions=MAX_SUB) 
            if PRINT_DEBUG: print "*** passed 2nd test assessSyncTreeQuality()"
            synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,links,0, includeUnlinkedText=SyncGrammarTree.INCLUDE_UNLINKED)
            if PRINT_DEBUG: print "*** calling assessSyncRuleQuality(synctree1)"
            assessSyncRuleQuality(synctree1, maxSubstitutions=MAX_SUB)
            if PRINT_DEBUG: print "*** passed assessSyncRuleQuality(synctree1)"; print synctree1
            synctree2 = SyncGrammarTree.createFromPhraseTree(ph2,links,1, includeUnlinkedText=SyncGrammarTree.INCLUDE_UNLINKED)
            assessSyncRuleQuality(synctree2, maxSubstitutions=MAX_SUB)
            if PRINT_DEBUG: print "*** passed assessSyncRuleQuality(synctree2)"
            assessCombinedSyncRuleQuality(synctree1, synctree2)
            if PRINT_DEBUG: 
                print "*** second pass with substitutions completed"
                print "synctree1: ", synctree1 
                print "synctree2: ", synctree2 
        except ValueError, e:
            # third pass: only allow substituted text in the target, and delete unlinked content in source
            if PRINT_DEBUG: print "*** starting third pass with substitutions"; print e
            try:
                MAX_SUB = 5
                assessSyncTreeQuality(ph1, links, linkOffset=0, substituteUnlinked=False, maxSubstitutions=0)
                assessSyncTreeQuality(ph2, links, linkOffset=1, substituteUnlinked=True, maxSubstitutions=MAX_SUB)
                if PRINT_DEBUG: print "*** passed 3rd test of assessSyncTreeQuality()"
                synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,links,0, includeUnlinkedText=SyncGrammarTree.INCLUDE_UNLINKED_NO_CONTENT)
                synctree2 = SyncGrammarTree.createFromPhraseTree(ph2,links,1, includeUnlinkedText=SyncGrammarTree.INCLUDE_UNLINKED)
                assessSyncRuleQuality(synctree1, maxSubstitutions=MAX_SUB)
                assessSyncRuleQuality(synctree2, maxSubstitutions=MAX_SUB)
                if PRINT_DEBUG: 
                    print "*** third pass with substitutions completed"
                    print "synctree1: ", synctree1 
                    print "synctree2: ", synctree2 
                
            except ValueError, e:
                # fourth pass: only allow substituted text in the target, and delete complete unlinked nodes in source
                if PRINT_DEBUG: print "*** starting fourth pass with substitutions in target, deleted nodes in source"; print e
                MAX_SUB = 5
                assessSyncTreeQuality(ph1, links, linkOffset=0, substituteUnlinked=False, maxSubstitutions=0)
                assessSyncTreeQuality(ph2, links, linkOffset=1, substituteUnlinked=True, maxSubstitutions=MAX_SUB)
                if PRINT_DEBUG: print "*** passed 4th test of assessSyncTreeQuality()"
                synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,links,0, includeUnlinkedText=SyncGrammarTree.UNLINK_NODE)
                synctree2 = SyncGrammarTree.createFromPhraseTree(ph2,links,1, includeUnlinkedText=SyncGrammarTree.INCLUDE_UNLINKED)
                assessSyncRuleQuality(synctree1, maxSubstitutions=MAX_SUB)
                assessSyncRuleQuality(synctree2, maxSubstitutions=MAX_SUB)
                if PRINT_DEBUG: 
                    print "*** fourth pass with substitutions and deletions completed"
                    print "synctree1: ", synctree1 
                    print "synctree2: ", synctree2 
                    
    # pair of sync trees created successfully
    return synctree1, synctree2 


def _makeContractedSyncGrammarForPhrase(ph1, ph2, links):
    """
    If the rule is of the form X(X#1 Y#0) -> X#1, 
    we can learn this rule by forcing in an extra layer in the target tree
    so the rule is learnt as X(X#1 Y#0) -> X(X#1).
    This avoids learning the structure of X#1 at the same time as the deletion of Y
    """
    assert len(links)>0, "No links in _makeContractedSyncGrammarForPhrase()"
    if PRINT_DEBUG: print "In _makeContractedSyncGrammarForPhrase"
    
    # if we allow STs to be extracted into separate statements, then 
    # contracted target rule of ST -> ST is no use
    if ph2.tag()=="ST":
        raise ValueError, "Not creating a contracted target tree that repeats ST node"


    srcNodesInLinks=[ls for (ls,lt) in links if lt is ph2]
    if len(srcNodesInLinks)==0: raise ValueError, "Cannot create contracted tree"
    _depth, bestPh1 = min((len(ph.treeposition()),ph) for ph in srcNodesInLinks)
    
    relatedSrcNode = bestPh1

    cutdownLinks = [(relatedSrcNode, ph2)]
    if PRINT_DEBUG_SYNC:
        print "cutdownLinks list:"
        for (ls,lt) in cutdownLinks:
            print ls.treeposition(), nodeText(ls), "---", lt.treeposition(), nodeText(lt)
                
    # make sync tree for ph1
    assessSyncTreeQuality(ph1, cutdownLinks, linkOffset=0, substituteUnlinked=False, maxSubstitutions=0)
    synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,cutdownLinks,0, includeUnlinkedText=SyncGrammarTree.INCLUDE_UNLINKED_NO_CONTENT)
    #synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,cutdownLinks,0, includeUnlinkedText=SyncGrammarTree.NO_UNLINKED_CONTENT)

    linkNumber = [ l for l in synctree1.links() if cutdownLinks[l-1][1] is ph2 ][0]
    if PRINT_DEBUG_SYNC: print "l num:", linkNumber, "\t links to ", cutdownLinks[linkNumber-1][1].treeposition()
    assert cutdownLinks[linkNumber-1][1] is ph2

    s2_1 = SyncGrammarTree( ph2.tag(), ph2.dep() )
    s2_2 = SyncGrammarTree( ph2.tag(), ph2.dep(), [linkNumber] )
    s2_1.append(s2_2)
    return synctree1, s2_1
    


def _makeContractedSyncGrammarForPhrase_old(ph1, ph2, links):
    """
    If the rule is of the form X(X#1 Y#0) -> X#1, 
    we can learn this rule by forcing in an extra layer in the target tree
    so the rule is learnt as X(X#1 Y#0) -> X(X#1).
    This avoids learning the structure of X#1 at the same time as the deletion of Y
    """
    
    raise DeprecationWarning, "This method seems far more complicated than it needs to be"

    assert len(links)>0, "No links in _makeContractedSyncGrammarForPhrase()"
    if PRINT_DEBUG: print "In _makeContractedSyncGrammarForPhrase"
    
    # if we allow STs to be extracted into separate statements, then 
    # contracted target rule of ST -> ST is no use
    if ph2.tag()=="ST":
        raise ValueError, "Not creating a contracted target tree that repeats ST node"

    srcNodesInLinks=[ls for (ls,lt) in links if lt is ph2]
    if len(srcNodesInLinks)==0: raise ValueError, "Cannot create contracted tree"
    _depth, bestPh1 = min((len(ph.treeposition()),ph) for ph in srcNodesInLinks)
    # print depth, bestPh1.treeposition()
    # assert len(srcNodesInLinks)==1, "Too many nodes link to the target tree"
    
    relatedSrcNode = bestPh1

    cutdownLinks = [(ls,lt) for (ls,lt) in links \
        if ls.isDescendent(relatedSrcNode) or ls is relatedSrcNode]

    if PRINT_DEBUG_SYNC:
        print "cutdownLinks list:"
        for (ls,lt) in cutdownLinks:
            print ls.treeposition(), "---", lt.treeposition()
                
    # make sync tree for ph1
    assessSyncTreeQuality(ph1, cutdownLinks, linkOffset=0, substituteUnlinked=False, maxSubstitutions=0)
    synctree1 = SyncGrammarTree.createFromPhraseTree(ph1,cutdownLinks,0, includeUnlinkedText=SyncGrammarTree.UNLINK_NODE)

    if PRINT_DEBUG_SYNC: print "synctree1.links()", synctree1.links()
    l_set = set([cutdownLinks[l-1][0].treeposition() for l in  synctree1.links()])
    if PRINT_DEBUG_SYNC: print "l_set", l_set

    # this needs debugging, as the assertion is being hit
    if not len(l_set)==1: raise ValueError, "Too many links"
    assert len(l_set)==1, "Too many links"
    # linkNumber = synctree1.links()[0]
    linkNumber = [ l for l in synctree1.links() if cutdownLinks[l-1][1] is ph2 ][0]
    if PRINT_DEBUG_SYNC: print "l num:", linkNumber, "\t links to ", cutdownLinks[linkNumber-1][1].treeposition()
    assert cutdownLinks[linkNumber-1][1] is ph2
    
    # make contracted ph2
    s2_1 = SyncGrammarTree( ph2.tag(), ph2.dep() )
    s2_2 = SyncGrammarTree( ph2.tag(), ph2.dep(), [linkNumber] )
    s2_1.append(s2_2)
    
    if PRINT_DEBUG:
        print "New synctree2: ", s2_1
        print "Exiting _makeContractedSyncGrammarForPhrase"
    return synctree1, s2_1



def _linkSubset(fullLinks, src, tgt):
    
    srcLinks = set(src.links())
    tgtLinks = set(tgt.links())
    missingLinks = srcLinks ^ tgtLinks
    agreedLinks = srcLinks & tgtLinks
    assert len(missingLinks)>0, "No missing links in rule"
    
    if PRINT_DEBUG:
        print
        print "Link subsets don't match"
        print "List of matching nodes:"
        for l in fullLinks: print l[0].treeposition(), nodeText(l[0]), " --- ", l[1].treeposition(), nodeText(l[1])
        print "Source tree links:", srcLinks
        print "Target tree links:", tgtLinks
        print "missingLinks: ", missingLinks
        print "agreedLinks: ", agreedLinks
        
    i = list(missingLinks)[0]-1 # try with first missing link
    linkMissing = fullLinks[i]
    refinedLinks = [ l for l in fullLinks if not commonAncestor(linkMissing[0],l[0]) == l[0].treeposition() ]
    refinedLinks.append(linkMissing)
        
    if PRINT_DEBUG:
        print "List of refinedLinks nodes:"
        for l in refinedLinks: print l[0].treeposition(), nodeText(l[0]), " --- ", l[1].treeposition(), nodeText(l[1])

    return refinedLinks
    
def _sharedLinkSubset(fullLinks, src, tgt):
    
    srcLinks = set(src.links())
    tgtLinks = set(tgt.links())
    agreedLinks = srcLinks & tgtLinks
    ll = [ fullLinks[i-1] for i in agreedLinks ]
    return ll
    


def makeSentencePairTree(tree1, tree2):
    tTreePair = PhraseDependencyTree.PhraseDependencyTree("(ROOT)")
    tTreeSP = PhraseDependencyTree.PhraseDependencyTree( "SP", (tree1[0].copy(), tree2[0].copy() ) )
    tTreePair.append(tTreeSP)
    tTreePair._rel=PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT
    tTreeSP._rel="TOP"
    tTreeSP._indPhrase = True
    tTreePair.markPositions()
    return tTreePair







def findPartialMatches( matchList, highlightPhrases ):
    """
    try to find if highlight nodes have been partially matched to more than one original
    This method is not currently being used
    """
    for (ph2,tok2) in highlightPhrases:
        multipleNodeMatches = [ n1 for (n1,n2) in matchList if n2 is ph2 ] 
        if (len(multipleNodeMatches)>1):
            print "Got more than one match"
            print nodeText(ph2)
            for n1 in multipleNodeMatches: 
                print nodeText(n1),
                print "Parent links as well? ", n1.parent() in multipleNodeMatches
                if (n1.parent() in multipleNodeMatches):
                    print "Parent: ", n1.parent()
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
            print ch1, ch1.label()
            try:
                findInMatchList(ch1,matchList)
            except ValueError:
                pass
        raise SystemExit, "Finished identifyDeletionsAtNode"
    
# this is probably of no use by itself
def getChildPOSList( treeNode ):
    return [ ch.label() for ch in treeNode ]
    
    
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
        if len(f[matchedOffset].treeposition()) < bestMatchPositionLength:
            bestMatch = f
            bestMatchPositionLength = len(bestMatch[matchedOffset].treeposition())
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
    





#SUBSTITUTE_TOKENS = ['.',',',':',';','``',"''",'RB','TO','CC','EX']
# def assessSyncTreeQuality(ph1, ph2, links, maxSubstitutions=0): # original, assess both trees
def assessSyncTreeQuality(ph, links, linkOffset=0, substituteUnlinked=False, maxSubstitutions=0):
    """
    Assess quality sync tree,
    and raise ValueError if we don't want to keep this rule.
    Returns the number of word substitutions that will be required 
    """
    substitutionsSoFar=0
    linkedPhrases = [ l[linkOffset] for l in links ]
    
    # good tree: must have all links for children in target
    # or have acceptable substitutions
    for ch in ph:
        if ch in linkedPhrases: continue
        #elif not ch.isLeaf() and ch.label() in MATCH_STOP_TAGS: continue
        elif not ch.has_content(): continue
        elif not substituteUnlinked: continue # let unlinked phrases pass
        elif substitutionsSoFar <= maxSubstitutions: 
            if ch.isLeaf():
                if PRINT_DEBUG:
                    print "assessSyncTreeQuality: tag of leaf:", ch.tag(), nodeText(ch)
                if ch.tag() == 'NNP':
                    raise ValueError, "Rule tree quality too low, substitute required for proper noun"
                elif ch.tag() == 'CD':
                    raise ValueError, "Rule tree quality too low, substitute required for number"
                else:
                    substitutionsSoFar += len(ch.leaves())
            else:
                substitutionsSoFar += assessSyncTreeQuality(ch, links, \
                    linkOffset=linkOffset, substituteUnlinked=substituteUnlinked, \
                    maxSubstitutions=maxSubstitutions-substitutionsSoFar)
        else:
            if PRINT_DEBUG: 
                print "******** to be discarded: %s *********" % nodeText(ch)
                print "Match discarded after ", substitutionsSoFar, "substitutions"
            raise ValueError, "Rule tree quality too low"
    if PRINT_DEBUG: print "substitutionsSoFar:", substitutionsSoFar
    return substitutionsSoFar
    
def assessSyncRuleQuality(ph, maxSubstitutions=0):
    """
    Check this rule doesn't have too many substitutions
    """
    pass
    substitutionsSoFar=0
    unlinkedChildren = False
    for ch in ph.children():
        if ch.tag() in MATCH_STOP_TAGS: continue
        elif substitutionsSoFar <= maxSubstitutions: 
            if ch.text():
                substitutionsSoFar += 1
                # reject rules where noun substitutions have been used
                if ch.tag().startswith('NNP'):
                    if PRINT_DEBUG: print "assessSyncRuleQuality() fixed text noun:", ch.text()
                    raise ValueError, "Rule contains fixed text noun"
            elif ch.hasChildren():
                substitutionsSoFar += assessSyncRuleQuality(ch, maxSubstitutions=maxSubstitutions-substitutionsSoFar)
            if ch.isDel(): unlinkedChildren=True
        else:
            if PRINT_DEBUG: 
                print "assessSyncRuleQuality(): Match discarded after ", substitutionsSoFar, "substitutions"
            raise ValueError, "Rule tree quality too low"
    if PRINT_DEBUG: print "assessSyncRuleQuality() substitutionsSoFar:", substitutionsSoFar
    
    # Try allowing more substitutions and hope that rule frequency will remove unnecessary phrases
    if False:
        # discard rules that involve substitutions but no linking
        # at a particular node
        linksAtThisLevel = len(ph.links())
        if PRINT_DEBUG: print "linksAtThisLevel: ", linksAtThisLevel, ph.tag(), ph.links()
        if unlinkedChildren and linksAtThisLevel==0 and substitutionsSoFar>0:
            raise ValueError, "Rule tree quality too low: substitutions but no linking. %s"%str(ph)
    
    return substitutionsSoFar


def assessCombinedSyncRuleQuality(srcSyncTree, tgtSyncTree):
    """
    Check this rule looks worth having, comparing src with tgt.
    Raise ValueError if not.
    """
    # discard rules that only change one DET into another DET
    ls = _getFixedTextNodesInSyncTree(srcSyncTree)
    lt = _getFixedTextNodesInSyncTree(tgtSyncTree)
    pos_s = set([n.tag() for n in ls])
    pos_t = set([n.tag() for n in lt])
    if len(pos_s)==1 and "DT" in pos_s and len(pos_t)==1 and "DT" in pos_t:
        raise ValueError, "Rule quality too low: only DTs are substituted"

    # only allow fixed text in the source tree if there is also some in the target tree
    if len(ls)>0 and len(lt)==0:
        raise ValueError, "Rule quality too low: fixed text in source only, none in target"
        
        
def _getFixedTextNodesInSyncTree(tree):
    # Get all nodes in tree with fixed text
    l=[]
    if tree.text(): l.append(tree)
    if tree.hasChildren(): 
        for ch in tree.children():
            l.extend(_getFixedTextNodesInSyncTree(ch))
    return l
        




def createTree( s, doc, min_phrase_size=MIN_PHRASE_SIZE ):
        raise NotImplementedError, "Need to change this over to use the StanfordCoreNLP parser"

        assert not doc==None, "No document, don't know which parser cache to use"
        pennParser = POSTagger.StanfordPennParser(doc)
        dpParser = POSTagger.StanfordDependencyParser(doc)
        tree = pennParser.parse(s) 
        dg=dpParser.parseToDepGraph(s)
        tree.addDependencies(dg)
        
        if PRINT_DEBUG: print "Marking independent phrases: ", min_phrase_size
        tree.markIndependentPhrase(min_phrase_size)
        return tree


def combine_duplicate_rules(rules, use_dep=True):
    """ Returns a new list of rules, with duplicates combined """
    syncGrammarDict = dict() # temporary store

    for r in rules:

    # need string representation, not actual object
        if use_dep:
            k = r.key()
        else:
            k = r.key_no_dep()

        if k in syncGrammarDict:
            syncGrammarDict[k].inc()
            if False and PRINT_DEBUG: print k, "already in dictionary ", syncGrammarDict[k].count()
        else:
            syncGrammarDict[k] = r
    return syncGrammarDict.values()



def removeDuplicateQtsgRules( syncGrammarPairs, oldSyncGrammarDict = [], use_dep=True ):
    """
    Create a list of SyncGrammarRule from pairs of trees.
    Each rule should appear only once, with a count of 
    instances found in the training data
    """
    # need to make this function more visible    
    return _removeDuplicateQSGRules( syncGrammarPairs, oldSyncGrammarDict = oldSyncGrammarDict, use_dep=use_dep )
    
    
def _removeDuplicateQSGRules( syncGrammarPairs, oldSyncGrammarDict = [], use_dep=True ):
    """
    Create a list of SyncGrammarRule from pairs of trees.
    Each rule should appear only once, with a count of 
    instances found in the training data
    """    
    syncGrammarDict = dict() # temporary store
    
    # copy across old ruleset
    for r in oldSyncGrammarDict:
        if use_dep:
            k = r.key()
        else:
            k = r.key_no_dep()
        syncGrammarDict[k] = r
        
    for (n1,n2) in syncGrammarPairs:
        r = SyncGrammarRule(n1,n2)
        # need string representation, not actual object
        if use_dep:
            k = r.key()
        else:
            k = r.key_no_dep()
        if k in syncGrammarDict: 
            syncGrammarDict[k].inc()
            if False and PRINT_DEBUG: print k, "already in dictionary ", syncGrammarDict[k].count()
        else:
            syncGrammarDict[k] = r
    return syncGrammarDict.values()


QSGRulesPickleDir = "qg"
QSGRulesPickleFile = "syncrules.pickle"
def saveQSGRules( rules, task, filename=QSGRulesPickleFile ):
    f = os.path.join(task.shelfDir(),QSGRulesPickleDir,filename) 
    _pickleRules( rules, f )
    
def loadQSGRules(task, filename=QSGRulesPickleFile):
    f = os.path.join(task.shelfDir(),QSGRulesPickleDir,filename) 
    return _unpickleRules(f)









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
    if PRINT_DEBUG_SYNC: print "Loading rules from: ", filename
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
    


def learnSubstitutionWords( qsgRules ):
    """
    From the set of qsgRules, identify word substitutions 
    and return these in a separate rule-set
    """
    debugcount = 0
    substRuleList=[]
    for rule in qsgRules:
        if not rule.isSubstitution(contentWords=True): continue

        # if debugcount > 1000: break
        debugcount+=1
        # print rule.describeWordSeq()
        
        substRule = SyncGrammarWordSubRule.convert(rule)
        substRuleList.append(substRule)
        
    syncGrammarDict = dict() # temporary store
    for r in substRuleList:
        k = r.key() # need string representation, not actual object
        if k in syncGrammarDict: 
            syncGrammarDict[k].inc()
            if False and PRINT_DEBUG: 
                print k, "already in dictionary ", syncGrammarDict[k].count()
                raise SystemExit
        else:
            syncGrammarDict[k] = r
            
    if False:
        for rk in syncGrammarDict:
            print syncGrammarDict[rk].count(), "\t", rk
    return syncGrammarDict.values()


class SyncGrammarTree(object):
    """
    A simple tree that represents one side of the synchronous grammar
    """
    # UNLINKED_POS = 0 # now using None list
    
    UNLINK_NODE, NO_UNLINKED_TEXT_ALLOWED, NO_UNLINKED_CONTENT, INCLUDE_UNLINKED, INCLUDE_UNLINKED_NO_CONTENT = range(5)
    
    def __init__(self, node, dep, linkNumber=None, text=None):
        if text: assert len(text.split())==1, "Too many tokens in the SyncGrammarTree text: %s"%text
        if linkNumber: assert isinstance(linkNumber,list), "Need link numbers to be supplied as a list"
        self._node = node
        self._dep = dep
        self._linknum = linkNumber
        self._children = []
        self._text = text
        
    def tag(self): return self._node
    def dep(self): return self._dep
    def text(self): return self._text
    
    def isLinked(self):
        """
        Is this phrase synchronized to a corresponding phrase in
        the other grammar tree?
        """
        return self._linknum is not None
        
    def isDel(self):
        """
        Indicates that this node will be deleted
        """
        if self.isLinked(): return False
        if self.hasText(): return False
        if len(self.links())>0: return False
        return True
        
    def checkAllLinked(self, single=False):
        if   self.isLinked(): 
            # print self.links()
            if single and not len(self.links())==1:
                raise SystemExit, "SyncGrammarTree node has more than one link: %s" % self.describeTree(asRule=False)
                raise ValueError, "SyncGrammarTree node has more than one link: "
        elif self._text is not None: pass
        elif self.hasChildren(): pass
        else: raise ValueError, "SyncGrammarTree is not fully linked"
        for ch in self.children():
            ch.checkAllLinked(single=single)
    


        
    def describeTree(self, asRule=True, includeTopDep=True, includeOtherDep=True, combine_noun_tags=False):
        txt = ""
        
        if includeTopDep:  ruleDep = self._dep
        else:           ruleDep = "-"
        
        self_node = self._node
        if combine_noun_tags and self_node.startswith('N') and self_node!="NP":
            self_node = 'NA'
            
        if asRule: 
            txt = u"( %s/%s ->" % ( self_node, ruleDep)
            if self._text is not None:
                assert len(self._children) == 0, "This node has children and text" 
                txt += u" %s )" % self.text() 
        else: # node, not rule
            txt += "("
            if self._text is not None:
                txt += u"%s/%s#%s" % ( self_node, ruleDep, self._text)
            else: 
                txt += u"%s/%s#%s" % ( self_node, ruleDep, self._linksAsString())

        if len(self._children):
            for ch in self._children:
                txt += " " + ch.describeTree(asRule=False, includeTopDep=includeOtherDep, includeOtherDep=includeOtherDep, combine_noun_tags=combine_noun_tags)
                
        txt += " ) "
        return txt
        
    def __str__(self):
        return self.describeTree()
        
    def _linksAsString(self):
        if self.isLinked():
            l = [str(i) for i in self._linknum]
            return ",".join(l)
        else:
            return ""
        
    def describeWordSeq(self):
        if self._text is not None:
            txt = "%s" % self._text
        elif len(self._children):
            txt = ""
            for ch in self._children:
                txt += " " + ch.describeWordSeq()
            txt += " "
        else: 
            txt = "#%s" % self._linksAsString()
        return txt
        
            
    def append(self,child):
        """
        Add a child node to this tree
        """
        self._children.append(child)
    
    def matches(self, phraseTree, use_dep_info=True):
        """
        Returns True if the phraseTree node has the same syntactical
        structure as this tree.
        """
        if not isinstance(phraseTree, PhraseDependencyTree.PhraseDependencyTree): return False
        #print "Matching: ", phraseTree.label()
        if not phraseTree.tag() == self.tag(): return False
        #if not phraseTree.dep() == self.dep(): return False
        
        # Match PP dep phrases exactly, but be relaxed about others
        if use_dep_info and self.tag() == 'PP':
            if not (self.dep() == phraseTree.dep()):
                return False
            
        # check fixed text in the rule
        if self.text():
            if not phraseTree.isLeaf(): return False
            if not self.text()==phraseTree[0]: return False
                
        if not self.hasChildren(): return True # nothing below to match

        # now match children
        if  len(phraseTree) <> len(self.children()): return False 
            
        # TODO: work out how to match children
        # Is this too recursive?
        for i in range(len(self._children)):
            # print "Matching child: (%s/%s)" % (self._children[i].tag(), self._children[i].dep())
            #print "Checking match at ", i, " of ", phraseTree[i]
            
            # exactly match child dependencies
            if use_dep_info and not (self._children[i].dep() == phraseTree[i].dep()):
                return False
            
            # match children tags and text
            if not self._children[i].matches(phraseTree[i], use_dep_info=use_dep_info): return False
            
            # TODO: work out how to match children
            # what is above is too recursive, and hits problems at the leaf nodes
            # if not self._children[i].tag() == phraseTree[i].tag(): return False
            pass
        # print "Children in rule matched completely"
        return True
                    
    def children(self):
        return self._children
    
    def hasChildren(self):
        return len(self._children)>0
      

    def hasFixedPronouns(self):
        # print "Target tree: ", self, "\tlinked ? ", self.isLinked()
        PRONOUN_TAGS = ['PRP','DT']
        if self.tag() in PRONOUN_TAGS and not self.isLinked():
            return True
        
        if self.hasChildren():
            for ch in self.children():
                result = ch.hasFixedPronouns()
                if result:
                    return True
        return False


    stopwords = nltk.corpus.stopwords.words('english')
    def hasText(self, contentWords=False, ignore_verbs=False):
        """
        Returns True if this tree contains any fixed text.
        If contentWords is True, this will ignore stop words
        """
        if False:
            print SyncGrammarTree.stopwords
            raise SystemExit,"stopwords"
        if self.text() is not None: 
            if contentWords:
                if self.tag() in MATCH_STOP_TAGS:
                    pass # move on to other words
                elif ignore_verbs and self.tag() in VERB_PHRASE_TAGS:
                    pass
                elif self.text().lower() in SyncGrammarTree.stopwords:
                    # print "Rejected ", self.text()
                    pass # try other words
                else:
                    return True
            else:
                return True
        if self.hasChildren():
            for ch in self.children():
                if ch.hasText(contentWords=contentWords, ignore_verbs=ignore_verbs): return True
        return False

    def getLinkedChildren(self):
        """ Returns a list of children in this tree with links """
        current = []
        if self.isLinked():
            current.append( (self, self._linknum) )
        for ch in self.children():
            current.extend(ch.getLinkedChildren())
        return current
    
        
    def getTextChildren(self):
        """
        Return a list of the text elements in this tree
        """
        curr = []
        if self.text() is not None:
            curr.append(self)
        if self.hasChildren():
            for ch in self.children():
                curr.extend(ch.getTextChildren())
        return curr


    def get(self,index):
        """
        Return the descendent at the position index
        """
        assert isinstance(index, list), "Index is not a list"
        assert len(index)>0, "No position provided"
        child = self.children()[index[0]]
        if len(index)==1:
            return child
        else:
            return child.get(index[1:])
            
    def word_alignment(self):
        """ Word alignment for text-rules only """
        return None

        
    def findLink(self, linknum, srcPhraseTree):
        """
        Find a link in the tree with the number linknum,
        and return its position as a list of positions.
        Will raise LookupError if no link found
        @var srcPhraseTree: the tree structure of the actual phrase, 
        useful if this type of sync grammar tree does not capture the phrase tree structure exactly
        """
        if isinstance(linknum, list): 
            if linknum is None: raise LookupError, "Src phrase has no link set"
            assert len(linknum)==1, "Looking up more than one link: %s" % str(linknum)
            linknum = linknum[0] 
        if (self._linknum and linknum in self._linknum):
            return []
        else:
            for i, ch in enumerate(self.children()):
                try:
                    position = ch.findLink(linknum, srcPhraseTree)
                    position.insert(0,i)
                    return position
                except LookupError:
                    # not found, so try next child
                    pass
        raise LookupError, "No link phrase found"


    def links(self):
        """
        List the links that this tree contains
        """
        if self.isLinked():
            ll = self._linknum
        else:
            ll = []
        
        for ch in self.children():
            ll.extend(ch.links())
            
        return ll
        
    def renumberLinks(self, linkDict):
        """
        Renumber the links in this tree, according to the look-up dictionary
        """
        if self.isLinked():
            ll = []
            for l in self._linknum:
                try:
                    ll.append(linkDict[l])
                except KeyError:
                    if len(ll)==0: ll.append(0)
                    # pass # link is not needed
            # print "Old: ", self._linknum, "\t\tNew: ", ll
            self._linknum = ll
        else:
            pass
            # print "Not linked"
        
        for ch in self.children():
            ch.renumberLinks(linkDict)
            
    def removeMultipleLinks(self):
        changed = False
        if self.isLinked() and len(self.links())>1:
            # just keep first link
            self._linknum = [ self._linknum[0] ]
            changed = True
        for ch in self.children():
            if ch.removeMultipleLinks():
                changed = True
        return changed
    


    
    @classmethod    
    def createFromPhraseTree(cls, phTree, links, offset=0, includeUnlinkedText=UNLINK_NODE):
        """
        Create from a phrase tree
        """
        linkedNodes = [l[offset] for l in links]
        linkedNodesPos = [l.treeposition() for l in linkedNodes ]
        
        # handle case where node contains only text
        if ( phTree.isLeaf() and (includeUnlinkedText==SyncGrammarTree.INCLUDE_UNLINKED  
                                  or (includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_CONTENT and not phTree.hasText() ))):
            # case where node contains only text
            syncRoot = SyncGrammarTree(phTree.label(), phTree._rel, text=nodeText(phTree))
        
        else: # normal tree
            syncRoot = SyncGrammarTree(phTree.label(), phTree._rel)
            for phCh in phTree:
                if phCh.treeposition() in linkedNodesPos:
                    linkPos = [i+1 for i,l in enumerate(linkedNodesPos) if l==phCh.treeposition()]
                    # linkPos = linkedNodesPos.index(phCh.treeposition())+1
                    syncCh = SyncGrammarTree(phCh.label(), phCh._rel, linkNumber=linkPos)
                elif phCh.isLeaf(): # unlinked leaf
                    if includeUnlinkedText==SyncGrammarTree.UNLINK_NODE:
                        syncCh = SyncGrammarTree(phCh.label(), phCh._rel) # structure only, no text or linking
                    elif includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_TEXT_ALLOWED:
                        raise ValueError, "Cannot include unlinked leaf"
                    elif includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_CONTENT and phCh.has_content():
                        raise ValueError, "Cannot include unlinked leaf"
                    elif includeUnlinkedText==SyncGrammarTree.INCLUDE_UNLINKED_NO_CONTENT and phCh.has_content():
                        syncCh = SyncGrammarTree(phCh.label(), phCh._rel) # structure only, no text or linking
                    else:
                        syncCh = SyncGrammarTree(phCh.label(), phCh._rel, text=nodeText(phCh))
                else:
                    # unlinked subtree 
                    syncCh = SyncGrammarTree(phCh.label(), phCh._rel)
                    # if includeUnlinkedText!=SyncGrammarTree.UNLINK_NODE:
                    # only re-create the structure of phCh if we are linking to something within
                    SyncGrammarTree._findLinkedChildren(phCh, syncCh, linkedNodes, linkedNodesPos, offset, includeUnlinkedText)
                
                syncRoot.append(syncCh)
            
        return syncRoot
    

    @classmethod    
    def parse(cls, s):
        """
        Create from a phrase tree string representation, where
        nodes have #linknumber information.
        Nodes that have no text must be inside their own brackets e.g. (NP/nsubj#1)
        """
        tree = parse.PhraseDependencyTree.PhraseDependencyTree(s)

        # identify the links                   
        link_information = {} # build up knowledge of links 
        for t in tree.subtrees():
            if "#" in t.tag():
                tag_nolink, link = t.tag().split("#")
                try:
                    link_information[int(link)] = t # TODO: handle more than one link?
                except ValueError: # # indicates text literal
                    if len(link) > 0:
                        t.append(link)
                    else:
                        # no text and no link
                        pass
                t.set_label(tag_nolink)
                 
        tree._correctDepTags()
        tree.markPositions()
        
        # mylist = sorted(mylist, key=itemgetter('name'))
        links = [ (v,None) for v in link_information.itervalues() ]
        syncTree = SyncGrammarTree.createFromPhraseTree(tree, links, includeUnlinkedText=True)
        return syncTree

        


    @classmethod    
    def _findLinkedChildren(cls, phTree, syncTree, linkedNodes, linkedNodesPos, offset, includeUnlinkedText):
        """
        Finds the children of phTree in the linkedNodes list
        """
        descendents = []
        for ch in phTree:
            if isinstance(ch,PhraseDependencyTree.PhraseDependencyTree):
                descendents.extend( [ l for l in linkedNodes if l.isDescendent(ch) ] )
        
        linkedChildren = [ch for ch in phTree \
            if isinstance(ch,PhraseDependencyTree.PhraseDependencyTree) \
            and ch.treeposition() in linkedNodesPos]
            
        # if anything linked, we need to explain this node further
        if PRINT_DEBUG:
            print
            print nodeText(phTree)
            print "Offset ", offset
            print "With ", phTree.tag(), " there are %d linked children and %d descendents" % (len(linkedChildren), len(descendents))
            
            print "Current tree position", phTree.treeposition()
            print "possible links:"
            for l in linkedNodesPos: print l
            print
        
        if len(linkedChildren)>0 or len(descendents)>0: 
            for ch in phTree:
                if PRINT_DEBUG: print "Working on child ", ch.tag(), nodeText(ch)
                if ch in linkedChildren: 
                    if PRINT_DEBUG: print "linked child"
                    linkPos = [i+1 for i,l in enumerate(linkedNodesPos) if l==ch.treeposition()]
                    syncCh = SyncGrammarTree(ch.label(), ch._rel, linkNumber=linkPos)
                elif ch.isLeaf():
                    # leaf node that is not linked
                    if includeUnlinkedText==SyncGrammarTree.UNLINK_NODE:
                        if PRINT_DEBUG: print "removing link to text leaf"
                        syncCh = SyncGrammarTree(ch.label(), ch._rel)
                    elif includeUnlinkedText==SyncGrammarTree.INCLUDE_UNLINKED:
                        if PRINT_DEBUG: print "fixed text leaf"
                        syncCh = SyncGrammarTree(ch.label(), ch._rel, text=nodeText(ch))
                    elif (includeUnlinkedText==SyncGrammarTree.INCLUDE_UNLINKED_NO_CONTENT or includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_CONTENT) and \
                         not ch.has_content():
                        if PRINT_DEBUG: print "fixed text leaf - no content"
                        syncCh = SyncGrammarTree(ch.label(), ch._rel, text=nodeText(ch))
                    else:
                        if PRINT_DEBUG: print "leaf with content - cannot include"
                        raise ValueError, "Cannot include leaf with content"
                else:
                    if PRINT_DEBUG: print "unlinked sub-tree, but may include links"
                    syncCh = SyncGrammarTree(ch.label(), ch._rel)
                    childsDescendents = [ l for l in descendents if l.isDescendent(ch) ]
                    if len(childsDescendents)>0:
                        SyncGrammarTree._findLinkedChildren(ch, syncCh, childsDescendents, linkedNodesPos, offset, includeUnlinkedText)
                    elif includeUnlinkedText==SyncGrammarTree.INCLUDE_UNLINKED:
                        SyncGrammarTree._createFixedTextTree(ch, syncCh)
                    elif includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_CONTENT and not ch.has_content():
                        SyncGrammarTree._createFixedTextTree(ch, syncCh)
                    else:
                        syncCh = SyncGrammarTree(ch.label(), ch._rel)

                    
                syncTree.append(syncCh)
        else:
            # a whole unlinked tree
            if PRINT_DEBUG: print "whole unlinked sub-tree"
            if includeUnlinkedText==SyncGrammarTree.UNLINK_NODE or \
               includeUnlinkedText==SyncGrammarTree.INCLUDE_UNLINKED_NO_CONTENT: #  and phTree.has_content():
                pass # leave this syncTree unlinked and unchanged
            elif includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_TEXT_ALLOWED or \
               includeUnlinkedText==SyncGrammarTree.NO_UNLINKED_CONTENT and phTree.has_content():
                raise ValueError, "Cannot include leaf with content"
            else:
                SyncGrammarTree._createFixedTextTree(phTree, syncTree)


    @classmethod    
    def _createFixedTextTree(cls, src, tgt):
        """
        Create a subtree copy of src, with all text fixed
        """
        assert not src.isLeaf(), "_createFixedTextTree() received a leaf node" 
        if PRINT_DEBUG: print "In _createFixedTextTree with", nodeText(src)
        for ch in src:
            if PRINT_DEBUG: print nodeText(ch)
            if ch.isLeaf():
                syncCh = SyncGrammarTree(ch.label(), ch._rel, text=nodeText(ch))
            else:
                # just remember top level structure
                syncCh = SyncGrammarTree(ch.label(), ch._rel)
                
                # Store the text of children as well
                SyncGrammarTree._createFixedTextTree(ch, syncCh)
                
            tgt.append(syncCh)
            

class SyncGrammarRule(object):
    """
    A rule relates a source SyncGrammarTree to a target SyncGrammarTree
    """
    def __init__(self, source, target, count=1, duplication=False):
        self._source = source
        self._target = target
        self._count = count
        self._rule_id = None
        self._makeLinksSequential()
        
        
    def _makeLinksSequential(self):
        """
        Reorder the link numbers to make them sequential, 
        so that identical rules can be spotted
        """
        tl = self._target.links()
        needSorting = False
        for i, l in enumerate(self._target.links()):
            if not i==l-1: 
                needSorting = True
                break
                
        if needSorting:
            # print "Rule target links need sorting"
            tldict = dict( (l,i+1) for i, l in enumerate(self._target.links()) )
            if PRINT_DEBUG: print "Target link renumbering: ", tldict
            self._source.renumberLinks(tldict)
            self._target.renumberLinks(tldict)
            # print self
            # raise SystemExit, "_makeLinksSequential()"
            pass
        
        
        

    def __str__(self):
        s = self._source.describeTree() + "\t" + self._target.describeTree()
        return s

    def describeWordSeq(self, wordsonly=False):
        s = self._source.tag() + " (" +\
            self._source.describeWordSeq() +\
            ")"
        s += "\t-->\t"
        s += self._target.tag() + " (" +\
            self._target.describeWordSeq() +\
            ")"
        return s
    
    def key(self, asRule=True):
        """ Returns a string representation of this object,
        that can be used in dictionary lookup
        """
        if True: # old version
            s = self._source.describeTree(asRule=asRule, includeTopDep=False) + \
                "\t" + self._target.describeTree(asRule=asRule, includeTopDep=False)
        else:
            s  = u"%s/- ->" % (self._source.tag())
            s += self._source.describeTree(asRule=False)
            s += "\t"
            s += u"%s/- ->" % (self._target.tag())
            s += self._target.describeTree(asRule=False)
        return s
    
    def key_no_dep(self):
        s1 = self._source.describeTree(asRule=True, includeTopDep=False, includeOtherDep=False, combine_noun_tags=False)
        s2 = self._target.describeTree(asRule=True, includeTopDep=False, includeOtherDep=False, combine_noun_tags=True)
        return s1 + "\t" + s2
        
    def __eq__(self, other):
        print "This: ", str(self)
        print "Other: ", str(other)
        raise NotImplementedError, "Not sure if this method is really what's required"
        return (str(self)==str(other))
        
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
        
    def rule_id(self):
        """
        Return a unique id for this rule within the ruleset
        """
        assert self._rule_id is not None or self.isIdentical(), "Rule ids have not been set up"
        return self._rule_id
        
    def set_rule_id(self, i):
        """
        Return a unique id for this rule within the ruleset
        """
        try:
            assert self._rule_id is None, "Rule ids already set up"
            pass
        except AttributeError:
            pass # old pickled object with no _rule_id
        self._rule_id = i
        
    def isIdentical(self):
        """
        Returns True if there target tree
        is identical to the source tree.
        """
        # return (unicode(self._source)==unicode(self._target))
        
        # try to follow isSuitable() method 
        if not self._source.tag() == self._target.tag(): return False
        # don't match .dep() at root level
        
        if False:
            print unicode(self._source.describeTree(asRule=False, includeTopDep=False))
            print unicode(self._target.describeTree(asRule=False, includeTopDep=False))
            print "-------"
        
        return  unicode(self._source.describeTree(asRule=False, includeTopDep=False, includeOtherDep=False)) == \
                unicode(self._target.describeTree(asRule=False, includeTopDep=False, includeOtherDep=False))


    def isIdentical_ignoring_noun_tags(self):
        """
        Returns True if there target tree
        is identical to the source tree,
        once dependencies and noun tags are ignored.
        """
        if not self._source.tag() == self._target.tag(): return False
        s1 = self._source.describeTree(asRule=True, includeTopDep=False, includeOtherDep=False, combine_noun_tags=True)
        s2 = self._target.describeTree(asRule=True, includeTopDep=False, includeOtherDep=False, combine_noun_tags=True)
        return s1==s2
    

    def partOfSpeechChange(self):
        """
        Returns True if the part of speech of this phrase has changed
        """
        return not (self._source._node == self._target._node ) 

    def depLabelChange(self):
        """
        Returns True if the part of speech of this phrase has changed
        """
        return not (self._source._dep == self._target._dep ) 

    def containsDeletions(self):
        """
        Returns True if children in the source tree
        will be deleted
        """
        if not self._source.hasChildren(): return False
        for ch in self._source.children():
            if not ch.isLinked(): return True
        return False
    
    def deletedNodes(self):
        """
        Returns a list of the nodes from the source tree that are deleted
        """
        delNodes = []
        if not self._source.hasChildren(): return None
        for ch in self._source.children():
            if not ch.isLinked(): delNodes.append(ch)
        return delNodes
        
    def isReordered(self):
        """
        Returns True if the src tree nodes need to be reordered
        to create the target tree
        """
        # Just need to see if the nodes are in numerical order
        # as the target tree nodes will be
        if not self._source.hasChildren(): return False
        i = 0
        for ch in self._source.children():
            if ch.isLinked():
                if ch._linknum > i: i = ch._linknum
                else: return True # not in expected order
        return False
        
    def containsInsertions(self):
        """
        Returns True if children in the target tree
        will be inserted by the grammar, rather
        than coming from the source tree
        """
        if not self._target.hasChildren(): return False
        for ch in self._target.children():
            if not ch.isLinked(): return True
        return False
    
    def isSubstitution(self, contentWords=False):
        return self._source.hasText(contentWords=contentWords) and self._target.hasText(contentWords=contentWords)

    def isNullRule(self):
        """
        Some T3 rules are Null rules:
        The source tree maps onto an entirely empty target tree (just a root node)
        """
        return not self._target.hasChildren() and not self._target.hasText() 

    
    def containsFixedPronouns(self):
        """
        Returns True if the target tree contains fixed pronouns.
        We are likely to get them (gender, number) wrong.
        """
        result =  self._target.hasFixedPronouns()
        if False and result: pass; # print "Stopping: ", self
        return result
    
    
    def matchesSource(self, srcPhraseTree):
        return self._source.matches(srcPhraseTree, use_dep_info=MATCH_DEP_LABELS)
    
    def isSyntaxTransform(self, contentWords=False):
        return not self._source.tag() == self._target.tag()
    
    def isLexicalized(self, contentWords=False):
        """
        Return True if the source tree contains words
        """
        return self._source.hasText(contentWords=contentWords)


    def introducesContent(self):
        """
        Return True if the target tree contains content words but the source tree does not
        """
        if not self.containsInsertions(): return False
        if self.isSubstitution(contentWords=True): return False
        return self._target.hasText(contentWords=True)

    def changes_syntax_only(self):
        """
        Return True if this rule only affect syntax,
        it is not lexicalized and it does not introduce words
        """
        if self.isLexicalized(contentWords=True): return False
        return not self._target.hasText(contentWords=True, ignore_verbs=True)

    def repeats_content(self):
        """ Returns True if there are content nodes in the source that are linked to more than one target node """
        linked_src = self._source.getLinkedChildren()
        for n, links in linked_src:
            if len(links) > 1 and n.tag() not in PhraseDependencyTree.PhraseDependencyTree.MATCH_STOP_TAGS:
                # node that has multiple links containing content
                # print "tag: ", n.tag(), "\tstop:", n.tag() in PhraseDependencyTree.PhraseDependencyTree.MATCH_STOP_TAGS
                return True
        return False 

    def isSuitable( self, srcTree, targetTreeNode):
        """
        Returns True if this rule is suitable for 
        applying to the phrase tree.
        This differs, in checking only that the tags match.
        Sentence creation is only possible with no targetTreeNode.
        """
        if not self._source.matches(srcTree, use_dep_info=MATCH_DEP_LABELS): return False
        if self._target.tag()=="ST" and not targetTreeNode: return True # allow new sentence to be created
        # allow compatible VPs
        if targetTreeNode.tag() in VERB_PHRASE_FROM_NOUN_PHRASE_TAGS and self._target.tag() in VERB_PHRASE_FROM_NOUN_PHRASE_TAGS:
            return True
        if targetTreeNode.tag() == self._target.tag(): return True
        return False

    def isSuitableSomewhere(self, src_subtree_info):
        """ Faster check based on text matching, but not guaranteed """
        return True
    

    def isSuitable_old( self, srcTree, targetTreeNode ):
        """
        Returns True if this rule is suitable for 
        applying to the phrase tree.
        The tags have to match.
        """
        raise DeprecationWarning, "Using isSuitable(), which does not do as much checking"
        
        if not self._source.matches(srcTree): return False
        
        if self._source.tag()=="S":
            if self._target.dep()=="TOP" \
                and not targetTreeNode: return True
            elif targetTreeNode:
                # print "Target node:", targetTreeNode.tag(), targetTreeNode.dep()
                if self._target.dep()=="TOP" and targetTreeNode.dep()=="TOP": return True
                elif self._target.dep()=="TOP" and targetTreeNode.dep()=="fixed": return True # are there more cases?
                elif not self._target.dep()=="TOP" and not targetTreeNode.dep()=="TOP": return True
            if PRINT_DEBUG: print "Rejected S rule:", self, "for target", targetTreeNode
            return False

        if targetTreeNode: # TODO: sort out what works
            
            # Beginning of sentence --- allow sentence pair rule
            if (targetTreeNode.tag()=="S" and targetTreeNode.dep()=="TOP") \
                and self._target.tag()=="SP":
                return True
            
            if not targetTreeNode.tag() == self._target.tag(): return False
            
            # a dodgy rule
            if self._target.tag() == 'NP' \
                and self._target.dep()=='poss'\
                and not self._source.dep()=='poss':
                #raise NotImplementedError, "This NP -> NP-poss rule is not to be trusted"
                return False

            #if not targetTreeNode.dep() == self._target.dep():  return False
        
        return True

    @classmethod    
    def createDuplicationRule(cls, phTree):
        """
        Create a rule that just duplicates this phrase
        """
        assert not phTree.isLeaf(), "Trying to duplicate a leaf node"
        links = [ (ch,ch) for ch in phTree ]
        src = SyncGrammarTree.createFromPhraseTree(phTree, links)
        #tgt = SyncGrammarTree.createFromPhraseTree(phTree, links)
        DUPLICATION_RULE_COUNT = 2 # need a value for it not to be penalized too much
        rule = SyncGrammarRule(src,src,count=DUPLICATION_RULE_COUNT)
        return rule

    @classmethod    
    def createFromString(cls, string):
        """
        Create a rule from a string representation:
        The source and target rules are separated by a tab character.
        Links are shown by #n markers at the end of each non-terminal.
        """
        txt1, txt2 = string.split("\t")
        srcTree = SyncGrammarTree.parse(txt1)
        try:
            tgtTree = SyncGrammarTree.parse(txt2)
        except ValueError, __e:
            # target tree is really deletion
            tgtTree = SyncGrammarTree.parse("(%s/%s#)" % (srcTree.tag(), srcTree.dep()))
        rule = SyncGrammarRule(srcTree, tgtTree)
        return rule

    
    def applyRule(self, ph):
        """
        Apply this rule to the phrase tree ph
        """
        raise NotImplementedError, \
        "Not possible to apply locally,"
        "as we need to recurse deeper into the tree"
        
    def isOKSTRule(self):
        """
        Return True if this is an ST rule and it passes particular tests for this node.
        ST rules have ST as the top tag in the target tree. 
        Perhaps ST rules should be a subclass.
        """
        if not self._target.tag() == 'ST': return False
        if self.introducesContent(): return False
        if len(self._target.children())==1 and not self._target.children()[0].tag()=="ST": return False # many rules turn ST into single NP
        
        
        # remove ST linked to leaf node in the source
        if len(self._target.children())==1 and self._target.children()[0].tag()=="ST":
            # ensure that target ST is linked to constituent, not leaf 
            assert self._target.get([0]).isLinked(), "Unlinked ST child"
            link = self._target.get([0])._linknum
            linkedSrcNode = self._source.get(self._source.findLink(link, None))
            if linkedSrcNode.tag() not in parse.PhraseDependencyTree.PhraseDependencyTree.INDEPENDENT_PHRASE_TAGS:
                return False

        return True # all checks seem OK
        


class SyncGrammarWordSubRule(SyncGrammarRule):
    """
    A rule relates a source SyncGrammarTree to a target SyncGrammarTree.
    This subclass handles lists of (POS-tag,word) substitutions
    rather than nodes in a phrase tree
    """
    pass    

    @classmethod
    def convert(cls, rule):
        """
        Convert from a SyncGrammarRule
        """
        assert isinstance(rule, SyncGrammarRule), "This is not a SyncGrammarRule"
        textchildrenSrc = rule._source.getTextChildren()
        textchildrenTgt = rule._target.getTextChildren()
        count = rule.count()
        substRule = SyncGrammarWordSubRule(textchildrenSrc,textchildrenTgt, count=count)
        return substRule
        
        
        
    def _makeLinksSequential(self):
        """No links with this type of rule"""
        pass

    def describeWordSeq(self, includeTopDep=True, wordsonly=False):
        s = ""
        if wordsonly:
            leaves = self._getLeafListFromTreeList(self._source)
            words = [l.describeWordSeq() for l in leaves]
            s += " ".join(words)
            s += "\t-->\t"
            leaves = self._getLeafListFromTreeList(self._target)
            words = [l.describeWordSeq() for l in leaves]
            s += " ".join(words)
        else:
            for w in self._source:
                s += w.describeTree(asRule=False, includeTopDep=includeTopDep)
                s += " "
            s += "\t-->\t"
            for w in self._target:
                s += w.describeTree(asRule=False, includeTopDep=includeTopDep)
                s += " "
        return s

    def __str__(self):
        return self.describeWordSeq()

    def key(self):
        """ Returns a string representation of this object,
        that can be used in dictionary lookup
        """
        s = self.describeWordSeq(includeTopDep=False)
        return s

    def isIdentical(self):
        leaves = self._getLeafListFromTreeList(self._source)
        words = [l.describeWordSeq() for l in leaves]
        src = " ".join(words)

        leaves = self._getLeafListFromTreeList(self._target)
        words = [l.describeWordSeq() for l in leaves]
        tgt = " ".join(words)
        return src == tgt


    def isSubstitution(self, contentWords=False):
        return True

    def matchesSource(self, srcPhraseTree):
        return True
        raise NotImplementedError, "Not sure how to handle matching the tree syntax to a list"
    
    
    def isSuitable( self, srcTree, targetTreeNode ):
        """
        Returns True if this rule is suitable for 
        applying to the phrase tree.
        The tags have to match.
        """
        if False:
            print "In isSuitable()"
            print "self:", unicode(self)
            print "self._source:", type(self._source)
            print self._source
        
        # leaves = [ l for l in srcTree.leafNodes() ]
        # leaves = [ l for l in srcTree if l.isLeaf() and l.tag() not in SUBSTITUTE_TOKENS]
        leaves = [ l for l in srcTree if l.isLeaf() ]
        # print "Leaves:", leaves
        
        for n in self._source:
            matchingleaves = [l for l in leaves if n.matches(l)]
            if len(matchingleaves)==0: return False
            
        # exited loop, meaning that all items in self._source have a matching leaf
        
        if False:
            print "Current rule: ", self
            print "Leaves:", leaves
            print srcTree
            print "*** matched rule"
        
        # TODO: need to check that the leaves are in order
        
        # raise SystemExit, "SyncGrammarWordSubRule.isSuitable()"
        return True

    def applyRule(self, ph):
        """
        Apply this rule to the phrase tree ph
        """
        assert type(ph)==parse.PhraseDependencyTree.PhraseDependencyTree, "Not provided with phrase tree"
        
        targetPhraseTree = parse.PhraseDependencyTree.PhraseDependencyTree("( %s )"% ph.tag())
        targetPhraseTree.copyAttributes(ph)

        if PRINT_DEBUG: print "Rule source list:", self._source, self._source[0]
        
        ruleLeaves = self._getLeafListFromTreeList(self._source)
        if PRINT_DEBUG: 
            print "Rule leaves:", ruleLeaves
            for l in ruleLeaves: print l
        leaves = [ (i,ch) for i,ch in enumerate(ph) if ch.isLeaf() ]
        if PRINT_DEBUG: print "Indexed leaves:", leaves
        
        matchingleaves = [(i,l,n) for i,l in leaves for n in ruleLeaves if n.matches(l)]
        if PRINT_DEBUG: print "matching leaves:", matchingleaves

        if PRINT_DEBUG: print "Creating paraphrase of:", ph
        
        substitutionDone = False
        for i, ch in enumerate(ph):
            match = filter(lambda m: m[0]==i, matchingleaves)
            if PRINT_DEBUG: print "match: ", match
            if len(match):
                # remove these words, and substitute in target words
                pass # skip the copying of this word
                if not substitutionDone:
                    # fill in the substitution words here
                    targetRuleLeaves = self._getLeafListFromTreeList(self._target)
                    for r in targetRuleLeaves:
                        if PRINT_DEBUG: print "Adding from rule:", r.describeTree(asRule=False)
                        targetCh = parse.PhraseDependencyTree.PhraseDependencyTree("( %s %s )"%(r.tag(), r.text()))
                        targetCh._rel = r.dep()
                        targetCh._fixed = True
                        targetPhraseTree.append(targetCh)
                    substitutionDone = True
            else:
                # keep original words
                targetPhraseTree.append(ch.copy())
            
        if PRINT_DEBUG: print "targetPhraseTree:", targetPhraseTree
        return targetPhraseTree



    def _getLeafListFromTreeList(self, treelist):
        leaves=[]
        for tree in treelist:
            leaves.extend(tree.getTextChildren())
        return leaves
    


class NoGrammarPathError(StandardError):
    """Raised when there is no grammar available
       to complete this tree
    """
    pass


                                                                                                            
if __name__=="__main__":
    # investigate()
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
    
    # testing if SyncGrammarRule.createFromString(cls, string) is working
    SyncGrammarRule.createFromString("(NP/nsubj (NNP/nn#0 ) (NNS/fixed#1))\t(NP/nsubj (NNP/nn#0) (NNS/fixed#1))")
    rule = SyncGrammarRule.createFromString("(NNP/nn Quantum)\t(NNP/nn Quantum)")
    print rule
    print "substitution: ", rule.isSubstitution(), "\tidentical: ", rule.isIdentical()
    subRule = SyncGrammarWordSubRule.convert(rule)
    print subRule
        
    

