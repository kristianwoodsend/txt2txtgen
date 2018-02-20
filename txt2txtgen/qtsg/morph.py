'''
Rewrite verb phrases based on John Carroll's morphg

Created on 4 Nov 2013

@author: kwoodsen
'''

import subprocess

from txt2txtgen.config.Config import MORPHG
from QGDefs import PRINT_DEBUG_PARAPHRASE


MORPHG_TAGS = {
               "VBZ" : "+s_V",
               # "VBP" : "", # just use base form
               "VBD" : "+ed_V",
               "VBG" : "+ing_V",
               "VBN" : "+en_V",
               
               # morphg can morph "be" verbs using the same tags 
               "VBZ-COP" : "+s_V",
               # "VBP-COP" : "", # just use base form
               "VBD-COP" : "+ed_V",
               "VBG-COP" : "+ing_V",
               "VBN-COP" : "+en_V",
               }

def morph_tree(src_tree, tgt):
    
    src_tag = src_tree.tag()
    tgt_tag = tgt.tag()
    
    if not requires_morph(src_tag, tgt_tag):
        raise ValueError, "morphing not needed"
    
    if PRINT_DEBUG_PARAPHRASE:
        print "Morphing from: ",
        print src_tree,
        print "to ", tgt
        
    assert src_tree.isLeaf(), "trying to apply morph to more than a leaf"
    lemma = src_tree.token().lemma
    
    copiedNode = src_tree.copy(deep=True)
    try:
        label = MORPHG_TAGS[tgt_tag]
        input = "%s%s" % (lemma, label) 
        
        # use pipes to capture input and output. stderr=pipe to stop the "verbstem" messages
        p = subprocess.Popen(MORPHG, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdoutdata, _stderrdata) = p.communicate(input)
        rewrite = stdoutdata
        assert p.poll()==0, "morphg not working"
    
    except KeyError:
        rewrite = lemma # just use base form
        if PRINT_DEBUG_PARAPHRASE:
            print "Unknown morph: ", src_tag, " -> ", tgt_tag

        
    copiedNode.set_label(tgt_tag)
    copiedNode[0] = rewrite
    
    if PRINT_DEBUG_PARAPHRASE: print "Morphed version: ", copiedNode
    
    return copiedNode
    
    
    
def requires_morph(src_tag, tgt_tag):
    if src_tag==tgt_tag:
        return False # exactly the same, so no morphing
    elif src_tag.startswith("V") and tgt_tag.startswith("V"):
        return True
    else:
        return False
    