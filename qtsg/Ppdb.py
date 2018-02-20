'''
Created on 7 Mar 2014

PPDB reading and loading as QTSG rules

@author: kwoodsen
'''

import os
import numpy as np

import txt2txtgen.config.Config as Config

from SyncTreeGrammar import SyncGrammarTree, SyncGrammarRule
from align import SubTreeInfo
import txt2txtgen.parse.PhraseDependencyTree


PPDB_DIR = Config.PPDB_DIR

def read_PPDB(size='s'):
    fn = os.path.join(PPDB_DIR, 'ppdb-1.0-%s-noccg'%size)
    assert os.path.exists(fn), "Cannot find PPDB file %s"%fn
    
    ruleset = [_read_PPDB_rule(l) for l in open(fn)]
    ruleset = [r for r in ruleset if r is not None]
    # print len(ruleset), " rules read in from ", fn
    return ruleset



def _read_PPDB_rule(line):
    # format of PPDB line: parent node, left, right, features, alignment
    parent, l, r, _features, word_alignment = line.split('|||')
    try:
        l.decode('ascii')
        r.decode('ascii')
        # print parent, "\t", l, "\t", r 
    except UnicodeDecodeError:
        # rule contains some unicode characters
        return None
    
    # check parent is in form [TAG]
    parent = parent.strip()
    assert parent[0]=='[', "Unexpected parent tag %s" % parent
    assert parent[-1]==']', "Unexpected parent tag %s" % parent
    parent_tag = parent[1:-1]
    
    lhs = [_process_production_element(s) for s in l.split()]
    rhs = [_process_production_element(s) for s in r.split()]
    word_aligns = [_process_word_align(s) for s in word_alignment.split()]
    
    # tidy up S rules with final punctuation
    if parent_tag=='S' and lhs[-1][1]=='.' and rhs[-1][1]=='.':
        parent_tag = 'ST'

    r = PpdbRule(parent_tag, lhs, rhs, word_aligns)
    # print "rule: \t", r
    return r
    
    

def _process_production_element(s):
    """
    Each element in the PPDB production is either a 
    non-terminal in the form [node,alignment]
    or it is a terminal word with no tag information.
    @return: (tag, word, alignment)
    """
    if s[0]=='[':
        assert s[-1]==']', "problem with PPDB element %s"%s
        s_no_brackets = s[1:-1]
        s_tag, s_align_str = s_no_brackets.split(',')
        s_align = int(s_align_str)
        return (s_tag, None, s_align)
    else:
        return (None, s, None)

def _process_word_align(s):
    """ split m-n into integers m and n
    @return: (m,n)
    """
    m, n = s.split('-')
    return (int(m), int(n))


class PpdbRule(SyncGrammarRule):
    """
    A rule relates a source SyncGrammarTree to a target SyncGrammarTree.
    This subclass handles lists of (POS-tag,word) substitutions
    rather than nodes in a phrase tree
    """
    pass    


    def __init__(self, parent_tag, source, target, word_aligns, probability=1):
        self._parent = parent_tag
        self._source = self._make_tree(parent_tag, source)
        self._target = self._make_tree(parent_tag, target)
        self._count = probability
        self._rule_id = None
        self._makeLinksSequential()
        self._process_word_aligns(word_aligns)


    def _make_tree(self, parent_tag, children):
        t = PpdbSyncGrammarTree(parent_tag, children)
        return t

    def _process_word_aligns(self, word_aligns):
        seq = [(i,(i,j)) for i,j in word_aligns]
        word_aligns_no_repeats = f7(seq)
        seq = [(j,(i,j)) for i,j in word_aligns_no_repeats]
        word_aligns_no_repeats = f7(seq)
        if False:
            print self._source
            print self._target
            print word_aligns
            print word_aligns_no_repeats

        for w in word_aligns_no_repeats:
            s = self._source.children()[w[0]]
            s.set_word_alignment(w[1])
            t = self._target.children()[w[1]]
            t.set_word_alignment(w[0])
            
            
    def isSuitable( self, srcTree, targetTreeNode):
        """
        Returns True if this rule is suitable for 
        applying to the phrase tree.
        This differs, in checking only that the tags match.
        Sentence creation is only possible with no targetTreeNode.
        """
        # print "Working with rule: ", self.rule_id()
        if not self._source.matches(srcTree): return False
        if self._target.tag()=="ST" and not targetTreeNode: return True # allow new sentence to be created
        if _node_matches(targetTreeNode.tag(), self._target.tag()): return True
        return False

    def isSuitableSomewhere(self, src_subtree_info):
        """ Check if this rule could be applied at some node in srcTree.
        Only rough check for speed - guaranteed only for False
        """
        assert isinstance(src_subtree_info, SubTreeInfo), "expecting SubTreeInfo object"
        
        # first stage: check that all text in this rule is somewhere in the tree
        leaves = src_subtree_info.leaves()
        missing_text = [ch._text for ch in self._source.children() \
                        if (isinstance(ch, PpdbSyncGrammarTreeText) and not ch._text in leaves) ]
        if len(missing_text)>0: 
            return False # some text in this rule does not feature in the sentence
        
        # second stage: match nodes as well as text 
        possible_matches = self._source._link_children_to_tree_nodes(src_subtree_info)
        possible_explanation = self._source._possible_explanation(possible_matches)
        return possible_explanation
        


def _node_matches(parse_tag, ppdb_tag):
    """
    Match tags between Stanford parse and PPDB
    """
    # print "Match? \t", parse_tag, ppdb_tag
    if parse_tag=="ST" and ppdb_tag.startswith('S'): return True # don't worry about final full stop
    if parse_tag.startswith(ppdb_tag): return True # mainly verbs: ignore verb info added to tag
    
    return parse_tag == ppdb_tag


class PpdbSyncGrammarTree(SyncGrammarTree):
    
    def __init__(self, node, children):
        super(PpdbSyncGrammarTree,self).__init__(node, None) # no dependency information
        for (tag, text, link) in children:
            if tag is not None: # child node
                assert link is not None, "node is not linked"
                ch = PpdbSyncGrammarTreeNode(tag, link)
                self._children.append(ch)
            else: # child text node
                assert text is not None, "no tag or text"
                ch = PpdbSyncGrammarTreeText(text)
                self._children.append(ch)


    def matches(self, phraseTree, use_dep_info=True):
        """
        Returns True if the phraseTree node has the same syntactical nodes as this tree.
        This Ppdb version is more complicated than other SyncGrammarTrees,
        because the nodes in the rule are provided in a flat structure,
        and we need to search for them in the phrase tree.
        """
        if not isinstance(phraseTree, txt2txtgen.parse.PhraseDependencyTree.PhraseDependencyTree): return False
        if not _node_matches(phraseTree.tag(), self.tag()): return False
        assert self.hasChildren(), "PPDB rule does not have any children"

        phrase_tree_info = SubTreeInfo(phraseTree)
        possible_matches = self._link_children_to_tree_nodes(phrase_tree_info)
        possible_explanation = self._possible_explanation(possible_matches)
        if not possible_explanation:
            return False
        
        # also need to check order
        try:
            _link_path = self._find_links_to_tree(phrase_tree_info, possible_matches)
            return True # link path valid
        except PpdbSyncGrammarTree.NoPathException:
            return False

                
    def _find_links_to_tree(self, phrase_tree_info, possible_matches):
        """
        Link the nodes in the rule to the phrase tree, as 
        the PPDB rules flatten the tree and lose the structure
        @return: boolean flags to indicate if phrase trees have been matched, 
                 links to nodes of the phraseTree
        """
        possible_explanation = self._possible_explanation(possible_matches)
        assert possible_explanation, "phrase tree does not match this PPDB rule at all"

        # find match for first child
        link_path = self._link_path(0, 0, phrase_tree_info, possible_matches)
        if len(link_path) < len(self.children()):
            # rule has not been fully linked
            raise PpdbSyncGrammarTree.NoPathException
        return link_path


    
    class NoPathException(Exception): 
        pass
    
    class EndOfTreeException(Exception): 
        pass


    def _link_children_to_tree_nodes(self, phrase_tree_info):
        """ @return Matrix of possible links between rule children and phrase nodes, ignoring order """
        matches = np.matrix([[ch.matches(ph) for ph in phrase_tree_info.subtrees()] for ch in self.children()], dtype=bool)
        return matches

    def _possible_explanation(self, possible_matches_matrix):
        """
        @return: True if all the children in this rule match something in the source tree 
        """
        possible_explanation = np.all(np.any(possible_matches_matrix, axis=1)) # if any row does not contain True, then rule has not been explained
        return possible_explanation
    
    def _find_matches_for_child_node(self, i, j, phrase_tree_info, possible_matches_matrix):
        """
        Find a node j or left-most descendant of j that matches child i of this rule
        """
        possible_matches = []
        if possible_matches_matrix[i,j]:
            possible_matches.append(j)
            
        # consider if left-most child also could match
        if len(phrase_tree_info.children(j))>0:
            leftmost_child = phrase_tree_info.children(j)[0]
            possible_matches.extend(self._find_matches_for_child_node(i, leftmost_child, phrase_tree_info, possible_matches_matrix))
        # print "possible matches for subtree ",j, "\t: ", possible_matches
        return possible_matches
    
    def _node_to_right(self, j, phrase_tree_info):
        """ @return node in the phrase tree to the right of j """
        parent = phrase_tree_info.parent(j)
        if parent is None:
            raise PpdbSyncGrammarTree.EndOfTreeException
        siblings = phrase_tree_info.children(parent)
        current_index = siblings.index(j)
        if current_index + 1 < len(siblings):
            return siblings[current_index + 1] # sibling to right
        else:
            # find sibling of parent
            return self._node_to_right(parent, phrase_tree_info)
        
        
    def _link_path(self, i, j, phrase_tree_info, possible_matches_matrix):
        try:
            possible_matches = self._find_matches_for_child_node(i, j, phrase_tree_info, possible_matches_matrix)
        except IndexError:
            # no i elements left in rule
            raise PpdbSyncGrammarTree.NoPathException
        
        # print "Considering ", i, j, len(possible_matches)
        if len(possible_matches) == 0:
            raise PpdbSyncGrammarTree.NoPathException
        for j_ch in possible_matches:
            try:
                node_to_right = self._node_to_right(j_ch, phrase_tree_info)
                # print node_to_right, " to the right of ", j_ch, "\t", phrase_tree_info.subtree(j_ch), " ... ", phrase_tree_info.subtree(node_to_right)
                path_from_here = self._link_path(i+1, node_to_right, phrase_tree_info, possible_matches_matrix)
                path_from_here.insert(0, (i,j_ch))
                # print i, j, "path from here: ", path_from_here
                return path_from_here

            except PpdbSyncGrammarTree.NoPathException:
                # no complete path with this possible_match
                # print "no complete path using ", j_ch, " at ", i, j
                # try the next possible match j_ch
                continue
                # raise NotImplementedError, "not sure what we need to do with this condition"
            
            except PpdbSyncGrammarTree.EndOfTreeException:
                # reached the end of the parse tree
                # did we use all the rule children?
                # print "Reached end of tree at rule child ", i
                if i < len(self.children())-1:
                    # no, did not describe all the rule terms
                    # try another possible match
                    continue # next j_ch

                else: # complete match     
                    path_from_here = [(i,j_ch)]
                    return path_from_here
                    
            
            # TODO: handle more than one match
            # TODO: do something when i reaches the end of the rule
            
        raise PpdbSyncGrammarTree.NoPathException # not sure about this
            
        
        
    def _link_to_tree_old(self, phraseTree):
        """
        Link the nodes in the rule to the phrase tree, as 
        the PPDB rules flatten the tree and lose the structure
        @return: boolean flags to indicate if phrase trees have been matched, 
                 links to nodes of the phraseTree
        """
        raise DeprecationWarning, "should not be using this"
        # need to see if phrase tree matches rule at any level
        phrase_tree_info = SubTreeInfo(phraseTree)
        phrase_tree_matches = [False for i in range(phrase_tree_info.count())] # store matched subtrees here
        nodes_to_phrase_tree = []
        
        print "descendents: ", phrase_tree_info._descendentIndices
        for i,ph in phrase_tree_info.indxd_trees(reverse=True):
            print i, ph
        raise NotImplementedError
    
        # does the next child in this rule match the next unmatched subtree?
        ph_current_frontier = -1
        for ch in self.children():
            this_child_matched = False # each child in the rule needs to match somewhere
            for i, ph in enumerate(phrase_tree_info.subtrees()):
                if i <= ph_current_frontier: continue # we have already passed here
                if phrase_tree_matches[i]: continue # already matched
                # print ch.matches(ph), "Checking match: ", ch, " - ", ph
                if ch.matches(ph):
                    this_child_matched = True
                    ph_current_frontier = i
                    phrase_tree_matches[i] = True
                    nodes_to_phrase_tree.append((ch,ph))
                    break
            if not this_child_matched: 
                # failed to match this child
                phrase_tree_matches[0] = False
                break # exit here with less than full match
            
            # print "child", ch, " matched"
            
            # now propagate match to parent nodes
            # print "phrase_tree_matches: ", phrase_tree_matches
            for i, ph in phrase_tree_info.indxd_trees(reverse=True):
                descendents = phrase_tree_info.children(i) # direct descendents only
                if len(descendents) == 0: continue # no descendents to check
                matched_descendents = [j for j in descendents if phrase_tree_matches[j]]
                if len(descendents) == len(matched_descendents):
                    # all the descendents of this node have been matched, so mark this one as well
                    phrase_tree_matches[i] = True
        
        # all children of this rule have been matched
        # has all the phrase tree been matched? Check top node
        return phrase_tree_matches, nodes_to_phrase_tree
         

    def findLink(self, linknum, phraseTree):
        """
        Find a link in the tree with the number linknum,
        and return its position as a list of positions.
        Will raise LookupError if no link found
        @var phraseTree: the tree structure of the actual phrase, 
        useful if this type of sync grammar tree does not capture the phrase tree structure exactly
        """
        if linknum is None:
            raise LookupError, "Source phrase not linked"
        if isinstance(linknum, list): 
            if linknum is None: raise LookupError, "Src phrase has no link set"
            assert len(linknum)==1, "Looking up more than one link: %s" % str(linknum)
            linknum = linknum[0] 
        assert self._linknum is None, "Links should not be at top level of PPDB rule"

        # find link in children
        linked_children = [(i, ch) for i, ch in enumerate(self.children()) if linknum in ch.links()]
        assert len(linked_children)==1, "More than one link to child"
        linked_child_num, linked_child = linked_children[0]
        
        # now find this linked_child in the phrase tree
        phrase_tree_info = SubTreeInfo(phraseTree)
        possible_matches = self._link_children_to_tree_nodes(phrase_tree_info)
        assert self._possible_explanation(possible_matches), "no possible explanation of this phrase tree"

        # get set of links        
        try:
            link_path = self._find_links_to_tree(phrase_tree_info, possible_matches)
            # print "child ", linked_child_num, " links to phrase ", link_path[linked_child_num][1]
            phrase_tree_index = link_path[linked_child_num][1]
            phrase_tree_node = phrase_tree_info.subtree(phrase_tree_index)
            # print linked_child, " represented by ", phrase_tree_node, " \tat ", phrase_tree_node.treeposition() 
            position =  phrase_tree_node.treeposition()[len(phraseTree.treeposition()):] # tree position relative to phraseTree
            return position # link path valid
        except PpdbSyncGrammarTree.NoPathException:
            assert False, "could not find a linked child in the link path"

                
        
class PpdbSyncGrammarTreeNode(SyncGrammarTree):
    def __init__(self, tag, link):
        super(PpdbSyncGrammarTreeNode,self).__init__(tag, None, [link]) # no dependency information

    def matches(self, phraseTree, use_dep_info=True):
        """ 
        Matches only node tag.
        """
        return _node_matches(phraseTree.tag(), self.tag())

    def set_word_alignment(self, position):
        """ No need to do anything as there should already be a link between source and target nodes """
        assert self.isLinked(), "Unlinked PPDBSyncGrammarTree"
        pass
    
    

class PpdbSyncGrammarTreeText(SyncGrammarTree):
    def __init__(self, text):
        super(PpdbSyncGrammarTreeText,self).__init__(None, None) # no tag or dependency information
        self._text = text 
        self._link = None
        
        
    def matches(self, phraseTree, use_dep_info=True):
        """ 
        Matches only text of leaf node.
        Ignores tag and dep info.
        """
        assert self.text(), "This PPDB text node does not have text"
        if not phraseTree.isLeaf(): return False
        return self.text()==phraseTree[0]
                
    def set_word_alignment(self, position):
        """ Stores the word alignment position information """
        # only the first time
        assert self._link is None, "this word alignment already set up"
        self._link = position
    
    def word_alignment(self):
        return self._link

def f7(seq):
    seen = set()
    return [ v for k,v in seq if k not in seen and not seen.add(k)]
            
