"""
Various debug flags and settings,
common to the qtsg module
"""

import txt2txtgen.config.Config as Config
import txt2txtgen.parse.PhraseDependencyTree as PhraseDependencyTree

PRINT_DEBUG = False
PRINT_DEBUG_SYNC = False
PRINT_DEBUG_SPLIT = False
PRINT_DEBUG_SPLIT_INDICATIONS = False
PRINT_DEBUG_LINKING = False
PRINT_INFO = False
PRINT_MATCH_LIST = False
PRINT_RULE_APPLICATION = False
PRINT_DEBUG_PARAPHRASE = False
PRINT_DEBUG_SPLIT_PARAPHRASE = False

DEBUG_SENTENCE_SPLIT = False
DEBUG_SENTENCE_SPLIT_RESULT = False

# should matching of rules to trees include dependency information?
MATCH_DEP_LABELS = False

# todo: sort out parsing and caching
# dpParser = POSTagger.StanfordDependencyParser()
# pennParser = POSTagger.StanfordPennParser()
graphvizDir = Config.GRAPHVIZ_DIR
FORMAT="ps"
GRAPHVIZ_EXTRA = False
MIN_PHRASE_SIZE = PhraseDependencyTree.PhraseDependencyTree.USE_CONSTITUENCY_STRUCTURE


MATCH_STOP_TAGS = PhraseDependencyTree.PhraseDependencyTree.MATCH_STOP_TAGS
VERB_PHRASE_TAGS = PhraseDependencyTree.PhraseDependencyTree.VERB_PHRASE_TAGS
VERB_PHRASE_FROM_NOUN_PHRASE_TAGS = set(('VP-VBZ', 'VP-VBP' , 'VP-VBD', 'VP-MD', 'VP-VBZ-COP', 'VP-VBP-COP' , 'VP-VBD-COP'))



