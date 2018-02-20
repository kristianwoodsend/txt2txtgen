'''
Created on 11 Dec 2014

@author: kristian
'''

import Numberjack as nj

import txt2txtgen



txt = "The Inuits used to hunt seals , and traded fur with the Europeans ."
parserxml = """<?xml version="1.0" encoding="UTF-8"?>
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

print txt

doc = txt2txtgen.parse.StanfordCoreNLP.DocInfo(parserxml)



phrases = []
sentence_index = []

for i_sentence, sentence in enumerate(doc.sentences()): 
    tree = sentence.parseTree()
    print tree
    this_sentence_phrases = [ph for ph in tree.getPhrases()]
    phrases.extend( this_sentence_phrases )
    sentence_index.extend([ i_sentence for ph in this_sentence_phrases])
    
n = len(phrases)
for i, ph in enumerate(phrases):
    # number phrase
    ph.tree().setPhrIndex(i)
    print ph.tree().phrIndex(), "\tfrom sentence:", sentence_index[i], "\t", ph.tree().tag(), " ".join(ph.leaves())

# features and information about each of the phrases
# token length is number of tokens in each phrase
# you might want to change this to number of characters, to match Twitter limit
phrase_token_length = [ len(ph.leaves()) for ph in phrases ]

# phrase scores should come from your ML model
phrase_scores = [0.0 for ph in phrases]
# for now, we can hard-code some scores
phrase_scores[1] = 1.0
#phrase_scores[7] = 1.0
        
# make the ILP model
model = nj.Model()
phrase_variable = [ nj.Variable("phr_%d"%i) for i in range(n) ]
sentence_variable = [ nj.Variable("sentence_%d"%i) for i in range(doc.sentenceCount()) ]

# connect sentence and phrase variables for internal logic
for i in range(n):
    s = sentence_index[i]
    model.add( sentence_variable[s] >= phrase_variable[i] )

# set a maximum length for the output
MAX_TOKENS = 10
model.add( nj.Sum( [ phrase_variable[i] * phrase_token_length[i] for i in range(n) ] ) <= MAX_TOKENS )

# set a minimum length for the output
MIN_TOKENS = 5
model.add( nj.Sum( [ phrase_variable[i] * phrase_token_length[i] for i in range(n) ] ) >= MIN_TOKENS )

# include a phrase if any of the phrases below it are included
for i in range(n):
    ph_node = phrases[i].tree()
    ph_node_parent = ph_node.parent()
    if ph_node_parent is not None: # the root node has no parent
        model.add( phrase_variable[i] <= phrase_variable[ph_node_parent.phrIndex()] )
        
        # force subjects and objects of verbs to be present
        dep_relation = ph_node.dep()
        if "subj" in dep_relation or "obj" in dep_relation or "comp" in dep_relation:
            # force the child to be present if the parent is chosen
            model.add( phrase_variable[i] >= phrase_variable[ph_node_parent.phrIndex()] )
        
        

#          Include phrase p1 if any of its dependents are also included
#         subto phrase_dependencies:
#           forall <p1> in PHRASES:
#             card(PHRASE_DEPENDENTS[p1]) * x[p1] >= sum <p2> in PHRASE_DEPENDENTS[p1]: x[p2];


# maximise the score of all chosen phrases
obj = nj.Sum( [ phrase_variable[i] * phrase_scores[i] for i in range(n) ] )
obj -= nj.Sum( [ phrase_variable[i] * 0.001 for i in range(n) ] ) # reluctantly add text
model.add( nj.Maximise(obj) )

print model 

solver = model.load("SCIP") 
solver.setVerbosity(1)
print solver.solve()
solver.printStatistics()
assert solver.is_sat(), "Not solved!"



# print out the solution 
for v in phrase_variable:
    print v.name(), "\t", v.get_value()
for v in sentence_variable:
    print v.name(), "\t", v.get_value()
    
pass

print
print "Output:"
outputText = txt2txtgen.summarize.IP.assembleHighlightsFromPhraseTrees( doc, \
                [ v.get_value() for v in phrase_variable ], \
                [ v.get_value() for v in sentence_variable ] )
for txt in outputText: print txt


