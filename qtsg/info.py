'''
Method that print out information on rules


Created on 19 Sep 2013

@author: kristian
'''
from operator import attrgetter

import nltk

from QGCore import describeTreeProductions, nodeText
def printAllPhraseInfo( phraseList ):
    for node in phraseList: 
        print node.tree().tag(), "/", node.tree().dep(), node.leaves()

def printAllMatchListInfo( matchList ):
    print "\nMatch list:"
    for (ph1,ph2) in matchList: 
        print ph1.treeposition(), "---", ph2.treeposition(), "\t\t", ph1.tag(), nodeText(ph1), " --- ", ph2.tag(), nodeText(ph2)
    print

    
def printRules( resultsList, escaped=False ):
    """ We expect a list of source and target trees """
    for (rs,rt) in resultsList:
        if escaped:
            print repr(str(rs) + '\t' + str(rt)), ","
        else:
            print rs, "\t", rt

        
def printRuleSet( resultsList, minCount=2, sort=True, escaped=False ):
    """ Print out a set of rules, involving rule objects """
    if sort:
        resultsList.sort(key=attrgetter('_count'), reverse=True)
    for r in resultsList:
        if escaped:
            print repr(unicode(r)), ","
        else:
            # print r.rule_id(), "\t", r.count(), "\t", r._source.links(), "\t", unicode(r)
            print r.count(), "\t", unicode(r)

    
def printRuleSetSubstitutions( resultsList, minCount=2, sort=True ):
    """ Print out a set of rules, involving rule objects """
    if sort:
        resultsList.sort(key=attrgetter('_count'), reverse=True)
    for rule in resultsList:
        # rule = SyncGrammarRule(r[0], r[1])
        if rule.isIdentical():
            # print ".\t",
            continue # skip identical rules
        if not rule.isSubstitution(contentWords=True): continue
        if rule.count() < minCount: continue
        print rule.count(), "\t\t", rule.describeWordSeq(wordsonly=True)
    
    
def printRuleSetInfo( rules ):
    print "Count of rules: \t\t", len(rules)
    modificationRules = [r for r in rules
        if not r.isIdentical()]
        
    print "Count of modification rules: \t", len(modificationRules)
    print "Count of no-change rules: \t", len(rules)-len(modificationRules)

    notIdenticalGrammar = modificationRules
    insertions = [ r for r in notIdenticalGrammar if r.containsInsertions() ]
    deletions = [ r for r in notIdenticalGrammar if r.containsDeletions() ]
    reorderings = [ r for r in notIdenticalGrammar if r.isReordered() ]
    syntaxChange = [ r for r in notIdenticalGrammar if r.isSyntaxTransform() ]
    nullRules = [ r for r in notIdenticalGrammar if r.isNullRule() ]
    lexRules = [ r for r in notIdenticalGrammar if r.isLexicalized() ]
    subRules = [ r for r in notIdenticalGrammar if r.isSubstitution() and not r.isIdentical() ]
    print "\nFor non-identical rules:"
    print "Number of insertion rules: \t", len(insertions)
    print "Number of deletion rules: \t", len(deletions)
    print "Number of null rules: \t", len(nullRules)
    print "Number of reordering rules: \t", len(reorderings)
    print "Number of syntax change rules: \t", len(syntaxChange)
    print "Number of lexicalized rules: \t", len(lexRules)
    print "Number of substitution rules: \t", len(subRules)


    # things CCB seems to want:
    grammar = rules
    srcChildren0 = [r for r in grammar if len(r._source.children()) == 0]
    srcChildren0lex = [r for r in srcChildren0 if r._source.hasText()]
    srcChildren1 = [r for r in grammar if len(r._source.children()) == 1]
    srcChildren2 = [r for r in grammar if len(r._source.children()) == 2]
    srcChildren3 = [r for r in grammar if len(r._source.children()) == 3]
    srcChildren4plus = [r for r in grammar if len(r._source.children()) > 3]
    print "\nAll rules, identical and non-identical:"
    print "Total number of rules in this grammar: \t", len(grammar)
    print "Number of rules where src tree has 0 children: \t", len(srcChildren0)
    print "Number of 0 children rules which are lexical subs: \t", len(srcChildren0lex)
    print "Number of rules where src tree has 1 children: \t", len(srcChildren1)
    print "Number of rules where src tree has 2 children: \t", len(srcChildren2)
    print "Number of rules where src tree has 3 children: \t", len(srcChildren3)
    print "Number of rules where src tree has 4+ children: \t", len(srcChildren4plus)

    srcChildren0 = [r for r in notIdenticalGrammar if len(r._source.children()) == 0]
    srcChildren0lex = [r for r in srcChildren0 if r._source.hasText()]
    srcChildren1 = [r for r in notIdenticalGrammar if len(r._source.children()) == 1]
    srcChildren2 = [r for r in notIdenticalGrammar if len(r._source.children()) == 2]
    srcChildren3 = [r for r in notIdenticalGrammar if len(r._source.children()) == 3]
    srcChildren4plus = [r for r in notIdenticalGrammar if len(r._source.children()) > 3]
    print "\nJust non-identical rules:"
    print "Total number of rules in this grammar: \t", len(notIdenticalGrammar)
    print "Number of rules where src tree has 0 children: \t", len(srcChildren0)
    print "Number of 0 children rules which are lexical subs: \t", len(srcChildren0lex)
    print "Number of rules where src tree has 1 children: \t", len(srcChildren1)
    print "Number of rules where src tree has 2 children: \t", len(srcChildren2)
    print "Number of rules where src tree has 3 children: \t", len(srcChildren3)
    print "Number of rules where src tree has 4+ children: \t", len(srcChildren4plus)



    
    print "\nPCFG synchronized phrases:"
    fdist = nltk.probability.FreqDist((r._source.tag(), r._target.tag()) for r in rules)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    print "\nPCFG synchronized phrases, modifications only:"
    fdist = nltk.probability.FreqDist((r._source.tag(), r._target.tag()) for r in modificationRules)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    return
    
    
def printResultsListInfo( fullResultsList ):
    
    print "Count of rules: \t\t", len(fullResultsList)
    modificationRules = [(n1,n2) for (n1,n2) in fullResultsList
        if not unicode(n1)==unicode(n2)]
    #for (n1,st1,n2,st2) in modificationRules: print st1,st2
    print "Count of modification rules: \t", len(modificationRules)
    print "Count of no-change rules: \t", len(fullResultsList)-len(modificationRules)
    
    print "\nPCFG synchronized phrases:"
    fdist = nltk.probability.FreqDist((n1._node,n2._node) for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    print "\nPCFG synchronized phrases, modifications only:"
    fdist = nltk.probability.FreqDist((n1._node,n2._node) for (n1,n2) in modificationRules)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    # stop here for now
    return
    
    print "\nDep parser synchronized phrases:"
    fdist = nltk.probability.FreqDist((n1._dep,n2._dep) for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k, '\t', v

    print "\nPCFG productions for all rules:"
    fdist = nltk.probability.FreqDist(
        (n1.productions()[0],n2.productions()[0]) 
        for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v

    print "\nPCFG productions for modification rules:"
    fdist = nltk.probability.FreqDist(
        (n1.productions()[0],n2.productions()[0]) 
        for (n1,n2) in modificationRules)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v

    print "\nPCFG productions for modification rules using my production code:"
    fdist = nltk.probability.FreqDist(
        (describeTreeProductions(n1,[]),describeTreeProductions(n2,[]))
        for (n1,n2) in modificationRules)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v

    print "\nPCFG productions for full rules using my production code:"
    fdist = nltk.probability.FreqDist(
        (describeTreeProductions(n1,[]),describeTreeProductions(n2,[]))
        for (n1,n2) in fullResultsList)
    for (k,v) in fdist.iteritems(): print k[0],'\t',k[1], '\t\t', v


