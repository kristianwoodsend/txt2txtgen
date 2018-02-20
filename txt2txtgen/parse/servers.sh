#cd $(dirname $0)
#set -x

#STANFORDDIR='/disk/scratch/stanford/stanford-parser-2008-10-26'
STANFORDDIR="/home/kristian/Documents/NLP/src/stanford/stanford-parser-2008-10-26"

# compile to bring up to date
javac -cp $STANFORDDIR/stanford-parser-2008-10-26.jar StanfordParserServer.java

# really need one for each format 
java -server -mx1g -cp $STANFORDDIR/stanford-parser-2008-10-26.jar:. StanfordParserServer -port 5560 -format penn $STANFORDDIR/englishPCFG.ser.gz 
#java -server -mx1g -cp $STANFORDDIR/stanford-parser-2008-10-26.jar:. StanfordParserServer  -port 5561 -format typedDependenciesCollapsed $STANFORDDIR/englishPCFG.ser.gz &
#java -server -mx1g -cp $STANFORDDIR/stanford-parser-2008-10-26.jar:. StanfordParserServer  -port 5562 -format wordsAndTags $STANFORDDIR/englishPCFG.ser.gz &

wait
