from nltk.parse import ParserI 
from nltk.tag.api import TaggerI 
import nltk
from subprocess import *
import os, re, tempfile, string, shelve, anydbm, codecs
import copy
from config import Config, Debug
from nlputils import NltkUtils
import PhraseDependencyTree
import bsddb.db

MARK_TOP_SENTENCE = True



def _newTempFile():
    fd, filename = tempfile.mkstemp(prefix='postag-', suffix='.txt')
    return filename

def _writeTempFile(sent):
    filename=_newTempFile()
    fw=codecs.open( filename, 'w+', 'utf-8' )
    for s in sent:
        fw.write(s)
        if (len(s)==0 or not s[-1]=="\n"): fw.write("\n")
    fw.close()
    return filename

# java -mx150m -cp "$scriptdir/stanford-parser.jar:" edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat "$format" $scriptdir/englishPCFG.ser.gz $1
# format="penn,typedDependencies,oneline,wordsAndTags,typedDependenciesCollapsed,latexTree"
SCRIPTDIR = Config.STANFORD_PARSER
COMMANDLINE = 'java -mx1500m -cp "'+SCRIPTDIR+'/stanford-parser.jar:" '
_commandTemplate = string.Template(COMMANDLINE + '$what -outputFormat "$format" -outputFormatOptions "$formatOptions" '
    + '-sentences newline '
    +SCRIPTDIR+'/englishPCFG.ser.gz $file')

NER_DIR = Config.STANFORD_NER_DIR
#_NERcommandTemplate = string.Template(NER_DIR+"/ner.sh $file")
_NERcommandTemplate = string.Template(NER_DIR+"/ner-batch.sh $file")

def _runStanfordParser(cmd):
    #print cmd
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE )
    pipe = proc.stdout
    
    # streamOut = codecs.StreamReader(pipe)
    streamOut = codecs.getreader('utf-8')(pipe)
    return streamOut


def key(s):
    # return s.encode('ascii','replace')
    return s.encode('ascii','replace').strip()
        
def isInCache(sentence, cache):
    """
    Returns true if the sentence is already in the cache
    """
    return (key(sentence) in cache)
     
    
class TextIterator(object):
    """ An iterator through text, provided as a pipe """
    def __init__(self, pipe):
        self._pipe = pipe

    def readlines(self):
        """ Line iterator """
        for line in self._pipe:
            yield line

    def readwords(self):
        """ Word iterator, where words are 
        separated by whitespace.
        Newlines are omitted """
        for line in self._pipe:
            readWordsInLine(line)
    
    def readWordsInLine(self,line):
        """ Word iterator over input line, where words are 
        separated by whitespace.
        """
        wspacere = re.compile(r'\s+')
        words = wspacere.split(line)
        for w in words:
            yield w




class StanfordPennParser(ParserI):
    """
    Uses the Stanford Java-based lexical parser to 
    assign Penn structure to the sentence
    
    The output of the Stanford parser is converted
    into a tree.
    """
    
    cache = None
    
    def __init__(self, doc):
        """
        Initialise parser, open cache
        """
        assert StanfordPennParser.cache, "Cache details not set up"
        self._cache = StanfordPennParser.cache.get(doc)

    def __del__(self):
        self._cache.close()
        

    def parse(self, sentence): 
        """ 
        Runs the Stanford parser on the list of sentences,
        and returns lists of nodes.
        This needs to be taken further to properly parse the sentence.
        """
        delimiter=" "
        # API requires sentence to be a list
        # combine into one string
        if isinstance(sentence,list):
            s = delimiter.join(sentence)
        elif isinstance(sentence,basestring):
            s = sentence
        else:
            assert False, "Sentence input is not a list or string"
            
        # Need to remove any final newline character
        # as it causes the parser problems
        nlpos = s.find('\n')
        assert (nlpos==-1 or nlpos==len(s)-1), "Newline present in sentence"
        if ( nlpos > 0 ): s = s[:nlpos]
        
        # use cache if possible
        try:
            taggedSent = self._cache[key(s)]
            if (Debug.PRT_Parsers>1): print "StanfordPennParser Retrieved from cache"
            if (Debug.PRT_Parsers>2): print "Parsed:\t", taggedSent
        except (KeyError):
            print "StanfordPennParser processing ", s
            filename=_writeTempFile([s])
            cmd = _commandTemplate.substitute(
                what='edu.stanford.nlp.parser.lexparser.LexicalizedParser',
                format='penn',
                formatOptions='', # 'markHeadNodes',
                file=filename)
            # print "cmd:", cmd
            pipe = _runStanfordParser(cmd)
            
            taggedSent=[]
            textIt = TextIterator(pipe)
            for line in textIt.readlines():
                # print line
                # skip blank lines
                if ( len(line) < 2 ):
                    continue
                taggedSent.append(line.strip())
            pipe.close()
            os.remove(filename)
            self._cache[key(s)]=taggedSent
            # print "Written to Penn cache"
        
        tsall="".join(taggedSent)
        t=None
        try:
            t = PhraseDependencyTree.PhraseDependencyTree(tsall)
            t.markPositions()
            t.markHeadWords()
            if MARK_TOP_SENTENCE: t.markTopSentenceNode()
            t.correctTree()
        except (ValueError),e:
            # parsing has failed, so remove from cache
            self._cache.pop(key(s))
            raise e
            
        return t

    def _parseNoValueError(self, sentence): 
        try:
            return self.parse(sentence)
        except ValueError:
            return None


    def batch_parse(self, sents): 
        """ 
        Parse each sentence in the list, as a batch. 
        @rtype: C{list} of L{Tree} 
        """
        if (Debug.PRT_Parsers): print "StanfordPennParser batch parsing"

        sentsForParsing=[]
        for s in sents:
            assert not s[-1]=="\n", "Sentence not clean:" % s
            if key(s) not in self._cache:
                sentsForParsing.append(s)
        if (Debug.PRT_Parsers>1): print "For parsing: ", sentsForParsing
        
        if ( len(sentsForParsing)>0 ):
            filename=_writeTempFile(sentsForParsing)
            cmd = _commandTemplate.substitute(
                what='edu.stanford.nlp.parser.lexparser.LexicalizedParser',
                format='penn',
                formatOptions='', # 'markHeadNodes',
                file=filename)
            # print "cmd:", cmd
            pipe = _runStanfordParser(cmd)
            taggedSent=[]
            taggedSentList=[]
            textIt = TextIterator(pipe)
            for line in textIt.readlines():
                # print line
                # skip blank lines
                if ( len(line) < 2 ):
                    if (Debug.PRT_Parsers>2):
                        print "BLANK LINE"
                        print "Tagged sentence: ", taggedSent
                    # store in cache here
                    taggedSentList.append(taggedSent)
                    taggedSent=[] # start again with next sentence
                    continue
                taggedSent.append(line.strip())
            pipe.close()
            os.remove(filename)
            
            # check that we have the right number of parsed sentences
            if ( not len(sentsForParsing) == len(taggedSentList) ):
                raise ValueError, "StanfordPennParser not parsed the correct number of sentences"
                
            for (s,t) in zip(sentsForParsing,taggedSentList):
                if (Debug.PRT_Parsers>2):
                    print "Original:", s
                    print "Parse:   ", t
                try:
                    self._cache[key(s)]=t
                except bsddb.db.DBRunRecoveryError, e:
                    print e
                    print "using key: \t", key(s)
                    print "setting to:\t", t
                    raise
                 

        # Use parse() function to generate the trees - 
        # Stanford parser results should be in the cache now
        return [self.parse(sent) for sent in sents]
        

class StanfordDependencyParser(ParserI):
    """
    Uses the Stanford Java-based lexical parser to 
    assign dependency structure to the sentence
    
    """
    
    def __init__(self, doc):
        """
        Initialise parser, open cache
        """
        assert StanfordDependencyParser.cache, "Cache details not set up"
        self._cache = StanfordDependencyParser.cache.get(doc)

    def __del__(self):
        self._cache.close()


    def parse(self, sentence): 
        """ 
        Runs the Stanford parser on the list of sentences,
        and returns lists of nodes.
        This needs to be taken further to properly parse the sentence.
        @return: a L{Tree} representing the dependency structure. 
        """
        dp = self.parseToDepGraph(sentence)
        return dp.tree()

    def _parse_NoValueError(self, sentence): 
        try:
            return self.parse(sentence)
        except ValueError:
            return None
        

        
    def batch_parse(self, sents): 
        """ 
        Parse each sentence in the list, as a batch. 
        @rtype: C{list} of L{Tree} 
        """
        if (Debug.PRT_Parsers): print "StanfordDependencyParser batch parsing"
        sentsForParsing=[]
        for s in sents:
            if not isInCache(s, self._cache):
                sentsForParsing.append(s)
                if (Debug.PRT_Parsers>1): print "Not in StanfordDependencyParser cache", s
        if (Debug.PRT_Parsers>1): print "For parsing: ", sentsForParsing

        try:
            taggedSentList = self._do_batch_parse(sentsForParsing)
            for (s,t) in zip(sentsForParsing,taggedSentList):
                if (Debug.PRT_Parsers>1):
                    print "Original:", s
                    print "Parse:   ", t
                self._cache[key(s)]=t
        except ValueError:
            # batch failed, try single line at a time
            if len(sentsForParsing)>1:
                for s in sentsForParsing:
                    try:
                        taggedSentList = self._do_batch_parse((s,))
                        t=taggedSentList[0]
                        if (Debug.PRT_Parsers>1):
                            print "Original:", s
                            print "Parse:   ", t
                        self._cache[key(s)]=t
                    except ValueError:
                        # individual parse failed, not sure what we want to do here
                        # raise
                        # raise SystemExit, "StanfordDepParser sentence not in cache"
                        pass
                

        # Use parse() function to generate the trees - 
        # Stanford parser results should be in the cache now
        return [self._parse_NoValueError(sent) for sent in sents]


    def _do_batch_parse(self, sentsForParsing):
        """
        Function to actually call the dependency parser
        """
        if ( len(sentsForParsing)==0 ): return []
    
        filename=_writeTempFile(sentsForParsing)
        cmd = _commandTemplate.substitute(
            what='edu.stanford.nlp.parser.lexparser.LexicalizedParser',
            # format='typedDependencies',
            format='typedDependenciesCollapsed', # this removes cycles
            formatOptions='',
            file=filename)
        # print "cmd:", cmd
        pipe = _runStanfordParser(cmd)
        taggedSent=[]
        taggedSentList=[]
        textIt = TextIterator(pipe)
        for line in textIt.readlines():
            # print line
            # skip blank lines
            if ( len(line) < 2 ):
                if (Debug.PRT_Parsers>2):
                    print "BLANK LINE"
                    print "Tagged sentence: ", taggedSent
                # store in cache here
                taggedSentList.append(taggedSent)
                taggedSent=[] # start again with next sentence
                continue
            taggedSent.append(line.strip())
        pipe.close()
        os.remove(filename)
            
        # check that we have the right number of parsed sentences
        if ( not len(sentsForParsing) == len(taggedSentList) ):
            raise ValueError, "StanfordDependencyParser not parsed the correct number of sentences"
        return taggedSentList        


    def parseToDepGraph(self, sentence): 
        """ 
        Runs the Stanford parser on the list of sentences,
        and returns lists of nodes.
        This needs to be taken further to properly parse the sentence.
        @return: a L{NltkUtils.DependencyGraph} representing the dependency structure. 
        """ 
        # API requires sentence to be a list
        # combine into one string
        delimiter=" "
        if isinstance(sentence,list):
            s = delimiter.join(sentence)
        elif isinstance(sentence,basestring):
            s = sentence
        else:
            assert True, "Sentence input is not a list or string"
            
        # Need to remove any final newline character
        # as it causes the parser problems
        nlpos = s.find('\n')
        assert (nlpos==-1 or nlpos==len(s)-1), "Newline present in sentence"
        if ( nlpos > 0 ): s = s[:nlpos]
        
        # use cache if possible
        try:
            parserOutput = self._cache[key(s)]
            if (Debug.PRT_Parsers>1): print "StanfordDependencyParser Retrieved from cache"
        except (KeyError):
            if (Debug.PRT_Parsers>2): print "StanfordDependencyParser processing ", s
            filename=_writeTempFile([s])
            cmd = _commandTemplate.substitute(
                what='edu.stanford.nlp.parser.lexparser.LexicalizedParser',
                # format='typedDependencies',
                format='typedDependenciesCollapsed', # this removes cycles
                formatOptions='',
                file=filename)
            pipe = _runStanfordParser(cmd)
            
            parserOutput=[]
            textIt = TextIterator(pipe)
            for line in textIt.readlines():
                # skip blank lines
                if ( len(line) < 2 ):
                    continue
                parserOutput.append(line)
            pipe.close()
            os.remove(filename)
            self._cache[key(s)]=parserOutput
            # print "Written to Dep cache: ", parserOutput
            
        # convert into dependency graph
        if (Debug.PRT_Parsers>2): print "Parser output: ",parserOutput 
        dp = NltkUtils.DependencyGraph(None)
        try:
            dp.parseDeps(parserOutput)
        except (ValueError), e:
            # parsing has failed, so remove from cache
            self._cache.pop(key(s))
            raise e
        return dp
        

class StanfordPOSTagger(TaggerI):
    """
    Uses the Stanford Java-based lexical parser to 
    assign Penn Treebank tags to each token
    """
    cache = None
    
    def __init__(self, doc):
        """
        Initialise parser, open cache
        """
        assert StanfordPOSTagger.cache, "Cache details not set up"
        self._cache = StanfordPOSTagger.cache.get(doc)

    def __del__(self):
        self._cache.close()


    def isInCache(self, sentence):
        """
        Returns true if the sentence is already in the cache
        """
        return (key(sentence) in self._cache)
     
     
    def tag(self, sentence):
        """
        Use this to tag each sentence on its own.
        Will retrieve previously-tagged version from cache
        if it is available
        """
        if (sentence[-1]=="\n"): sentence = sentence[:-1]
        # use cache if possible
        try:
            taggedSent = self._cache[key(sentence)]
            if (Debug.PRT_Parsers>1): print "StanfordPOSTagger Retrieved from POS cache"
        except (KeyError):
            if (Debug.PRT_Parsers>1): print "StanfordPOSTagger processing ", sentence
            taggedSent = self.batch_tag_2( [sentence] )[0]
            self._cache[key(sentence)]=taggedSent
            # print "Written to POS cache"
            
        # Parser can add full stop to abbreviation
        if (not len(sentence.split())<=len(taggedSent)):
            if (Debug.PRT_Parsers>2):
                print len(sentence.split()), sentence
                print len(taggedSent), taggedSent
            
            self._cache.pop(key(sentence))
            # raise ValueError, "Tagged sentence doesn't have enough tokens"
        
        return taggedSent

    
    def batch_tag_2(self, sentences): 
        """ 
        Runs the Stanford parser on the list of sentences,
        and returns lists of (token,tag) pairs.
        """ 
        filename=_writeTempFile(sentences)
        cmd = _commandTemplate.substitute(
            what='edu.stanford.nlp.parser.lexparser.LexicalizedParser',
            format='wordsAndTags',
            formatOptions='',
            file=filename)
        pipe = _runStanfordParser(cmd)
        
        taggedSent=[]
        textIt = TextIterator(pipe)
        for line in textIt.readlines():
            # skip blank lines
            if ( len(line) < 2 ):
                continue
            taggedLine=[]
            taggedSent.append(taggedLine)
            for w in textIt.readWordsInLine(line):
                # Final newline? also added as token
                tup = nltk.tag.str2tuple(w)
                if ( tup[1] is not None ):
                    taggedLine.append(tup)
                # old code, before using str2tuple
                #if ( w.count('/') ):
                #    taggedLine.append( tuple(w.split('/') ) )
        pipe.close()
        os.remove(filename)
        return taggedSent

    def batch_tag(self, sentences): 
        """ 
        Runs the Stanford parser on the list of sentences,
        and returns lists of (token,tag) pairs.
        """ 
        if (Debug.PRT_Parsers): print "StanfordPOSTagger batch parsing"
        sentsForParsing=[]
        for s in sentences:
            if (s[-1]=="\n"): s = s[:-1]
            if key(s) not in self._cache:
                sentsForParsing.append(s)
                if (Debug.PRT_Parsers>2): print "NOT IN CACHE"
        if (Debug.PRT_Parsers>1): print "For parsing: ", sentsForParsing
        
        if ( len(sentsForParsing)>0 ):
            filename=_writeTempFile(sentsForParsing)
            cmd = _commandTemplate.substitute(
                what='edu.stanford.nlp.parser.lexparser.LexicalizedParser',
                format='wordsAndTags',
                formatOptions='',
                file=filename)
            pipe = _runStanfordParser(cmd)
            taggedSent=[]
            taggedSentList=[]
            textIt = TextIterator(pipe)
            for line in textIt.readlines():
                if (Debug.PRT_Parsers>3): print line
                # skip blank lines
                if ( len(line) < 2 ):
                    if (Debug.PRT_Parsers>2): 
                        print "BLANK LINE"
                        print "Tagged sentence: ", taggedSent
                    # store in cache here
                    taggedSentList.append(taggedSent)
                    taggedSent=[] # start again with next sentence
                    continue
                for w in textIt.readWordsInLine(line):
                    # Final newline? also added as token
                    tup = nltk.tag.str2tuple(w)
                    if ( tup[1] is not None ):
                        taggedSent.append(tup)
            pipe.close()
            os.remove(filename)
            
            # check that we have the right number of parsed sentences
            if ( not len(sentsForParsing) == len(taggedSentList) ):
                raise ValueError, "StanfordPOSTagger not tagged the correct number of sentences"
                
            for (s,t) in zip(sentsForParsing,taggedSentList):
                if (Debug.PRT_Parsers>2): 
                    print "Original:", s
                    print "Parse:   ", t
                self._cache[key(s)]=t

        # Use tag() - results should be in the cache now
        return [self.tag(sent) for sent in sentences]


class StanfordNERTagger(TaggerI):
    """
    Uses the Stanford Java-based named-entity recognizer.
    Default classifier is used.
    Identifies named entities as Person, Organization, Place.
    """
    
    def __init__(self, doc):
        """
        Initialise parser, open cache
        """
        assert StanfordNERTagger.cache, "Cache details not set up"
        self._cache = StanfordNERTagger.cache.get(doc)

    def __del__(self):
        self._cache.close()


    def tag(self, sentence):
        """
        Use this to tag each sentence on its own.
        Will retrieve previously-tagged version from cache
        if it is available
        """
        # use cache if possible
        try:
            if (sentence[-1]=="\n"): sentence = sentence[:-1]
            taggedSent = self._cache[key(sentence)]
            #print "StanfordNERTagger Retrieved from NER cache", taggedSent
        except (KeyError):
            if (Debug.PRT_Parsers): print "StanfordNERTagger processing ", sentence
            filename=_writeTempFile([sentence])
            cmd = _NERcommandTemplate.substitute(
                file=filename)
            # print cmd
            pipe = _runStanfordParser(cmd)
            
            taggedSent=pipe.readline()
            pipe.close()
            os.remove(filename)
            #TODO: put in proper checking of parser
            if (len(taggedSent)==0): 
                raise ValueError, "Nothing back from NER parser"
            self._cache[key(sentence)]=taggedSent
            # print "Written to NER cache: ", taggedSent
            
        # separate words and tags into tuples
        try:
            textIt = TextIterator(None)
            taggedLine=[]
            for w in textIt.readWordsInLine(taggedSent):
                # Final newline? also added as token
                tup = nltk.tag.str2tuple(w)
                if ( tup[1] is not None ):
                    taggedLine.append(tup)
            # NER turns abbreviations into separate . tokens
            if (not len(sentence.split())<=len(taggedLine)):
                print len(sentence.split()), sentence
                print len(taggedLine), taggedLine
                raise ValueError, "Tagged sentence doesn't have enough tokens"
        except (ValueError),e:
            pass
            if (True): # remove misparsed sentences to try again another time
                # parsing has failed, so remove from cache
                self._cache.pop(key(sentence))
                raise e
        return taggedLine

    def batch_tag(self, sentences): 
        """ 
        Runs the Stanford parser on the list of sentences,
        and returns lists of (token,tag) pairs.
        """ 
        if (Debug.PRT_Parsers): print "StanfordNERTagger batch parsing"
        sentsForParsing=[]
        for s in sentences:
            if (s[-1]=="\n"): s = s[:-1]
            if key(s) not in self._cache:
                sentsForParsing.append(s)
                if (Debug.PRT_Parsers>2): print "NOT IN CACHE"
        if (Debug.PRT_Parsers>1): print "For parsing: ", sentsForParsing
        
        if ( len(sentsForParsing)>0 ):
            filename=_writeTempFile(sentsForParsing)
            cmd = _NERcommandTemplate.substitute(
                file=filename)
            pipe = _runStanfordParser(cmd)

            taggedSentList=[]
            textIt = TextIterator(pipe)
            for line in textIt.readlines():
                if (Debug.PRT_Parsers>3): print line
                # skip blank lines
                if ( len(line) < 2 ):
                    if (Debug.PRT_Parsers>2): 
                        print "BLANK LINE"
                    continue
                else:
                    taggedSentList.append(line)
            pipe.close()
            os.remove(filename)
            
            # check that we have the right number of parsed sentences
            if ( not len(sentsForParsing) == len(taggedSentList) ):
                if (Debug.PRT_Parsers>2): 
                    for t in taggedSentList: print "Parse:   ", t
                raise ValueError, "StanfordNERTagger not tagged the correct number of sentences (tagged %d, wanted %d)" % (len(taggedSentList),len(sentsForParsing))  
                
            for (s,t) in zip(sentsForParsing,taggedSentList):
                if (Debug.PRT_Parsers>2): 
                    print "Original:", s
                    print "Parse:   ", t
                self._cache[key(s)]=t

        # Use tag() - results should be in the cache now
        return [self.tag(sent) for sent in sentences]




class StanfordTokenizer:
    @classmethod
    def tokenize(cls, s):
        SCRIPTDIR = Config.STANFORD_PARSER
        COMMANDLINE = 'java -mx1500m -cp "'+SCRIPTDIR+'/stanford-parser.jar:" '
        _commandTemplate = string.Template(COMMANDLINE + 'edu.stanford.nlp.process.DocumentPreprocessor -plainOutput -file $file')
        
        # print "StanfordTokenizer processing ", s
        filename=_writeTempFile([s])
        cmd = _commandTemplate.substitute(file=filename)
        # print "cmd:", cmd
        pipe = _runStanfordParser(cmd)
        
        taggedSent=[]
        textIt = TextIterator(pipe)
        for line in textIt.readlines():
            # print line
            # skip blank lines
            if ( len(line) < 2 ):
                continue
            taggedSent.append(line.strip())
        pipe.close()
        os.remove(filename)
        return taggedSent

 
class StanfordParser(ParserI): 
    """ 
    A processing interface for identifying non-overlapping groups in 
    unrestricted text.  Typically, chunk parsers are used to find base 
    syntactic constituants, such as base noun phrases.  Unlike 
    L{ParserI}, C{ChunkParserI} guarantees that the C{parse} method 
    will always generate a parse. 
    """ 
    # def __init__(self):
    
    def parse(self, sent):
        """ 
        @return: A parse tree that represents the structure of the 
        given sentence, or C{None} if no parse tree is found.  If 
        multiple parses are found, then return the best parse. 
        
        @param sent: The sentence to be parsed 
        @type sent: L{list} of L{string} 
        @rtype: L{Tree} 
        """
        return None
        


if __name__=="__main__":
    print "Running Stanford tagger"
    # t = StanfordPOSTagger()
    s0 = "Jim's uncle's dog , called Bruno , said \" Woof \"."
    s1="Hurricane-force winds up to 90 mph -LRB- 145 kph -RRB- are hampering the rescue operation , which involves a Coast Guard cutter and a C-130 Hercules aircraft ."
    s2="The strong winds have delayed the arrival of several helicopters to help rescue the skipper and crew , said Petty Officer Walter Shinn , a Coast Guard spokesman ."
    
    s3 = "The full height of the right leg of the red table pushes the limit ."
    s4 = "The full height of the red table 's right leg pushes the limit ."
    s5 = "The table leg height pushes the limit ."
    s6 = "The full height of the table leg pushes the limit ."
    
    s = "Winds destroy town , pushing death toll to 100 ."
    s8 = "Death toll pushed to 100 ."
    
    # Penn parser
    if (False):
        t = StanfordPennParser()
        output = t.parse(s1)
        output = t.parse(s2)
        print "Done"
        ss = [ s1, s2 ]
        output2 = t.batch_parse( ss )
        print len(output2)
        print output2[0].leaves()
        print output2[1].leaves()
        # print "Max depth:", output.height()
        # print output.leaves()[0].__class__
        
        # print output[0,0,0].__class__
        # print dir(output[0,0,0])
        # output.draw()
    
    # Dependency parser
    if (True):
        t = StanfordDependencyParser()
        t._cache={}
        Debug.PRT_Parsers=3
        output = t.parse(s)
        print output
        print "Max depth:", output.height()
        output.draw()
    
    # NER tagger
    if (False): 
        t = StanfordNERTagger()
        ss = [ s1, s2 ]
        output2 = t.batch_tag( ss )
        print len(output2)
        print output2[0]
        print output2[1]
        
    

