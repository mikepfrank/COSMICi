#========================================================================================
#   mainserver.py                                           [python module source file]
#
#       This module defines the MainServer class, which is for the
#       main server object in the COSMICi-server application, which
#       waits for new connections on the main "COSMO" port.
#
#
#       Classes defined in this module:
#       -------------------------------
#
#           Acknowledge_MsgHndlr    - Message handler that generates "ACK" responses
#                                       to incoming messages (text lines), and sends
#                                       them back along the return path of the original
#                                       sender's TCP connection.
#
#           TermDisp_MsgHndlr       - Message handler that displays both incoming and
#                                       outgoing messages (in different colors) in the
#                                       new TikiTerm window that was created to handle
#                                       the connection from a given sender.
#
#           Command_MsgHndlr        - Message handler that interprets incoming messages
#                                       as command lines and executes them.
#
#           MainConnHandler         - Connection handler for managing new client
#                                       connections.  Pops up new connection window,
#                                       registers the above message handlers.
#
#           MainSrvReqHandler       - Handler for connection requests.  Closes window
#                                       when connection ends.
#
#           MainServer              - Main server object.  Listens for connection
#                                       requests and invokes request handlers.
#
#
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

import time             # MainSrvReqHandler.finish() uses time.sleep()

import logmaster        # module-level uses getLogger()
import communicator     # module-level uses MessageHandler
import ports            # class MainServer uses COSMO_PORT
import sitedefs         # class MainServer uses MY_IP
import tikiterm         # used several places

    # List of all exported (public) names.

__all__ = [ 'Acknowledge_MsgHndlr',     # Message handler classes.
            'TermDisp_MsgHndlr',
            'Command_MsgHndlr',
            'MainConnHandler',          # Other classes.
            'MainSrvReqHandler',
            'MainServer'            ]

    # Module logger.
logger = logmaster.getLogger(logmaster.appName + '.mnSrv')

global cosmicIserver, cosmicIServer, cis
cis = cosmicIserver = cosmicIServer = None  # Initialized by COSMICi_server module.

    #===================================================================
    #   Message handlers for use by MainConnHandler.
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
class Acknowledge_MsgHndlr(communicator.BaseMessageHandler):    # Message handler that just acknowledges message receipt.
    
    defHandlerName = "main.ack"
    
    def handle(inst, msg):                                      # To handle a message,
        if msg.dir == communicator.DIR_IN:                                       # If it's an incoming message,
            logger.debug("Acknowledge_MsgHndlr.handle(): Acknowledging received message [%s]..." % msg.data.strip())
            replystr = "ACK " + msg.data.upper()
            logger.debug("Acknowledge_MsgHndlr.handle(): Sending acknowledgement string [%s]..." % replystr.strip())
            msg.replyWith(replystr)                    # Append 'ACK ', upcase it, and reply.
            logger.info("Finished sending reply string [%s]."%replystr.strip())
# End class Acknowledge_MsgHndlr.

# Color scheme:
#   Green = server normal output
#   Red = server error output
#   Yellow = input from user
#   Cyan = input from a node 

class TermDisp_MsgHndlr(communicator.BaseMessageHandler):       # Message handler that displays messages on a terminal.
    
    defHandlerName = "main.disp"
    
    def handle(inst, msg):

            # Determine text display color based on message direction.
        
        if msg.dir == communicator.DIR_IN:
            color = tikiterm.Cyan
        else:
            color = tikiterm.Green

            # Assign this color as the foreground color of the text.
        
        style = tikiterm.TikiTermTextStyle(color)

            # Put the message data to the connection's terminal window.

#        logger.debug("TermDisp_MsgHndlr.handle(): Displaying %s message [%s] with color %s..." %
#                     ('incoming' if msg.dir == communicator.DIR_IN else 'outgoing',
#                      msg.data.strip(), color))
        
        msg.conn.term.put(msg.data, style)
# End class TermDisp_MsgHndlr.

class Command_MsgHndlr(communicator.BaseMessageHandler):        # Message handler that sends commands to central processor.
    
    defHandlerName = "main.cmd"
    
    def handle(inst, msg):                                      # To handle a message,

        global cosmicIServer

        if msg.dir == communicator.DIR_IN:                          # If it's an incoming message,

            if hasattr(msg.conn, 'node'):
                oldnode = msg.conn.node                                     # Remember what node was talking to the connection, if any.
            else:
                oldnode = None

#            logger.debug("Command_MsgHndlr.handle(): Processing message [%s] as a command..."
#                         % msg.data.strip())

                # Here, we attempt to interpret the message as a server command.
                # For some reason, this try/except clause isn't catching the exception.
                # Ah, it's because the exception is getting raised in a different thread,
                # the commandHandler thread.

            try:
                    # The following accesses the commandHandler by going through
                    # the global CosmicIServer object, defined in module COSMICi_server,
                    # which should be the module invoked to start the program.
                cosmicIServer.commandHandler.process(msg)
            except Exception as e:
                logger.warning("Command_MsgHndlr.handle(): An attempt to process the message [%s] as a command raised an exception; ignoring..." % str(msg))

                # Update the 'component' field in the receiver thread's
                # logging context.  (And also the sender thread's.)
                
            if hasattr(msg.conn, 'node') and msg.conn.node != oldnode:      # If our idea of what node is talking to this connection has changed,
                if msg.conn.node != None:
                    logger.debug("Command_MsgHndlr.handle(): Aha, I now know this connection is for node %d!"
                                 % msg.conn.node.nodenum)
                    component = 'node'+str(msg.conn.node.nodenum)
                    msg.conn.term.set_title("Main connection from Node #%d" % msg.conn.node.nodenum)    # Is this even doing anything now?
                else:
                    component = 'unknown'

                    # The following updates the '.component' logging
                    # context field for BOTH the current (receiver)
                    # thread, as well as the associated sender thread
                    # (the same object as the connection itself).

                msg.conn.update_component(component)

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^            
# End class Command_MsgHndlr
#-----------------------------

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # End of message handler definitions for use by MainConnHandler.
    #====================================================================

    #====================================================================
    #   MainConnHandler                                 [public class]
    #
    #       An object of class MainConnHandler serves as the primary
    #       connection handler for new connections from nodes (or
    #       test clients) to the main port of the central server.
    #
    #       At the moment, all that a MainConnHandler does, in its
    #       .handle(<conn>) method, is the following:
    #
    #           1) Opens up a new TikiTerm window named
    #               "Main Server Connection #0" (or similar)
    #               on which will be displayed I/O sent via
    #               this connection.
    #
    #           2) Registers three MessageHandler objects to
    #               handle messages sent via this connection:
    #
    #               a) An Acknowledge_MsgHndlr object, which
    #                   simply replies to each incoming message
    #                   with an "ACK ..." response.
    #
    #               b) A TermDisp_MsgHndlr object, which echoes
    #                   each incoming (and outgoing) message to
    #                   the above terminal.
    #
    #               c) A Command_MsgHndlr object, which passes each
    #                   message to the cosmicIServer.commandHandler
    #                   worker thread for execution.
    #
    #              One reason for not doing all these in a single
    #              handler is to allow any of them to be removed
    #              dynamically; e.g., if the server is put into
    #              background mode, the TermDisp_MsgHndlr can be
    #              taken down, and added back later if the GUI is
    #              started back up.
    #
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class MainConnHandler(communicator.BaseConnectionHandler):
    def handle(inst, conn:communicator.Connection):

        (sender_ip, sender_port) = conn.req_hndlr.client_address
        clientaddr = "%s:%d"%(sender_ip, sender_port)

        logger.debug("MainConnHandler.handle(): Handling a new main server connection from %s..." % clientaddr)

            # At this point, the connection doesn't yet know what node it's serving.
            # (Although if we were smart, in some cases we might be able to guess it
            # from the IP address, if the node has connected previously from that addr
            # and its DHCP address hasn't been reassigned in the meantime).

        conn.node = None    # Means, not yet determined.

            # Pop up a new TikiTerm window for displaying this connection's I/O.

        title = "Main Server Connection #%d from %s" % (conn.cid, clientaddr)
            # -Later we will want to change the title to include the node # (once we know it).
            
        logger.debug("MainConnHandler.handle(): Popping up a new terminal window named [%s]..."%title)
        conn.term = tikiterm.TikiTerm(title=title, in_hook=conn.sendOut)
            # -The in_hook assignment causes input lines typed by the user to be
            #  sent out to the remote client over the connection's return path.

            # Register our message handlers.

        logger.debug("MainConnHandler.handle(): Registering main-server message handlers...")
        #conn.addMsgHandler(Acknowledge_MsgHndlr())     # Replies to lines with ACK commands
        #   ^- This is commented out to avoid excessive return traffic 
        conn.addMsgHandler(TermDisp_MsgHndlr())         # Displays lines on terminal
        conn.addMsgHandler(Command_MsgHndlr())          # Processes lines as command
        
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# End class MainConnHandler.
#----------------------------

    # We have to override the request-handler class in order to close
    # the terminal window automatically if the socket closes.

class MainSrvReqHandler(communicator.LineCommReqHandler):
        # What to do on the way out of the request-handling loop
        # (e.g. after the socket stops working).
    def finish(inst):
        logger.debug("MainSrvReqHandler.finish(): Getting ready to close the connection's terminal window...")
        style = tikiterm.TikiTermTextStyle(tikiterm.Yellow, tikiterm.Red)
        inst.conn.term.put("\nCONNECTION STOPPED FUNCTIONING; CLOSING THIS TERMINAL WINDOW IN 10 SECS...\n", style)
        time.sleep(10)
            # Destroy the lil' terminal window for this connection that we created earlier.
        logger.debug("MainSrvReqHandler.finish(): Now I'm going to actually close the terminal window...")
        inst.conn.term.closewin()    
                # Above, we are assuming that MainConnHandler.handle() has already run
                # and has created the connection's TikiTerm window.
                
# End class MainSrvReqHandler.       

    #====================================================================
    #   MainServer                                      [public class]
    #
    #       The MainServer is a LineCommunicator that waits on
    #       COSMO_PORT for any node to request to initiate its
    #       main server connection.
    #
    #       A single ConnectionHandler is registered, which
    #       registers three MessageHandler objects for each connection:
    #       one of them is a simple Acknowledge_MsgHndlr, which sends
    #       an immediate 'ACK' message reply to each message back to
    #       the node; the 2nd MessageHandler is a TermDisp_MsgHndlr,
    #       which displays the incoming (and outgoing) messages in a
    #       virtual terminal window created for this purpose.
    #       Incoming and outgoing messages are displayed in different
    #       colors; the 3rd MessageHandler is a Command_MsgHndlr,
    #       which simply routes the messages to the commandHandler,
    #       which is the CosmicIServer's central command-handling
    #       worker thread.
    #
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class MainServer(communicator.LineCommunicator):

        # Override some LineCommunicator class variables with new defaults for initializer.

            # Default role for main server's listener thread.
            
    defaultRole = 'mnSrv'                   

            # Default listen address for main server.

    defaultAddr = (sitedefs.MY_IP, ports.COSMO_PORT)

        # The only reason we need to extend LineCommunicator's
        # __init__() here is to provide it with the server's
        # address.  Would it be cleaner to have LineCommunicator
        # check for attribute .defaultAddr, and use it if it is
        # defined?  Not clear.  But this way takes less code.

    def __init__(self, cis=None, myaddr=defaultAddr, role:str=defaultRole):
        logger.debug("MainServer.__init__(): Initializing for role [%s]."
                     % role)
        self.cis = cis
        self.role = role
                #-> This server attribute will get used as a base role
                #        string for any listener threads that we create.
                
        communicator.LineCommunicator.__init__(self, myaddr, role,
                                               reqhandler_class=MainSrvReqHandler)

    def setup(self):    # After initialization of MainServer,
        self.addConnHandler(MainConnHandler())
            #_ Add a new MainConnHandler() to handle the connection.

    def start(self):
        
            # Include our IP address and port number in the log file.  
            # Helps us distinguish test runs carried out at different sites.
        
        logger.normal("Starting main TCP server, listening at %s:%d." %
                          self.server_address)

        self.startListening()
            #_ Go ahead and start accepting connection requests in a background thread.
        
# End class MainServer.

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# End module mainserver.py.
#===========================================================================================
