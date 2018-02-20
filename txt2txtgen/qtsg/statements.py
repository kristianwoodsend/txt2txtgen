'''
Statement extraction using QTSG

Created on 26 Sep 2013

@author: kristian
'''

import QGCore, QGParaphrase, SyncTreeGrammar
from QGDefs import PRINT_DEBUG_PARAPHRASE, PRINT_DEBUG_SPLIT_PARAPHRASE, MIN_PHRASE_SIZE



def split_grammar_ST(all_rules):
    """ Split the grammar into ST-generating rules and all others """
    st_grammar = []
    normal_grammar = []
    for r in all_rules:
        if r._target.tag() == "ST":
            # assert r.isOKSTRule(), "Rule not good: %s" % str(r)
            if r.isOKSTRule():
                st_grammar.append(r)
            else:
                # print "Bad ST rule: ", str(r)
                pass # should warn about bad rules?
        else: # for all other rules
            normal_grammar.append(r)

    return st_grammar, normal_grammar


def split_sentence(src, st_grammar, rewrite_grammar, limit_rewrites_per_node=0):
    """ 
    Split the src sentence tree into new ST sentences, using st_grammar.
    Returns a list of possible new sentences, including the original sentence.
    """
    assert src.tag()=="ROOT", "Unexpected source tag %s indicates this is not the top of the sentence" % src.tag()
    assert len(src) == 1, "Unexpected structure at top of the sentence - %d children" % len(src)
    
    # not this assert - sometime we are getting SINV
    #assert src[0].tag() == "ST", "Unexpected source tag %s indicates this is not the top of the sentence" % src[0].tag()
    st_paraphrases = [src[0]]
    st_rulelist = [None]

    if PRINT_DEBUG_SPLIT_PARAPHRASE:
        print "src tree"
        print src
        print "---------"
    
    for src_subtree in src.subtrees():
        
        # print src_subtree.treeposition(), src_subtree.tag()
        applicable_rules = [r for r in st_grammar if r.isSuitable(src_subtree, None)]
        if limit_rewrites_per_node > 0 and len(applicable_rules) >  limit_rewrites_per_node:
            applicable_rules = applicable_rules[:limit_rewrites_per_node]
            
        if PRINT_DEBUG_SPLIT_PARAPHRASE:
            print src_subtree.treeposition(), src_subtree.tag(), "\tsplitting rules ", len(applicable_rules)
            
        for r in applicable_rules: 
            if PRINT_DEBUG_SPLIT_PARAPHRASE: print "Applying ", r
            
            try:
                # new_sentence = QGParaphrase.createParaphraseTree(src_subtree, r, rewrite_grammar, QGParaphrase.LIMIT_RULE_DEPTH-1)
                new_sentence = QGParaphrase.createParaphraseTree(src_subtree, r, rewrite_grammar, 0, rewrite_only_if_necessary=True)
                assert new_sentence.tag() == "ST", "Unexpected sentence structure created"
                if PRINT_DEBUG_PARAPHRASE: print "Marking independent phrases: ", MIN_PHRASE_SIZE
                new_sentence.markIndependentPhrase(MIN_PHRASE_SIZE)

                st_paraphrases.append(new_sentence)
                st_rulelist.append(r)
                if PRINT_DEBUG_SPLIT_PARAPHRASE:
                    print r
                    # print new_sentence
                    print QGCore.nodeText(new_sentence)
            except QGParaphrase.NoGrammarPathError, e:
                if PRINT_DEBUG_PARAPHRASE:
                    print "Failed to make new sentence ", e, "\t", r

    return st_paraphrases, st_rulelist


def create_ST_paraphrase_tree(src, grammar):
    """ creates a paraphrase tree from the src tree, using the grammar.
    Assumes the root node is ST, and will copy the root node as no ST rule will be in the grammar.
    """ 
    # assert src.tag() == "ST" or src.tag() == "SINV", "Unexpected source tag %s indicates this is not the top of the sentence" % src.tag()
    dupRule = SyncTreeGrammar.SyncGrammarRule.createDuplicationRule(src)
    paraphrase = QGParaphrase.createParaphraseTree(src, dupRule, grammar, 0)
    # print result
    return paraphrase
        
    
