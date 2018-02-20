"""
A program for parsing data by
calling the ParserServer script of ArkRef.
This sets up the Stanford Parser as a server
waiting for input.
It avoids having to start up the java process
and load the data each call.

N.B. The ParserServer is expecting just the one line of input
from the client, which it then parses and returns the parsed output.
It then closes the socket, so any further messages from this client
will be refused.
"""


import socket



host = "localhost"
# port = 5556
buf = 1024


def callParser( text, port ):
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    # communicate
    sock.sendall(text + '\n')
    print "Sending message '",text,"'....."
    print "Now listening"
    
    data_in=""
    data_block="dummy data"
    while len(data_block) > 0:
        data_block = sock.recv(buf)
        data_in += data_block
    print "Received message: ",data_in
    data_in = sock.recv(buf)
    print "Received message: ",data_in
    
    # Close socket
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()



def_msg = "===Enter message to send to server===";
print "\n",def_msg

# Send messages
text = raw_input('>> ')
print("Penn:")
callParser( text, 5560 ) # penn parser
#print("Dep:")
#callParser( text, 5561 ) # dependency parser
#print("POS:")
#callParser( text, 5562 ) # POS-tagger


