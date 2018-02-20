"""
Investigate how to represent the dependencies
between phrases rather than head-words,
and keep the ability to regenerate the sentences.
"""



#import os
import nltk
import string
import copy

from txt2txtgen.config import Debug

#from POSTagger import StanfordDependencyParser, StanfordPennParser, \
#    _newTempFile, _writeTempFile
#from ListFiles import listAllFiles
#from ExtractFeatures import *
#import ExtractPhraseFeatures

    
FORMAT="pdf"
GRAPHVIZ_EXTRA = False
#MIN_PHRASE_SIZE = 2


class Phrase(object):
    def __init__(self, tree, leaves):
        self._tree = tree
        self._leaves = leaves
    
    def tree(self):
        return self._tree
        
    def leaves(self):
        return self._leaves
        
            
 

class PhraseDependencyTree(nltk.tree.ParentedTree):
    """
    Phrase tree with dependency information.
    """
    FIXED_DEPENDENT="<-"
    USE_CONSTITUENCY_STRUCTURE = -1
    INDEPENDENT_PHRASE_TAGS = ('S','SBAR','SQ','SBARQ','SINV','ST',
        'ADJP','ADVP','NP', 'PP','PRN','PRT','QP','VP','UCP',
        'WHADJP','WHADVP','WHAVP','WHNP','WHPP',
        'CHOICE', 'ROOT', 
        'FRAG', 'XS', 'NX')
    
    COPULA_VERB_TAGS = set(('VBZ-COP', 'VBP-COP' , 'VBD-COP', 'VB-COP', 'VBG-COP', 'VBN-COP'))
    MATCH_STOP_TAGS = set(('.', ',' , ':', '-LRB-', '-RRB-', "''", "``", 'POS', 'IN','DT','TO','CC', 'MD', 'RB', 'PRP', 'PRP$')).union(COPULA_VERB_TAGS)
    
    # subdivide verb phrases into types --- all different
    VERB_PHRASE_TAGS = set(('VBZ', 'VBP' , 'VBD', 'VB', 'VBG', 'VBN', 'MD', 'TO')).union(COPULA_VERB_TAGS)

    
    def __eq__old(self, other):
        """
        Tests equality based on where we are in the tree as well as strings.
        Fails if wordPos values are not unique in the tree (multiple sentences)
        """
        raise DeprecationWarning,"Equality based on wordPos tests"
        if not isinstance(other, PhraseDependencyTree): return False
        return self._wordPos==other._wordPos \
            and self.parent == other.parent \
            and nltk.tree.ParentedTree.__eq__(self, other)
            
        
    def __init__(self, node_or_str, children=None):
        # if children is None: return # see note in Tree.__init__() 
        super(PhraseDependencyTree,self).__init__(node_or_str, children)
        
        self._head=None # record if this is the head word of the parent phrase
        self._rel=None  # relation between this node and its parent
        self._fixed=False # this subtree is a fixed part of the parent phrase
        self._indPhrase=False # this node and below can be an independent phrase
        self._wordPos=[] # Position of leaf tokens in the sentence
        self._phraseIndex=None # Index of this phrase in the full list of phrases
        self.__tokenInfo = None # Token information from Stanford parser
        
        
    def tag(self): return self.label()
    def dep(self): return self._rel
    
    # Get and set methods for the index of this node in the total phrase list
    def phrIndex(self): return self._phraseIndex
    def setPhrIndex(self, i):
        # reduced documents require phrase index to be set again
        # assert self._phraseIndex==None, "Phrase index already set to %d for %s"%(self._phraseIndex,self)
        self._phraseIndex=i
    
    def markHeadWords(self):
        raise DeprecationWarning, "Head word markers were something in the old Stanford output"
        if (self.label().endswith("=H")):
            print "Head word: ", self.label()
            self._head = True
            self.set_label(self.label()[:-2])
            
        for ch in self:
            if isinstance(ch, nltk.tree.Tree):
                ch.markHeadWords()
            
    def markPositions(self):
        if (Debug.PRT_PhraseDependencyTree > 2): print "markPositions:", self.label()
        pos = 0
        pos = self._markPositions(pos)
        assert (pos==len(self.leaves())),"Tokens not matching leaves"
        
    def _markPositions(self,pos):
        if (self.isLeaf()):
            self._wordPos=[pos]
            pos += 1
        else:
            for ch in self:
                try:
                    pos = ch._markPositions(pos)
                except AttributeError:
                    raise PhraseTreeError(ch)
        return pos
    
    def getWordPosition(self): return self._wordPos
    
    def storeTokenInfo(self, tokens):
        for l in self.leafNodes():
            assert len(l._wordPos) == 1, "Word position not set up for this leaf"
            pos = l._wordPos[0]
            l.__tokenInfo = tokens[pos]
        pass
    
    def storeSingleTokenInfo(self, token):
        assert self.isLeaf(), "No token information for nodes that are not leaves"
        assert self.__tokenInfo is None, "Token information already set up"
        self.__tokenInfo = token
        
    def token(self):
        assert self.isLeaf(), "No token information for nodes that are not leaves"
        return self.__tokenInfo
        

    def token_range(self):
        """
        Return the range of token indices covered by this node.
        Returns a tuple (start, end), where start is the index
        of the left-most leaf, and end is the index of the first 
        leaf to the right of this node 
        """
        if self.isLeaf():
            # return position of this token
            t = self.token()
            if t is not None:
                return (t.index, t.index + 1)
            else:
                return None
        
        else:
            all_ranges_inc_None = [ch.token_range() for ch in self]
            child_ranges = [r for r in all_ranges_inc_None if r is not None]
            #print self.tag(), self, child_ranges
            if len(child_ranges) == 0: 
                return None
            
            left_token_ranges, right_token_ranges = zip(*child_ranges)
            return (min(left_token_ranges), max(right_token_ranges))

    
    
    def markTopSentenceNode(self):
        """
        Find the Sentence node S under ROOT, and mark it as a top level
        node ST
        """
        if self.tag()=="ROOT":
            if len(self)>0 and self[0].tag()=="S":
                # sentence node under root
                self[0].set_label("ST")
        
    
    def mark_copula_verbs(self):
        """
        Mark all the verb instances of "be" with their own tags
        """
        for t in self.subtrees(filter=lambda n: n.isLeaf() and n.tag() in self.VERB_PHRASE_TAGS ):
            if t.token().lemma == "be":
                t.set_label(t.label() + "-COP")
                #print "Rewritten tag for be verb: \t", t.tag(), t.token().lemma
    
    
    def verb_phrase_subtypes(self):
        """
        mark the different types of verb phrase based on first verb POS-tag
        """
        for t in self.subtrees(filter=lambda n: n.tag()=="VP"):
            verb_pos = [p for p in t.pos() if p[1] in self.VERB_PHRASE_TAGS]
            try:
                first_verb_postag = verb_pos[0][1]
                # don't combine tags into VERB_PHRASE_FROM_NOUN_PHRASE_TAGS here, do that in the QTSG matching
                # print label, " from ", t.pos()
                label = "VP-"+first_verb_postag
                t.set_label(label)
            except IndexError:
                # handle verb_pos being empty by just using label VP
                if (Debug.PRT_PhraseDependencyTree > 0):
                    print "No verb tagged: ", t.pos()
                pass
        
    def mark_NP_possession(self):    
        """
        Mark possession noun phrases so they cannot be linked to others
        """
        for t in self.subtrees(filter=lambda n: n.tag()=="NP" and n.dep()=="poss"):
            t.set_label("NP-POSS")

    
    
    def correctTree(self):
        """
        Remove buggy nodes from parser:
        single child S(VP) to VP
        """
        raise DeprecationWarning, "Not sure if we want the tree corrected any more"
        for t in self.subtrees(filter=lambda n: n.tag()=="S" and len(n)==1):
            p = t.parent
            i = p.index(t)
            p.pop(i)
            ch = t.pop(0)
            p.insert(i,ch)
            
            
    
    def addDependencies(self,dg):
        """
        Add in dependencies into the phrase structure tree.
        param dg A dependency graph
        """
        if (Debug.PRT_PhraseDependencyTree > 2): print "Adding dependencies"
        already_visited = set([])
        self._addDependenciesForAddr(dg,0,already_visited) # root
        # fix all unassigned relations
        self._fixUnassignedDependencies()
        self._setFixedPhrases()
        
        
    def _fixUnassignedDependencies(self):
        if (not self._rel): self._rel=PhraseDependencyTree.FIXED_DEPENDENT
        for ch in self:
            if isinstance(ch, PhraseDependencyTree): 
                ch._fixUnassignedDependencies()
        
            
    def _addDependenciesForAddr(self,dg,addr,already_visited):
        """
        Working through dependency graph from root, 
        add dependency relations to this tree.
        We only assign a relation to a node on the tree if
        none has been assigned already.
        This assumes we work through the graph following dependencies.
        """
        root = self.root()
        already_visited.add(addr)
        for dep in dg.deps(addr): # mark the dependencies of this address
            if (Debug.PRT_PhraseDependencyTree > 2): 
                print "Working with dep", dep
                print len(self.leaves()), self.leaves()
            rel = dg.rel(dep)
            dep_pos = self.leaf_treeposition(dep-1)
            for i in range(1,len(dep_pos)): # up to leaf node, but not including it
                midNode = root[dep_pos[:i]]
                if (Debug.PRT_PhraseDependencyTree > 2): 
                    print "position: ", midNode.treeposition(),
                    print "current: ", midNode.label(),
                    print "parent: ", midNode.parent().label()
                if (not midNode._rel): 
                    midNode._rel=rel
                    rel = PhraseDependencyTree.FIXED_DEPENDENT # assign real rel only once
                    
                if (Debug.PRT_PhraseDependencyTree > 2): print "relation: ", midNode._rel
                
            # work through child dependencies
            if dep not in already_visited:
                self._addDependenciesForAddr(dg,dep,already_visited)
                
    def _setFixedPhrases(self):
        """
        Sets self._fixed true if this node
        represents a single phrase with no 
        decision points.
        """
        for ch in self:
            if isinstance(ch, PhraseDependencyTree): 
                ch._setFixedPhrases()
                
        # This tree is fixed if all children are fixed,
        self._fixed = True
        for ch in self:
            if isinstance(ch, PhraseDependencyTree): 
                if (not ch.isFixed()) : # child has independent phrases
                    self._fixed = False
                    break
                elif (not ch._rel==PhraseDependencyTree.FIXED_DEPENDENT ):
                    self._fixed = False
                    break # this child is not fixed to the parent
                    
                # elif (len(ch.leaves()) >= minIndependentLength):
                #    self._fixed = False # child can exist as independent phrase
                #     break
        
        if (Debug.PRT_PhraseDependencyTree > 2): print "setting fixed: ", self.label(), self._fixed


    def isFixed(self):
        """
        If true, this subtree contains no phrase decision points
        """
        return self._fixed or self.dep()==PhraseDependencyTree.FIXED_DEPENDENT
        
    def fixedLeaves(self):
        """
        Return all leaves below that are fixed to this node
        """
        if self.isLeaf(): return self.leaves()
        
        l=[]
        for ch in self:
            if ch.isFixed(): l.extend(ch.fixedLeaves())
        return l

        
    def fixedPOS(self):
        """
        Return POS tuples for all leaves below that are fixed to this node
        """
        raise DeprecationWarning, "I don't think this is used"
        # todo: delete this and related methods

        if self.isLeaf(): return self.pos()
        l=[]
        for ch in self:
            if ch.isFixed(): l.extend(ch.fixedPOS())
        return l


    def dependentPOS(self):
        """
        Return tokens for all leaves below that are dependent of this node
        """
        if self.isLeaf(): return (self.token(),)
        l=[]
        for ch in self:
            if not ch.isIndependentPhrase(): l.extend(ch.dependentPOS())
        return l

        
        
    def markIndependentPhrase(self, minIndependentLength=2):
        """
        Sets self._indPhrase true if this node
        has at least minIndependentLength leaves.
        If the magic value of USE_CONSTITUENCY_STRUCTURE is used for minIndependentLength,
        independent phrases will be marked based on the parser phrase structure
        and the list of phrase markers INDEPENDENT_PHRASE_TAGS
        """
        for ch in self:
            if isinstance(ch, PhraseDependencyTree): 
                ch.markIndependentPhrase(minIndependentLength)
                
        if (minIndependentLength==PhraseDependencyTree.USE_CONSTITUENCY_STRUCTURE):
            if self._tag_is_independent_phrase():
                self._indPhrase = True
            
        elif (self._rel==PhraseDependencyTree.FIXED_DEPENDENT):
            self._indPhrase = False

        elif (len(self.leaves()) >= minIndependentLength):
            self._indPhrase = True
        if (Debug.PRT_PhraseDepTree):
            print self.tag(), self.dep(), "\tIndependent",self._indPhrase,"\tLeaves: ", self._wordPos            
    
    def _tag_is_independent_phrase(self):
        if self.isLeaf(): 
            return False
        elif self.tag() in PhraseDependencyTree.INDEPENDENT_PHRASE_TAGS: 
            return True
        # handle VP and NP-TMP, NP-POSS
        elif self.tag().startswith("VP") or self.tag().startswith("NP"): 
            return True
        
        else:
            # just have all non-terminals as independent?
            if Debug.PRT_PhraseDependencyTree: 
                print "Independent phrase? ", self.tag(), self.leaves(), "\n", self
                assert False, "Found unknown tag: %s" % self.tag()
            
            return True
    
        
    def isIndependentPhrase(self):
        """
        True if this node can be considered an independent phrase.
        
        N.B. This method gets called a lot.
        """
        return self._indPhrase


    def collapseIntoPhrases(self):
        """
        Identifies fixed nodes, and collapses them into
        single phrase nodes
        """
        raise DeprecationWarning, "I don't think this is used"
        # TODO: delete this and related methods
        
        if (Debug.PRT_PhraseDependencyTree > 2): print "copiedNodeList here: ", self
        if (self.isFixed() and self is not self.root()):
            # Collapse the children into a single string
            if (Debug.PRT_PhraseDependencyTree > 2): print "Leaves: ", self.leaves()
            txt = " ".join(self.leaves())
            l=[]
            self._getLeafWordPos(l)
            if (Debug.PRT_PhraseDependencyTree > 2): print "Node text: ", txt
            if (Debug.PRT_PhraseDependencyTree > 2): print "Node leaf pos: ", l, "Node pos: ", self._wordPos
            self[0] = txt
            self._wordPos=l
            del self[1:]
            if (Debug.PRT_PhraseDependencyTree > 2): print self
        else:
            for ch in self:
                if isinstance(ch, PhraseDependencyTree): 
                    ch.collapseIntoPhrases()
            self._mergeNonIndPhrases()

    
    def _getLeafWordPos(self,l):
        raise DeprecationWarning, "I don't think this is used"
        # TODO: delete this and related methods
        
        l.extend(self._wordPos)
        if (not self.isLeaf()): 
            for ch in self:
                ch._getLeafWordPos(l)
        if (Debug.PRT_PhraseDependencyTree > 2): print self.label(), l

                    
    def collapseFixedLinks(self):
        """
        If link to parent is fixed, then remove this node
        and move children to the parent
        """
        raise DeprecationWarning, "I don't think this is used"
        # TODO: delete this and related methods
        
        # Do children first, before we lose contact with them
        for ch in self:
            if (Debug.PRT_PhraseDependencyTree > 2): print "At ", self.label(), "Current child: ", ch.label(), "Leaf:", ch.isLeaf()
            if not ch.isLeaf(): 
                ch.collapseFixedLinks()
                
        if (Debug.PRT_PhraseDependencyTree > 2): print "I'm here: ", self.label()
        if (self.parent == None ):
            pass # root node
        elif (self._rel==PhraseDependencyTree.FIXED_DEPENDENT \
            or not self.isIndependentPhrase() ):
            parent = self.parent
            if (Debug.PRT_PhraseDependencyTree > 2): print "Parent: ", self.parent, " I'm at index ", self.parent_index
            while len(self):
                ch = self.pop(0)
                self.parent.insert(self.parent_index,ch)
                if (Debug.PRT_PhraseDependencyTree > 2): print " I'm at parent index ", self.parent_index
                if (Debug.PRT_PhraseDependencyTree > 2): print self.parent
            self.parent._wordPos.extend(self._wordPos) # parent takes word pos too
            self.parent.remove(self)
            if (Debug.PRT_PhraseDependencyTree > 2): print "Finally, parent now:"
            if (Debug.PRT_PhraseDependencyTree > 2): print parent, parent._wordPos
        
        # collapse if child node is leaf, and link to child is fixed
        elif (len(self)==1 and self[0].isLeaf() \
              and not self[0].isIndependentPhrase()):
            # move grandchild to child
            self._wordPos.extend(self[0]._wordPos)
            gch = self[0][0]
            self[0] = gch
            
    def _mergeNonIndPhrases(self):
        raise DeprecationWarning, "I don't think this is used - only in collapseIntoPhrases() which is not called"
        # TODO: delete this and related methods
        
        for ch in self:
            while ( not ch.isIndependentPhrase() \
                and not ch.right_sibling==None \
                and not ch.right_sibling.isIndependentPhrase()):
                assert ch.isLeaf(), "Child is not leaf: %s" % ch
                ch[0] += " " + ch.right_sibling[0]
                ch._wordPos.extend(ch.right_sibling._wordPos)
                self.remove(ch.right_sibling)
                if (Debug.PRT_PhraseDependencyTree > 2): print "Merging phrases", ch, ch._wordPos
                
            
    def isLeaf(self):
        """
        Return true if this node represents a leaf.
        True if the single node below this one is a string.
        """
        return ( len(self)==1 and isinstance(self[0],basestring))
        
        
    def isDescendent(self, other):
        """
        Returns true if this node is a descendent of the other node.
        """
        assert isinstance(other, nltk.tree.ParentedTree), "Other node is not a tree"
        if self.root() is not other.root(): return False
        thisPos = self.treeposition()
        otherPos = other.treeposition()
        if len(thisPos) <= len(otherPos): return False
        for i in range(len(otherPos)):
            # print "*** POS: ", i, "\t", thisPos[i], "\t", otherPos[i]
            if not thisPos[i] == otherPos[i]: return False
        return True
            
            
            
    def leafNodes(self):
        """ Iterates through all leaf nodes """ 
        for l in self.subtrees():
            if l.isLeaf():
                yield l
                
                
    def leaf_nodes_in_order(self):        
        """ Iterates through all leaf nodes, but respecting choices and pruning tree """
        # involves delegation, so not using generator
        l = [] 
        if self.isLeaf():
            l.append(self)
        else:
            for ch in self:
                l.extend(ch.leaf_nodes_in_order())
        return l
                
            
    def getPhrases(self):
        """
        Return list of independent phrases contained 
        """
        if (Debug.PRT_PhraseDependencyTree > 2):
            print
            print "In getPhrases()"
            print "Working on tree:"
            print self
        indPhrases = []
        currentPhrase=[]
        currentWordPos=[]
        
        # Don't call on root, but on children
        for ch in self:
            ch._getPhrases(indPhrases, currentPhrase,currentWordPos)
            
        # add the remaining words to top level phrase --- QTSG trees are starting at ST, not ROOT
        indPhrases.append(Phrase(self,currentPhrase))
        return indPhrases
        
    def _getPhrases(self, indPhrases, parentPhrase, parentWordPos):
        """
        Builds up list of independent phrases.
        If there are dependent children, this will
        add the leaves to the parent phrase, and 
        the word positions to the parent's list of word positions
        """
        if (Debug.PRT_PhraseDependencyTree > 2): 
            print self.label(), ":", self.leaves(), "\tword pos:", self._wordPos
            
            
        # TODO: DEBUG --- is this causing phrases to be lost?
        # if (not self.isIndependentPhrase()):
        if (self.isLeaf() and not self.isIndependentPhrase()):
            if (Debug.PRT_PhraseDependencyTree > 2): 
                print self.label(), "not independent, part of parent phrase", self.leaves()
                print "word pos:", self._wordPos
            
            # handle possible independent phrases somewhere below
            if not self.isLeaf():
                for ch in self:
                    ch._getPhrases(indPhrases, parentPhrase,parentWordPos)
                
            parentPhrase.extend(self.leaves())
            # append the word positions individually
            # to avoid duplications
            # we could convert into a set, but this preserves order (may not be a good thing)
            parentWordPos.extend([i for i in self._wordPos if i not in parentWordPos])
            #for i in self._wordPos :
            #    if i not in parentWordPos:
            #        parentWordPos.append(i) 
            #print self._wordPos, parentWordPos
        elif (self.isLeaf()):
            if (Debug.PRT_PhraseDependencyTree > 2): print self.label(), " at ", self.treeposition(), "Leaf and independent phrase", self.leaves()
            indPhrases.append( Phrase(self, self.leaves()))
        else:
            currentPhrase=[]
            for ch in self:
                ch._getPhrases(indPhrases, currentPhrase,self._wordPos)
            indPhrases.append(Phrase(self,currentPhrase))
        
        if (Debug.PRT_PhraseDependencyTree > 1): 
            print "After:\t", self.label(), ":", self.leaves(), "\tword pos:", self._wordPos
            
    
    def has_content(self):
        """
        Returns True if any leaf contains a content word
        """
        if self.isLeaf(): 
            return self._leaf_has_content()
        
        for st in self.subtrees():
            if st is self: continue # don't repeat this node
            if st.has_content():
                return True
        return False

    def _leaf_has_content(self):
        """
        Returns True if this leaf contains content
        """
        assert self.isLeaf(), "This is not a leaf node"
    
        lemma = self.token().lemma
        if lemma == "be" or lemma=="have" or lemma=="do" or lemma=="go" or lemma=="use":
            return False # do not count "be" as a content word
    
        elif self.tag() not in PhraseDependencyTree.MATCH_STOP_TAGS: 
            return True
    
        else:
            return False

            
            
    def copyAttributes(self, original):
        """
        Copies the attributes from original to self
        """
        assert isinstance(original,PhraseDependencyTree), "Cannot copy from object that is not a PhraseDependencyTree"
        self._head   =  original._head
        self._rel    =  original._rel
        self._fixed  =  original._fixed
        self._indPhrase=original._indPhrase
        self._wordPos=  original._wordPos[:] # make copy
        self.__tokenInfo = original.__tokenInfo # Link to original token information from Stanford parser


    
    @classmethod
    def convert(cls, val): 
        """
        Call this specialized convert method that also copies the attributes,
        as well as the tag information and children
        """
        copy = super(PhraseDependencyTree,cls).convert(val)
        #print "Copy: ", copy, copy.__class__
        if isinstance(val, PhraseDependencyTree):
            assert isinstance(copy,PhraseDependencyTree), "Failed to copy instance of PhraseDependencyTree"
            copy.copyAttributes(val) 
            #raise NotImplementedError, "convert for PhraseDependencyTree"
        return copy

    @classmethod
    def create(cls, string): 
        """
        Create a new PhraseDependencyTree from the parse string
        """
        raise DeprecationError, "Is this being used? Seem to always go through StanfordCoreNLP class"
        tree = PhraseDependencyTree(string)
        tree._correctDepTags()
        tree.markPositions()
        tree.markTopSentenceNode()
        tree.mark_copula_verbs()
        tree.verb_phrase_subtypes()
        return tree
    
    
    def _correctDepTags(self):
        for t in self.subtrees():
            try:
                n, d = t.tag().split("/")
                if d == "None": d = None
            except ValueError:
                n= t.tag()
                d = None
            t.set_label(n)
            t._rel = d
        
        

    def copy(self, deep=True): 
        """
        Make a deep copy of this tree without all the conversion nonsense
        """
        if deep:
            children = []
            for ch in self:
                if isinstance(ch, nltk.tree.Tree):
                    children.append( ch.copy(True) )
                else:
                    children.append( ch )
            cp = self.__class__( self.label(), children )
        else:
            raise NotImplementedError, "copy needs to have copy module"
            cp = copy.copy(self)
        cp.copyAttributes(self)
        return cp



    def pprint(self, margin=70, indent=0, nodesep='', parens='()', quotes=False): 
           """ 
           @return: A pretty-printed string representation of this tree. 
           @rtype: C{string} 
           @param margin: The right margin at which to do line-wrapping. 
           @type margin: C{int} 
           @param indent: The indentation level at which printing 
               begins.  This number is used to decide how far to indent 
               subsequent lines. 
           @type indent: C{int} 
           @param nodesep: A string that is used to separate the node 
               from the children.  E.g., the default value C{':'} gives 
               trees like C{(S: (NP: I) (VP: (V: saw) (NP: it)))}. 
           """ 
    
           # Try writing it on one line. 
           s = self._pprint_flat(nodesep, parens, quotes) 
           if len(s)+indent < margin: 
               return s 
           
           # If it doesn't fit on one line, then write it on multi-lines. 
           # Special handling of PhraseDependencyTree here
           if isinstance(self, PhraseDependencyTree):  
               s = '%s%s/%s%s' % (parens[0], self.tag(), self.dep(), nodesep)
           elif isinstance(self.label(), basestring):  
               s = '%s%s%s' % (parens[0], self.label(), nodesep) 
           else: 
               s = '%s%r%s' % (parens[0], self.label(), nodesep) 
           for child in self: 
               if isinstance(child, nltk.tree.Tree): 
                   s += '\n'+' '*(indent+2)+child.pprint(margin, indent+2, 
                                                     nodesep, parens, quotes) 
               elif isinstance(child, tuple): 
                   s += '\n'+' '*(indent+2)+ "/".join(child) 
               elif isinstance(child, basestring) and not quotes: 
                   s += '\n'+' '*(indent+2)+ '%s' % child 
               else: 
                   s += '\n'+' '*(indent+2)+ '%r' % child 
           return s+parens[1] 
    

    def _pprint_flat(self, nodesep, parens, quotes): 
           childstrs = [] 
           for child in self: 
               if isinstance(child, nltk.tree.Tree): 
                   childstrs.append(child._pprint_flat(nodesep, parens, quotes)) 
               elif isinstance(child, tuple): 
                   childstrs.append("/".join(child)) 
               elif isinstance(child, basestring) and not quotes: 
                   childstrs.append('%s' % child) 
               else: 
                   childstrs.append('%r' % child) 
           if isinstance(self, PhraseDependencyTree):  
               return '%s%s/%s%s %s%s' % (parens[0], self.tag(), self.dep(), nodesep,
                                       string.join(childstrs), parens[1]) 
           elif isinstance(self.label(), basestring): 
               return '%s%s%s %s%s' % (parens[0], self.label(), nodesep,  
                                       string.join(childstrs), parens[1]) 
           else: 
               return '%s%r%s %s%s' % (parens[0], self.label(), nodesep,  
                                       string.join(childstrs), parens[1]) 
    
 
 
class PhraseTreeError(TypeError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return "%s is not a PhraseDependencyTree" % self.value
        
