'''
Created on 6 Mar 2015

@author: kwoodsen
'''

import os
import sys
import codecs

import txt2txtgen
from txt2txtgen.summarize.Choosers import SingleShotChoiceTree

from optparse import OptionParser




def command_line_parser():
    parser = OptionParser(usage="Example script to demonstrate generation using QTSG. \nSupply a text file containing source text, and a set of grammar rules.")
    parser.add_option("-f", "--file", dest="filename",
                      help="read in sentences from FILE", metavar="FILE",
                      default='examples/sentence_data')
    parser.add_option("-g", "--grammar", dest="grammar",
                      help="read in grammar from FILE", metavar="FILE",
                      default='qtsg-rules.pickle')
    parser.add_option("-l", "--long", action='store_true',
                      dest="verbose", default=False,
                      help="print out QTSG rules and information")
    return parser


def parse_doc(txt):
    """ Parse the text and return a document """
    xml = txt2txtgen.parse.StanfordCoreNLP.parseText(txt)
    doc = txt2txtgen.parse.StanfordCoreNLP.DocInfo(xml)
    return doc


def example_file_reader(options):
    """ Read in lines from the examples/sentence_data file.
    Expected format is single sentence per line.
    """
    with codecs.open(options.filename, encoding='UTF-8', mode='r') as f:
        while True:
            src_txt = f.readline()
            if len(src_txt)==0: break
            yield src_txt
            
    return # end of file


def load_grammar(options):
    """ Load in the QTSG grammar for simplification """
    
    qtsg_rules = txt2txtgen.qtsg.SyncTreeGrammar._unpickleRules( options.grammar )
    qtsg_rules = [r for r in qtsg_rules if not r.isIdentical()]
    qtsg_rules = [r for r in qtsg_rules if r.count() > 2]
    
    # split the grammar into two types: ones that create new sentences, and ones that modify the sentence
    st_grammar, normal_grammar = txt2txtgen.qtsg.statements.split_grammar_ST(qtsg_rules)

    # separate rule objects handle splitting of sentences into two
    try:
        filename_split_grammar = os.path.join(os.path.dirname(options.grammar), 'qtsg-split-rules.pickle')
        split_grammar = txt2txtgen.qtsg.SyncTreeGrammar._unpickleRules(filename_split_grammar)
    except IOError:
        split_grammar = [] # does not have to be present
    #split_grammar = [r for r in split_grammar if r.count() > 2]

    if options.verbose:
        txt2txtgen.qtsg.info.printRuleSetInfo( qtsg_rules )
        
    return st_grammar, normal_grammar, split_grammar




if __name__ == '__main__':
    sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
    
    cl_parser = command_line_parser()
    (options, args) = cl_parser.parse_args()

    # set the location of Stanford CoreNLP parser
    # Can also set in the file txt2txtgen/config/Config.py
    txt2txtgen.config.Config.STANFORD_CORENLP = '/disk/scratch/tools/stanford/stanford-corenlp-full-2013-06-20'
    
    # prop_file is Stanford CoreNLP properties file
    task = None
    prop_file = None
    txt2txtgen.parse.StanfordCoreNLP.startServer(prop_file)
    
    input_text_reader = example_file_reader(options)

    # load in QTSG
    print "Loading in QTSG..."
    st_grammar, normal_grammar, split_grammar = load_grammar(options)
    
    for src_txt in input_text_reader:
        
        print "------------------------------\n"        
        print "Rewriting source text: ", src_txt 
    
        # parse the text
        src_doc = txt2txtgen.formats.ParsedArticle.ParsedSentencesArticle(task, parse_doc(src_txt))
        
        for src_sentence in src_doc.sentences():
            # apply the grammar to a sentence, to create some possible paraphrases
            src_tree = src_sentence.parseTree()
            st_paraphrases, _st_rulelist = txt2txtgen.qtsg.statements.split_sentence(src_tree, st_grammar, normal_grammar, limit_rewrites_per_node=2)

            # these choice_trees capture all the information about possible rewrites
            # this would be the input to the ILP
            choice_trees = [ txt2txtgen.qtsg.statements.create_ST_paraphrase_tree(st, normal_grammar) for st in st_paraphrases]

            chooser = txt2txtgen.summarize.Choosers.NumberjackPhraseChooser(None)
            output = chooser.choose(choice_trees)

            # print out the paraphrases        
            for s in output: print s


