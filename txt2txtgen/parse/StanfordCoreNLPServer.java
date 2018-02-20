
/**
 * Wrapper class to run the Stanford Parser as a socket server so the grammar need not
 * be loaded for every new sentence.
 *
 * This has been modified so that the main method runs the interactive shell,
 * but the shell outputs the xml format rather than the text format.
 * Everything else should be the same as the normal interactive shell.
 * We get the full Stanford CoreNLP pipeline.
 * 
 * @todo May want to add in the printing out of n-best parses
 * 
 * modified by k.woodsend@ed.ac.uk
 */

import java.io.*;
import java.util.*;

import edu.stanford.nlp.io.IOUtils;
import edu.stanford.nlp.pipeline.*;
import static edu.stanford.nlp.util.logging.Redwood.Util.*;
import edu.stanford.nlp.util.*;
import edu.stanford.nlp.util.logging.*;




// from edu.stanford.nlp.pipeline

public class StanfordCoreNLPServer extends edu.stanford.nlp.pipeline.StanfordCoreNLP {

/**
 * This can be used just for testing or for command-line text processing.
 * This runs the pipeline you specify on the
 * text in the file that you specify and sends some results to stdout.
 * The current code in this main method assumes that each line of the file
 * is to be processed separately as a single sentence.
 * <p>
 * Example usage:<br>
 * java -mx6g edu.stanford.nlp.pipeline.StanfordCoreNLP properties
 *
 * @param args List of required properties
 * @throws java.io.IOException If IO problem
 * @throws ClassNotFoundException If class loading problem
 */
public static void main(String[] args) throws IOException, ClassNotFoundException {
  Timing tim = new Timing();
  StanfordRedwoodConfiguration.minimalSetup();

  //
  // process the arguments
  //
  // extract all the properties from the command line
  // if cmd line is empty, set the properties to null. The processor will search for the properties file in the classpath
  Properties props = null;
  if (args.length > 0) {
    props = StringUtils.argsToProperties(args);
  }
  
  // multithreading thread count
  String numThreadsString = (props == null) ? null : props.getProperty("threads");
  int numThreads = 1;
  try{
    if (numThreadsString != null) {
      numThreads = Integer.parseInt(numThreadsString);
    }
  } catch(NumberFormatException e) {
    err("-threads [number]: was not given a valid number: " + numThreadsString);
  }

  //
  // construct the pipeline
  //
  StanfordCoreNLP pipeline = new StanfordCoreNLP(props);
  props = pipeline.getProperties();
  long setupTime = tim.report();

  // blank line after all the loading statements to make output more readable
  log("");

  //
  // Run the interactive shell
  //
  shell(pipeline);

  if (TIME) {
    log();
    log(pipeline.timingInformation());
    log("Pipeline setup: " +
        Timing.toSecondsString(setupTime) + " sec.");
    log("Total time for StanfordCoreNLP pipeline: " +
        tim.toSecondsString() + " sec.");
  }
}


/**
 * Runs an interactive shell where input text is processed with the given pipeline.
 *
 * @param pipeline The pipeline to be used
 * @throws IOException If IO problem with stdin
 */
private static void shell(StanfordCoreNLP pipeline) throws IOException {
  String encoding = pipeline.getEncoding();
  BufferedReader r = new BufferedReader(IOUtils.encodedInputStreamReader(System.in, encoding));
  System.err.println("Entering interactive shell. Type EOF (Ctrl-D) to quit.");
  String fulltext = "";

  while (true) {
    System.err.print("NLP> ");
    String line = r.readLine();
	fulltext += " " + line;

    if (line == null) {
      // EOF for exit
      break;
    } 
    else if (line.length()==0) {
      // blank line indicates that document is complete
      
      //System.out.println("Here is the input text in the Stanford parser (length " + fulltext.length() + "):");
      //System.out.println(fulltext);
      //System.out.println("===============================================");
      Annotation anno = pipeline.process(fulltext);
      pipeline.xmlPrint(anno, System.out); // prints out xml
      fulltext = ""; // clear fulltext to start again
    }
    	
  }
}


}



/**
OutputStream fos = new BufferedOutputStream(new FileOutputStream(outputFilename));
xmlPrint(annotation, fos);
fos.close();
*/
