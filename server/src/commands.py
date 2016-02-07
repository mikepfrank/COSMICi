#=============================================================================
#   commands.py                                 [python module source code]
#
#       This module performs command-line processing & execution for
#       the COSMICi server.  It is highly interdependent with the
#       main (COSMICi_server) module.
#
#       All commands are executed by a special worker thread, the
#       CommandHandler (class definition below).  (However, it may
#       delegate tasks to other workers in the system, as needed.)
#
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

                        # Used at/in:               Used names
                        # ------------------        -----------------------------
import logmaster        # (module level)            getLogger(), WarningException
import worklist         # (module level)            Worker
import communicator     # Command.__init__()        Message()
import threading        # CommandHandler.process()  current_thread()
import timestamp	# ?			    ?

    #===================================================================
    #   Global constants, variables, and objects.       [code section]
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

global logger           # The logger (logging channel) for this module.
global cosmicIServer    # The main CosmicIServer object.
global cis              # More concise abbreviation for the above.


        #====================================================================
        #   Exported names.                                [special global]
        #
        #       Names we define that other modules might want to use.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

__all__ = ['EmptyCommand',                  # Exception classes.
           'Command', 'CommandHandler',     # Regular classes.
           'commandHandler'                 # Global objects.
           ]


        #====================================================================
        #   logger                                          [private global]
        #
        #       A logger, subordinate to the main application logger,
        #       for logging messages posted from within this module.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

global logger
logger = logmaster.getLogger(logmaster.appName + ".cmds")


        #====================================================================
        #   cosmicIServer, cis                              [private globals]
        #
        #       This will be a copy of the main CosmicIServer object
        #       from the COSMICi_server module.  It gets initialized
        #       in the initializer for commandHandler, which is called
        #       from the initializer for cosmicIServer, so we know that
        #       the cosmicIServer instance has already been created at
        #       that point.
        #
        #       cis is just a convenient abbreviation for cosmicIServer.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

global cosmicIServer, cis
cosmicIServer = None        # Will be initialized in CommandHandler.__init__()
cis = cosmicIServer         # Abbreviation.


    #==================================================================
    #   Class definitions.                          [code section]
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #==================================================================
        #   EmptyCommand                        [public exception class]
        #
        #       This InfoException is thrown by
        #       CommandHandler.process() when it is given a message
        #       that is empty or contains only whitespace.  This
        #       situation is unexpected, but can be safely ignored.
        #       It tends to happen when a connection is closing.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class EmptyCommand(logmaster.InfoException):
    defLogger = logger
    

        #===================================================================
        #   Command                                         [public class]
        #
        #       Class of objects that represent individual command lines
        #       sent from sensor nodes to the central server.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class Command:

    #-----------------------------------------------------------------------
    #   Instance data members:                      [class documentation]
    #
    #       msg         - The text message containing the command line.
    #       cmdString   - Command line as a string (sans trailing
    #                       newline).
    #       cmdWords    - Command as a sequence of (whitespace-delimited)
    #                       words.
    #       cmdName     - Command type string, a single word.
    #       cmdArgs     - Command argument strings, a sequence of words.
    #
    #------------------------------------------------------------------------

        #--------------------------------------------------------------------
        #   Instance initializer.                   [special instance method]
        #
        #       The Command initializer parses the input message
        #       (which should be a text line message as produced by a
        #       LineCommunicator, not a binary message as would be
        #       produced by a regular Communicator - although that may
        #       be supported in some future version) as a sequence
        #       of whitespace-separated words, the first of which is
        #       interpreted as a command name, and the rest as a list
        #       of arguments.  (How the arguments are interpreted is up
        #       to the handler for the particular command.)  If the
        #       command line is all whitespace, a warning exception is
        #       thrown.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def __init__(inst, msg:communicator.Message):
            # Initialize data members.
        inst.msg = msg                          # Remember the original message.
        inst.cmdString = msg.data.strip()       # Remove leading/trailing whitespace.
        inst.cmdWords = inst.cmdString.split()  # Split on whitespace delimiters.
        if len(inst.cmdWords) == 0:
            raise EmptyCommand("commands.Command.__init__(): List of "
                               "command words is empty!  Can't determine "
                               "command name.")
        inst.cmdName = inst.cmdWords[0]         # Interpret 1st word as command name.
        inst.cmdArgs = inst.cmdWords[1:]        # Rest of words are argument list.
    # End Command.__init__()
    
# End class Command
       

        #========================================================================
        #   CommandHandler                                      [public class]
        #
        #       An object of class CommandHandler is a special kind of
        #       Worker thread whose job is to parse and execute complete
        #       command lines (or in the future, also binary format
        #       command packets) that may be sent to it from any of the
        #       following sources:
        #
        #           1) Interactive user commands typed on STDIN
        #               (normally, in the main GUI console window).
        #               (Presently not supported.)
        #
        #           2) Commands triggered by other GUI operations
        #               (button presses, menu events).
        #               (None yet supported.)
        #
        #           3) Command messages sent to us from a node via
        #               its main server connection. - This is all
        #               that is really working at the moment.
        #
        #           4) Binary-format command message packets sent to
        #               us from a node's FEDM (Front-End Digitizer Module)
        #               via its UART-BRIDGE connection to the server.
        #               NOTE: We are descoping binary messages for now.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class CommandHandler(worklist.Worker):
    defaultRole = 'cmdHndlr'    # Role string of Worker thread.

        #----------------------------------------------------------------------
        #   .__init__()                              [special instance method]
        #
        #       This retains a reference to the CosmicIServer instance
        #       we are working for, and then does the usual initialization
        #       for Worker instances.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def __init__(inst, *args, role=None, cosmiciserver=None, **kwargs):
        
        global cosmicIServer, cis
        inst.cis = cis = cosmicIServer = cosmiciserver

        if role==None: role = inst.defaultRole
        
        worklist.Worker.__init__(inst, *args, role=role, **kwargs)


        #----------------------------------------------------------------------
        #   .process()                               [public instance method]
        #
        #       Parses and executes a given message (of the text-string
        #       line variety, as produced by LineCommunicator) as a
        #       command to the COSMICi server.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
                 
    def process(this, msg:communicator.Message):

            # If we're not already in the CommandHandler worker thread, then
            # do the work in that thread, in the background.
        
        if threading.current_thread() != this:          # Ensure we're in worker thread.
            this(lambda: this.process(msg))
            return

        self = this     # Our thready self is this very object that we are operating on.

#        logger.debug("CommandHandler.process(): Processing the message: [%s]..." % msg.data.strip())

        try:
            cmd = Command(msg)     # Parse message into command/argument words.
        except EmptyCommand:
            logger.info("CommandHandler.process(): Ignoring empty command [%s]." % msg.data)
            return

            # For the moment, we are assuming that all commands are originating
            # from sensor nodes, and that the first argument to every command
            # is the node's ID (0,1,2,3).  However, this is really an unnecessary
            # convention for all but the POWERED_ON message, because all subsequent
            # messages from a given node will be received on a Connection that is
            # already associated with that node.  So, consider changing this.  It
            # would require some extensive rewriting though.  Also, even if we don't
            # do that, really, we should check for the node number only if this is a
            # command that isn't coming from the user (operator of server app), as
            # opposed to coming from a remote node.  Should Messages be marked
            # with their source?  Or should we just be more flexible in our parsing?
            # Some commands may not make sense to associate with nodes at all, e.g.
            # a server shutdown command.  Need to think this through properly, and
            # figure out what's really the right way to handle things.

        nodenum = self.parseNodeNum(cmd)    # Extract node number from command line.
            #\_ Also updates component in log context.

            # Now that we know the node number that this command claims to be coming
            # from, we take this at face value, and assume that the entire connection
            # on which we received that message is the main connection associated with
            # that node number, and change the connection window's title accordingly.
            # Please observe that this is a very brittle thing to do, because it only
            # really makes sense for node-specific commands received over a MainServer
            # connection.  See the comment above the previous line of code.  So, for
            # example, if the user tries to type a command on the console, the following
            # line will at present cause the command-handler thread to raise an exception
            # and exit, effectively crippling the server.

        if hasattr(msg.conn, 'term'):   # Is the connection this message came from even associated with a terminal widget?
            msg.conn.term.set_title("Node #%d Main Server Connection #%d" % (nodenum, msg.conn.cid))

            # Finally, we are ready to try dispatching the command for execution.
        
        try:            
                # Note to self, the "msg" above, a Communicator message,
                # does not have exactly the same fields as the original
                # Message class objects defined in this file.  This may
                # cause problems.  Need to fix them. - Obsolete comment?

            self.dispatch_command(cmd)

        except Exception as e:
            logger.error("CommandHandler.process(): Caught an exception [%s] while dispatching command [%s].  Ignoring." % (str(e), cmd.cmdString))
            
            
        finally:    
                # Most command handlers will temporarily change the "component"
                # field in this thread's logging context to the name of whatever
                # node sent the command, to facilitate debugging.  Here, we change
                # it back to "server" to avoid confusion when debugging the command
                # parse-and-dispatch process.
                
            logmaster.setComponent("server")

    # End CommandHandler.process().

        #-------------------------------------------------------------------
        #   .dispatch_command()                       [public instance method]
        #
        #       Process a line that was just received, interpreting it
        #       like a command line.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            
    def dispatch_command(self, cmd):

# This work is now done in the Command() constructor instead.
#        cmd.cmdWords = cmd.cmdString.split()    # Get list of whitespace-separated words of message.
#        if len(cmd.cmdWords) == 0:
#            logger.error("Received empty list of command words; ignoring.")
#            return
#        cmd.cmdName = cmd.cmdWords[0]       # First word is the command name.
#        cmd.cmdArgs = cmd.cmdWords[1:]      # Arguments: List of all words after the first.

        # The following code is organized roughly in the order in which we expect
        # a given message will be first received within a given run.

        if cmd.cmdName == 'POWERED_ON':             # First, a node powers up.
            self.handleNodeOn(cmd)

        elif cmd.cmdName == 'LOGMSG':               # Then it will start sending us log messages,
            self.handleLogMsg(cmd)
            
        elif cmd.cmdName == 'HEARTBEAT':            # and heartbeats (if we can figure out how to implement them).
            self.handleHeartbeat(cmd)

        elif cmd.cmdName == 'BRIDGE_MODE':          # And whenever it changes its bridging mode,
            self.handleBridgeMode(cmd)              # it'll send us one of these messages.
            
            # We need to add some code here to handle a NODE_TYPE command,
            # by which the Nios firmware informs us of which type of node
            # it is implementing, "CTU_GPS" or "FEDM".  This information
            # should then be passed to the node model so it can refine
            # itself.

        elif cmd.cmdName == 'PONG':                 # In the meantime, it will respond to PINGs.
            logger.warning("Command PONG not yet implemented; ignoring.")
            
        elif cmd.cmdName == 'FEDM_POWERUP':         # Then eventually the Front-End Digitizer Module will relay its powerup message,
            logger.warning("Command FEDM_POWERUP not yet implemented; ignoring.")
            
        elif cmd.cmdName == 'FEDM_HEARTBEAT':       # and start relaying us heartbeats as well.
            logger.warning("Command FEDM_HEARTBEAT not yet implemented; ignoring.")
            
        elif cmd.cmdName == '1ST_SYNC':             # Eventually, the user will turn on the CTU, and it will start sending sync pulses.
            logger.warning("Command 1ST_SYNC not yet implemented; ignoring.")
            
        elif cmd.cmdName == 'PULSE_DATA':           # Stochastically, about every few seconds or so, we hope to get a digitized pulse of PMT data.
            logger.warning("Command PULSE_DATA not yet implemented; ignoring.")
            
        elif cmd.cmdName == 'MISSING_SYNCS':        # Occasionally, expected sync pulses might go missing.
            logger.warning("Command MISSING_SYNCS not yet implemented; ignoring.")
            
        elif cmd.cmdName == 'CALIBRATE_TIMING':     # Once an hour or so, we'll recalibrate the CTU timing.
            logger.warning("Command CALIBRATE_TIMING not yet implemented; ignoring.")

        else:
            logger.error("CommandHandler.dispatchCommand(): Received unknown command word '%s'; ignoring." % cmd.cmdName)
    # End .process_command().

        # Parses the originating node's ID out of the command line.

    def parseNodeNum(self, cmd):

            # Make sure the command even has enough arguments for there to be a
            # node number argument present!
        
        if not len(cmd.cmdArgs) >= 1:
            logger.error("CommandHandler.parseNodeNum(): I expected this command to have at least one argument, a node number.  It doesn't.")
            return None

            # Try parsing the first argument as a node number.  If this fails,
            # log an error and use the invalid node number '-1'.

        try:
            cmd.nodeNum = int(cmd.cmdArgs[0])
        except ValueError:
            logger.error("CommandHandler.parseNodeNum(): I expected the first argument to this command to be a node number, an integer.  It isn't.  Using -1 instead.")
            cmd.nodeNum = -1    # Invalid value.
            return              # No point in setting the component or skipping the arg.

            # Change the component name in this thread's logging context to the
            # name of the node that sent this command.  When we finish processing
            # the command later, we can switch the component back to "server"

        logmaster.setComponent("node#%d" % cmd.nodeNum)

            # Now that we've parsed the node number into its own attribute,
            # it doesn't need to be in the arg list any more.  Strip it off arg list.
            
        cmd.cmdArgs = cmd.cmdArgs[1:]
        
        return  cmd.nodeNum
    #<-- End .parseNodeNum()

        #-------------------------------------------------------------
        #   Command handlers.                   [class subsection]
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

            #-----------------------------------------------------------------
            #   .handleNodeOn()                      [public instance method]
            #
            #       Handles messages of the form:
            #
            #           POWERED_ON <nodenum> <ipaddr> <macaddr>
            #
            #       indicating that a node has just been powered on,
            #       and is ready to begin operation.
            #
            #       The claimed IP address is checked against that of
            #       the message sender, for consistency.  And all the
            #       information given is added to our model sensor net.
            #
            #       In the future, the sensor net model will be stored
            #       persistently, which will allow a node on power-up
            #       to ask us what its node ID number is, given just
            #       its MAC address (say).  (The command protocol will
            #       have to be extended to allow that.)
            #
            #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def handleNodeOn(self, cmd):
        if len(cmd.cmdArgs) != 2:
            logger.error("POWERED_ON has %d arguments after node number; 2 were expected.  Ignoring command." % len(cmd.cmdArgs))
            i = 0
            for cmd in cmd.cmdArgs:
                logger.debug("\thandleNodeOn: Arg #%d is: %s." % (i, cmd))
                cmd = cmd + 1
            return
        
        # First, parse the argument list.
        (arg_ipaddr, arg_mac) = cmd.cmdArgs

        # Next, check to make sure that the node is reporting its own IP address
        # accurately, as a little sanity check.
        (sender_ip, sender_port) = cmd.msg.conn.req_hndlr.client_address
        if (arg_ipaddr != sender_ip):
            logger.warning("Node %d's self-reported IP address %s does not "
                           "match actual IP address %s of message sender!?  "
                           "Using it anyway..."
                           % (cmd.nodeNum, arg_ipaddr, sender_ip))

        # Tell the sensor-net model that the node is turned on.
        cis.sensorNet.nodeOn(cmd.nodeNum, arg_ipaddr, arg_mac, cmd.msg.time)
    # End CommandHandler.handleNodeOn()


            #------------------------------------------------------------------
            #   .handleLogMsg()                      [public instance method]
            #
            #       Handles messages of the form
            #
            #           LOGMSG <nodenum> <level> <depth> <message...>
            #
            #       indicating that a node wants to communicate a log
            #       message to the server console and/or log file.  It
            #       also goes to a special log file reserved for log
            #       messages just from that one particular node.
            #
            #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def handleLogMsg(self, cmd):
        if len(cmd.cmdArgs) < 3:
            logger.error("LOGMSG has %d arguments after node id; at least 3 were expected.  Ignoring command.", len(cmd.cmdArgs))
            return

            # First, parse the argument list.
        
        if (cmd.cmdArgs[0] == '(unset)'):
            logger.error("Received LOGMSG from node with unset node ID.  Ignoring.")
            return
        
        arg_nodenum = cmd.nodeNum
        arg_level = cmd.cmdArgs[0]
        arg_depth = cmd.cmdArgs[1]; arg_depth = int(arg_depth)
        arg_logmsg = " ".join(cmd.cmdArgs[2:])      # Join remaining arguments, delimited by spaces.

#        logger.debug("Received LOGMSG request from node %d at level [%s], depth %d, with contents [%s]." %
#                (arg_nodenum, arg_level, arg_depth, arg_logmsg))

            # Check that the node ID given looks correct, remember when we saw the node.
        cis.sensorNet.verifyNode(arg_nodenum, cmd.msg.sender_ip(), cmd.msg.time)

            # Prefix message with spaces to indent by recursion depth.
        arg_logmsg = ("Node %d: "%arg_nodenum) + "  "*arg_depth + arg_logmsg

            # Generate the log message requested.
        
# Doesn't work b/c NormalLoggerAdapter has no .byname() method!  Fix sometime.
#        logger.byname(arg_level, "Node %d: %s: %s" % (arg_nodenum, arg_level, arg_logmsg))
# This version works, but produces redundant log entries, on uninformative channel "root"
#        logmaster.byname(arg_level, "Node %d: %s: %s" % (arg_nodenum, arg_level, arg_logmsg))
#           ^ Currently commented out because it is redundant with the below, which already
#             goes to the main log file as well as to the node's log file.

            # Also log it to the node's own special logger.
        if arg_nodenum in cis.sensorNet.nodes:
            cis.sensorNet.nodes[arg_nodenum].logger.log(logmaster.lvlname_to_loglevel(arg_level), arg_logmsg)
        else:
            logger.error("Can't log message [%s] for node %d, it doesn't exist in the sensor net model yet!" % (arg_nodenum, arg_logmsg))
    # End CommandHandler.handleLogMsg().


            #--------------------------------------------------------------
            #   .handleHeartbeat()               [public instance method]
            #
            #       Handles messages of the form
            #
            #           HEARTBEAT <nodenum>
            #
            #       indicating just that a node's script is still
            #       running.  (Missing heartbeats for a while may
            #       indicate that a node has gone down, or that
            #       wireless connectivity to the node has been lost.)
            #
            #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
                    
    def handleHeartbeat(self, cmd):
        
        if len(cmd.cmdArgs) != 1:
            logger.error("HEARTBEAT has %d arguments after node id; 1 was expected.  Ignoring command." % len(cmd.cmdArgs))
            return

            # First, parse the argument list.
        arg_nodenum = cmd.nodeNum
        arg_hbnum = int(cmd.cmdArgs[0])

            # Check that the node ID given looks correct, remember when we saw the node.
        cis.sensorNet.verifyNode(arg_nodenum, cmd.msg.sender_ip(), cmd.msg.time)

            # Log the heartbeat.
        #cmd.msg.time = timestamp.CoarseTimeStamp(cmd.msg.time)  # already done
        logger.normal("Heartbeat #%d received from node %d at %s." % (arg_hbnum, arg_nodenum, str(cmd.msg.time)))
    # End CommandHandler.handleHeartbeat()

    def handleBridgeMode(self, cmd):

        if len(cmd.cmdArgs) != 1:
            logger.error("BRIDGE_MODE has %d arguments after node id; 1 was expected.  Ignoring command." % len(cmd.cmdArgs))

            # Parse out the argument list.

        arg_nodenum = cmd.nodeNum
        arg_bmstr = cmd.cmdArgs[0]

            # Check that the node ID given looks correct, remember when we saw the node.
        cis.sensorNet.verifyNode(arg_nodenum, cmd.msg.sender_ip(), cmd.msg.time)

            # Log the event.
        logger.normal("Node %d reports that its bridging mode has changed to %s."
                      % (arg_nodenum, arg_bmstr))

            # Inform the model of the Wi-Fi module that its bridge mode has changed.
            # First, we have to translate the bridge mode strings from bridges.uwi
            # into the codes that model.py deals with.

        if arg_bmstr == 'NORMAL':       # The mode that bridges.uwi calls 'normal',
            model_bm = 'DEFAULT'        # model.py calls 'default'.  It's not nominal for us.
        elif arg_bmstr == 'UART-ONLY':  # For this mode,
            model_bm = 'UART'           # model.py uses a shorter name.
        elif arg_bmstr in ('NONE', 'TREFOIL', 'FLYOVER'):
            model_bm = arg_bmstr        # These mode names are unchanged.
        else:
            model_bm = 'UNSUPPORTED'    # Some other bridge mode; we don't support it.
        
        cis.sensorNet.nodes[arg_nodenum].wifi_module.bridgeMode_is(arg_bmstr)

    #<- End def handleBridgeMode()
        
            #-------------------------------------------------
            # Add additional command handlers here as needed.
            #-------------------------------------------------

    # End CommandHandler.handleHeartbeat().
# End class CommandHandler.

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   End module commands.py.
#======================================================================================
