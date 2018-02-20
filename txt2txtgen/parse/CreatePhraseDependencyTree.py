"""
Investigate how to represent the dependencies
between phrases rather than head-words,
and keep the ability to regenerate the sentences.
"""

from POSTagger import StanfordDependencyParser, StanfordPennParser
import os
import nltk

    
FORMAT="pdf"
GRAPHVIZ_EXTRA = False
MIN_PHRASE_SIZE = 2
prtLevel = 0


def makePhraseTree( doc, s, min_phrase_size=MIN_PHRASE_SIZE ):
    """
    Make a phrase tree for sentence s in document doc
    doc The document
    s sentence
    Returns phrase tree object
    """
    
    # Set up parser objects, with caches of their own
    pennParser = StanfordPennParser(doc.filename())
    depParser = StanfordDependencyParser(doc.filename())
    
    if (prtLevel): print "Making phrase tree for sentence: ", s
    tree = pennParser.parse(s) 
    #print tree
    #assert tree[0].node in successfulPennParse, "Not a sentence, but %s"%tree[0].node
    dg = depParser.parseToDepGraph(s)

    try:
        if (prtLevel): print "Adding dependencies"
        tree.addDependencies(dg)
        if (prtLevel): print "Marking independent phrases: ",min_phrase_size
        tree.markIndependentPhrase(min_phrase_size) # arg is min token size for a phrase
        if False: # __str__ not handling unicode trees
            print "Before collapseFixedLinks 1", tree
            
            if False:
                # compresses tree into phrases
                tree.collapseFixedLinks()
                print "Before co phr", tree
                tree.collapseIntoPhrases()
                print "Before collapseFixedLinks 2", tree
                tree.collapseFixedLinks()
                print "After collapseFixedLinks 2", tree
    except IndexError, e:
        print e
        print "Failed to fully parse"
        tree = None
        
    return tree
    


# Create Graphviz files
def makeGraphvizDiagram( f, txt ):
    fTmp = _writeTempFile( txt )
    cmd = "dot -T%s -o%s %s" % (FORMAT, f, fTmp)
    print cmd
    result = os.system(cmd)
    print "Result: ", result
    assert result==0, "Graphviz has failed"
    #os.remove(fTmp)


def makeGraphvizDiagramFromTree( f, tree ):
    txt=[]
    leafList=[]
    txtStart="digraph G { "
    txtStart+='\ngraph [rankdir=TB, nodesep=0.25, ranksep=0.05];'
    #txtStart+='\ngraph [rankdir=TB, nodesep=0.25, ranksep=0.05, size="3,5!"];'
    txtEnd="}"
    txt.append(txtStart)
    txt.extend(_makeGraphvizDiagramFromTree(tree,leafList))
    
    # make leaf nodes all the same rank
    #txt.append("{rank=same; ")
    #txt.extend(leafList)
    #txt.append("}")
    
    txt.append(txtEnd)
    #print txt
    #print "leafList: ",leafList
    #print 
    makeGraphvizDiagram( f, txt )
    
def _makeGraphvizDiagramFromTree( tree, leafList ):
    txt=[]
    nodeTxt = tree.node
    if (GRAPHVIZ_EXTRA and tree._head): nodeTxt += ' H'
    # if (tree.isFixed()): nodeTxt += ' F'
    if (GRAPHVIZ_EXTRA and len(tree._wordPos)>0): nodeTxt += " "+str(tree._wordPos) 
    if (GRAPHVIZ_EXTRA and tree.isLeaf()):
        nodeTxt += '\\n' + tree[0]
        
    s = '%s [label="%s", shape=none, fontname="Helvetica", fontsize=11.0];\n' % (treePos(tree),nodeTxt)
    txt.append(s)
    if (tree.isLeaf()):
        sPos = treePos(tree)
        leafTxt = tree[0]
        s_leaf = '%s_l [label="%s", shape=none, fontname="Times", fontsize=11.0];\n' % (sPos,leafTxt)
        txt.append(s_leaf)
        slink='%s -> %s_l [arrowhead=none];' % (sPos,sPos)
        txt.append(slink)
        leafList.append('%s_l' % sPos )
        
    
    if ( not tree.isLeaf() ):
        for n in tree:
            txt.extend(_makeGraphvizDiagramFromTree(n,leafList))
            slink='%s -> %s [arrowhead=none]' % (treePos(tree),treePos(n))
            label=""
            if (n._rel): #  and not n._rel==PhraseDependencyTree.FIXED_DEPENDENT):
                label=n._rel
            if (n.isIndependentPhrase()):
                pass
            if (label and not label=="fixed"):
                slink += ' [label="%s"]' % label
                slink += ' [style="dotted", fontname="Helvetica-Italic", fontsize=11.0]' 
            slink+=';'
            txt.append(slink)
    return txt
        
NODE_PREFIX = "n"    
def treePos(n):
    s1=NODE_PREFIX+str(n.treeposition())
    # print "Before: ",s1
    s2=s1.replace('(','')
    s2a=s2.replace(')','')
    s3=s2a.replace(',','_')
    s4=s3.replace(' ','')
    # print "After: ", s4
    return s4
    
    
    
    
# Various sentences and highlights from the corpus
#canada.mad.cow
eg_ca_hd="Canada reports new mad cow case"
eg_ca_t0="A new case of mad cow disease was confirmed in Canada , its 13th case since 2003 ."
eg_ca_t1="There was no risk to public health because no part of the animal entered the human food systems , government inspectors said ."
eg_ca_t2="The Canadian Food Inspection Agency said Monday that the latest case of mad cow disease , also known as bovine spongiform encephalopathy , or BSE , does not suggest the problem is more widespread ."
eg_ca_t3="Luterbach said Canada has been assessed by the World Organization for Animal Health and given a controlled-risk status , indicating it has the proper checks and balances to control the disease ."
eg_ca_t4="Luterbach said more than 220,000 cattle in Canada have been tested for BSE since the country 's first case in 2003 ."
eg_ca_h1="Canadian agency : Latest case does n't suggest the problem is more widespread ."
eg_ca_h2="No part of animal entered human food systems , government inspectors say ."
eg_ca_h3="Official says Canada has proper checks and balances to control disease ."
eg_ca_h4="More than 220,000 cattle in Canada tested for disease since first case in 2003 ."


# church.conference
eg_ch_h1="Lambeth Conference , held every decade , brings together Anglican church leaders ."
eg_ch_h2="Some bishops have boycotted event over gay clergy and female bishops ."
eg_ch_h3="Conservative Anglican bishops decided last month to form their own movement ."
eg_ch_h4="Anglican Communion is 3rd biggest church in the world , has 80M members ."
eg_ch_t1="Controversy over gay clergy and female bishops is likely to dominate the Anglican church 's once-a-decade conference , which begins Wednesday ."
eg_ch_t2="The Lambeth Conference in Canterbury , southern England , brings together archbishops and bishops from the Anglican church around the world ."
eg_ch_t3="But many invited bishops are boycotting the event , angry that the church allowed the consecration of a gay bishop in the United States in 2003 ."

# england.cech.ap2008
eg_en_h1="Chelsea goalkeeper Petr Cech has signed a new five-year contract ."
eg_en_h2="The Czech Republic player joined from Rennes in 2004 ."
eg_en_h3="The 26-year-old has made 115 appearances for the London club ."
eg_en_t1="Chelsea goalkeeper Petr Cech has signed a new five-year contract to keep him at the club until 2013 ."
eg_en_t2="The 26-year-old Cech has made 115 appearances for Chelsea since joining from French club Rennes in 2004 ."

#king.poll2009
eg_king_t1="But whites remain less optimistic , the survey found ."


if __name__=="__main__":
    
    graphvizDir = Config.GRAPHVIZ_DIR
    dpParser=StanfordDependencyParser()
    pennParser=StanfordPennParser()
    sl_en=(eg_en_h1,eg_en_h2,eg_en_h3,eg_en_t1,eg_en_t2)
    sl_ch=(eg_ch_h1,eg_ch_h2,eg_ch_h3,eg_ch_h4,eg_ch_t1,eg_ch_t2,eg_ch_t3)
    sl_ca=(eg_ca_h1,eg_ca_h2,eg_ca_h3,eg_ca_h4,eg_ca_t1,eg_ca_t2,eg_ca_t3,eg_ca_t4,eg_ca_hd,eg_ca_t0)
    sl = (eg_king_t1,) # sl_en + sl_ch + sl_ca # (eg_ch_h1, eg_ch_t1)  # sl_en + sl_ch + sl_ca
    for i, s in enumerate(sl_ca):
        fp= graphvizDir + "dp%d.%s" % (i,FORMAT) 
        fpt=graphvizDir + "dpt%d.%s" % (i,FORMAT) 
        tree = pennParser.parse(s) 
        
        # print tree
        makeGraphvizDiagramFromTree(fp,tree[0])
         

        dg=dpParser.parseToDepGraph(s)
        dotTxt = dg.createGraphviz()
        fdg=graphvizDir + "dg%d.%s" % (i,FORMAT)  
        makeGraphvizDiagram(fdg, dotTxt)
        
        tree.addDependencies(dg)
        fdl=graphvizDir + "dgl%d.%s" % (i,FORMAT)  
        # print tree
        makeGraphvizDiagramFromTree(fdl,tree[0])
                
        
        fc=graphvizDir + "dc%d.%s" % (i,FORMAT) 
        print "Marking independent phrases"
        tree.markIndependentPhrase(MIN_PHRASE_SIZE)
        tree.collapseFixedLinks()
        tree.collapseIntoPhrases()
        tree.collapseFixedLinks()
        # print tree
        makeGraphvizDiagramFromTree(fc,tree[0])
        
        phraseList = tree.getPhrases()
        print "Independent phrase list:"
        for i in phraseList:
            print i[0].node, i[0]._rel, i[0]._wordPos, i[1]
            # ExtractPhraseFeatures.processPhrase(i[1])
        

