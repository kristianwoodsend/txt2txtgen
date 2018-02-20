'''
Old alignment methods from SyncTreeGrammar.
This approach allowed more fuzzy matching, suitable for learning substitution rules.

Created on 19 Sep 2013

@author: kristian
'''

from parse import PhraseDependencyTree
from nlputils import NltkUtils

from QGCore import nodeText, commonAncestor, nodeDistance, nodeTextNoPunctuation
from QGDefs import *
from info import printAllMatchListInfo, printAllPhraseInfo

def topLevelPhrasesMatch(m):
    """
    Returns true if the two phrases have the same top level constituency
    """
    ph1, ph2 = m
    e1 = ph1.tag()[0]
    e2 = ph2.tag()[0]
    
    # only match PP phrases if the dep labels also match
    if ph1.tag() == "PP" and ph2.tag() == "PP":
        if ph1.dep() == ph2.dep(): return True
        elif ph1.dep()=="agent": return True # confusion over "by ..." is agent or prepc_by 
        elif ph2.dep()=="prepc_by": return True # just let them through 
        else:
            return False
    
    if e1==e2: 
        return True
    elif ph1.tag()=='VP' and e2=='S': # possible that VP contains SBAR
        return False # was True, but I can't remember the case where we needed this
    elif e1=='V' and e2=='S': # not clear if we really want to transform VP to S without knowing n-subject
        if PRINT_DEBUG: print "Not letting this through"
        return False
    elif e1=='P' and e2=='S': # PP can be transformed into SBAR relative clause
        return True
    elif e1=='N' and e2=='S': # Allow an NP into S, assuming that NP contains SBAR relative clause
        return True
    else: 
        return False
    
def linkMatchingNodes(srcTree, destTree, matchList, includeDestRoot=False):
    """
    Returns a subset of the matchList 
    so that every child of destTree is linked (if possible)
    to children or grandchildren of srcTree
    """
    
    if PRINT_DEBUG_LINKING: print "Link set for :" , srcTree.treeposition(), "---", destTree.treeposition()
    refML = [ m for m in matchList if m[0].isDescendent(srcTree) and m[1].isDescendent(destTree) ]
    if includeDestRoot:
        refML.extend([ m for m in matchList if m[0].isDescendent(srcTree) and m[1] is destTree])
    if PRINT_DEBUG_LINKING: printAllMatchListInfo(refML)
    return refML
    
    
def removeDuplicatedLinksToTargets(matchList):
    """
    If more than one source links to a target node, choose the highest one
    """
    mldict = {}
    for m in matchList:
        key = m[1].treeposition()
        if PRINT_DEBUG_LINKING: print "Key:",key
        if key in mldict:
            oldL = mldict[key][0].treeposition()
            newL = m[0].treeposition()
            if len(newL) < len(oldL):
                # print "Replacing", oldL, " with ", newL
                mldict[key]=m
        else:
            mldict[key]=m
    refML = mldict.values()
    return refML
    



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
        for ch in ch1List: print ch[0].tag(), ch[0], ch[1] 
        print "ch2"
        for ch in ch2List: print ch[0], ch[1] 
    
    # do loop explicitly to catch recursion errors and carry on
    matching=[]
    for (ch1,txt1) in ch1List:
        for (ch2,txt2) in ch2List:
            try:
                if (ch1,ch2) not in matchList and wordsMatch(txt1,txt2, ch1.tag(), ch2.tag()):
                    matching.append((ch1,ch2))
            except RuntimeError:
                # recursion problem in matching trees
                pass
        
    # if len(matching)>0:
    #     print "\n\n\nMatching: ", matching
    #    raise SystemExit, "Need to add POS tags"
    return matching
                
                
def linkHigherEquivalentNodes(matchList):
    """
    If a node in the matchList has an identical node
    higher up the tree, link to that one as well.
    
    We are only doing this if the node higher up has not already
    been matched.
    """
    equivMatchList=[]
    alreadyMatchedSourceNodes = [m[0] for m in matchList]
    alreadyMatchedTargetNodes = [m[1] for m in matchList]
    for (s,t) in matchList:
        # if t.parent() in alreadyMatchedTargetNodes: continue
        # print "Working on S: ", s.treeposition()
        sEquiv = _higherEquivalentNodes(s)
        # if len(sEquiv): print "S\t",s.treeposition(), sEquiv[0].treeposition(), "\tPair in match list: ", (sEquiv,t) in matchList, "T parent already matched:", t.parent() in alreadyMatchedTargetNodes
        for n in sEquiv:
            if n not in alreadyMatchedSourceNodes:
            # if (n,t) not in matchList:
                # print "S: matching ", n.treeposition(), "to", t.treeposition()
                equivMatchList.append((n, t))
    for (s,t) in matchList:
        if s.parent() in alreadyMatchedSourceNodes: continue
        tEquiv = _higherEquivalentNodes(t)
        # if len(tEquiv): print "T\t",t.treeposition(), tEquiv[0].treeposition(), "\tPair in match list: ", (s,tEquiv) in matchList
        for n in tEquiv:
            if n not in alreadyMatchedTargetNodes:
                # print "T: matching ", s.treeposition(), "to", n.treeposition()
                equivMatchList.append((s, n))
    return equivMatchList
    
        
def _higherEquivalentNodes(n):
    """
    Returns the parent node if there is a fixed
    dependency to the child, and the tags match.
    TODO: could go higher, need to think how to make this safe
    """
    
    a = n
    equivalentNodes=[]
    # while a.dep() == PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT:
    while a.dep() == PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT \
        or (a.parent() and a.tag()==a.parent().tag()):
        if not a.parent(): break # hit the top of the tree
        a = a.parent()
        equivalentNodes.append(a)
        # print a.treeposition(), a.tag(), a.dep(), nodeText(a)
    return equivalentNodes



    
def linkParentNodes(matchList, matchListNoStopList, maxDepth = 1):
    """
    Considers pairs of matched nodes in the match list.
    If two nodes have the same parent, then this parent
    is matched to the ancestor of the corresponding
    highlight nodes.
    
    A maxDepth=1 allows siblings to be matched
    """
    matchingParentNodes=[]
    if PRINT_DEBUG: 
        print "\nInvestigating node distances"
        
        assert len(matchList) > 0, "No matches to work with"
        srcroot = matchList[0][0].root()
        hiroot = matchList[0][1].root()
        print "Roots: ", id(srcroot), "---", id(hiroot)
        for ms, mh in matchList:
            print id(ms.root()), "---", id(mh.root())
            if not id(ms.root()) == id(srcroot): print "src!!!"
            if not id(mh.root()) == id(hiroot): 
                print "hi!!!"
                print "Original tree:"
                print nodeText(hiroot)
                print hiroot
                print "New tree involving:", mh
                print nodeText(mh.root())
                print mh.root()
                

    
    for (s1, h1) in matchList: # was matchListNoStopList
        # for (s2, h2) in matchListNoStopList[i+1:]:
        for (s2, h2) in matchListNoStopList:
            d = nodeDistance(s1, s2)
            if PRINT_DEBUG: print "nodeDistance: ", d, "\t\t", s1.treeposition(), "---", s2.treeposition(), "\t; highlights\t", h1.treeposition(), "---", h2.treeposition(), 
            if d<=maxDepth:
                ca1 = s1.root()[commonAncestor(s1, s2)]
                ca2 = h1.root()[commonAncestor(h1, h2)]
                if (ca1,ca2) in matchList: continue
                if (ca1,ca2) in matchingParentNodes: continue
                if PRINT_DEBUG: 
                    print
                    print "Original:  ", nodeText(s1), " --- ", nodeText(s2), "\tdistance ", d
                    print "Highlight: ", nodeText(h1), " --- ", nodeText(h2), nodeDistance(h1,h2)
                    print "Ancestors in match list? ", (ca1,ca2) in matchList
                    print "Original parent phrase: ", nodeText(ca1)
                    print "Highlight parent phrase:", nodeText(ca2)
                
                matchingParentNodes.append( (ca1, ca2) )
    return matchingParentNodes



def linkParentNodesOfSingleChildren(matchList, srcPL, tgtPL):
    """
    If both src and target nodes are single children of their parents,
    link the parents too
    """
    ml=[]
    srcPLPos = [p.tree().treeposition() for p in srcPL]
    for (s,t) in matchList:
        if not s.parent(): continue # don't worry about root
        sChList = [ ch for ch in s.parent() if ch.treeposition() in srcPLPos ]
        #print "SRC child:", s.treeposition(),  len(sChList), [p.treeposition() for p in sChList]
        if len(sChList)==1:
            ml.append((s.parent(), t.parent()))
    return ml
    
def linkParentNodesOfSingleTargetChild(matchList, srcPL, tgtPL):
    """
    If target node is a single child of its parent,
    link the parents too
    """
    ml=[]
    tgtPLPos = [p.tree().treeposition() for p in tgtPL]
    for (s,t) in matchList:
        if not t.parent(): continue # don't worry about root
        tChList = [ ch for ch in t.parent() if ch.treeposition() in tgtPLPos ]
        #print "TGT child:", t.treeposition(),  len(tChList), [p.treeposition() for p in tChList]
        if len(tChList)==1:
            ml.append((s.parent(), t.parent()))
    return ml
    
def linkParentNodesOfSingleLinkedChildren(matchList, srcPL, tgtPL):
    """
    If a linked node is the only linked child of its parent, at both source and target,
    link the parents too
    """
    ml=[]
    srcLinkedPos = [s.treeposition() for (s,_t) in matchList ]
    tgtLinkedPos = [t.treeposition() for (s,t) in matchList ]
    
    for (s,t) in matchList:
        if not s.parent(): continue # don't worry about root
        if not t.parent(): continue # don't worry about root
        
        sChList = [ ch for ch in t.parent() if ch.treeposition() in srcLinkedPos ]
        tChList = [ ch for ch in t.parent() if ch.treeposition() in tgtLinkedPos ]
        # print "S-T child:", s.treeposition(),"---",t.treeposition(),  "\t", len(sChList), "---", len(tChList), [p.treeposition() for p in tChList]
        if len(sChList)==1 and len(tChList)==1:
            ml.append((s.parent(), t.parent()))
    
    return ml
    
    
def refineML_TopLevelMatch(ml):
    if PRINT_DEBUG:
        for m in ml:
            print "Phrase match\t%s\t-> %s\t\t(%s)\t-> (%s)" % (m[0].tag(), m[1].tag(), nodeText(m[0]), nodeText(m[1])), topLevelPhrasesMatch(m)
    return [ m for m in ml if topLevelPhrasesMatch(m) ]


def refineML_RemoveKnownMatches(ml, knownML):
    return [ m for m in ml if m not in knownML ]

def refineML_RemoveDuplicates(ml):
    newML = []
    for m in ml:
        if m not in newML:
            newML.append(m)
    return newML


def refineML_RemoveMissedProperNouns(ml, knownML):
    return [ m for m in ml if _refineML_RemoveMissedProperNounsTest(m) ]

def _refineML_RemoveMissedProperNounsTest(m):
    """
    Return True if the match conveys any NP present in the source tree
    """
    if m[0].isLeaf() or m[1].isLeaf(): return True
    # looking for S where NP isn't included
    # if m[0].tag()=="S" and m[1].tag():
    srcTags = [ch.tag() for ch in m[0]]
    tgtTags = [ch.tag() for ch in m[1]]
        
    if "NP" not in srcTags and "NP" in tgtTags:
        # TODO: check that NP actually contains proper nouns as children
        if PRINT_DEBUG:
            # print "Missing NP"
            print nodeText(m[0])
            print nodeText(m[1])
            #raise SystemExit
        return False
    return True


def _createPhraseMatchList(tree1, tree2, matchList, doEquivNodes=False):
    """
    Create the list of linked phrases between tree1 and tree2
    """
    phraseListTxt1 = tree1.getPhrases()
    phraseListHi1 = tree2.getPhrases()
    
    if PRINT_DEBUG or PRINT_DEBUG_SPLIT:
        print "\nPhrase 1 nodes:"
        printAllPhraseInfo(phraseListTxt1)
        print "\nPhrase 2 nodes:"
        printAllPhraseInfo(phraseListHi1)
    
    # Match phrases based on word content
    # match exact phrases first
    matchList.extend( _phraseMatchListExactText(phraseListTxt1, phraseListHi1) )
    if PRINT_MATCH_LIST: 
        print matchList
        print "Exact phrase matching:"
        printAllMatchListInfo(matchList)
    
    # match based on headwords
    matchList.extend(_phraseMatchListHeadwords(phraseListTxt1, phraseListHi1,stoplist=True))
    
    matchList = refineML_TopLevelMatch(matchList)
    matchList = refineML_RemoveDuplicates(matchList)
    bestMatchList = matchList[:] # copy of matches we believe
    if PRINT_MATCH_LIST:
        print "*** raw match list, after identical phrases matched"
        printAllMatchListInfo(matchList)
        print "----------"
        

    # relatively safe matches are completed
    # now build up tree
    continueMatching = True
    watchdogLoopCounter = 0
    while (continueMatching)>0:
        watchdogLoopCounter += 1
        if watchdogLoopCounter > 10: raise ValueError,"watchdog for match list creation"
        _oldMLLength = len(matchList) # only for debugging, can compare to newML length
        newML = []
        
        # Link parent nodes together as well
        # including stop words
        newML.extend(linkParentNodes(matchList, matchList))
        if PRINT_MATCH_LIST:
            print "*** match list, after parent phrases matched"
            printAllMatchListInfo(newML)
    
        # Link equivalent higher nodes
        # generally this is no longer needed, now that we can contract trees
        # It is still needed if we are describing links to more than one target
        if doEquivNodes:
            mequiv = linkHigherEquivalentNodes(matchList)
            if PRINT_MATCH_LIST:
                print "*** equivalent nodes"
                printAllMatchListInfo(mequiv)
                # raise SystemExit
            newML.extend(mequiv)
            if PRINT_MATCH_LIST: printAllMatchListInfo(newML)
    
        newML.extend(linkParentNodesOfSingleChildren(matchList, phraseListTxt1, phraseListHi1 ))
        newML.extend(linkParentNodesOfSingleTargetChild(matchList, phraseListTxt1, phraseListHi1 ))
        newML.extend(linkParentNodesOfSingleLinkedChildren(matchList, phraseListTxt1, phraseListHi1 ))
    
        # Link child nodes that may not be independent phrases
        # but which do have identical word content
        # Working with highlights rather than sentences
        # as it's more important to match all the phrases of the highlight
        # nodesAlreadyMatched = [ n2 for (n1,n2) in matchList ] 
        for (ph1, ph2) in matchList:
            if ph1.isLeaf() or ph2.isLeaf(): continue
            newML.extend(linkIdenticalNodes(ph1,ph2,matchList))
            newML.extend(linkIdenticalWords(ph1,ph2,matchList))
            
        if PRINT_MATCH_LIST: 
            print "*** After further linking nodes"
            printAllMatchListInfo(newML)
    
    
        # Remove any rules that involve a change to top level phrase type
        # We think that the only rules worth learning keep the 
        # top level phrase element the same
        
        newML = refineML_TopLevelMatch(newML)
        newML = refineML_RemoveDuplicates(newML)
        newML = refineML_RemoveKnownMatches(newML, matchList)
        # newML = refineML_RemoveMissedProperNouns(newML, matchList)
        
        matchList.extend(newML)
        matchList = topDownConsistency(tree1, tree2, matchList, bestMatchList)
        
        # check to see what this iteration has done
        newMLAcceptedLinks = [ m for m in newML if m in matchList ]
        if len(newMLAcceptedLinks)==0: continueMatching=False
        
        if PRINT_MATCH_LIST:
            print
            print "After refining matchList so top levels match"
            print "New matches:"
            printAllMatchListInfo(newML)
            print "New matches that were accepted:"
            printAllMatchListInfo(newMLAcceptedLinks)
            print "Full set of matches:"
            printAllMatchListInfo(matchList)
        
        # TODO: make a consistent tree
        
    # raise SystemExit,"End of while loop"

    matchListRefined = topDownConsistency(tree1, tree2, matchList, bestMatchList)
    matchList = matchListRefined
    if PRINT_MATCH_LIST:
        print
        print "After refining matchList after making consistent top down"
        printAllMatchListInfo(matchList)
        
    # raise SystemExit,"topDownConsistency"
    return matchList
    
    
def topDownConsistency(tree1, tree2, matchList, bestMatchList):
    refML = _topDownConsistencySrcRec(tree1, tree2, matchList, bestMatchList)
    if PRINT_MATCH_LIST:
        print "Refined match list, after src side making consistent top down"
        printAllMatchListInfo(refML)
    refML = _topDownConsistencyTgtRec(tree1, tree2, refML, bestMatchList)
    if PRINT_MATCH_LIST:
        print "Refined match list, after making consistent top down"
        printAllMatchListInfo(refML)
    # raise SystemExit,"topDownConsistency"
    return refML


def _topDownConsistencySrcRec(tree1, tree2, matchList, bestMatchList):
    """
    Recurrent version
    """
    refML = []
    ph2list = [ ph2 for (ph1,ph2) in matchList if ph1 is tree1 and \
            ( ph2 is tree2 or ph2.isDescendent(tree2))]
    
    if PRINT_DEBUG:
        print "Current pos: ", tree1.tag(), tree1.treeposition(), " --- ", tree2.treeposition(), len(ph2list)
        for ph2 in ph2list:
            print tree1.treeposition(), "---", ph2.treeposition()
    
    if len(ph2list)==1:
        bestPh2 = ph2list[0]
        refML.append( (tree1, bestPh2) )
    elif len(ph2list)>1:
        try:
            bestPh2 = [ ph2 for ph2 in ph2list if (tree1,ph2) in bestMatchList ][0]
        except IndexError:
            # depths = map(lambda ph: len(ph.treeposition()), ph2list) # for debugging
            _depth, bestPh2 = min((len(ph.treeposition()),ph) for ph in ph2list)
        refML.append( (tree1, bestPh2 ) )
    else:
        bestPh2 = tree2 # to be passed to next level
    
    if not tree1.isLeaf():
        for ch in tree1:
            refML.extend(_topDownConsistencySrcRec(ch, bestPh2, matchList, bestMatchList))
    return refML
    
def _topDownConsistencyTgtRec(tree1, tree2, matchList, bestMatchList):
    """
    Recurrent version, making the target tree consistent.
    We want to allow several nodes in source tree to link to this, but they
    must be consistently from the same tree1
    """
    refML = []
    
    # only include descendents of tree1 in match list
    ph1list = [ ph1 for (ph1,ph2) in matchList if ph2 is tree2 and \
            ( ph1 is tree1 or ph1.isDescendent(tree1))]
    for ph1 in ph1list: refML.append( (ph1, tree2) )

    if PRINT_DEBUG:
        print "Current pos: ", tree1.tag(), tree1.treeposition(), " --- ", tree2.tag(), tree2.treeposition(), len(ph1list)
        for ph1 in ph1list:
            print ph1.treeposition(), "---", tree2.treeposition()
        
    if len(ph1list)==1:
        bestPh1 = ph1list[0]
    elif len(ph1list)>1:
        # _depths = map(lambda ph: len(ph.treeposition()), ph1list) # just for debugging
        _depth, bestPh1 = max((len(ph.treeposition()),ph) for ph in ph1list)
    else:
        bestPh1 = tree1 # to be passed to next level
    
    if not tree2.isLeaf():
        for ch in tree2:
            refML.extend(_topDownConsistencyTgtRec(bestPh1, ch, matchList, bestMatchList))
    return refML
    
    
def _phraseMatchListExactText(phraseList1, phraseList2):
    # Match phrases based on word content
    # match exact phrases first
    if False:
        print "_phraseMatchListExactText"
        for (ph1,ph2) in allPhrasePairs(phraseList1, phraseList2):
            print nodeTextNoPunctuation(ph1),"---",nodeTextNoPunctuation(ph2),
            print nodeTextNoPunctuation(ph1)==nodeTextNoPunctuation(ph2)
            
    matchList = [(ph1,ph2) \
        for (ph1,ph2) in allPhrasePairs(phraseList1, phraseList2) \
        if nodeTextNoPunctuation(ph1)==nodeTextNoPunctuation(ph2)]
    return matchList


def _phraseMatchListHeadwords(phraseList1, phraseList2, stoplist):
    matchList = [(ph1,ph2) \
        for (ph1,ph2) in allPhrasePairs(phraseList1, phraseList2) \
        if phrasesMatch(ph1, ph2, headwords=True, stoplist=stoplist) ]
    return matchList

def _phraseMatchListNonHeadwords(phraseList1, phraseList2, stoplist):
    matchList = [(ph1,ph2) \
        for (ph1,ph2) in allPhrasePairs(phraseList1, phraseList2) \
        if phrasesMatch(ph1, ph2, headwords=False, stoplist=stoplist) ]
    return matchList


def allPhrasePairs(l1, l2):
    for phrase1 in l1:
        ph1 = phrase1.tree()
        for phrase2 in l2:
            ph2 = phrase2.tree()
            yield ph1, ph2

MATCH_STOP_TAGS = set(('.',',','IN','DT','TO','CC'))
#MATCH_STOP_TAGS = set(('.',',','IN','DT','TO','VBZ','CC'))
def phrasesMatch( tree1, tree2, stoplist=True, headwords=False ):
    """
    Returns True if the phrases match.
    Currently removes case information and looks for identity match.
    TODO: cope with lists of words, remove stop words and check content words
    """
    
    assert type(tree1)==PhraseDependencyTree.PhraseDependencyTree, "Phrase not correct type"
    assert type(tree2)==PhraseDependencyTree.PhraseDependencyTree, "Phrase not correct type"
    
    if headwords: # only use words that have dep==FIXED 
        tok1List = [p for ch in tree1 for p in ch.pos() if ch.isLeaf() and 
            ch.dep()==PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT ]
        tok2List = [p for ch in tree2 for p in ch.pos() if ch.isLeaf() and 
            ch.dep()==PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT ]
    else:
        tok1List = [p for ch in tree1 for p in ch.pos() if ch.isLeaf() ]
        tok2List = [p for ch in tree2 for p in ch.pos() if ch.isLeaf() ]
        
    #print "tok1List:",tok1List
    #print "tok2List:",tok2List
    for (t1,tag1) in tok1List:
        if stoplist and (tag1 in MATCH_STOP_TAGS): continue
        for (t2,tag2) in tok2List:
            if wordsMatch(t1,t2, tag1, tag2):
                # print t1, tag1, " matches ", t2, tag2 
                return True
                
    return False


def wordsMatch( w1, w2, tag1, tag2 ):
    return NltkUtils.stem(w1, tag1)==NltkUtils.stem(w2, tag2)
