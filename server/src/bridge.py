#=============================================================================
#   bridge.py                                   [python module source code]
#
#       Bridge connection handling facility.  Classes for serving
#       bridged connections from sensor nodes.
#
#       The connection data from each bridge is logged to a node-
#       specific file, and echoed to a TikiTerm terminal window.
#
#       The purpose of this facility is to allow us to receive raw
#       data streams directly from the script's AUXIO or the Wi-Fi
#       board's UART, and also to send commands back to these streams
#       as needed.  Also, the raw data streams will be logged to files,
#       to facilitate forensic analysis & reconstruction of the raw
#       data, in case the processed data is lost.
#
#       Really, the AUXIO and UART bridge instances ought to be defined
#       in separate subclasses, because they need behavior that is a
#       little bit different from each other.  Aside from the differing
#       names, the UART bridge needs to expect mixed text & binary data
#       (to handle plugging the serial link into UwTerminal, the FEDM
#       board, and FEDM emulators), whereas the AUXIO bridge should
#       receive only ASCII text data.  Furthermore, messages from the
#       UART bridge should be treated as commands and executed, whereas
#       messages arriving on the AUXIO bridge only need to be transcribed
#       to the terminal window and a file.  However, these separate
#       subclasses are not yet implemented (as of 9/28/'09).
#
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # Standard python modules.

                            #   Used in:                     Names used:
                            #   ------------------------    --------------------
import time                 #   BridgeMsgHandler.handle()   time()

    # Custom modules.

                            #   Used in:                     Names used:
                            #   ------------------------    --------------------
import logmaster            #   (module level)              getLogger(), appName
import communicator         #   (module level)              BaseMessageHandler, ...
import tikiterm             #   BridgeMsgHandler.handle()   Cyan, Green
import timestamp            #   BridgeMsgHandler.handle()   CoarseTimeStamp()
import sitedefs             #   BridgeServer.__init__()     MY_IP

    # Exported names (public).

__all__ = [ 'BridgeMsgHandler',             # Classes.
            'BridgeConnHandler',
            'BrdgSrvReqHandler',
            'BridgeServer'          ]

    # Module logger.
logger = logmaster.getLogger(logmaster.appName + '.brdg')

    #===========================================
    #   Class definitions.      [code section]
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #==================================================================
        #   BridgeMsgHandler                            [public class]
        #
        #       This implementation subclass of the abstract class
        #       BaseMessageHandler has several jobs:
        #
        #           1) Echo the incoming/outgoing message (with a
        #               timestamp) to a file that transcribes all
        #               the messages received/sent over that bridge
        #               connection.
        #
        #           2) Also echo the message (without annotations)
        #               to an active TikiTerm window.  The text color
        #               should depend on the message direction (incoming
        #               vs. outgoing).  [Not yet implemented.]
        #
        #           3) Log the activity (at some log level) to a
        #               logger specific to this connection.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class BridgeMsgHandler(communicator.BaseMessageHandler):

        # Override the default message-handler name (which is "unnamed").
        # These message handlers are "standard bridge" message handlers.

    defHandlerName = "std.brdg"
    
#    def __init__(inst, conn:communicator.Connection = None):
#        communicator.BaseMessageHandler.__init__(inst, conn, name="std.brdg")
    
    def handle(self, msg:communicator.Message):

#        logger.debug("BridgeMsgHandler.handle(): Handling the %s message [%s]..." %
#                     ('incoming' if msg.dir == communicator.DIR_IN else 'outgoing',
#                      msg.data.strip()))

            # Compose a string representation of the time now
            # when we are processing the message, for use in
            # logging.

        timestr = str(timestamp.CoarseTimeStamp(time.time()))

#        logger.debug("BridgeMsgHandler.handle(): Time string is %s..." % timestr)

            # Set some message parameters based on the message
            # direction (incoming/outgoing).  In future we might
            # want to extend this so that outgoing messages typed
            # interactively by user are in a different color from
            # automatic messages sent by the server.
        
        if msg.dir == communicator.DIR_IN:
            dirchar = '<'
            msgcolor = tikiterm.Cyan
        else:
            dirchar = '>'
            msgcolor = tikiterm.Green

#        logger.debug("BridgeMsgHandler.handle(): Color is %s, direction char is %s..." % (msgcolor, dirchar))

            # Get the message itself, as a string.
        
        msgstr = msg.data   # Assume this is already a string (not byte sequence)

            # Display the message (in the appropriate color) in
            # this connection's TikiTerm window.

#        logger.debug("BridgeMsgHandler.handle(): About to display message [%s] in color %s on our terminal window..." % (msgstr.strip(), msgcolor))

        try:
            self.conn.term.put(msgstr, tikiterm.TikiTermTextStyle(msgcolor))
        except:
            logger.exception("BridgeMsgHandler.handle(): There was some kind of exception in .conn.term.put().")

            # Write the message directly to the connection transcript file.
            # We prefix it with a timestamp and a direction indicator ("<", ">").

#        logger.debug("BridgeMsgHandler.handle(): Writing message [%s] to our transcript file..." % msgstr.strip())
            
        self.conn.transcr_filehandle.write("%s: %s %s" % (timestr, dirchar, msgstr))
                # - Assume msgstr ends in newline already.

#        logger.debug("BridgeMsgHandler.handle(): Flushing transcript file %s..." % self.conn.transcr_file)

        self.conn.transcr_filehandle.flush()

            # Instead of the module logger, use a special new logger we created earlier
            # just for this connection, with a name like "COSMICi.node0.auxio", etc.

#        logger.debug("BridgeMsgHandler.handle(): Logging message [%s] to connection log..." % msgstr.strip())

            # OK, this is kind of kludgey.  This depends on the fact that when our bridge server was
            # created, the node model that created it tacked on this extra ".node" field, which pointed
            # back to the creating node object, which holds the handle to the actual logger.  Ick.
        
#        self.conn.comm.node.logger.info("%s: @%s: [%s]" %
#                              (self.conn.transcr_file, timestr, msgstr.strip()))
        
    # End method BridgeMsgHandler.handle().
# End class BridgeMsgHandler.


        #================================================================
        #   BridgeConnHandler                           [public class]
        #
        #       This implementation subclass of the abstract
        #       class BaseConnectionHandler has several jobs:
        #
        #           1) Open (for appending) the transcript file
        #               for transcribing in/out messages over
        #               this connection.  (We do this even before
        #               a connection is received.)
        #
        #           2) When a connection comes in, pop up a new
        #               TikiTerm virtual terminal window to display
        #               data received via this connection.
        #
        #           3) Register a message handler for this connection
        #               to echo incoming messages to the terminal
        #               and to the transcript file.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
class BridgeConnHandler(communicator.BaseConnectionHandler):

    #---------------------------------------------------------------
    #   Instance data members:
    #
    #       .transcr_file - The filename of the transcript file that
    #               this bridge handler will transcribe messages to.
    #
    #       .transcr_filehandle - The handle to the transcript file
    #               stream, open for writing.
    #
    #-----------------------------------------------------------------

        #--------------------------------------------------------------------
        #   .__init__()                             [special instance method]
    
    def __init__(self, filename):
        logger.info("Creating connection handler to transcribe bridge data to filename %s..." % filename)

        self.transcr_file = filename
        # Let's open the log file in "append" mode with default buffering.
        self.transcr_filehandle = open(filename, 'a')
        self.transcr_filehandle.write("\n\n" + "-"*70 + "\n")
        self.transcr_filehandle.write("At %s opened %s transcript...\n\n"
                                      % (timestamp.CoarseTimeStamp(time.time()), filename))
        self.transcr_filehandle.flush()     # Make sure transcript file header gets written right away.

        #---------------------------------------------------------------------
        #   .handle()                               [public instance method]
        
    def handle(self, conn):
        logger.info("Received a connection which will be transcribed to %s..." % self.transcr_file)

            # Make sure the connection has a copy of the file information.  (Why is this necessary?)

        conn.transcr_file = self.transcr_file
        conn.transcr_filehandle = self.transcr_filehandle

            # Label the receiver thread and its thread-local logging context with the
            # appropriate role and component (knowing this bridge's assigned node).

        comp_str = "node #%d" % conn.comm.nodeID
        logger.debug("About to update the component name to: [%s]..." % comp_str)
        conn.update_component(comp_str)

            # Pop up a new TikiTerm window for displaying this connection's I/O.

        bridge_win_title = "Node #%d %s Bridge #%d" % (conn.comm.nodeID, conn.comm.name.upper(), conn.cid)
        logger.debug("Trying to pop up a new TikiTerm window titled %s..." % bridge_win_title)

        conn.term = tikiterm.TikiTerm(title=bridge_win_title, in_hook=conn.sendOut)
            # -The in_hook assignment causes input lines typed by the user to be
            #  sent out to the remote client over the connection's return path.

            # Add the usual bridge message handler to this connection.

        logger.debug("Adding a message handler for the node %d %s bridge..." % (conn.comm.nodeID, conn.comm.name.upper()))
                     
        conn.addMsgHandler(BridgeMsgHandler(conn))

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# End class BridgeConnHandler.
#------------------------------


    # We have to override the request-handler class in order to close
    # the terminal window automatically if the socket closes.
    
    # NOTE: This code was blatantly copy-and-pasted from mainserver.py.  It
    # would be cleaner to have a general module for "servers with terminals"
    # that provided this functionality (and other functionality shared
    # between bridge.py and mainserver.py), and then have the bridge and
    # mainserver modules just inherit their stuff from it.  But, that's
    # quite a bit of refactoring; I'm not yet sure it is warranted.

class BrdgSrvReqHandler(communicator.LineCommReqHandler):
        # What to do on the way out of the request-handling loop
        # (e.g. after the socket stops working).
    def finish(inst):
        logger.debug("BrdgSrvReqHandler.finish(): Getting ready to close the connection's terminal window...")
        style = tikiterm.TikiTermTextStyle(tikiterm.Yellow, tikiterm.Red)
        inst.conn.term.put('\n')
        inst.conn.term.put("CONNECTION STOPPED FUNCTIONING; CLOSING THIS TERMINAL WINDOW IN 10 SECS...\n", style)
        time.sleep(10)
            # Destroy the lil' terminal window for this connection that we created earlier.
        logger.debug("BrdgSrvReqHandler.finish(): Now I'm going to actually close the terminal window...")
        inst.conn.term.closewin()    
                # Above, we are assuming that MainConnHandler.handle() has already run
                # and has created the connection's TikiTerm window.
                
# End class BrdgSrvReqHandler.       


        #===========================================================================
        #   BridgeServer                                            [public class]
        #
        #       This is a class for receiving bridged data streams from remote
        #       nodes, and also asynchronously sending messages back to those
        #       nodes.  The lines of bridged data are logged to a file.
        #
        #       Like MainServer, this is implemented as a subclass of
        #       LineCommunicator.  (Is this a mistake?  It makes it difficult
        #       to handle lines that aren't terminated right away, i.e., that
        #       are left dangling for a while.)
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class BridgeServer(communicator.LineCommunicator):

    #-----------------------------------------------------------------------
    # Instance data members: (in addition to those of base classes)
    #   .name - ASCII name of this particular bridge server.
    #   .nodeID - What node ID number is this BridgeServer listening to.
    #   .port - What port number is this BridgeServer listening on.
    #
    # This extra attribute is tacked onto us after creation by the model
    # node object that created us:
    #
    #   .node - Points back to the actual node model that created us.
    #           This then references the node's logger object.  This
    #           really should be done more cleanly, say by passing the
    #           logger (or the node) to our initializer.
    #-----------------------------------------------------------------------

        #-----------------------------------------------------------------
        #   .__init__()                         [special instance method]
        #
        #       We must override our parent class LineCommunicator's
        #       initializer, because the arguments to our constructor
        #       are different.  We take a base port number, a
        #       node number, and a bridge name ("auxio"/"uart").
        #       From these, we calculate the ip:port address and
        #       role string to pass along to LineCommunicator's
        #       initializer.  We also add a special connection
        #       handler to support bridged communications.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def __init__(self, basePort, nodeID, name:str):

            # Save initializer arguments.
        
        self.name = name
        self.nodeID = nodeID

            # Calculate port number for listening for bridge connections
            # from this node.  Use the base port number for this type of
            # bridge, plus the node ID number as an offset.
        
        self.port = basePort + nodeID
        
        logger.info("Setting up server for receiving %s bridge from "
                    "node %d on port %d." % (name, nodeID, self.port))

            # Do default initialization for LineCommunicator.  Pass it
            # our listen address and a thread role string ("auxio0", etc.)
            
        communicator.LineCommunicator.__init__(self, (sitedefs.MY_IP, self.port),
                                               role="%s%d"%(name,nodeID),
                                               comp="node%d"%nodeID,
                                               reqhandler_class = BrdgSrvReqHandler
                                               )

            # Create & add the connection handler for this bridge server.
            # Since we're already extending __init__() anyway, just do this
            # here instead of in a separate .setup() method.
            
        self.addConnHandler(BridgeConnHandler("node%d.%s.trnscr"
                                              % (nodeID, name)))

        #-------------------------------------------------------------------
        #   .start()                            [public instance method]
        #
        #       Use this to start the bridge server after creation.
        #       The actual listener and connection-handling threads
        #       run in the background.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def start(self):           # Pass this message
        logger.debug("Bridge server %s (node %d) is about to start listening for client connections..."
                     % (self.name, self.nodeID))
        self.startListening()          # to our Communicator superclass.

        #-------------------------------------------------------------------
        #   .send()                             [public instance method]
        #
        #       Sends a message to the connection (if any) being
        #       managed by this bridge server.  Does nothing if
        #       no clients have connected yet.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def send(self, string:str):

            # We should probably check here to make sure that the client
            # is connected, and give a warning if not.

        logger.debug("Bridge server %s is sending message [%s] to all active clients..." % (self.name, string.strip()))

            # Create a message object that the underlying Communicator can understand.

        msg = communicator.Message(string)

            # Tell the Communicator to send it to all its clients (there should be only 1 though).

        self.sendAll(msg)
