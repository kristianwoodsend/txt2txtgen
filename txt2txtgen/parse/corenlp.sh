#cd $(dirname $0)
#set -x

#STANFORDDIR='/disk/scratch/stanford/stanford-parser-2008-10-26'
STANFORDDIR="/home/kristian/workspace/NLP/stanford-corenlp-full-2013-06-20"

# compile to bring up to date
javac -cp "$STANFORDDIR/*" StanfordCoreNLPServer.java

# run server
echo java -mx3g -cp "$STANFORDDIR/*:." StanfordCoreNLPServer
java -mx3g -cp "$STANFORDDIR/*:." StanfordCoreNLPServer


wait
