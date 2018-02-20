'''
Created on 6 Mar 2015

@author: kwoodsen
'''

import os
import sys
import codecs

import txt2txtgen

from optparse import OptionParser




def command_line_parser():
    parser = OptionParser(usage="Example script to demonstrate extraction of grammar rules using QTSG. \nSupply a text file containing (source text, target text, blank line) lines.")
    parser.add_option("-f", "--file", dest="filename",
                      help="read in sentences from FILE", metavar="FILE",
                      default='examples/qtsg_data')
    parser.add_option("-l", "--long", action='store_true',
                      dest="verbose", default=False,
                      help="print out QTSG rules and information")
    parser.add_option("-s", "--save", action='store_true',
                      dest="save", default=False,
                      help="save the QTSG rules to a pickle file in the current directory")
    parser.add_option("-k", "--kauchak", action='store_true',
                      dest="kauchak", default=False,
                      help="Input files are in the format of David Kauchak's aligned sentences for simplification. Use -f to set the directory. This script expects the files normal.aligned and simple.aligned")
    parser.add_option("-r", "--revisions-corpus", action='store_true',
                      dest="revisions", default=False,
                      help="Input files are in the format of Kristian Woodsend's sentences from Simple Wikipedia revisions. Use -f to set the directory. This script expects a directory of files *.old, *.new and *.lines")
    parser.add_option("-a", "--alignments-corpus", action='store_true',
                      dest="alignments", default=False,
                      help="Input files are in the format of Kristian Woodsend's aligned sentences from Simple Wikipedia. Use -f to set the directory. This script expects the files aligned.main and aligned.simple")
    parser.add_option("-n", "--number-lines", type="int",
                      dest="line_limit", default=0,
                      help="Limit the number of input lines")
    return parser


def parse_doc(txt):
    """ Parse the text and return a document """
    xml = txt2txtgen.parse.StanfordCoreNLP.parseText(txt)
    doc = txt2txtgen.parse.StanfordCoreNLP.DocInfo(xml)
    return doc


def example_file_reader(options):
    """ Read in lines from the examples/qtsg_data file.
    Expected format:
    - line for source sentence(s)
    - line for target sentence(s)
    - blank line
    """
    with codecs.open(options.filename, encoding='UTF-8', mode='r') as f:
        while True:
            src_txt = f.readline()
            tgt_txt = f.readline()
            blank_line = f.readline()
            assert blank_line.strip() == '', "data file not in the format we expect"
            if len(src_txt)==0 or len(tgt_txt) == 0: break

            if options.verbose:
                print "Extracting rules from text:"
                print src_txt.strip()
                print tgt_txt.strip()
                print
                
            yield (src_txt, tgt_txt)
            
    return # end of file


def kauchak_alignments_file_reader(options):
    """ Read in lines from Kauchak's aligned sentences v2 corpus """
    input_dir = os.path.dirname(options.filename)
    filename_src = os.path.join(input_dir, 'normal.aligned')
    filename_tgt = os.path.join(input_dir, 'simple.aligned')
    
    line_counter = 0
    with codecs.open(filename_src, encoding='UTF-8', mode='r') as f_src:
        with codecs.open(filename_tgt, encoding='UTF-8', mode='r') as f_tgt:
            while True:
                src_txt = f_src.readline()
                tgt_txt = f_tgt.readline()
                if len(src_txt)==0 or len(tgt_txt) == 0: break
                line_counter +=1 
                
                src_txt = src_txt.split('\t')[2].strip() # expecting 3 fields
                tgt_txt = tgt_txt.split('\t')[2].strip() 
    
                if options.verbose:
                    print line_counter, "\tExtracting rules from text:"
                    print src_txt.strip()
                    print tgt_txt.strip()
                    print
                    
                yield (src_txt, tgt_txt)




def woodsend_revisions_file_reader(options):
    """ Read in lines from Kauchak's aligned sentences v2 corpus """
    input_dir = os.path.dirname(options.filename)
    input_dir = '/disk/scratch/kwoodsen/wiki/corpus-revisions/corpus-files' # TODO: remove this
    line_counter = 0 

    file_pattern = "1*.old"
    for fn in txt2txtgen.utils.ListFiles.listAllFiles( file_pattern, input_dir ):
        fn = os.path.splitext(fn)[0] # remove suffix
        print fn
        filename_src = fn + '.old'
        filename_tgt = fn + '.new'
        filename_lines = fn + '.lines'
    
        try:
            # with statements handle closing of files if .lines file is not present
            with codecs.open(filename_src, encoding='UTF-8', mode='r') as f_src:
                with codecs.open(filename_tgt, encoding='UTF-8', mode='r') as f_tgt:
                    with codecs.open(filename_lines, encoding='UTF-8', mode='r') as f_lines:
                        src_lines = f_src.readlines()
                        tgt_lines = f_tgt.readlines()
                        for alignment_info in f_lines:
                            line_counter +=1 
                            
                            src_linenumber, tgt_linenumber = alignment_info.split('\t')
                            src_linenumber = int(src_linenumber)
                            tgt_linenumber = int(tgt_linenumber)
                            src_txt = src_lines[src_linenumber]
                            tgt_txt = tgt_lines[tgt_linenumber]
                            
                            if options.verbose:
                                print line_counter, "\tExtracting rules from text:"
                                print src_txt.strip()
                                print tgt_txt.strip()
                                print
                                
                            yield (src_txt, tgt_txt)
                            
        except IOError, e:
            if options.verbose:
                print "Skipping ", fn, " as there is no alignment file"
            pass


def woodsend_alignments_file_reader(options):
    pass



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
    
    # list of the QTSG pairs from all the sentences 
    all_qtsg_results = []
    all_qtsg_split_results = []
    all_qtsg_st_results = []
    
    if options.kauchak:
        input_text_reader = kauchak_alignments_file_reader(options)
    elif options.revisions:
        input_text_reader = woodsend_revisions_file_reader(options)
    elif options.alignments:
        input_text_reader = woodsend_alignments_file_reader(options)
    else:
        input_text_reader = example_file_reader(options)
    
    count_input_lines = 0
    for (src_txt, tgt_txt) in input_text_reader:
        count_input_lines += 1
        if options.line_limit > 0 and count_input_lines > options.line_limit:
            break
        
        # parse the text
        try:
            src_doc = txt2txtgen.formats.ParsedArticle.ParsedSentencesArticle(task, parse_doc(src_txt))
            tgt_doc = txt2txtgen.formats.ParsedArticle.ParsedSentencesArticle(task, parse_doc(tgt_txt))
            doc_pair = txt2txtgen.formats.ParsedArticle.PairedSourceTargetArticle(task, src_doc, tgt_doc)
        except AssertionError:
            # parsing or sentence splitting problem
            continue
        
        sentence_matchlist = txt2txtgen.scripts.MatchSentencesAndExtractQTSG.processDocPair(doc_pair)
        
        qtsg_results = txt2txtgen.scripts.MatchSentencesAndExtractQTSG.learnQGRules(sentence_matchlist, doc_pair)
        
        all_qtsg_results.extend(qtsg_results)

        split_results, st_results = txt2txtgen.scripts.MatchSentencesAndExtractQTSG.learnQGSplitRules(sentence_matchlist, doc_pair)
        all_qtsg_split_results.extend(split_results)
        all_qtsg_st_results.extend(st_results)
                
    
    # convert from synchronous trees to rules with counter
    qtsg_rules = txt2txtgen.qtsg.SyncTreeGrammar.removeDuplicateQtsgRules(all_qtsg_results)
    qtsg_split_rules = txt2txtgen.qtsg.SplitSentences.removeDuplicateQtsgRules(all_qtsg_split_results)
    
    # remove rules that do not involve rewriting
    qtsg_rules = [r for r in qtsg_rules if not r.isIdentical()]
    qtsg_split_rules = [r for r in qtsg_split_rules if not r.isIdentical()]
    
    if options.verbose:
        print
        print "Information on QTSG rules"
        txt2txtgen.qtsg.info.printRuleSetInfo( qtsg_rules )
    
        print
        print "List of rules with substitutions"
        txt2txtgen.qtsg.info.printRuleSetSubstitutions(qtsg_rules, minCount=2) 
        
        print 
        print "All rules:"
        txt2txtgen.qtsg.info.printRuleSet(qtsg_rules)
        
        
        #print
        #print "Information on QTSG rules for splitting sentences"
        #txt2txtgen.qtsg.SplitSentences.printRuleSetInfo( qtsg_split_rules )
    

    if options.save:
        txt2txtgen.qtsg.SyncTreeGrammar._pickleRules( qtsg_rules, 'qtsg-rules.pickle')
        txt2txtgen.qtsg.SyncTreeGrammar._pickleRules( qtsg_split_rules, 'qtsg-split-rules.pickle')


