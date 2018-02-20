'''
Connection to Stanford core NLP software.

We are using corenlp package for the python connection,
https://github.com/relwell/stanford-corenlp-python

Created on 24 Jul 2013

@author: kristian
'''


import nltk
import nltk.parse.dependencygraph

import txt2txtgen
import txt2txtgen.config.Config as Config
import txt2txtgen.config.Debug as Debug


import jsonrpclib, simplejson
import pexpect, atexit, time, sys, os
import subprocess
import unicodedata

# ElementTree import, some options faster than others
#import cElementTree as ET
#import lxml.etree as ET
import xml.etree.ElementTree as ET # Python 2.5


JSON_CORENLP_PORT = 8085

TAG_SENTENCES = "sentences"
TAG_SENTENCE = "sentence"

TAG_TOKENS = "tokens"
TAG_TOKEN = "token"
TAG_WORD = "word"
TAG_LEMMA = "lemma"
TAG_CHAR_BEGIN = "CharacterOffsetBegin"
TAG_CHAR_END = "CharacterOffsetEnd"
TAG_POS = "POS"
TAG_NER = "NER"

TAG_PARSETREE = "parse"

TAG_DEPS = "dependencies"
TAG_DEP = "dep"
TAG_DEP_GOV = "governor"
TAG_DEP_DEP = "dependent"

ATTRIB_ID = "id"
ATTRIB_TYPE = "type"
ATTRIB_INDEX = "idx"


TAG_COREF = "coreference"
TAG_COREF_MENTION = "mention"


MARK_TOP_SENTENCE = True

# the pexpect object for the Stanford parser Java program
stanfordJavaProcess = None

def _connectToStanfordParser(text):
    global stanfordJavaProcess
    assert stanfordJavaProcess is not None, "server has not been started"
    
    lines = text.splitlines()
    for l in lines:
        stanfordJavaProcess.sendline(l)
        stanfordJavaProcess.expect("NLP>")
        
    stanfordJavaProcess.sendline() # blank line to get parse
    stanfordJavaProcess.expect_exact("\nNLP>", timeout=300)
    before = stanfordJavaProcess.before
    # tidy up output: must not have any whitespace before <xml>
    xml = before.strip()
    xml = xml.replace('\r\r\n','\n')
    return xml



def startServer(configFile=None):
    
    global stanfordJavaProcess
    assert stanfordJavaProcess is None, "server started already"
    #if stanfordJavaProcess is not None: 
    #    return # server started already
    
    # print "cwd:", os.getcwd()
    if configFile:
        assert os.path.exists(configFile), "Can't find the properties file for Stanford parser at %s"%configFile
    cmdLine = _javaServerCommandLine(configFile)
    print "Starting server: ", cmdLine 
    
    stanfordJavaProcess = pexpect.spawn(cmdLine)
    # stanfordJavaProcess.logfile = sys.stdout

    stanfordJavaProcess.expect("Entering interactive shell.", timeout=300)
    # interactive shell
    stanfordJavaProcess.expect("\nNLP> ", timeout=30)

    # print "Parser appears to be up and working"



def _javaServerCommandLine(configFile):
    """
    Checks the location of the jar files.
    Spawns the server as a process.
    """

    java_path = "java"
    classname = "StanfordCoreNLPServer" # my file with main() in the parse directory
    corenlp_path = txt2txtgen.config.Config.STANFORD_CORENLP
    memory = "-Xmx3g" # add memory limit on JVM
    props = ""
    if configFile is not None:
        props = "-props %s" % configFile

    #print "cwd:", os.getcwd()
    return "%s %s -cp txt2txtgen/parse:../parse:%s/* %s %s" % (java_path, memory, corenlp_path, classname, props)
    

def __testIfServerWorking():
    global __stanfordJavaProcess
    assert __stanfordJavaProcess is not None, "Lost server process"
    assert __stanfordJavaProcess.poll() is None, "Stanford parser server has stopped"
    
    wakeuptest = jsonrpclib.Server("http://localhost:%d" % JSON_CORENLP_PORT)
    assert wakeuptest is not None, "Lost client for parser server"
    for _trial in range(20):
        try:
            # print "Testing to see if server is up", _trial
            result = simplejson.loads(wakeuptest.parse("test"))
            # print result
            assert result is not None, "Nothing coming back from print result"
            # everything seems OK
            return 
        
        except IOError:
            # print "Server not responding yet, trial", _trial
            # go round loop again
            time.sleep(1)
            
    # timeout
    raise SystemExit, "Not able to connect to Stanford parser process"



@atexit.register
def stopServer():
    global stanfordJavaProcess
    if stanfordJavaProcess is not None:
        stanfordJavaProcess.sendline() # blank line
        stanfordJavaProcess.sendeof()
        result = stanfordJavaProcess.terminate()
        print >> sys.stderr, "Closing Stanford parser"
        # assert result, "Unsuccessful at closing Stanford parser"
    stanfordJavaProcess = None
    

def parseText(text):
    """
    Sends text to parser, and returns the xml information
    """
    # older versions of pexpect cannot cope with unicode
    
    # print "raw text in parseText() : ", text
    utext = unicode(text)
    ascii_text = unicodedata.normalize('NFKD', utext).encode('ascii', 'ignore')
    # print "ascii text in parseText() : ", ascii_text
    xml = _connectToStanfordParser(ascii_text)
    
    # tidy xml if necessary by removing errors printed by parser at the beginning
    if not xml.startswith("<?xml"):
        if False:
            print "Not clean start to XML"
            print xml
            print xml.find("<?xml")
        xml = xml[xml.find("<?xml"):]
    return xml


# This is the parser cache filename. This will get defined when the task is known.
__parser_cache = None

def startCache(task):
    """
    Open cache 
    """
    d = task.shelfDir()
    global __parser_cache
    __parser_cache = txt2txtgen.utils.FeatureCache.PickleCache(task, "corenlp.shelved", "corenlp")
    if (Debug.PRT_Cache): print "Parser cache info: ", __parser_cache
    pass

def start(task):
    """
    Start cache and start the Stanford parser
    """
    startCache(task)
    startServer(task.stanfordParserConfig())
    
    
    
    
def parseDoc(doc):
    global __parser_cache
    if (Debug.PRT_Cache): print "Parser cache info: ", __parser_cache
    assert __parser_cache, "Cache details not set up"
    try:
        xml = __parser_cache.get(doc.parseCacheKey())
        if (Debug.PRT_Cache): print "Taking XML from cache"
    except:
        # document is not in cache
        xml = parseText(doc.rawText())
        print xml
        __parser_cache.set(doc.parseCacheKey(), xml)
        if (Debug.PRT_Cache): print "Taking XML from parser"
    return DocInfo(xml)



class DocInfo():
    '''
    Provides methods to access the information returned by the parser. 
    '''

    def __init__(self, xml):
        '''
        Create using the dictionary of information returned by the parser
        '''
        self.xml = xml
        root = ET.fromstring(xml)
        sentencesXml = root.find("document/sentences")
        assert sentencesXml is not None, "No sentences information from parser"
        self._sentences = self.__initSentences(sentencesXml)
        corefXml = root.find("document/coreference")
        # TODO: may need to remove this assert if docs with no coreferencing mean that this element does not exist
        self._coref = []
        if corefXml is not None:
            assert corefXml is not None, "No coref information from parser"
            self._coref = [ CorefInfo(et) for et in corefXml.findall(TAG_COREF) ]
        
        
    def __initSentences(self, xml):
        slist = [ SentenceInfo(et) for et in xml.findall(TAG_SENTENCE) ]
        return slist
        
        
    def sentences(self):
        """ 
        Return all the sentence information as a list
        """
        return self._sentences
    
    def sentenceCount(self):
        """ Returns the number of sentences """
        return len(self._sentences)
    
    def sentence(self, i):
        """ 
        Return the sentence information for sentence i
        """
        assert i < len(self._sentences), "Sentence %d requested from list of length %d" % (i, len(self._sentences))
        return self._sentences[i]

    def corefCount(self):
        """ Returns the number of coreferences """
        return len(self._coref)
    
    def coref(self, i):
        """ 
        Return the coreference information for coref i
        """
        assert i < len(self._coref), "Sentence %d requested from list of length %d" % (i, len(self._coref))
        return self._coref[i]

    def corefs(self):
        """ 
        Return all the coreference information as a list
        """
        return self._coref
    
        


class SentenceInfo():
    '''
    Provides methods to access the information returned by the parser.
    Access methods for the dictionary returned on an individual sentence. 
    
    N.B. The attributes here are read-only, with no protection 
    '''
    def __init__(self, xml):
        '''
        Interpret information returned by the parser
        '''
        assert xml.tag == TAG_SENTENCE, "Not sentence element"
        
        # store list of tokens
        t = xml.find(TAG_TOKENS)
        self.__tokens = [ TokenInfo(et) for et in t.findall(TAG_TOKEN) ]
        
        try:
            self.__parsetext = xml.find(TAG_PARSETREE).text.strip()
    
            self.__dep = None
            possible_depxml = xml.findall(TAG_DEPS)
            # NB collapsed-ccprocessed-dependencies introduces multiple-govenors when removing CC links
            depxml = [x for x in possible_depxml if x.get(ATTRIB_TYPE)=="collapsed-dependencies"]
            assert len(depxml) == 1, "Cannot find dependency information of type collapsed-dependencies"
            graph = self.createDepGraph(depxml[0])
            self.__dep = graph
    
            self.__parsetree = None
            self.__parsetree = self.__createParseTree()
        except AttributeError:
            self.__parsetree = None
        
        self.__id = int(xml.attrib.get(ATTRIB_ID))-1


    @staticmethod
    def createDepGraph(xml):
        """
        Interpret the xml dependency information and create a dependency graph.
        """
        assert xml.tag == TAG_DEPS, "Not dependency element"
        
        # nltk.parse.DependencyGraph._parse() does not respect the node addresses we provide,
        # it assumes that the entries are in token order
        # which StanfordCoreNLP does not do, so we need to sort here
        
        
        # entries = [ SentenceInfo.__createDepEntryText(d) for d in xml.iterfind(TAG_DEP) ] # python 2.7 only
        entries = [ SentenceInfo.__createDepEntryText(d) for d in xml.findall(TAG_DEP) ]
        
        # remove any blank entries caused by invalid info from parser
        # entries = [(i, line) for (i,line) in entries if not line is None]
        entries.sort()
        text = "\n".join((i[1] for i in entries))
        dg = txt2txtgen.nlputils.NltkUtils.DependencyGraph(text)
        return dg

        
    @staticmethod
    def __createDepEntryText(d):
        """
        Reads the xml related to a dependency relation,
        and returns the tuple (dependent_address, text)
        where the text is in CONLL(10) format
        """
        assert d.tag == TAG_DEP, "Not individual dependency element"
        governor = d.find(TAG_DEP_GOV)
        dependent = d.find(TAG_DEP_DEP)
        word = dependent.text
        address = dependent.get(ATTRIB_INDEX)
        head = governor.get(ATTRIB_INDEX)
        rel = d.get(ATTRIB_TYPE)
        
        line = "%s\t%s\t_\t_\t_\t_\t%s\t%s\t_\t_" % (address, word, head, rel)
        return (int(address), line)
    

    def __createParseTree(self):
        """
        Creates the PhraseDependencyTree from the parse and dependency information
        """
        assert self.__parsetree is None, "Tree already created"
        t=None
        try:
            t = txt2txtgen.parse.PhraseDependencyTree.PhraseDependencyTree(self.__parsetext)
            t.markPositions() # should match up with token information
            t.storeTokenInfo(self.tokens())
            if MARK_TOP_SENTENCE: t.markTopSentenceNode()
            t.mark_copula_verbs()
            t.verb_phrase_subtypes()
            # t.correctTree() # TODO: work out if this is needed
            t.addDependencies(self.dependencies())
            t.mark_NP_possession() # needs dependency information to spot possession
            t.markIndependentPhrase(minIndependentLength=txt2txtgen.parse.PhraseDependencyTree.PhraseDependencyTree.USE_CONSTITUENCY_STRUCTURE)
        except (ValueError),e:
            # parsing has failed 
            # TODO: work out what might be appropriate
            raise e
        return t

        
   
    def cfg(self):
        """ Returns the parse tree string """
        return self.__parsetext
    
    def parseTree(self):
        """ Returns the parse tree string """
        return self.__parsetree


    
    def dependencies(self):
        """ Returns the dependency graph """
        assert self.__dep is not None, "Dependency graph not created"
        return self.__dep

    def id(self):
        """ 
        Returns the index of this sentence in the whole document.
        First sentence is given index 0.
        """
        return self.__id


    def tokens(self):
        """ Returns the word list """
        return self.__tokens
        
    def token(self, i):
        """ 
        Return the information for token i
        """
        assert i < len(self.__tokens), "Token %d requested from list of length %d" % (i, len(self.__tokens))
        return self.__tokens[i]
    
    def tokenString(self):
        """
        Return the tokenized text as a string
        """
        tokenWords = [t.word for t in self.tokens()]
        return " ".join(tokenWords)
    
    
class TokenInfo():
    '''
    Provides methods to access the information returned by the parser.
    Access methods for individual tokens. 
    '''
    def __init__(self, xml):
        '''
        Interpret information returned by the parser
        '''
        assert xml.tag == TAG_TOKEN, "Not token element"
        self.word = xml.find(TAG_WORD).text
        
        try:
            self.lemma = xml.find(TAG_LEMMA).text.lower() # lose case info
        except AttributeError:
            # no text from the LEMMA tag
            self.lemma = None
            
        try:
            self.POS = xml.find(TAG_POS).text
        except AttributeError:
            self.POS = None
            
        try:
            self.NER = xml.find(TAG_NER).text
        except AttributeError:
            self.NER = None
        
        self.index = int(xml.attrib.get(ATTRIB_ID))-1 # start counts at zero, like Python
        charStart = int(xml.find(TAG_CHAR_BEGIN).text)
        charEnd = int(xml.find(TAG_CHAR_END).text)
        self.range = ((charStart-1, charEnd-1)) # start counts at zero, like Python

        
        
class CorefInfo():
    '''
    Provides methods to access the coreference information returned by the parser.
    '''
    def __init__(self, xml):
        '''
        Interpret information returned by the parser
        '''
        assert xml.tag == TAG_COREF, "Not coref element"
        self.__mentions = [ CorefMentionInfo(et) for et in xml.findall(TAG_COREF_MENTION) ]
        representatives = [ m for m in self.mentions() if m.representative ]
        assert len(representatives) == 1, "Can't find single representative mention"
        self.__representative = representatives[0]


    def mentions(self):
        """ Returns the list of mentions  """
        return self.__mentions

    def representative(self):
        """ Returns the representative mention  """
        return self.__representative
    
    def involvesSentence(self, s):
        """ Returns true if there is a mention in this coreference involving sentence s """
        for m in self.__mentions:
            if m.sentence == s: return True
        return False 
    

class CorefMentionInfo():
    '''
    Provides attributes to access the coreference mention information returned by the parser.
    '''
    def __init__(self, xml):
        '''
        Interpret information returned by the parser
        '''
        assert xml.tag == TAG_COREF_MENTION, "Not coref mention element"
        # change numbering to 0 -- (end-1) to match python indexing
        self.sentence = int(xml.find("sentence").text) - 1
        self.start = int(xml.find("start").text) - 1
        self.end = int(xml.find("end").text) - 1
        self.head = int(xml.find("head").text) - 1
        if "representative" in xml.keys():
            self.representative = True
        else:
            self.representative = False


if __name__ == '__main__':
    text = "Hello world.  \n\n It is so beautiful"
    result = parseText(text)
    # print "Result", result
    info = DocInfo(result)
    print info
    


