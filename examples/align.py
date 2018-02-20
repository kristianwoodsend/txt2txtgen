'''
Created on 6 Mar 2015

@author: kwoodsen
'''

import sys
import codecs

import txt2txtgen

from optparse import OptionParser




def command_line_parser():
    parser = OptionParser(usage="Example script to demonstrate word alignments. \nSupply a text file containing (source text, target text, blank line) lines.")
    parser.add_option("-f", "--file", dest="filename",
                      help="read in sentences from FILE", metavar="FILE",
                      default='examples/align_data')
    parser.add_option("-l", "--long", action='store_true',
                      dest="verbose", default=False,
                      help="print out more alignment information")
    return parser


def parse_doc(txt):
    """ Parse the text and return a document """
    xml = txt2txtgen.parse.StanfordCoreNLP.parseText(txt)
    doc = txt2txtgen.parse.StanfordCoreNLP.DocInfo(xml)
    return doc


def show_alignments(matchlist, long=False):
    """ Prints out the aligned words """
    leaves = [(sn, tn) for (sn, tn) in matchlist if sn.isLeaf() and tn.isLeaf()]
    leaves.sort(key=lambda (sn,tn): sn.token().index)
    
    for (sn, tn) in leaves:
        if long:
            print sn.token().index, "\t", sn.treeposition(), "\t", txt2txtgen.qtsg.QGCore.nodeText(sn),
            print "\t---\t",
            print tn.token().index, "\t", tn.treeposition(), "\t", txt2txtgen.qtsg.QGCore.nodeText(tn)
        else:
            print '%d-%d ' % (sn.token().index, tn.token().index), 
    print


if __name__ == '__main__':
    sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)
    
    cl_parser = command_line_parser()
    (options, args) = cl_parser.parse_args()

    # set the location of Stanford CoreNLP parser
    # Can also set in the file txt2txtgen/config/Config.py
    txt2txtgen.config.Config.STANFORD_CORENLP = '/disk/scratch/tools/stanford/stanford-corenlp-full-2013-06-20'
    
    # prop_file is Stanford CoreNLP properties file
    prop_file = None
    txt2txtgen.parse.StanfordCoreNLP.startServer(prop_file)
    
    # expecting format to be:
    # line for source sentence(s)
    # line for target sentence(s)
    # blank line
    with codecs.open(options.filename, encoding='UTF-8', mode='r') as f:
        while True:
            src_txt = f.readline()
            tgt_txt = f.readline()
            blank_line = f.readline()
            assert blank_line.strip() == '', "data file not in the format we expect"
            if len(src_txt)==0 or len(tgt_txt) == 0: break

            # do alignment            
            src_doc = parse_doc(src_txt)
            tgt_doc = parse_doc(tgt_txt)
            matchlist = txt2txtgen.qtsg.align.align_nodes_multisentence_no_corefs(src_doc, tgt_doc)
            if options.verbose:
                print "Source:\t", src_txt.strip()
                print "Target:\t", tgt_txt.strip()
            show_alignments(matchlist, long=options.verbose)


