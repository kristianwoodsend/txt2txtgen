"""
Investigation how to get sync grammar to relate sentences to highlights
"""


from config import Config
from parse import POSTagger, PhraseDependencyTree
from nlputils import NltkUtils
from features import ExtractFeatures
from utils import ListFiles
from tasks import CNNAssessmentFiles, BBCCaptionFilelist, DUC04Filelist
from summarize import WriteHighlights
from features.FeatureList import *
from nlputils import TfIdf
from nlputils.TfIdf import CorpusFreqDist
import nltk.probability
import cPickle as pickle
import sys, os, codecs


# all the core functions of QG
from SyncTreeGrammar import *
import SplitSentences
from SplitSentences import *


PRINT_DEBUG = False
PRINT_INFO = False

graphvizDir = Config.GRAPHVIZ_DIR
FORMAT="ps"
GRAPHVIZ_EXTRA = False
MIN_PHRASE_SIZE = 1


# Simplified sentence examples
# this one is not a good example. the parser uses (PP for NP(example B and F))
f1="Some countries , including Britain and France , are in Europe ."
s1a="Some countries , for example Britain and France , are in Europe ."
s1b="Some countries are in Europe ."

# working
f2="The Nearctic Ecozone includes most of North America ."
s2="Most of North America is in the Nearctic Ecozone ."

# "for example" not parsing correctly
f3="Fish like cod live in the sea ."
s3="Fish , for example cod , live in the sea ."

# working
f4="Carpets are like rugs ."
s4="Carpets are similar to rugs ."

# active / passive VPs not recognised as different
f5="He is known as Bob ."
s5="People know him as Bob ."

# not adding initial NP
f6="It is considered a good thing ."
s6="Many people think it is a good thing ."

# active and passive VPs are not recognised as different
f7="It is made of metal ."
s7="There is metal in it ."

# active and passive forms of VPs are not recognised as different
f8="It is used for talking ."
s8="We use it for talking ."

f9="The name given to these islands is Hebrides ."
s9="The name which we give to these islands is Hebrides ."

# structure seems too deep to capture
f10="Planets are divided into three sorts ."
s10="There are three sorts of planets ."

# matching the VP lower down, not the relative clause
f11="The man walking past the door was Bob ."
s11="The man who was walking past the door was Bob ."

f12="The man given the letter was Bob ."
s12="Bob got the letter ."

# OK
f13="Antigua and Barbuda is an island nation located in the eastern Caribbean Sea ."
s13="Antigua and Barbuda is an island nation in the eastern Caribbean Sea ."

# advb clause buried in VP that is already used, so it is not moving 
# target "the chalk" clause is S, but no S in the source at the correct level
f14="The chalk comes out of the eraser so it can be used again ."
s14="Because the chalk comes out of the eraser , it can be used again ."

# not working correctly
# system is matching the wrong "can" words
f15="Since we can use geometry to describe geometrical shapes , we can work out angles ."
s15="Because we can use geometry to describe geometrical shapes , we can work out angles ."

# working --- needed equivalent parent node matching
f16 ="A book with such a cover is a paperback ."
s16a="A book with this sort of cover is a paperback ."
s16b="A book with this type of cover is a paperback ."

f17 ="John Brown used to live in London , but now he lives in York ."
# almost learnt. "used to live" --> "lived", checks "used to", but doesn't include "in the past"
s17a="In the past , John Brown lived in London ."
# this is learnt, with "used to live" --> "lived", because "Before" triggers substitutions
s17b="Before , John Brown lived in London ."
# this one OK
s17c="Now , he lives in York ."

f18="As a boy , John Brown would go fishing in the river ."
s18="When he was a boy , John Brown often went fishing in the river ."




########
# examples from simple-english.txt

f20 ="John Smith walked his dog and later petted Mary 's cat ."
s20a="John Smith walked his dog ."
s20b="Later , he petted Mary 's cat ."
s20c="Later , John petted Mary 's cat ."


f21="John Smith walked his dog ."
s21="John Smith walked his dog ."

f22="John Smith walked his dog to the supermarket ."
s22="John Smith walked to the supermarket with his dog ."

# mostly working --- parser puts later at the same level as but
f23="John Smith walked his dog but later he was tired ."
s23a="John Smith walked his dog ."
s23b="Later , he was tired ."

# John Smith walked his big , hairy dog , Bluto , to the supermarket on Main Street .
# Later , he was so tired that he collapsed onto his bed exhausted .
# John Smith walked his dog to the supermarket because he was hungry .

# getting confused with lexical identity links. Structure may be too complex
f25="John Smith , who was very tired , walked his dog to the supermarket because he was hungry but he returned to his home still hungry and even more tired because the market was closed ."
s25a="John Smith was very tired ."
s25b="Nevertheless , he walked his dog to the supermarket because he was hungry ." 
s25c="But the market was closed ."
s25d="So he returned to his home still hungry and even more tired ."

f26="John Smith walked his dog to the supermarket where he thought he might buy some apples , but Mary Jones , who considered herself superior to John ( although many people believed that she did n't have any reason to feel that way ) , arrived first and spitefully bought the remaining three apples and so John , who was mad as hell at Mary by this time , had to go home hungry anyway ."
s26a="John Smith walked his dog to the supermarket ."
s26b="He thought he might buy some apples ."
s26c="But Mary Jones arrived first and bought the remaining three apples ." 
s26d="She did this just for spite ."
s26e="( Mary considered herself superior to John ."
s26f="However , many people believed that she had no reason to feel that way . )" 
s26g="By this time however , John was mad as hell at Mary ." 
s26h="But he had to go home hungry anyway ."

# working
f27="John Smith walked his dog and later petted Mary 's cat ."
f27a="John Smith , a man , walked his dog and later petted Mary 's cat ."
f27b="John Smith walked his dog and afterwards met Mary ."
s27a="John Smith walked his dog ."
s27b="Later , he petted Mary 's cat ."
s27c="Later , John petted Mary 's cat ."
s27d="He met Mary ."
s27e="He met Mary later ."

f28="John Smith liked to walk his dog ; but today , the dog was sick ."
s28a="John Smith liked to walk his dog ."
s28b="Today however , the dog was sick ."

# conjunction OK
f29="John Smith walked his dog but he did n't like it ."
s29a="John Smith walked his dog ." 
s29b="But he did n't like it ."

# Swapping of NPs in main and subordinate clauses creating complicated rules
f30="John Smith walked his dog even though he was very tired ."
f30a="John Smith walked his dog , and as a result he was very tired ."
f30b="John Smith walked his dog because the dog needed exercise ."
s30a="John Smith was very tired ."
s30b="Even so , he walked his dog ."
s30c="John Smith walked his dog ."
s30d="But he was very tired ."
s30e="However , he was very tired ."
s30f="Even so , he was very tired ."
s30g="The dog needed exercise ."
s30h="So John Smith walked his dog ."
s30i="Hence he was very tired ."

# confusing set of sentences
# two uses of "angry", but some rules coming out
f31="John Smith walked his dog , which made him angry because the dog always cut into on-coming traffic , which , in turn , made the drivers angry at John , not the dog ."
s31a="John Smith was angry while walking his dog ."
s31b="This was because the dog would always cut into on-coming traffic."
s31c="This , in turn , made the drivers irritated at John , not the dog ."

f32="John Smith , who was very tired , walked his dog ."
f32a="John Smith ( a man ) , who was very tired , walked his dog ."
s32a="John Smith was very tired ." 
s32b="He walked his dog ."
s32c="John Smith walked his dog ."

# can't match tired with tired: one is VBN, one JJ
f33="John Smith , very tired , walked his dog ."
s33a="John Smith was very tired ." 
s33b="He walked his dog ."

# able to pull out appos to separate sentence
f34="John Smith , an Irishman , walked his dog ."
s34a="John Smith was an Irishman ." 
s34b="He walked his dog ."

# OK
f35="John , very emotional , walked his dog ."
s35a="John was very emotional ." 
s35b="He walked his dog ."
s35c="John walked his dog ."

f36="John was very emotional and walked his dog ."
s36a="John was very emotional ." 
s36b="He walked his dog ."
s36c="John walked his dog ."

# to test recurring structures are linked properly
f37="John , a man of the south of the country , walked his dog ."
s37a="John went to the south of the country ." 

f39="John visits the second-largest city in Greece and the capital of the region of Macedonia ."
s39a="John visits the second-largest city in Greece ."
s39b="John visits the capital of the region of Macedonia ."

f40="Thessaloniki is the second-largest city in Greece and the capital of the region of Macedonia ."
f40a="Thessaloniki , the second-largest city in Greece , is the capital of the region of Macedonia ."
f40b="Thessaloniki is the second-largest city in Greece , and is the capital of the region of Macedonia ."
s40a="Thessaloniki is the second-largest city in Greece ."
s40b="It is the capital of the region of Macedonia ."
s40c="Thessaloniki is the capital of the region of Macedonia ."

f41=u"Its honorific title is Symprot\xc3vousa , literally `` co-capital '' , a reference to its historical status as the Symvasil\xc3vousa or `` co-reigning '' city of the Byzantine Empire , alongside Constantinople ."
s41a=u"Its honorific title is Symprot\xc3vousa ."
s41b=u"It is literally `` co-capital ''."
s42c="It is a reference to its historical status as the Symvasil\xc3vousa or `` co-reigning '' city of the Byzantine Empire , alongside Constantinople ."



# not working: cannot generate 3 sentences from the one node
f43=u"The city hosts an annual International Trade Fair , the International Thessaloniki Film Festival , and the largest bi-annual meeting of the Greek diaspora ."
s43a=u"The city hosts an annual International Trade Fair ."
s43b=u"It hosts the International Thessaloniki Film Festival ."
s43c=u"It also hosts the largest bi-annual meeting of the Greek diaspora ."

f44=u"Thessaloniki is home to numerous notable Byzantine monuments , including the Paleochristian and Byzantine monuments of Thessalonika , a UNESCO World Heritage Site , as well as several Ottoman and Sephardic Jewish structures ."
s44a=u"Thessaloniki is home to numerous notable Byzantine monuments ."
s44b=u"These include the Paleochristian and Byzantine monuments of Thessalonika , a UNESCO World Heritage Site , as well as several Ottoman and Sephardic Jewish structures ."

u"""
Its honorific title is (Symprot\xc3vousa), literally `` co-capital '', a reference to its historical status as the (Symvasil\xc3vousa) or `` co-reigning '' city of the Byzantine Empire, alongside Constantinople.
According to the 2001 census, the municipality of Thessaloniki had a population of 363,987, its Urban Area 800,764 and the Larger Urban Zone (LUZ) of Thessaloniki has an estimated 995,766 residents.
The city hosts an annual International Trade Fair, the International Thessaloniki Film Festival, and the largest bi-annual meeting of the Greek diaspora.
Thessaloniki is home to numerous notable Byzantine monuments, including the Paleochristian and Byzantine monuments of Thessalonika, a UNESCO World Heritage Site, as well as several Ottoman and Sephardic Jewish structures.
"""

f45="Grebes are small to medium-large in size , have lobed toes , and are excellent swimmers and divers ."
s45a="Grebes are small to medium-large in size ."
s45b="Grebes have lobed toes ."
s45c="Grebes are excellent swimmers and divers ."

f46="However , although they can run for a short distance , they are prone to falling over , since they have their feet placed far back on the body ."
f46a="They are prone to falling over often , since they have their feet placed far back on the body ."
s46a="They can run for a short distance ."
s46b="However , they are prone to falling over ."
s46c="They have their feet placed far back on the body ."
s46d="This is because they have their feet placed far back on the body ."
s46e="They are prone to falling over often ."



f47="Cancerous cells are often quite weak but since the cancer is actually a part of the body , the body will not attack it even though often it could easily kill it ."
s47a="Cancerous cells are often quite weak ."
s47b="Since the cancer is actually a part of the body , the body will not attack it , even though the cancer often could easily kill the body ."

# the second of the two tokens "cancer" is not getting linked, stopping PRN from being removed
f48="Another difficulty in treating cancer is that there are many different types of cancer -LRB- each have their own symptoms and causes -RRB- ."
s48a="Another hard problem in treating cancer is that there are many different types of cancer ."
s48b="Each have their own symptoms and causes ."

# parser erroneously attaches "and now..." too deep to see the "they".
# would need to allow VP->S rules, and assume "they" for this rule to be captured
f49="They also announced three gigs in the UK followed by a full UK tour and now have their own label , Nul Records , set up exclusively to distribute Futureheads material ."
s49a="They also announced three gigs in the UK followed by a full UK tour ."
s49b="They now have their own label , Nul Records , set up exclusively to distribute Futureheads material ."


# Hoffman
f60="In 1960, Hoffman landed a role in an off-Broadway production and followed with a walk-on role in a Broadway production in 1961 ."
f61="Hoffman then studied at the famed Actors Studio and became a dedicated method actor ."






# pairs = [ (f30,s30a), (f30,s30b) ]
# pairs = [ (f20, s20a), (f20, s20b), (f20, s20c) ]
# pairs = [ (f27a, s27a), (f27a, s27b) ]
pairs = [ (f1, s1a), (f1, s1b), (f2, s2), (f3, s3), (f4, s4) ]
#pairs = [ (f5, s5), (f6, s6), (f7, s7), (f8, s8), (f9, s9) ]
#pairs = [ (f10, s10), (f11, s11), (f12, s12), (f13, s13), (f14, s14) ]
#pairs = [ (f15, s15), (f16, s16a), (f16, s16b), (f17, s17a), (f17, s17b), (f17, s17c) ]

# all of the pairs
pairs = [ (f30,s30a), (f30,s30b), (f20, s20a), (f20, s20b), (f20, s20c), 
         (f27a, s27a), (f27a, s27b), (f1, s1a), (f1, s1b), (f2, s2), 
         (f3, s3), (f4, s4), (f5, s5), (f6, s6), (f7, s7), (f8, s8), 
         (f9, s9), (f10, s10), (f11, s11), (f12, s12), (f13, s13), (f14, s14),
         (f15, s15), (f16, s16a), (f16, s16b), (f17, s17a), (f17, s17b),
         (f17, s17c), (f18, s18) ]



def investigate(doc):
    investigateSinglePairs(doc)
    # investigateSentenceSplittingUsingSP(doc)
    # investigateSentenceSplittingUsingNodeAndSentence(doc)
    #applySplitting(doc)
    
    
def investigateSinglePairs(doc):
    fullResultsList = []
    count = 0
    
    for currentSentencePair in pairs:
        tText1 = createTree(currentSentencePair[0],doc)
        tHighlight1 = createTree(currentSentencePair[1],doc)
        
        if False:
            print
            print "Source text tree:"
            print tText1.pprint()
            print
            print "Target text tree:"
            print tHighlight1.pprint()
        
        results = syncGrammar( tText1, tHighlight1 )
        fullResultsList.extend(results)
        
        for s1,t1 in results:
            print s1,"\t",t1
            r = SyncGrammarRule(s1,t1)
            print r
            print
            
        #printRulesAndExamples(results)
        #raise SystemExit
        count += 1
        # if count > 1: break
            
    
    
    singleSRuleset = qtsg.SyncTreeGrammar._removeDuplicateQSGRules(fullResultsList)
    print "\nConsolidating single-sentence grammar set"
    for  r in singleSRuleset:
        print r
        print 
        
    print
    print "Sync grammar generation completed"
    printResultsListInfo( fullResultsList )


#sentenceSplitPairs = [ (f23, s23a, s23b) ]
sentenceSplitPairs = [ (f25, s25a, s25b) ]
#sentenceSplitPairs = [ (f25, s25b, s25c) ]
#sentenceSplitPairs = [ (f27, s27a, s27b) ]
#sentenceSplitPairs = [ (f27b, s27a, s27e) ]
#sentenceSplitPairs = [ (f28, s28a, s28b) ]
#sentenceSplitPairs = [ (f30a, s30c, s30i) ]
#sentenceSplitPairs = [ (f30b, s30c, s30g) ]
#sentenceSplitPairs = [ (f30b, s30g, s30h) ]
#sentenceSplitPairs = [ (f32, s32a, s32b) ]
#sentenceSplitPairs = [ (f32, s32a, s32c) ]
#sentenceSplitPairs = [ (f34, s34a, s34b) ]
#sentenceSplitPairs = [ (f35, s35a, s35c) ]
#sentenceSplitPairs = [ (f36, s36a, s36b) ]
#sentenceSplitPairs = [ (f39, s39a, s39b) ]
#sentenceSplitPairs = [ (f40a, s40a, s40b) ]
#sentenceSplitPairs = [ (f40, s40a, s40c) ]
#sentenceSplitPairs = [ (f40a, s40a, s40c) ]
#sentenceSplitPairs = [ (f40a, s40c, s40a) ]
#sentenceSplitPairs = [ (f43, s43a, s43b) ]
#sentenceSplitPairs = [ (f43, s43b, s43c) ]
#sentenceSplitPairs = [ (f44, s44a, s44b) ]
#sentenceSplitPairs = [ (f45, s45a, s45b) ]
#sentenceSplitPairs = [ (f45, s45b, s45c) ]
#sentenceSplitPairs = [ (f46, s46a, s46b) ]
#sentenceSplitPairs = [ (f46, s46b, s46c) ]
#sentenceSplitPairs = [ (f46, s46b, s46d) ]
#sentenceSplitPairs = [ (f46, s46a, s46b),(f46, s46b, s46c) ]
#sentenceSplitPairs = [ (f46a, s46e, s46d) ]
#sentenceSplitPairs = [ (f47, s47a, s47b) ]
#sentenceSplitPairs = [ (f48, s48a, s48b) ]
#sentenceSplitPairs = [ (f49, s49a, s49b) ]

#sentenceSplitPairs = [ (f32, s32a, s32c), (f32, s32a, s32c), (f32, s32a, s32c) ]


sentenceSplitPairs = [ (f23, s23a, s23b), (f25, s25a, s25b), (f25, s25b, s25c), 
                      (f27, s27a, s27b), (f27b, s27a, s27e), (f28, s28a, s28b), 
                      (f30a, s30c, s30i), (f30b, s30c, s30g), (f30b, s30g, s30h), 
                      (f32, s32a, s32b), (f32, s32a, s32c), (f34, s34a, s34b), 
                      (f35, s35a, s35c), (f36, s36a, s36b), (f39, s39a, s39b), 
                      (f40a, s40a, s40b), (f40, s40a, s40c), (f40a, s40a, s40c), 
                      (f40a, s40c, s40a), (f43, s43a, s43b), (f43, s43b, s43c), 
                      (f44, s44a, s44b), (f45, s45a, s45b), (f45, s45b, s45c), 
                      (f46, s46a, s46b), (f46, s46b, s46c), (f46, s46b, s46d), 
                      (f46, s46a, s46b),(f46, s46b, s46c), (f46a, s46e, s46d), 
                      (f47, s47a, s47b), (f48, s48a, s48b), (f49, s49a, s49b) ]

def investigateSentenceSplittingUsingSP(doc):
    fullResultsList = []
    count = 0
    
    for s,t1,t2 in sentenceSplitPairs:
        sTree = createTree(s,doc)
        tTree1 = createTree(t1,doc)
        tTree2 = createTree(t2,doc)
        
        # tTree1[0]._rel=PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT
        # tTree2[0]._rel=PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT
        
        tTreePair = PhraseDependencyTree.PhraseDependencyTree("(ROOT)")
        tTreeSP = PhraseDependencyTree.PhraseDependencyTree( "SP", (tTree1[0].copy(), tTree2[0].copy() ) )
        tTreePair.append(tTreeSP)
        tTreePair._rel=PhraseDependencyTree.PhraseDependencyTree.FIXED_DEPENDENT
        tTreeSP._rel="TOP"
        tTreeSP._indPhrase = True
        tTreePair.markPositions()
        
        
        print
        print "Source text tree:"
        print sTree.pprint()
        print
        print "Target text tree:"
        print tTreePair.pprint()
        
        results = syncGrammar( sTree, tTreePair )
        fullResultsList.extend(results)
        #printRulesAndExamples(results)
        
        
        # raise SystemExit
        count += 1
        # if count > 1: break
            
        
    print
    print "Sync grammar generation completed"
    printResultsListInfo( fullResultsList )
    
    print
    print "Full rule list"
    printRules( fullResultsList ) 

def investigateSentenceSplittingUsingNodeAndSentence(doc):
    count = 0
    fullResultsList = []
    fullSingleResultsList = []
    
    for s,t1,t2 in sentenceSplitPairs:
        print "\n------------------"
        print "Src:   ", s
        print "Tgt-1: ", t1
        print "Tgt-2: ", t2
        sTree = createTree(s,doc)
        tTree1 = createTree(t1,doc)
        tTree2 = createTree(t2,doc)
        
        if True:
            print "-----"
            print sTree
            print "-----"
            print tTree1
            print "-----"
            print tTree2
            print "-----"
        
        results, singleResults = qtsg.SplitSentences.syncGrammarSentenceSplit(sTree, tTree1, tTree2)
        fullResultsList.extend(results)
        fullSingleResultsList.extend(singleResults)

    print "splitting results:"
    for (s1,t1,s2,t2,after) in fullResultsList:
        print qtsg.SplitSentences.SplitSentenceRule(s1,t1,s2,t2,after)
        print "---"
        
    print "single results:"
    for  r in fullSingleResultsList:
        print r
        
    # raise SystemExit,"Debugging sentence splitting"

    # create single sentence rules
    singleSResults=[]
    for s,t1,t2 in sentenceSplitPairs:
        print "\n------------------"
        print "Src:   ", s
        print "Tgt-1: ", t1
        print "Tgt-2: ", t2
        sTree = createTree(s,doc)
        tTree1 = createTree(t1,doc)
        tTree2 = createTree(t2,doc)

        results = syncGrammar( sTree, tTree1 )
        singleSResults.extend(results)
        printResultsListInfo(results)
        results = syncGrammar( sTree, tTree2 )
        singleSResults.extend(results)
        printResultsListInfo(results)
        printResultsListInfo(singleSResults)
        
        
            
        

    print
    print "Sync grammar generation completed. ", len(results), "rules created"
        
    print "Consolidating grammar set"
    ruleset = qtsg.SplitSentences._removeDuplicateQSGRules(fullResultsList)
    for  r in ruleset:
        print r
        print 
    
    singleSRuleset = qtsg.SyncTreeGrammar._removeDuplicateQSGRules(singleSResults)
    print "\nConsolidating single-sentence grammar set"
    for  r in singleSRuleset:
        print r
        print 

    
    
    
    raise SystemExit,"Completed rule generation"
    
        

    
def applySplitting(task, doc):
    raise DeprecationWarning, "no longer in sync with functions"
    sentencesToSplit = (f40b,)
    # sentencesToSplit = (f40b,)
    ruleset = qtsg.SplitSentences.loadQSGRules(task)
    singleSRuleset = qtsg.SyncTreeGrammar.loadQSGRules(task)
    
    for s in sentencesToSplit:
        print "\n------------------"
        print "Src:   ", s
        sTree = createTree(s,doc)
        
        if True:
            print "-----"
            print sTree
            print "-----"
    
        sentenceSplitList=[] # details for each phrase
        # try applying paraphrase splitting from the top down
        topNode, sentenceSplitList = _sentenceSplitParaphrase(sTree, ruleset, singleSRuleset)
        print "Paraphrase with Original, inplace changes:"
        print sTree
        
    ordered = orderSplitSentences(sentenceSplitList)
    
    

    