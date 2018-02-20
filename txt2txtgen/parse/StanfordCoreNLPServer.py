'''
Created on 24 Jul 2013

This has been modified from the corenlp package
https://github.com/relwell/stanford-corenlp-python

The problem with that package is that the interpretation of the data
is hidden inaccessibly in the server.
The implementation is removing essential information.

Instead, this implementation takes all the text output from the 
interactive shell of Stanford CoreNLP, and provides it to the client.
There won't be any runtime impact, as the process has to be done somewhere anyway.

@author: kristian
'''

import config.Config

DIRECTORY = config.Config.STANFORD_CORENLP
from parse.StanfordCoreNLP import JSON_CORENLP_PORT

import json
import optparse
import os
import re
import sys
import traceback
import pexpect
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
import signal


class ProcessError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ParserError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TimeoutError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
            


def init_corenlp_command(corenlp_path, memory, properties):
    """
    Checks the location of the jar files.
    Spawns the server as a process.
    """

    java_path = "java"
    classname = "StanfordCoreNLPServer" # my file with main() in the parse directory
    # include the properties file, so you can change defaults
    # but any changes in output format will break parse_parser_results()
    current_dir_pr = os.path.dirname(os.path.abspath(__file__)) + "/" + properties
    if os.path.exists(properties):
        props = "-props %s" % (properties)
    elif os.path.exists(current_dir_pr):
        props = "-props %s" % (current_dir_pr)
    else:
        # just use default properties, no file
        props = ""
        # raise Exception("Error! Cannot locate: %s" % properties)


    # add memory limit on JVM
    if memory:
        limit = "-Xmx%s" % memory
    else:
        limit = ""

    return "%s %s -cp parse:%s/* %s %s" % (java_path, limit, corenlp_path, classname, props)


def parse_parser_results(text):
    # find xml in the text from the shell:
    # starts with <root>, ends with </root>
    startxml = "<root>"
    endxml = "</root>"
    try:
        start = text.index(startxml)
        end = text.rindex(endxml)
        result = text[start:end+len(endxml)]
    except ValueError as e:
        if VERBOSE:
            print "Text missing start and end xml tags"
            print text
        raise e
    return result
    


class StanfordCoreNLP:

    """
    Command-line interaction with Stanford's CoreNLP java utilities.
    Can be run as a JSON-RPC server or imported as a module.
    """

    def __init__(self, corenlp_path=DIRECTORY, memory="3g", properties='default.properties'):
        """
        Checks the location of the jar files.
        Spawns the server as a process.
        """

        # spawn the server
        start_corenlp = init_corenlp_command(corenlp_path, memory, properties)
        if VERBOSE:
            print start_corenlp
        self.corenlp = pexpect.spawn(start_corenlp)

        # show progress bar while loading the models
        timeouts = [20, 200, 600, 600, 20]
        if VERBOSE:
            # widgets = ['Loading Models: ', Fraction()]
            # pbar = ProgressBar(widgets=widgets, maxval=5, force_update=True).start()
            # Model timeouts:
            # pos tagger model (~5sec)
            # NER-all classifier (~33sec)
            # NER-muc classifier (~60sec)
            # CoNLL classifier (~50sec)
            # PCFG (~3sec)
            for i in xrange(5):
                self.corenlp.expect("done.", timeout=timeouts[i])  # Load model
                print "Loaded model ", i+1
                # pbar.update(i + 1)
            self.corenlp.expect("Entering interactive shell.")
            interactive_timeout = 3
            # pbar.finish()
        else:
            interactive_timeout = sum(timeouts)

        # interactive shell
        self.corenlp.expect("\nNLP> ", timeout=interactive_timeout)

    def close(self, force=True):
        self.corenlp.terminate(force)

    def isalive(self):
        return self.corenlp.isalive()

    def __del__(self):
        # If our child process is still around, kill it
        if self.isalive():
            self.close()

    def _parse(self, text):
        """
        This is the core interaction with the parser.

        It returns a Python data-structure, while the parse()
        function returns a JSON object
        """

        # CoreNLP interactive shell cannot recognize newline
        if '\n' in text or '\r' in text:
            to_send = re.sub("[\r\n]", " ", text).strip()
        else:
            to_send = text

        # clean up anything leftover
        def clean_up():
            while True:
                try:
                    self.corenlp.read_nonblocking(8192, 0.1)
                except pexpect.TIMEOUT:
                    break
        clean_up()

        self.corenlp.sendline(to_send)

        # How much time should we give the parser to parse it?
        # the idea here is that you increase the timeout as a
        # function of the text's length.
        # max_expected_time = max(5.0, 3 + len(to_send) / 5.0)
        max_expected_time = max(300.0, len(to_send) / 3.0)

        # repeated_input = self.corenlp.except("\n")  # confirm it
        t = self.corenlp.expect(["\nNLP> ", pexpect.TIMEOUT, pexpect.EOF,
                                 "\nWARNING: Parsing of sentence failed, possibly because of out of memory."],
                                timeout=max_expected_time)
        incoming = self.corenlp.before
        if t == 1:
            # TIMEOUT, clean up anything left in buffer
            clean_up()
            print >>sys.stderr, {'error': "timed out after %f seconds" % max_expected_time,
                                 'input': to_send,
                                 'output': incoming}
            raise TimeoutError("Timed out after %d seconds" % max_expected_time)
        elif t == 2:
            # EOF, probably crash CoreNLP process
            print >>sys.stderr, {'error': "CoreNLP terminates abnormally while parsing",
                                 'input': to_send,
                                 'output': incoming}
            self.corenlp.close()
            raise ProcessError("CoreNLP process terminates abnormally while parsing")
        elif t == 3:
            # out of memory
            print >>sys.stderr, {'error': "WARNING: Parsing of sentence failed, possibly because of out of memory.",
                                 'input': to_send,
                                 'output': incoming}
            return

        if VERBOSE:
            print "%s\n%s" % ('=' * 40, incoming)
        try:
            # KW modified: just return the xml string, and let 
            # the client end make sense of it 
            results = parse_parser_results(incoming)

        except Exception as e:
            if VERBOSE:
                print traceback.format_exc()
            raise e

        return results




    def parse(self, text):
        """
        This function takes a text string, sends it to the Stanford parser,
        reads in the result, parses the results and returns a list
        with one dictionary entry for each parsed sentence, in JSON format.
        """
        if len(text)>10:
            print "Here is the text before dumping to server:"
            print text
            print "========================="

        parsedtext = json.dumps(self._parse(text))
        print "From parser:"
        print parsedtext
        if len(text)>10:
            raise SystemExit, 1
        return parsedtext



def closeServer(a,b):
    """
    Close the server gracefully.
    Apparently this takes two arguments, even though documentation says none
    """
    print >>sys.stderr, "Bye."
    exit()


if __name__ == '__main__':
    """
    The code below starts an JSONRPC server
    """
    
    signal.signal(signal.SIGINT, closeServer)
    
    parser = optparse.OptionParser(usage="%prog [OPTIONS]")
    parser.add_option('-p', '--port', default='%d'%JSON_CORENLP_PORT,
                      help='Port to serve on (default %d)'%JSON_CORENLP_PORT)
    parser.add_option('-H', '--host', default='127.0.0.1',
                      help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    parser.add_option('-q', '--quiet', action='store_false', default=True, dest='verbose',
                      help="Quiet mode, don't print status msgs to stdout")
    parser.add_option('-S', '--corenlp', default=DIRECTORY,
                      help='Stanford CoreNLP tool directory (default %s)' % DIRECTORY)
    parser.add_option('-P', '--properties', default='default.properties',
                      help='Stanford CoreNLP properties file (default: default.properties)')
    options, args = parser.parse_args()
    VERBOSE = options.verbose
    # server = jsonrpc.Server(jsonrpc.JsonRpc20(),
    #                         jsonrpc.TransportTcpIp(addr=(options.host, int(options.port))))

    
    server = SimpleJSONRPCServer((options.host, int(options.port)), logRequests=False)

    nlp = StanfordCoreNLP(options.corenlp, properties=options.properties)
    server.register_function(nlp.parse)

    if VERBOSE: 
        print 'Stanford parser serving on http://%s:%s' % (options.host, options.port)
    
    server.serve_forever()
        
