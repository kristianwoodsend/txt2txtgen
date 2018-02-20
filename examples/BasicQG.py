'''
Created on 22 Jan 2015

@author: kristian
'''

import parse.StanfordCoreNLP
import qtsg.align, qtsg.info, qtsg.SyncTreeGrammar, qtsg.statements
from summarize.Choosers import ChoiceTree, SingleShotChoiceTree


text = "The Inuits used to hunt seals , and traded fur with the Europeans ."
headline = "Inuits trade fur !"
text_parserxml = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet href="CoreNLP-to-HTML.xsl" type="text/xsl"?>
<root>
  <document>
    <sentences>
      <sentence id="1">
        <tokens>
          <token id="1">
            <word>The</word>
            <lemma>the</lemma>
            <CharacterOffsetBegin>1</CharacterOffsetBegin>
            <CharacterOffsetEnd>4</CharacterOffsetEnd>
            <POS>DT</POS>
            <NER>O</NER>
          </token>
          <token id="2">
            <word>Inuits</word>
            <lemma>Inuits</lemma>
            <CharacterOffsetBegin>5</CharacterOffsetBegin>
            <CharacterOffsetEnd>11</CharacterOffsetEnd>
            <POS>NNPS</POS>
            <NER>O</NER>
          </token>
          <token id="3">
            <word>used</word>
            <lemma>use</lemma>
            <CharacterOffsetBegin>12</CharacterOffsetBegin>
            <CharacterOffsetEnd>16</CharacterOffsetEnd>
            <POS>VBD</POS>
            <NER>O</NER>
          </token>
          <token id="4">
            <word>to</word>
            <lemma>to</lemma>
            <CharacterOffsetBegin>17</CharacterOffsetBegin>
            <CharacterOffsetEnd>19</CharacterOffsetEnd>
            <POS>TO</POS>
            <NER>O</NER>
          </token>
          <token id="5">
            <word>hunt</word>
            <lemma>hunt</lemma>
            <CharacterOffsetBegin>20</CharacterOffsetBegin>
            <CharacterOffsetEnd>24</CharacterOffsetEnd>
            <POS>NN</POS>
            <NER>O</NER>
          </token>
          <token id="6">
            <word>seals</word>
            <lemma>seal</lemma>
            <CharacterOffsetBegin>25</CharacterOffsetBegin>
            <CharacterOffsetEnd>30</CharacterOffsetEnd>
            <POS>NNS</POS>
            <NER>O</NER>
          </token>
          <token id="7">
            <word>,</word>
            <lemma>,</lemma>
            <CharacterOffsetBegin>31</CharacterOffsetBegin>
            <CharacterOffsetEnd>32</CharacterOffsetEnd>
            <POS>,</POS>
            <NER>O</NER>
          </token>
          <token id="8">
            <word>and</word>
            <lemma>and</lemma>
            <CharacterOffsetBegin>33</CharacterOffsetBegin>
            <CharacterOffsetEnd>36</CharacterOffsetEnd>
            <POS>CC</POS>
            <NER>O</NER>
          </token>
          <token id="9">
            <word>traded</word>
            <lemma>trade</lemma>
            <CharacterOffsetBegin>37</CharacterOffsetBegin>
            <CharacterOffsetEnd>43</CharacterOffsetEnd>
            <POS>VBD</POS>
            <NER>O</NER>
          </token>
          <token id="10">
            <word>fur</word>
            <lemma>fur</lemma>
            <CharacterOffsetBegin>44</CharacterOffsetBegin>
            <CharacterOffsetEnd>47</CharacterOffsetEnd>
            <POS>NN</POS>
            <NER>O</NER>
          </token>
          <token id="11">
            <word>with</word>
            <lemma>with</lemma>
            <CharacterOffsetBegin>48</CharacterOffsetBegin>
            <CharacterOffsetEnd>52</CharacterOffsetEnd>
            <POS>IN</POS>
            <NER>O</NER>
          </token>
          <token id="12">
            <word>the</word>
            <lemma>the</lemma>
            <CharacterOffsetBegin>53</CharacterOffsetBegin>
            <CharacterOffsetEnd>56</CharacterOffsetEnd>
            <POS>DT</POS>
            <NER>O</NER>
          </token>
          <token id="13">
            <word>Europeans</word>
            <lemma>Europeans</lemma>
            <CharacterOffsetBegin>57</CharacterOffsetBegin>
            <CharacterOffsetEnd>66</CharacterOffsetEnd>
            <POS>NNPS</POS>
            <NER>MISC</NER>
          </token>
          <token id="14">
            <word>.</word>
            <lemma>.</lemma>
            <CharacterOffsetBegin>67</CharacterOffsetBegin>
            <CharacterOffsetEnd>68</CharacterOffsetEnd>
            <POS>.</POS>
            <NER>O</NER>
          </token>
        </tokens>
        <parse>(ROOT (S (NP (DT The) (NNPS Inuits)) (VP (VP (VBD used) (PP (TO to) (NP (NN hunt) (NNS seals)))) (, ,) (CC and) (VP (VBD traded) (NP (NN fur)) (PP (IN with) (NP (DT the) (NNPS Europeans))))) (. .))) </parse>
        <dependencies type="basic-dependencies">
          <dep type="root">
            <governor idx="0">ROOT</governor>
            <dependent idx="3">used</dependent>
          </dep>
          <dep type="det">
            <governor idx="2">Inuits</governor>
            <dependent idx="1">The</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="3">used</governor>
            <dependent idx="2">Inuits</dependent>
          </dep>
          <dep type="prep">
            <governor idx="3">used</governor>
            <dependent idx="4">to</dependent>
          </dep>
          <dep type="nn">
            <governor idx="6">seals</governor>
            <dependent idx="5">hunt</dependent>
          </dep>
          <dep type="pobj">
            <governor idx="4">to</governor>
            <dependent idx="6">seals</dependent>
          </dep>
          <dep type="cc">
            <governor idx="3">used</governor>
            <dependent idx="8">and</dependent>
          </dep>
          <dep type="conj">
            <governor idx="3">used</governor>
            <dependent idx="9">traded</dependent>
          </dep>
          <dep type="dobj">
            <governor idx="9">traded</governor>
            <dependent idx="10">fur</dependent>
          </dep>
          <dep type="prep">
            <governor idx="9">traded</governor>
            <dependent idx="11">with</dependent>
          </dep>
          <dep type="det">
            <governor idx="13">Europeans</governor>
            <dependent idx="12">the</dependent>
          </dep>
          <dep type="pobj">
            <governor idx="11">with</governor>
            <dependent idx="13">Europeans</dependent>
          </dep>
        </dependencies>
        <dependencies type="collapsed-dependencies">
          <dep type="root">
            <governor idx="0">ROOT</governor>
            <dependent idx="3">used</dependent>
          </dep>
          <dep type="det">
            <governor idx="2">Inuits</governor>
            <dependent idx="1">The</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="3">used</governor>
            <dependent idx="2">Inuits</dependent>
          </dep>
          <dep type="nn">
            <governor idx="6">seals</governor>
            <dependent idx="5">hunt</dependent>
          </dep>
          <dep type="prep_to">
            <governor idx="3">used</governor>
            <dependent idx="6">seals</dependent>
          </dep>
          <dep type="conj_and">
            <governor idx="3">used</governor>
            <dependent idx="9">traded</dependent>
          </dep>
          <dep type="dobj">
            <governor idx="9">traded</governor>
            <dependent idx="10">fur</dependent>
          </dep>
          <dep type="det">
            <governor idx="13">Europeans</governor>
            <dependent idx="12">the</dependent>
          </dep>
          <dep type="prep_with">
            <governor idx="9">traded</governor>
            <dependent idx="13">Europeans</dependent>
          </dep>
        </dependencies>
        <dependencies type="collapsed-ccprocessed-dependencies">
          <dep type="root">
            <governor idx="0">ROOT</governor>
            <dependent idx="3">used</dependent>
          </dep>
          <dep type="det">
            <governor idx="2">Inuits</governor>
            <dependent idx="1">The</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="3">used</governor>
            <dependent idx="2">Inuits</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="9">traded</governor>
            <dependent idx="2">Inuits</dependent>
          </dep>
          <dep type="nn">
            <governor idx="6">seals</governor>
            <dependent idx="5">hunt</dependent>
          </dep>
          <dep type="prep_to">
            <governor idx="3">used</governor>
            <dependent idx="6">seals</dependent>
          </dep>
          <dep type="conj_and">
            <governor idx="3">used</governor>
            <dependent idx="9">traded</dependent>
          </dep>
          <dep type="dobj">
            <governor idx="9">traded</governor>
            <dependent idx="10">fur</dependent>
          </dep>
          <dep type="det">
            <governor idx="13">Europeans</governor>
            <dependent idx="12">the</dependent>
          </dep>
          <dep type="prep_with">
            <governor idx="9">traded</governor>
            <dependent idx="13">Europeans</dependent>
          </dep>
        </dependencies>
      </sentence>
    </sentences>
  </document>
</root>
"""

headline_parserxml = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet href="CoreNLP-to-HTML.xsl" type="text/xsl"?>
<root>
  <document>
    <sentences>
      <sentence id="1">
        <tokens>
          <token id="1">
            <word>Inuits</word>
            <lemma>Inuits</lemma>
            <CharacterOffsetBegin>1</CharacterOffsetBegin>
            <CharacterOffsetEnd>7</CharacterOffsetEnd>
            <POS>NNPS</POS>
            <NER>O</NER>
          </token>
          <token id="2">
            <word>trade</word>
            <lemma>trade</lemma>
            <CharacterOffsetBegin>8</CharacterOffsetBegin>
            <CharacterOffsetEnd>13</CharacterOffsetEnd>
            <POS>VBP</POS>
            <NER>O</NER>
          </token>
          <token id="3">
            <word>fur</word>
            <lemma>fur</lemma>
            <CharacterOffsetBegin>14</CharacterOffsetBegin>
            <CharacterOffsetEnd>17</CharacterOffsetEnd>
            <POS>NN</POS>
            <NER>O</NER>
          </token>
          <token id="4">
            <word>!</word>
            <lemma>!</lemma>
            <CharacterOffsetBegin>18</CharacterOffsetBegin>
            <CharacterOffsetEnd>19</CharacterOffsetEnd>
            <POS>.</POS>
            <NER>O</NER>
          </token>
        </tokens>
        <parse>(ROOT (S (NP (NNPS Inuits)) (VP (VBP trade) (NP (NN fur))) (. !))) </parse>
        <dependencies type="basic-dependencies">
          <dep type="root">
            <governor idx="0">ROOT</governor>
            <dependent idx="2">trade</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="2">trade</governor>
            <dependent idx="1">Inuits</dependent>
          </dep>
          <dep type="dobj">
            <governor idx="2">trade</governor>
            <dependent idx="3">fur</dependent>
          </dep>
        </dependencies>
        <dependencies type="collapsed-dependencies">
          <dep type="root">
            <governor idx="0">ROOT</governor>
            <dependent idx="2">trade</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="2">trade</governor>
            <dependent idx="1">Inuits</dependent>
          </dep>
          <dep type="dobj">
            <governor idx="2">trade</governor>
            <dependent idx="3">fur</dependent>
          </dep>
        </dependencies>
        <dependencies type="collapsed-ccprocessed-dependencies">
          <dep type="root">
            <governor idx="0">ROOT</governor>
            <dependent idx="2">trade</dependent>
          </dep>
          <dep type="nsubj">
            <governor idx="2">trade</governor>
            <dependent idx="1">Inuits</dependent>
          </dep>
          <dep type="dobj">
            <governor idx="2">trade</governor>
            <dependent idx="3">fur</dependent>
          </dep>
        </dependencies>
      </sentence>
    </sentences>
  </document>
</root>
"""



if False: # hopefully you can preprocess the text through the parser
    input_text = headline
    if parse.StanfordCoreNLP.stanfordJavaProcess is None:
        parse.StanfordCoreNLP.startServer()
    parsexml = parse.StanfordCoreNLP.parseText(input_text)
    print "Input text:"
    print input_text
    print parsexml
    print "--------------"
    raise NotImplementedError, "should cache this so we don't need parser"

print "Input information to learn the QG from"
print "Sentence: ", text
print "Tweet: ", headline

doc = parse.StanfordCoreNLP.DocInfo(text_parserxml)
headline_doc = parse.StanfordCoreNLP.DocInfo(headline_parserxml)


# QG learns how to translate source sentence into headline
src_sentence = doc.sentence(0)
tgt_sentence = headline_doc.sentence(0)

# this matches words (leaf nodes), then nodes higher in the two trees
matchList = qtsg.align.align_nodes(src_sentence, tgt_sentence)

# print out the token and node alignments we have
qtsg.info.printAllMatchListInfo(matchList)


# create a grammar, by linking matched trees
qg_tree_pairs = qtsg.SyncTreeGrammar.extract_grammar( matchList )
qg_rules = [qtsg.SyncTreeGrammar.SyncGrammarRule(s,t) for (s,t) in qg_tree_pairs]
qg_rules = [r for r in qg_rules if not r.isIdentical()]
qg_rules = qtsg.SyncTreeGrammar.combine_duplicate_rules(qg_rules)

# print out what the grammar looks like so far
for r in qg_rules:
    print r
qtsg.info.printRuleSetInfo(qg_rules)

# split the grammar into two types: ones that create new sentences, and ones that modify the sentence
st_grammar, normal_grammar = qtsg.statements.split_grammar_ST(qg_rules)

# apply the grammar to a sentence, to create some possible paraphrases
src_tree = src_sentence.parseTree()
st_paraphrases, _st_rulelist = qtsg.statements.split_sentence(src_tree, st_grammar, normal_grammar)

print
print "Possible root paraphrase sentences:"
for i, st in enumerate(st_paraphrases):
    print i, "\t", qtsg.QGCore.nodeText(st)


# these choice_trees capture all the information about possible rewrites
# this would be the input to the ILP
choice_trees = [ qtsg.statements.create_ST_paraphrase_tree(st, normal_grammar) for st in st_paraphrases]


# everything below is just to print out what the grammar has produced
print
print "Parse trees to choose from:"
for i, tree in enumerate(choice_trees):
    print  "Tree ", i, ":"
    print tree
    
 
    #ct = ChoiceTree.create(tree, None)
    ct = SingleShotChoiceTree.create(tree, None)
    ct.reset()
    
    result_list = []
    try:
        while True:
            current_choices = [subct.current for subct in ct.flatten()]
            ct.set_choices()
            result_list.append(qtsg.QGCore.nodeText(tree))
            ct.next_choice()
    except StopIteration:
        pass

    print "Possible outputs from this tree:"    
    for s in result_list: print s
    print

