'''
Methods for showing information about rulesets

Created on 19 Sep 2013

@author: kristian
'''


from SyncTreeGrammar import loadQSGRules, SyncGrammarRule

def investigatePickledResults():
    """
    Read in pickled sync grammar and do some investigations
    """
    syncGrammar = loadQSGRules()
    print "Sync grammar generation completed"
    #printResultsListInfo( syncGrammar )
    print 
    
    syncGrammarRules = [ SyncGrammarRule(n1,n2) for (n1,n2) in syncGrammar ]
    print "Sync Grammar rules length: ", len(syncGrammarRules)
    modificationRules = [r for r in syncGrammarRules
        if not r.isIdentical()]
    print "Modified rules: ", len(modificationRules)
    
    # how many rules involve a simple deletion
    testRule = modificationRules[6]
    print testRule
    print "Is identical:", testRule.isIdentical()
    print "Is partOfSpeechChange:", testRule.partOfSpeechChange()
    print "Is depLabelChange:", testRule.depLabelChange()
    print "Has containsDeletions:", testRule.containsDeletions()
    print "Deleted nodes:", [n._node for n in testRule.deletedNodes()]
    print "Is reordered:", testRule.isReordered()
    
    print "\n\nInvestigating deletions: "
    delOnlyRules = [ r for r in modificationRules 
        if r.containsDeletions() and not r.isReordered() ]
    #for r in delOnlyRules: print r
    print "\nNumber of deletion only rules: ", len(delOnlyRules)
    fdist = nltk.probability.FreqDist()
    for r in delOnlyRules:
        delNodes = r.deletedNodes()
        for n in delNodes: fdist.inc(n._node)
    print "Tags deleted:"
    for (k,v) in fdist.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*v/fdist.N())
        
    tagChangeOnly = [ r for r in modificationRules 
        if r.partOfSpeechChange() and 
        not r.containsDeletions() and 
        not r.isReordered() and
        not r.containsInsertions() ]
    print "\n\nNumber of modification rules involving only tag change", len(tagChangeOnly) 
    fdist = nltk.probability.FreqDist((r._source._node,r._target._node) for r in tagChangeOnly)
    for (k,v) in fdist.iteritems(): print k, '\t', v, \
        "\t%8.1f %%" % (100.0*v/fdist.N())
        
    # transform in POS involving some change
    posChange = [ r for r in modificationRules 
        if r.partOfSpeechChange() and 
        (r.containsDeletions() or r.isReordered() or r.containsInsertions() ) ]
    print "\n\nNumber of modification rules changing POS involving some change", len(posChange) 
    fdist = nltk.probability.FreqDist((r._source._node,r._target._node) for r in posChange)
    for (k,v) in fdist.iteritems(): print k, '\t', v, \
        "\t%8.1f %%" % (100.0*v/fdist.N())
    
    print "\n\nCount rules instances: which appear more than once"
    fdist = nltk.probability.FreqDist(str(r) for r in syncGrammarRules )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break

    print "\n\nCount instances of true modification: which appear more than once"
    someRealChange = [ r for r in modificationRules
        if (r.containsDeletions() or r.isReordered() or r.containsInsertions() ) ]
    fdist = nltk.probability.FreqDist(str(r) for r in someRealChange )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break

    print "\n\nCount unique rules of modification which involve just deletions"
    someRealChange = [ r for r in modificationRules
        if r.containsDeletions() and not (r.isReordered() or r.containsInsertions()) ]
    fdist = nltk.probability.FreqDist(str(r) for r in someRealChange )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break

    print "\n\nCount instances of POS modification: which appear more than once"
    fdist = nltk.probability.FreqDist(str(r) for r in posChange )
    print "Number of bins: ", fdist.B()
    for i, (k,v) in enumerate(fdist.iteritems()): 
        print k, '\t', v
        if i > 10: break
        

        
def investigatePickledResultsRuleSet():
    """
    Read in pickled sync grammar and do some investigations
    using the set of rules, counted into groups
    """
    syncGrammarRules = loadQSGRules()
    print "Sync Grammar rules length: ", len(syncGrammarRules)
    
    # print stats for rule set
    fdist = nltk.probability.FreqDist()
    fdistCount = nltk.probability.FreqDist()
    fdistDups = nltk.probability.FreqDist()
    fdistDels = nltk.probability.FreqDist()
    fdistIns = nltk.probability.FreqDist()
    fdistReorder = nltk.probability.FreqDist()
    for r in syncGrammarRules: 
        fdist.inc(r._source.tag())
        fdistCount.inc(r._source.tag(), r.count())
        if r.isIdentical(): fdistDups.inc(r._source.tag())
        if r.deletedNodes(): fdistDels.inc(r._source.tag())
        if r.containsInsertions(): fdistIns.inc(r._source.tag())
        if r.isReordered(): fdistReorder.inc(r._source.tag())
        
    print "Source parent tag for rule:\t\t\tBy count:"
    for (k,v) in fdist.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*v/fdist.N()),\
        "\t\t", fdistCount[k],\
        "\t%8.1f %%" % (100.0*fdistCount[k]/fdistCount.N())
    
    print "\nNo-change rules:"
    for (k,v) in fdistDups.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistDups[k]/fdistDups.N()),\
        "\t%8.1f %%" % (100.0*fdistDups[k]/fdist[k])

    print "\nDeleted nodes rules:"
    for (k,v) in fdistDels.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistDels[k]/fdistDels.N()),\
        "\t%8.1f %%" % (100.0*fdistDels[k]/fdist[k])

    print "\nInserted nodes rules:"
    for (k,v) in fdistIns.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistIns[k]/fdistIns.N()),\
        "\t%8.1f %%" % (100.0*fdistIns[k]/fdist[k])

    print "\nReordered nodes rules:"
    for (k,v) in fdistReorder.iteritems(): print k,'\t\t', v,\
        "\t%8.1f %%" % (100.0*fdistReorder[k]/fdistReorder.N()),\
        "\t%8.1f %%" % (100.0*fdistReorder[k]/fdist[k])
        


