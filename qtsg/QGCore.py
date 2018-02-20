"""
Various helpful functions for the QG module
"""

from itertools import count, izip

import txt2txtgen.parse.PhraseDependencyTree as PhraseDependencyTree
from QGDefs import *


class PhraseTreeChoice(PhraseDependencyTree.PhraseDependencyTree):
    """
    A node in the PhraseDependencyTree that contains a choice
    of sub-trees. We assume that exactly one will be chosen.
    """
    TAG = "CHOICE"

    @classmethod    
    def create(cls, choices):
        assert len(choices)>0, "PhraseTreeChoice does not have any children"
        
        # combine choices that actually produce the same text
        choiceDict={}
        for ch, count, identical, rule in choices:
            # print nodeText(ch), count, identical
            key = nodeText(ch)
            try:
                # combine with existing entry
                currCh, currCount, currIdentical, currRule = choiceDict[key]
                choiceDict[key] = (currCh, currCount + count, currIdentical or identical, currRule)
            except KeyError:
                # New entry, add to dictionary
                choiceDict[key] = (ch, count, identical, rule)
        # print choiceDict
        
        choices = choiceDict.values()
        children, counts, identicalFlags, rules = zip(*choices)
        
        
        if False:
            print "identicalFlags:", identicalFlags
            # raise SystemExit, "PhraseTreeChoice identical output check"

        # cut down to 1 choice now, so no need for CHOICE structure
        if len(choices)==1:
            return children[0]
            
    
        assert len(choices)>1, "PhraseTreeChoice does not have a choice of children"
            
        t = PhraseTreeChoice( PhraseTreeChoice.TAG, children)
        t._counts = counts
        t._identicalFlags = identicalFlags
        t._totalCount = sum(counts)
        t._rules = rules
        lengths = map(lambda ch: len(ch.leaves()), children)
        longestValue, longestIndex = max(izip(lengths, range(len(choices))))
        t.setChoice(longestIndex)

        # do some checks on the resulting object
        assert isinstance(t, PhraseTreeChoice), "Cannot create a paraphrase choice tree from %s" % t
        assert t.tag() == PhraseTreeChoice.TAG, "Tag not correctly set up %s" % t.tag()
        assert t._identicalFlags, "t._identicalFlags not set up"
        assert len(t._identicalFlags) == len(t), "Wrong number of identical phrase flags"
        assert len(t._counts) == len(t), "Wrong number of rule count flags"
        for ch in t:
            assert not isinstance(ch, PhraseTreeChoice), "Cannot create a paraphrase choice tree from %s" % ch
        
        return t


    def __init__(self, node_or_str, children=None):
        #print "In PhraseTreeChoice.__init__() making ", node_or_str
        if children is None: return # see note in Tree.__init__() 
        super(PhraseTreeChoice,self).__init__(node_or_str, children)
        self._indPhrase = True
        self._choice = 0


    # TODO: delegation methods to current choice
    def leaves(self): return self[self._choice].leaves()

    def leaf_nodes_in_order(self):        
        """ Iterates through all leaf nodes, but respecting choices and pruning tree """ 
        # delegate to current choice
        return self[self._choice].leaf_nodes_in_order()
                
    def token_range_not_needed(self):
        """
        Return the range of token indices covered by this node.
        Returns a tuple (start, end), where start is the index
        of the left-most leaf, and end is the index of the first 
        leaf to the right of this node.
        This returns the range of tokens covered by any of the choices at this node
        """
        assert not self.isLeaf(), "Only leaf information at this choice node"
        child_ranges = [ch.token_range() for ch in self if ch is not None]
        left_token_ranges, right_token_ranges = zip(*child_ranges)
        return (min(left_token_ranges), max(right_token_ranges))

    
    def counts(self): return self._counts
    def identicals(self): return self._identicalFlags
    def totalCount(self): return self._totalCount
    def getChoice(self): return self._choice
    def setChoice(self, i): self._choice = i
    def dep(self): return self[self._choice].dep()
    def current_rule(self):
        if self._choice is None: # this choice is not currently being used
            return None
        else:
            return self._rules[self._choice]
    
    # special handling for fixed leaves --- nothing is fixed, only depends on choice
    def fixedLeaves(self): return []

    def copyAttributes(self, original):
        """
        Copies the attributes from original to self
        """
        assert isinstance(original,PhraseTreeChoice), "Cannot copy from object that is not a PhraseTreeChoice"
        super(PhraseTreeChoice,self).copyAttributes(original)
        self._counts = original._counts
        self._totalCount = original._totalCount
        self._identicalFlags = original._identicalFlags



##############################################
# print functions
##############################################

def nodeText(node):
    return " ".join(node.leaves())
    
def nodeTextNoPunctuation(node):
    punctuationTags=['SYM',"`","'",',','.',':']
    leaves = [ l[0] for l in node.pos() if l[1] not in punctuationTags]
    return " ".join(node.leaves())
    
def nodePhraseText(node):
    leaves = node.root.leaves()
    words = [leaves[i] for i in node._wordPos]
    return " ".join(words)
    
def describeSyncTrees(ph1, ph2, links):
    """
    Describe the grammar structure of the subtree at ph1, 
    the subtree at ph2,
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

def printPhraseTreeStructure( phraseTree ):
    print "%s/%s" % (phraseTree.tag(), phraseTree.dep()), 
    print "(",
    for ch in phraseTree:
        print "%s/%s" % (ch.tag(), ch.dep()), 
    print ")"
    


##############################################
# node distance and ancestor functions
##############################################
def equivalentNodes( n1, n2 ):
    return n1.__repr__() == n2.__repr__()


def nodeDistance(n1, n2):
    ca = commonAncestor( n1, n2)
    root = n1.root()
    n1pos = n1.treeposition()
    n2pos = n2.treeposition()
    
    if False and PRINT_DEBUG:
        print
        print "ca.treeposition: ", ca, n1.root()[ca].tag(), n1.root()[ca].dep(), n1.root()[ca].leaves()
        print "n1.treeposition: ", n1.treeposition(), n1.tag(), n1.dep(), n1.leaves()
        print "n2.treeposition: ", n2.treeposition()
    
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
    if PRINT_DEBUG:
        # checks to see if the root nodes are really same
        print "Root nodes: ",  id(n1.root()), id(n2.root()), "Unrelated nodes?"
        if not n1.root() is n2.root():
            print "Unrelated nodes here"
            pass
    assert n1.root() is n2.root(), "Unrelated nodes"
    
    # Find the tree positions of the start & end leaves, and 
    # take the longest common subsequence. 
    start_treepos = n1.treeposition()
    end_treepos = n2.treeposition()
    return commonAncestorPositions(start_treepos, end_treepos)


def commonAncestorPositions(p1, p2):
    # Find the first index where they mismatch: 
    for i in range(len(p1)): 
        if i == len(p2) or p1[i] != p2[i]: 
            return p1[:i] 
    return p1         


