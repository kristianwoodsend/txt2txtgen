'''
Alignment methods for nodes in trees

Created on 19 Sep 2013

@author: kristian
'''
import numpy as np

from .QGDefs import MATCH_STOP_TAGS, VERB_PHRASE_FROM_NOUN_PHRASE_TAGS
import QGCore
from txt2txtgen.parse.StanfordCoreNLP import DocInfo

PRINT_DEBUG_ALIGNMENTS = False




def align_nodes_multisentence_corefs(src_info, tgt_info, linenums=None):
    """
    Align nodes across multiple src and tgt sentences.
    Uses any coreference information as further alignments
    Return a list of aligned nodes
    """
    assert isinstance(src_info, DocInfo), "Expecting DocInfo object"
    assert isinstance(tgt_info, DocInfo), "Expecting DocInfo object"

    coref_src_node_sets = [[corefNode(src_info, m) for m in c.mentions()] for c in src_info.corefs()]
    coref_tgt_node_sets = [[corefNode(tgt_info, m) for m in c.mentions()] for c in tgt_info.corefs()]

    matchlist = []
    if linenums is None: 
        # try all combinations
        linenums = [(i,j) for i in range(src_info.sentenceCount()) for j in range(tgt_info.sentenceCount())]
        
    for (i, j) in linenums:
        s = src_info.sentence(i)
        t = tgt_info.sentence(j)
        ml = align_nodes_coreferencing(s, t, matchlist, coref_src_node_sets, coref_tgt_node_sets)
        matchlist.extend(ml)
    return matchlist
            

def align_nodes_multisentence_no_corefs(src_info, tgt_info, linenums=None):
    """
    Align nodes across multiple src and tgt sentences.
    Uses no coreference information
    Return a list of aligned nodes
    """
    assert isinstance(src_info, DocInfo), "Expecting DocInfo object"
    assert isinstance(tgt_info, DocInfo), "Expecting DocInfo object"

    if linenums is None: 
        # try all combinations
        linenums = [(i,j) for i in range(src_info.sentenceCount()) for j in range(tgt_info.sentenceCount())]
        
    matchlist = []
    
    for (i, j) in linenums:
        s = src_info.sentence(i)
        t = tgt_info.sentence(j)
        ml = align_nodes(s, t)
        matchlist.extend(ml)

    return matchlist
            


def align_nodes_multisentence_no_corefs_with_linenumbering(src_info, tgt_info, linenums):
    """
    Align nodes across multiple src and tgt sentences.
    Uses any coreference information as further alignments
    Return a list of aligned nodes
    """
    assert isinstance(src_info, DocInfo), "Expecting DocInfo object"
    assert isinstance(tgt_info, DocInfo), "Expecting DocInfo object"

    matchlist = []
    for (i, j) in linenums:
        s = src_info.sentence(i)
        t = tgt_info.sentence(j)
        ml = align_nodes(s, t)
        matchlist.extend(ml)
    return matchlist
            

def align_nodes_coreferencing(src_sentence, tgt_sentence, current_matchlist, coref_src_node_sets, coref_tgt_node_sets):
    """
    Align nodes in the trees src and tgt.
    Return a list of aligned nodes
    """
    # build up list of all subtrees
    src = SubTreeInfo(src_sentence.parseTree())
    tgt = SubTreeInfo(tgt_sentence.parseTree())
    _print_node_info(src, tgt)
    
    # identify target nodes that need explaining
    needExplaining = [ nodeHasContent(tt) for tt in tgt.subtrees()] 
                        
    # find src nodes that explain target nodes
    explains = _aligned_lemmas_matrix(src, tgt)
    
    # add to explains matrix with coreference set information
    coreferenced_nodes = _align_coreferences(explains, needExplaining, src, tgt, current_matchlist, coref_src_node_sets, coref_tgt_node_sets)

    tgt_partially_explained = _partial_explanations_list(src, tgt, explains, needExplaining)
    
    return _gridAlignMatchList(src, tgt, explains, tgt_partially_explained, needExplaining, coreferenced_nodes)


def align_nodes(src_sentence, tgt_sentence):
    """
    Align nodes in the trees src and tgt.
    Return a list of aligned nodes
    """
    # build up list of all subtrees
    src = SubTreeInfo(src_sentence.parseTree())
    tgt = SubTreeInfo(tgt_sentence.parseTree())

    # identify target nodes that need explaining
    needExplaining = [ nodeHasContent(tt) for tt in tgt.subtrees()] 
                        
    _print_node_info(src, tgt)
   
    # find src nodes that explain target nodes
    explains = _aligned_lemmas_matrix(src, tgt)
    tgt_partially_explained = _partial_explanations_list(src, tgt, explains, needExplaining)
    if PRINT_DEBUG_ALIGNMENTS:
        print "Target partially explained:", tgt_partially_explained

    coreferenced_nodes = [False] * tgt.count() # no coref info in this method
    return _gridAlignMatchList(src, tgt, explains, tgt_partially_explained, needExplaining, coreferenced_nodes)


def _print_node_info(src, tgt):
    if PRINT_DEBUG_ALIGNMENTS: # print out info
        print "Source nodes: "
        for i in src.indices():
            st = src.subtree(i)
            print i, "\t", st.treeposition(), st.tag(), st.dep(), "\t", QGCore.nodeText(st)
        print "\nTarget nodes, flag for content: "
        for i in tgt.indices():
            tt = tgt.subtree(i)
            print i, "\t", nodeHasContent(tt), "\t", tt.treeposition(), tt.tag(), tt.dep(), "\t", QGCore.nodeText(tt)

    

def _aligned_lemmas_matrix(src, tgt):
    """
    Align nodes in the trees src and tgt based on content information.
    Return matrix of alignments
    """
    # find src nodes that explain target nodes
    explains = np.matrix([[leafLemmaMatches(st, tt) for tt in tgt.subtrees()] for st in src.subtrees()])
    if PRINT_DEBUG_ALIGNMENTS:
        print "Alignments after initial lemma matching:"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        
    return explains

def _partial_explanations_list(src, tgt, explains, needExplaining):
    """
    Marks target nodes as partially explained if anywhere in the subtree is explained by a source node
    """
    # find src nodes that explain target nodes
    partially_explains = explains.copy()
    
    for j, tt in tgt.indxd_trees():
        # explore whole of target subtree
        for i, st in src.indxd_trees():
            for j_ch in tgt.descendents(j):
                if needExplaining[j_ch] and explains[i, j_ch]:
                     partially_explains[i,j] = True
                     # print j, "explained by ", i, "because of child ", j_ch
            
    if PRINT_DEBUG_ALIGNMENTS:
        print "Partial explanations:"
        # print explains
        printAlignmentInfo(src, tgt, partially_explains)

    is_partially_explained = partially_explains.any(axis=0).getA().flatten()
    assert len(is_partially_explained)==tgt.count(), "lost some target nodes"
    return is_partially_explained




def _align_coreferences(explains, needExplaining, src, tgt, current_matchlist, coref_src_node_sets, coref_tgt_node_sets):
    """
    Align nodes based on coreference information, adding to the existing explains matrix
    """
    # make a note of coreferenced nodes
    coreferenced_nodes = [False] * tgt.count()
    
    # try to find which corefs are relevant here
    for j, tt in tgt.indxd_trees():
        corefed_tt = [tt2 for corefset in coref_tgt_node_sets for tt2 in corefset if tt in corefset]
        
        if PRINT_DEBUG_ALIGNMENTS:
            print j, " links to tt", QGCore.nodeText(tt), "---", len(corefed_tt)
            for tt3 in corefed_tt:
                if tt3 is not None:     
                    print "tt linked node", QGCore.nodeText(tt3)
        
        # find src nodes that are already matched to these tgt nodes
        linked_st = [st2 for (st2, tt2) in current_matchlist if tt2 in corefed_tt]
        # add direct and dependent children of linked_st
        linked_st_children = [st2 for st in linked_st for st2 in st if not st.isLeaf() and st2.isFixed()]
        linked_st.extend(linked_st_children)
        
        if PRINT_DEBUG_ALIGNMENTS:
            if len(linked_st) > 0:
                pass # debug here
            print "src links:", len(linked_st)
            print "children of src links:", len(linked_st_children)
            for st3 in linked_st: print st3.treeposition(), QGCore.nodeText(st3)
            for st2 in linked_st:
                for srcset in coref_src_node_sets:
                    if st2 in srcset:
                        print srcset
            _coref_src_sets_temp = [srcset for srcset in coref_src_node_sets for st2 in linked_st if st2 in srcset]

        corefed_st = [st3 
                      for corefset in coref_src_node_sets 
                      for st3 in corefset 
                      for st2 in linked_st 
                      if st2 in corefset]
        if PRINT_DEBUG_ALIGNMENTS:
            print "src corefed links:", len(corefed_st)
            for st3 in corefed_st: print st3.treeposition(), QGCore.nodeText(st3)
        
        # even if no src-side coreferences, still add in single linked source node
        if len(corefed_st)==0:
            corefed_st.extend(linked_st) 
    
        if PRINT_DEBUG_ALIGNMENTS:
            print "src corefed links including single linked nodes:", len(corefed_st)
            for st3 in corefed_st: print st3.treeposition(), QGCore.nodeText(st3)
        
        # change the explain matrix
        for i, st in src.indxd_trees():
            if st in corefed_st:
                explains[i,j] = True
                # needExplaining[j] = True # make this node need explaining, even if it is a pronoun
                coreferenced_nodes[j] = True
    return coreferenced_nodes


# alignment functions
def _gridAlignMatchList(src, tgt, explains, tgt_partially_explained, needExplaining, coreferenced_nodes):
    """
    This method of alignment is based on matrix.
    For nodes to align, the source node must "explain" the target node
    but not its parent.
    
    This method aligns based on lexical (lemma) identity of content words
    
    @todo Increase tolerance so that substitution is possible.
    """
    
    # We are only concerned with explaining non-terminal nodes
    # Leave the leaves alone
    # They are already linked using lemmas, although the linking is important for higher nodes
    
    # find src nodes that explain tgt node
    _linkExplanations(src, tgt, explains, tgt_partially_explained, needExplaining)
    
    # _shrink_explanation_boxes(src, tgt, explains)
    # remove any explanations not listed in needExplaining
    # which use out-of-subtree links
    # _remove_spurious_explanations_not_needed(src, tgt, explains, needExplaining)
    
    # clean out explanations so that only compatible tags align
    # but don't worry about leaves - these are based on lexical identity
    # we are trying to match non-terminal nodes
    _remove_incompatible_tags(src, tgt, explains)

    _remove_unnecessarily_high_explanations(src, tgt, explains)
    
    # remove explanations when a source child node adequately explains this target node
    # relying on removing non-matching tags beforehand
    _remove_too_high_source_nodes(src, tgt, explains)
    
    # not doing careful VP alignment any more, as we have split VP types
    
    # VPs are often single-child, or single child plus non-content function word, 
    # so more careful alignment is necessary
    # _top_vp_alignment(src, tgt, explains)
    #_remove_function_word_vp_alignments(src, tgt, explains, needExplaining)
    
    # remove explanation if it falls outside sync trees
    # we must not remove incompatible tags before this, as 
    # we need a fully-connected tree
    # _remove_too_wide_target_nodes(src, tgt, explains)

    # might leave this for QTSG rules to do
    # _prefer_simpler_for_target(src, tgt, explains)
    
    alignments = explains
        
    if PRINT_DEBUG_ALIGNMENTS:
        print "\nAligned phrases"        
        printAlignmentInfo(src, tgt, alignments)

    # return list of matching nodes, rather than alignment matrix
    matchList = [(st,tt) \
                 for i, st in src.indxd_trees()
                 for j, tt in tgt.indxd_trees()
                 if alignments[i,j] ]
        
    return matchList



def _linkExplanations(src, tgt, explains, tgt_partially_explained, needExplaining):
    """
    Change the explains matrix to link parents that explain target parent nodes
    """
    if PRINT_DEBUG_ALIGNMENTS:
        print "Before linking explanations:"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        print
        
    stillChanging = True
    while (stillChanging):
        stillChanging = False
        for j, tt in tgt.indxd_trees(reverse=True):
            if not needExplaining[j]: 
                continue
            
            for i, st in src.indxd_trees(reverse=True):
                if explains[i,j]: continue

                # do any of the children of the source node explain the target node,
                # if so, then the whole src node explains the target node                    
                r = srcChildExplainsTarget(i, j, src, explains)
                if r:
                    # print i, "explains ", j
                    explains[i,j] = True
                    stillChanging = True
                    
                # for nodes that are currently unexplained,
                # does this source node explain all tgt children?
                # if all the target children can be explained, then the whole target is explained
                r = srcExplainsAllTargetChildren(i, j, tgt, explains, tgt_partially_explained, needExplaining)
                if r:
                    # print i, "explains children of", j
                    explains[i,j] = True
                    stillChanging = True
    
                    
    if PRINT_DEBUG_ALIGNMENTS:
        print "After linking explanations:"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        print
    
    
def _get_rightmost_child(info):
    right_child = 0
    try:
        while True:
            right_child = info.children(right_child)[-1]
    except IndexError:
        pass # run out of children
    return right_child


def _remove_spurious_explanations_not_needed(src, tgt, explains, needExplaining):
    # handle full-stop at end in a special way,
    # as we are allowing STs in target to link at any place in src
    src_right_child = _get_rightmost_child(src)
    tgt_right_child = _get_rightmost_child(tgt)
    aligned_full_stops = explains[src_right_child, tgt_right_child]
        
    for (i, st, j, tt) in aligned_nodes(src, tgt, explains): # breadth-first, working down
        if st.isLeaf() or tt.isLeaf(): 
            continue # no descendents
        j_children_with_content = [jj for jj in tgt.children(j) if needExplaining[jj]]
        if PRINT_DEBUG_ALIGNMENTS:
            print "Target ", j, "has children needing explaining: ", j_children_with_content
        if len(j_children_with_content) < 2: 
            continue

        if False:
            # try all descendents
            j_descendents = tgt.descendents(j)
        else:
            # try only descendents of linked children
            j_descendents = []
            j_descendents.extend(tgt.children(j))
            for jj in j_children_with_content:
                j_descendents.extend(tgt.descendents(jj))
                                     
        j_desc_no_exp_needed = [jj for jj in j_descendents if not needExplaining[jj]]
        
        i_links = [ii for ii in src.indices() for jj in j_desc_no_exp_needed if explains[ii,jj]]
        i_links_set = set(i_links)
        spurious_i_links = i_links_set - src.descendents(i)
        
        if PRINT_DEBUG_ALIGNMENTS:
            print "@", i, j, "links:", i_links, "\tv\t", src.descendents(i), "\t=", i_links_set - src.descendents(i) 
            
        for ii in spurious_i_links:
            for jj in j_desc_no_exp_needed:
                # special case for final fullstop
                if aligned_full_stops and ii==src_right_child and jj==tgt_right_child:
                    continue # don't un-align full stop
                if explains[ii, jj]:
                    explains[ii, jj] = False
                    if PRINT_DEBUG_ALIGNMENTS:
                        print "Spurious explanation %d -- %d" % (ii, jj), "\t", QGCore.nodeText(src.subtree(ii)), " -- ", QGCore.nodeText(tgt.subtree(jj))
                        print i, j, j_desc_no_exp_needed
                        print i_links, "\tv\t", src.descendents(i), "\t=", i_links_set - src.descendents(i) 
                        print "src parent info: ", src.parent(i), src.parent(ii)
                        print "tgt parent info: ", tgt.parent(j), tgt.parent(jj)



def _shrink_explanation_boxes(src, tgt, explains):
    """
    Experimenting with how to align
    
    Here: work through all alignments top down.
    Remove any explanations that are outside of descendents
    """
    all_src_indices = set(src.indices())
    all_tgt_indices = set(tgt.indices())
    for (i, st, j, tt) in aligned_nodes(src, tgt, explains): # breadth-first, working down
        src_not_descendents = all_src_indices - src.descendents(i) - set([i])
        tgt_not_descendents = all_tgt_indices - tgt.descendents(j) - set([j])
        print "From src ", i, " not descendents: ", src_not_descendents
        print "From tgt ", j, " not descendents: ", tgt_not_descendents
        
        
    raise NotImplementedError, "how to shrink the tree down?"
    
    
def _top_vp_alignment(src, tgt, explains):
    """
    Alignment of VPs needs to be more careful, as the 
    only differences between child and parent are
    addition of function words.
    Try only aligning top VP, or where new dependency label indicates new clause
    """
    for (i, st, j, tt) in aligned_nodes(src, tgt, explains): # breadth-first, working down
        if not _is_VP(i, src): continue 
        if not _is_VP(j, tgt): continue 
        
        # new VP tree, or left-most node
        src_node_OK = _is_linkable_VP(i, src)
        
        # new VP tree, or left-most node, or new predicate
        tgt_node_OK = _is_linkable_VP(j, tgt)
            
        if PRINT_DEBUG_ALIGNMENTS:
            print "In top VP alignment"
            print "Src: ", src_node_OK, st.tag(), st.dep(), src.subtree(src.parent(i)).tag(), QGCore.nodeText(st)
            print "Tgt: ", tgt_node_OK, tt.tag(), tt.dep(), tgt.subtree(tgt.parent(j)).tag(), QGCore.nodeText(tt)
            
        if not (src_node_OK and tgt_node_OK):
            explains[i,j]=False
            if PRINT_DEBUG_ALIGNMENTS:
                print "Removing lower VP link (%d,%d) \t%s -- %s" % (i, j, QGCore.nodeText(st), QGCore.nodeText(tt))



def _remove_function_word_vp_alignments(src, tgt, explains, needExplaining):
    """
    Alignment of VPs needs to be more careful, in the case where the 
    only differences between child and parent are
    addition of function words.
    Stop alignment where target VP has added function word compared to already-explained child
    """
    for (i, st, j, tt) in aligned_nodes(src, tgt, explains): # breadth-first, working down
        if not _is_VP(i, src): continue 
        if not _is_VP(j, tgt): continue 
    
        tgt_child_explanations = [j_ch for j_ch in tgt.children(j) if explains[i, j_ch]]
        tgt_child_needing_explanations = [j_ch for j_ch in tgt.children(j) if needExplaining[j_ch]]
        if tgt_child_explanations==tgt_child_needing_explanations:
            # everything that needs explaining in tgt, the src explains further down 
            explains[i,j]=False
            if PRINT_DEBUG_ALIGNMENTS:
                print i, j, "Explains tgts: ", tgt_child_explanations, "\t and needs explaining:", tgt_child_needing_explanations, tgt_child_explanations==tgt_child_needing_explanations
        pass
    
        src_child_explanations = [i_ch for i_ch in src.children(i) if explains[i_ch, j]]
        src_child_needing_explanations = [i_ch for i_ch in src.children(i) if src.subtree(i_ch).has_content()]
        if src_child_explanations==src_child_needing_explanations:
            # everything that src explains is explained by one of its children, and it is adding only function words 
            # which should be handled by an alignment further up 
            explains[i,j]=False
            if PRINT_DEBUG_ALIGNMENTS:
                print i, j, "Explains srcs: ", src_child_explanations, "\t and containing content:", src_child_needing_explanations, src_child_explanations==src_child_needing_explanations
        

        
def _is_VP(i, info):
    return info.subtree(i).tag().startswith("VP")

def _is_linkable_VP(i, info):
    assert _is_VP(i, info), "Not a VP"
    
    if info.subtree(i).dep() == "partmod": 
        # don't trust partmod anywhere
        return False
    
    if _is_VP(info.parent(i), info)==False: 
        return True # this is a top-level VP
    
    if info.subtree(i).token_range()[0] == info.subtree(info.parent(i)).token_range()[0]:
        # left-most element is OK
        return True
    
    
    siblings = info.children(info.parent(i))
    sibling_VPs = [j for j in siblings if _is_VP(j, info)]
    if len(sibling_VPs) > 1 and i!=sibling_VPs[0]:
        # not the first VP, so we can link
        return True
    
    return False


def _remove_incompatible_tags(src, tgt, explains):
    if False and PRINT_DEBUG_ALIGNMENTS:
        print "compatible tags?"
    for (i, st, j, tt) in aligned_nodes(src, tgt, explains):
        # are tags compatible
        if False and PRINT_DEBUG_ALIGNMENTS:
                    print st.tag(), tt.tag(), topLevelConstituentMatch(st, tt)
        explains[i,j] = topLevelConstituentMatch(st, tt)
    if PRINT_DEBUG_ALIGNMENTS:
        print "Explanations after compatibility checks"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        print
    
    
def _remove_unnecessarily_high_explanations(src, tgt, explains):
    """ Remove an explanation if a child of src node explains the tgt node
        and this src node also explains the parent of tgt
    """
    stillChanging = True
    while (stillChanging):
        stillChanging = False
        for (i, st, j, tt) in aligned_nodes(src, tgt, explains):
            # does a src child also explain this tgt?
            src_child_explanations = [i_ch for i_ch in src.descendents(i) if explains[i_ch, j]]
            # does src also explain a parent of tgt?
            tgt_parent_explanations = [j_parent for j_parent in tgt.ancestors(j) if explains[i, j_parent]]
            
            if len(src_child_explanations)>0 and len(tgt_parent_explanations)>0:
                if PRINT_DEBUG_ALIGNMENTS:
                    print "Unnecessary explanation %d -- %d" % (i, j), "\t", QGCore.nodeText(st), " -- ", QGCore.nodeText(tt)
                explains[i, j] = False
                stillChanging = True
                
    if PRINT_DEBUG_ALIGNMENTS:
        print "Explanations after removing unnecessarily high explanations"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        print

            
            

def _remove_too_high_source_nodes(src, tgt, explains):
    stillChanging = True
    while (stillChanging):
        stillChanging = False
        for i, st in src.indxd_trees(reverse=True):
            
            tgts_explained_by_i = [j for j in tgt.indices() if explains[i,j]]
            tgts_explained_by_i_children = [j for j in tgt.indices()
                                            for i_ch in src.descendents(i)
                                            if explains[i_ch,j]]

            # are any of the targets in tgts_explained_by_i
            # lower than any of the targets in  tgts_explained_by_i_children
            for j in tgts_explained_by_i:
                for jj in tgts_explained_by_i_children:
                    if j in tgt.descendents(jj):
                        if PRINT_DEBUG_ALIGNMENTS:
                            print "Possible too-high explanation? %d -- %d" % (i, j), "\t", QGCore.nodeText(st), " -- ", QGCore.nodeText(tgt.subtree(j))
                        explains[i, j] = False
                        stillChanging = True

    if PRINT_DEBUG_ALIGNMENTS:
        print "Explanations after removing too-high explanations"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        print

    
def _remove_too_high_source_nodes_old(srcTreeSubtrees, tgtTreeSubtrees, srcChildrenIndices, explains):
    stillChanging = True
    while (stillChanging):
        stillChanging = False
        for i, st in enumerate(srcTreeSubtrees):
            for j, tt in enumerate(tgtTreeSubtrees):
                if explains[i,j]:
                    # don't expect coreferenced nodes to be properly explained, the links come from nowhere 
                    if srcSkipTreeExplainsTarget(i, j, srcChildrenIndices, explains):
                        explains[i,j] = False
                        stillChanging = True
                        if PRINT_DEBUG_ALIGNMENTS:
                            print "Removing too-high explanation %d -- %d" % (i, j), "\t", QGCore.nodeText(st), " -- ", QGCore.nodeText(tt)

    if PRINT_DEBUG_ALIGNMENTS:
        print "Explanations after removing too-high explanations"
        # print explains
        printAlignmentInfo(srcTreeSubtrees, tgtTreeSubtrees, explains)
        print
    

def _remove_too_wide_target_nodes(src, tgt, explains):
    """ check if the src children link to tgt children within the tgt tree
    Will alter explains matrix
    """
    stillChanging = True
    while (stillChanging):
        stillChanging = False
        # only consider nodes where there are alignments
        for (i, st, j, tt) in aligned_nodes(src, tgt, explains, reverse=False): # top-down
            # are all the alignments below this in the subtrees?
#             linked_not_tgt_tree = [(i_ch, j_ch) 
#                       for (i_ch, st_ch, j_ch, tt_ch) in aligned_nodes(src, tgt, explains)
#                       if i_ch in src.descendents(i)   
#                       and not (j_ch == j or j_ch in tgt.descendents(j))]
            
            linked_not_src_tree = [(i_ch, j_ch) 
                      for (i_ch, st_ch, j_ch, tt_ch) in aligned_nodes(src, tgt, explains)
                      if not (i_ch == i or i_ch in src.descendents(i))
                      and j_ch in tgt.descendents(j) ]   
            
            if PRINT_DEBUG_ALIGNMENTS:
                print i, j, "has linked but not src descnts:", linked_not_src_tree

            # remove these out-of-src-tree alignments
            for (i_ch, j_ch) in linked_not_src_tree:
                # is there an alternative explanation for tgt within the tree?
                linked_src_tree = [(i2, j2) 
                          for (i2, st_ch, j2, tt_ch) in aligned_nodes(src, tgt, explains)
                          if (i2 == i or i2 in src.descendents(i))
                          and j2 == j_ch ]   
                if PRINT_DEBUG_ALIGNMENTS:
                    print i_ch, j_ch, "has alternative explanation from ", i, ":", linked_src_tree
                
                # remove out-of-tree explanation in favour of in-tree
                if len(linked_src_tree)> 0:
                    explains[i_ch, j_ch] = False
                    stillChanging = True
                    if PRINT_DEBUG_ALIGNMENTS:
                        print i_ch, j_ch, "has alternative explanation :", linked_src_tree
                        print "Removing outside-of-tree explanation %d -- %d" % (i_ch, j_ch), "\t", QGCore.nodeText(src.subtree(i_ch)), " -- ", QGCore.nodeText(tgt.subtree(j_ch))
            
            if stillChanging:
                # we have made a change lower down in the tree,
                # so start top-down list of alignments again 
                break 
                            
    if PRINT_DEBUG_ALIGNMENTS:
        print "Explanations after removing too-wide targets"
        # print explains
        printAlignmentInfo(src, tgt, explains)
        print
            
    
def _prefer_simpler_for_target(src, tgt, explains):
    """ Do targets have multiple explanations? """
    for j in tgt.indices():
        linked_src = [i for i in src.indices() if explains[i,j]]
        if len(linked_src) > 2:
            print "Multiple sources: ", linked_src, "---", j
            raise NotImplementedError, "not sure how to handle multiple targets"
        if len(linked_src) > 1:
            i0 = linked_src[0]
            i1 = linked_src[1]
            #if i0 in src.descendents(i1): print i1, "-->", i0
            #if i1 in src.descendents(i0): print i0, "-->", i1
            if not (i0 in src.descendents(i1) or i1 in src.descendents(i0)):
                src_tree_pos = [src.subtree(i).treeposition() for i in linked_src]
                src_tree_pos_len = [len(pos) for pos in src_tree_pos]
                src_pos_list = zip(src_tree_pos_len, linked_src, src_tree_pos)
                src_pos_list.sort()
                # choose to link to the highest source, first on list
                for poslen, i, pos in src_pos_list[1:]:
                    explains[i, j] = False
                    if PRINT_DEBUG_ALIGNMENTS:
                        print "Multiple sources: ", linked_src, "---", j
                        print "Based on unrelated sources ", src_pos_list, ",\tdeleting link ", i, j
                
                
                
def _remove_too_wide_target_nodes_old(src, tgt, explains):
    """ check if the src children link to tgt children within the tgt tree
    Will alter explains matrix
    """
    stillChanging = True
    while (stillChanging):
        stillChanging = False
        for i in src.indices():
            linked_targets = [j for j in tgt.indices() if explains[i,j]]
            
            linked_targets_descendents = linked_targets[:] # copy
            for j in linked_targets: 
                linked_targets_descendents.extend( tgt.descendents(j) )
                
            if PRINT_DEBUG_ALIGNMENTS:
                print "src ", i, QGCore.nodeText(src.subtree(i)), " explains ", linked_targets_descendents
                print "src", i, " has children", src.children(i)
                 
            # do all source child nodes link within this list?
            for i_ch in src.children(i):
                for j in tgt.indices():
                    if explains[i_ch, j] and j not in linked_targets_descendents:
                        explains[i_ch, j] = False
                        stillChanging = True
                        if PRINT_DEBUG_ALIGNMENTS:
                            print "Removing outside-of-tree explanation %d -- %d" % (i_ch, j), "\t", QGCore.nodeText(src.subtree(i_ch)), " -- ", QGCore.nodeText(tgt.subtree(j))
                


def removeLinksOutsideTargetSubtree(i, srcTreeSubtrees, tgtTreeSubtrees, srcChildrenIndices, tgtChildrenIndices, explains):
    raise NotImplementedError, "Not sure if we need this"
    changed = False
    




def getIndicesOfChildren(tree, subtrees):
    """
    Return the list of all direct children of tree
    as indices in the list of subtrees 
    """
    l = []
    for i, ch in enumerate(subtrees):
        for ch2 in tree:
            if ch is ch2: # do an exact address match, not text match
                l.append(i)
    return l


def getIndicesOfDescendents(tree, subtrees):
    """
    Return the list of all direct children of tree
    as indices in the list of subtrees 
    """
    raise DeprecationWarning, "should be using info object now"
    l = []
    for i, ch in enumerate(subtrees):
        if ch.isDescendent(tree): # anywhere in subtree of tree 
            l.append(i)
    return l


def initialLemmaMatching(srcTreeSubtrees, tgtTreeSubtrees, alignments):
    raise DeprecationWarning, "should be using leafLemmaMatches()"
    # align matching lemmas
    for i, st in enumerate(srcTreeSubtrees):
        if not st.isLeaf(): continue
        for j, tt in enumerate(tgtTreeSubtrees):
            if not tt.isLeaf(): continue
            
            # both source and targets are leaves
            # do lemmas match?
            if st.token().lemma == tt.token().lemma:
                alignments[i,j] = True


def leafLemmaMatches(src, tgt):
    """
    Return true if both src and tgt are leaves, and the lemmas match
    """
    if src.isLeaf() and tgt.isLeaf() and src.token().lemma == tgt.token().lemma:
        return True
    else:
        return False
    

def srcChildExplainsTarget(i, j, src, alignments, recursive=False):
    """
    Return True if any child of source node i explains target j
    """
    for i_ch in src.children(i):
        if alignments[i_ch,j]:
            return True
        if recursive:
            recursive_result = srcChildExplainsTarget(i_ch, j, src, alignments, recursive=recursive)
            if recursive_result: 
                return True
    return False
                

def srcExplainsAllTargetChildren(i, j, tgt, alignments, tgt_partially_explained, needExplaining):
    """
    Return True if source node i explains all target children of j
    """
    some_child_aligns = False
    for j_ch in tgt.children(j):
        if not needExplaining[j_ch]: continue
        if tgt_partially_explained[j_ch] and not alignments[i, j_ch]:
            return False # some node is explained elsewhere
        if alignments[i, j_ch]:
            some_child_aligns = True
    return some_child_aligns


def bestSrcExplanationForTarget(j, srcTreeSubtrees, tgtTreeSubtrees, srcChildrenIndices, tgtChildrenIndices, explains, needExplaining):
    """
    Does any source node explain this target?
    """
    # does this node need explaining?
    assert needExplaining[j], "This target node does not need explaining"
    
    explained_by_anything = explains.any(axis=0).getA().flatten()
    assert explained_by_anything[j] == False, "This target node already explained elsewhere"
    
    if len(tgtChildrenIndices[j])==0: 
        return None
    
    # Are any of the children explained?
    for j_ch in tgtChildrenIndices[j]:
        if not needExplaining[j_ch]: continue
        for i, st in enumerate(srcTreeSubtrees):
            if explains[i, j_ch]:
                # this source node already explains a child
                print "Src ", i, "\tmay explain \tTgt ", j, "\tby explaining: ", j_ch
    
    return None



def srcSkipTreeExplainsTarget(i, j, srcChildrenIndices, explains):
    """
    Return True if a grandchild (or below) source node i explains target j,
    but not the direct child.
    There is a skip in the explanation.
    """
    for i_ch in srcChildrenIndices[i]:
        if not explains[i_ch, j]: # not direct child
            if srcChildExplainsTarget(i_ch, j, srcChildrenIndices, explains, recursive=True):
                return True # found an explaining sub-node
    return False


def srcNotExplainingTargetWhenOthersCan(i, j, tgt, explains, needExplaining):
    if not needExplaining[j]: 
        return False
    
    explained_by_anything = explains.any(axis=0).getA().flatten()
    for j_ch in tgt.children(j):
        if not needExplaining[j_ch]: continue
        if explained_by_anything[j_ch] and not explains[i, j_ch]:
            # this source node cannot explain a child when another source node can
            print "Src ", i, "\tfailing to explain \tTgt ", j_ch, "\tchild of ", j
            return True
    return False


def topLevelConstituentMatch(src, tgt):
    """
    Returns true if the two phrases have the same top level constituency
    """
    # don't match leaves by tag, just by lemma
    if src.isLeaf() and tgt.isLeaf(): return True
    if src.isLeaf() or tgt.isLeaf(): return False
    
    stag = src.tag()
    ttag = tgt.tag()
    e1 = stag[0]
    e2 = ttag[0]
    
    # TODO: find best way to match nodes by tag
    if stag=="S" and ttag=="ST": return True # allow new sentences to be formed from S
    if stag=="ST" and ttag=="S": return True # allow new sentences to be formed from S
    
    if False and stag=="NP" and ttag=="NP": # try not handling possession here
        # print src.dep(), tgt.dep() 
        # handle possession separately
        if src.dep()=="poss" and tgt.dep()=="poss": return True
        elif src.dep()=="poss" or tgt.dep()=="poss": return False
        else: return True # anything else OK
    
    if stag=="NP" and (ttag=="ST" or ttag=="S"): return True # allow apposition
    
    # be careful about matching PPs - the type of PP has to match
    if stag=="PP" and ttag=="PP":
        return src.dep()==tgt.dep()
    
    if stag.startswith("VP") and ttag.startswith("VP"):
        if stag == ttag:
            return True # exact match
        elif stag in VERB_PHRASE_FROM_NOUN_PHRASE_TAGS and ttag in VERB_PHRASE_FROM_NOUN_PHRASE_TAGS:
            # both src and tgt can attach to a noun phrase
            return True
        else:
            # don't match together any other type of VP
            return False
        
    return stag == ttag



def nodeHasContent(tree):
    """
    Returns True if any leaf contains a content word
    """
    return tree.has_content()
    

class SubTreeInfo:
    """ Information on this tree, and resulting subtrees, for use in alignment algorithm """
    def __init__(self, tree):
        self._roottree = tree
        self._subtrees = [st for st in tree.subtrees()]
        self._indexed_subtrees = [(i,st) for i, st in enumerate(self._subtrees)]
        self._childrenIndices = [ getIndicesOfChildren(st, self._subtrees) for st in self._subtrees ]
        self._leaves = tree.leaves()
        self._count = len(self._subtrees)
        self._descendentIndices = [set(self._descendents(i)) for i in self.indices()]
        self._parents = [None] * self._count
        parent_child_list = [(i, ch) for i in self.indices() for ch in self.children(i)]
        for (p, ch) in parent_child_list:
            self._parents[ch] = p
        assert self._parents[0] is None, "Root tree not at index 0"
        self._ancestorIndices = [self._ancestors(i) for i in self.indices()]
        
        breadth_first_order = [0]
        breadth_first_order.extend(self._breadth_first_descendents([0]))
        # print breadth_first_order
        self._indexed_subtrees_breadth = [self._indexed_subtrees[e] for e in breadth_first_order]
        self._indexed_subtrees_reversed = self._indexed_subtrees_breadth[:]
        self._indexed_subtrees_reversed.reverse()
        
    def _descendents(self, i):
        """ recursively work through children and build up list of descendents """
        l = []
        l.extend(self._childrenIndices[i])
        for ii in self._childrenIndices[i]:
            l.extend(self._descendents(ii))
        return l

    def _ancestors(self, i):
        """ recursively work through parents and build up list of ancestors """
        p = self.parent(i)
        if p is None: # root node
            return [] # stop recursion
        else:
            l = [self.parent(i)]
            l.extend(self._ancestors(p))
            return l
        
    def _breadth_first_descendents(self, parents):
        """ recursively work through children and build up list of descendents, working breadth-first """
        l = [i for p in parents for i in self.children(p)]
        if len(l)>0: # new children
            l2 = self._breadth_first_descendents(l)
            l.extend(l2)
        return l
    
    
    def subtrees(self): return self._subtrees
    def count(self): return self._count
    def leaves(self): return self._leaves
    
    def indxd_trees(self, reverse=False): 
        """ provide the trees in (index, tree) form, but in breadth-first order """
        if reverse:
            return self._indexed_subtrees_reversed
        else:
            return self._indexed_subtrees_breadth
    
    def indices(self):
        index_list = [i for i in range(self._count)] 
        return index_list
    
    def subtree(self, i): return self._subtrees[i]
    def children(self, i): return self._childrenIndices[i]
    def descendents(self, i): return self._descendentIndices[i]
    def parent(self, i): return self._parents[i]
    def ancestors(self, i): return self._ancestorIndices[i]
    
    
def printSubtreeInfo(subtrees):
    """
    Prints out the list of subtree
    """
    print "Subtrees:"
    for st in subtrees:
        print st.treeposition(), st.tag(), st.getWordPosition(), st.isLeaf(),
        if st.isLeaf(): 
            print st.token().word, st.token().lemma
        else:
            print


def printAlignmentInfo(src, tgt, alignments):
    for (i, st, j, tt) in aligned_nodes(src, tgt, alignments):
        print st.treeposition(), st.tag(), QGCore.nodeText(st),
        print "\t---\t",
        print tt.treeposition(), tt.tag(), QGCore.nodeText(tt)


def aligned_nodes(src, tgt, alignments, reverse=False):
    for (i, st) in src.indxd_trees(reverse=reverse):
        for (j, tt) in tgt.indxd_trees(reverse=reverse):
            if alignments[i,j]:
                yield (i, st, j, tt)



# ----------------------------------------
# coreferencing functions

def corefNode(parseinfo, mention):
    """
    Returns the best node in the tree that matches the mention
    """
    sentence = parseinfo.sentence(mention.sentence)
    tree = sentence.parseTree()
    for st in tree.subtrees():
        # print st.tag(), st.token_range(), (mention.start, mention.end)==st.token_range()
        if (mention.start, mention.end)==st.token_range():
            return st
    # nothing found that matches exactly --- should not happen
    return None
    
    

    

    
def _subtree_list(s):
    """
    Return the list of subtrees from this sentence, and a list of child indices
    """
    raise DeprecationWarning, "should be through Info object"
    tree = s.parseTree()
    return _subtree_list_from_tree(tree)

def _subtree_list_from_tree(tree):
    raise DeprecationWarning, "should be through Info object"
    subtrees = [st for st in tree.subtrees()]
    childrenIndices = [ getIndicesOfChildren(st, subtrees) for st in subtrees ]
    if False and PRINT_DEBUG_ALIGNMENTS:
        print "childrenIndices: ", childrenIndices
    return subtrees, childrenIndices
    
