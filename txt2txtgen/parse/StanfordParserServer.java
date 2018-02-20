
import edu.stanford.nlp.parser.lexparser.LexicalizedParser;
import edu.stanford.nlp.parser.lexparser.Options;
import edu.stanford.nlp.trees.*;

import java.io.*;

import java.net.*;
import java.util.Properties;

/**
 * Wrapper class to run the Stanford Parser as a socket server so the grammar need not
 * be loaded for every new sentence.
 * 
 * Modified to work independently of arkref
 *  
* @param format A comma separated list of ways to print each Tree.
*                For instance, "penn" or "words,typedDependencies".
*                Known formats are: oneline, penn, latexTree, words,
*                wordsAndTags, rootSymbolOnly, dependencies,
*                typedDependencies, typedDependenciesCollapsed,
*                collocations, semanticGraph.  All of them print a blank line after
*                the output except for oneline.  oneline is also not
*                meaningul in XML output (it is ignored: use penn instead).
* @param optionsString Options that additionally specify how trees are to
*                be printed (for instance, whether stemming should be done).
*                Known options are: <code>stem, lexicalize, markHeadNodes,
*                xml, removeTopBracket, transChinese,
*                includePunctuationDependencies, basicDependencies, treeDependencies,
*                CCPropagatedDependencies, collapsedDependencies
*                </code>.
 * @author mheilman@cmu.edu
 * modified by k.woodsend@ed.ac.uk
 */
public class StanfordParserServer  {

	//@SuppressWarnings("unchecked")
	
	
	public static void main_working(String[] args) {
		  Options op = new Options();
	  String serializedInputFileOrUrl = "/home/kristian/Documents/NLP/src/stanford/stanford-parser-2008-10-26/englishPCFG.ser.gz";
	  LexicalizedParser lp = new LexicalizedParser(serializedInputFileOrUrl, op);
	      PrintWriter pwOut = op.tlpParams.pw();
	      PrintWriter pwErr = op.tlpParams.pw(System.err);
	      lp.parse(op.tlpParams.defaultTestSentence());
	  lp.parse("I have a dog . \n");
	  
	  Tree bestParseTest = lp.getBestParse();
	  System.err.println(bestParseTest);
	  
	  TreePrint tp;
	  String optionsString = "";
	  //tp = new TreePrint("dependencies");
	  tp = new TreePrint("typedDependenciesCollapsed",optionsString,new PennTreebankLanguagePack());
	  tp.printTree(lp.getBestParse(), pwOut);
	}

	
  private static void printOptions(Options op) {
    op.display();
    op.tlpParams.display();
  }
	
	
	
	public static void main(String[] args) {

		//INITIALIZE PARSER
		String serializedInputFileOrUrl = null;
		int port = 5560;
		int maxLength = 60;
		boolean markHeadNodes = false;
                String sentenceDelimiter = "\n";
                String format = "penn";
                String optionsString = "";

		// variables needed to process the files to be parse
		int argIndex = 0;
		if (args.length < 1) {
			System.err.println("usage: java edu.stanford.nlp.parser.lexparser." + "LexicalizedParser parserFileOrUrl\nOptions: -port, -maxLength, -format, -optionsString");
			System.exit(1);
		}

		Options op = new Options();
		// while loop through option arguments
		while (argIndex < args.length && args[argIndex].charAt(0) == '-') {
			if (args[argIndex].equalsIgnoreCase("-sentences")) {
				sentenceDelimiter = args[argIndex + 1];
				if (sentenceDelimiter.equalsIgnoreCase("newline")) {
					sentenceDelimiter = "\n";
				}
				argIndex += 2;
			} else if (args[argIndex].equalsIgnoreCase("-loadFromSerializedFile")) {
				// load the parser from a binary serialized file
				// the next argument must be the path to the parser file
				serializedInputFileOrUrl = args[argIndex + 1];
				argIndex += 2;
			} else if (args[argIndex].equalsIgnoreCase("-maxLength")) {
				maxLength = new Integer(args[argIndex + 1]);
				argIndex += 2;
			} else if (args[argIndex].equalsIgnoreCase("-port")) {
				port = new Integer(args[argIndex + 1]);
				argIndex += 2;
			} else if (args[argIndex].equalsIgnoreCase("-format")) {
				format = args[argIndex + 1];
				argIndex += 2;
			} else if (args[argIndex].equalsIgnoreCase("-optionsString")) {
				optionsString = args[argIndex + 1];
				argIndex += 2;
			} else {
				argIndex = op.setOptionOrWarn(args, argIndex);
			}
		} // end while loop through arguments

		LexicalizedParser lp = null;
		// so we load a serialized parser
		if (serializedInputFileOrUrl == null && argIndex < args.length) {
			// the next argument must be the path to the serialized parser
			serializedInputFileOrUrl = args[argIndex];
			argIndex++;
		}
		if (serializedInputFileOrUrl == null) {
			System.err.println("No grammar specified, exiting...");
			System.exit(0);
		}
		try {
			lp = new LexicalizedParser(serializedInputFileOrUrl, op);
		} catch (IllegalArgumentException e) {
			System.err.println("Error loading parser, exiting...");
			System.exit(0);
		}
		lp.setMaxLength(maxLength);
		lp.setOptionFlags("-outputFormat", "oneline");



		// declare a server socket and a client socket for the server
		// declare an input and an output stream
		ServerSocket parseServer = null;
		BufferedReader br;
		PrintWriter outputWriter;
		Socket clientSocket = null;
		try {
			parseServer = new ServerSocket(port);
		}
		catch (IOException e) {
			System.err.println(e);
                        System.exit(-1);
		} 

		// Create a socket object from the ServerSocket to listen and accept 
		// connections.
		// Open input and output streams
		while (true) {
			System.err.println("Waiting for Connection on Port: "+port);
			try {
				clientSocket = parseServer.accept();
				System.err.println("Connection Accepted From: "+clientSocket.getInetAddress());
				br = new BufferedReader(new InputStreamReader(new DataInputStream(clientSocket.getInputStream())));
				outputWriter = new PrintWriter(new PrintStream(clientSocket.getOutputStream()));
				ByteArrayOutputStream buf = new ByteArrayOutputStream();
				PrintWriter bufWriter = new PrintWriter(new PrintStream(buf));
				String doc = "";

				do{
					doc += br.readLine();
				}while(br.ready());
				System.err.println("Received: " + doc);

				//PARSE
				try{
                                
					lp.parse(doc);



					//OUTPUT RESULT
					TreePrint tp;
					Tree bestParse = lp.getBestParse();
                                        tp = new TreePrint(format,optionsString,new PennTreebankLanguagePack());
                                        // tp = new TreePrint("typedDependenciesCollapsed","",new PennTreebankLanguagePack());
					tp.printTree(bestParse, bufWriter);
					
					// bufWriter.println(); // do all possible parses at once and separate out? 
					bufWriter.flush();
					bufWriter.close();
                                        System.err.println(buf.toString().replaceAll("\\s+", " "));
					outputWriter.println(buf.toString().replaceAll("\\s+", " "));
					// outputWriter.println(lp.getPCFGScore());

				}catch(Exception e){
					outputWriter.println("(ROOT (. .))");
					e.printStackTrace();
				}

				outputWriter.flush();
				outputWriter.close();

			}catch (IOException e) {
				e.printStackTrace();
			}
		}
	}

}

