#!/usr/bin/python
#|  NOTE: The above path must link to a python3.1 series interpreter.
#|******************************************************************************
#|                                  TOP OF FILE
#|******************************************************************************
#|
#|      FILE NAME:      COSMICi_server.py,      [python script source code]
#|                      COSMICi_server.pyw                   
#|
#|      SYNOPSIS:
#|
#|          This file is the main program file for the central server
#|          application for the COSMICi project.
#|
#|       Note: These two files should be identical.  To enforce this,
#|       on Windows, we can create the first file as a hard-link to the
#|       second (or vice-versa) by using the command:
#|
#|           mklink /h COSMICi_server.pyw COSMICi_server.py
#|
#|       and similarly with a "ln" command on UNIX-like platforms.  The
#|       only difference between these files is that the python interpreter
#|       will not automatically create a console window for the filename
#|       ending in .pyw, due to that extension being used.  But a console
#|       window should not be needed anyway, since we create our own in
#|       a TkInter-based GUI.  If the main window does not come up, run
#|       the .py version of the script instead to see prior debug output
#|       in the normal Python console window.
#|
#|           NOTE:  Currently one should always run COSMICi_server.py
#|       instead of COSMICi_server.pyw, since at present one must close
#|       the Windows console window in order to stop the server application.
#|
#|   Programming language:     Python 3.1.1-4
#|                               (other versions not yet tested)
#|
#|   Operating systems:        Microsoft Windows Vista Ultimate SP1,
#|                             Microsoft Windows XP 2002 Professional SP3
#|                               (others not yet tested)
#|
#|   Description:
#|
#|       (Some future version of) this server will start up an NTP client on
#|       the local host, if not already started, and makes sure the system
#|       time is synchronized with the NTP time source, to an accuracy of
#|       within about +/- 10 ms.  (Note: Starting/configuring NTP may require
#|       Administrator privileges on the local host.)
#|
#|           [WARNING: The above feature is not yet implemented.  In the
#|           meantime, the local NTP client must be manually configured.
#|           However, it can be implemented without too much difficulty
#|           using the os.system() function on platforms with built-in
#|           support for NTP, such as Windows Vista.]
#|
#|       Then, it starts a thread which waits for incoming connections
#|       from COSMICi sensor nodes on a designated TCP port (for now, port
#|       "COSMO" = 26766), and starts a new thread to process messages sent
#|       over the connection, and lets the remote side close the connection
#|       when ready, after which the receiver thread is retired.
#|
#|           (NOTE: Currently the Wi-Fi modules never close their initial
#|           connections, but leave them open indefinitely, for purposes
#|           of sending log messages and heartbeats from the Wi-Fi script,
#|           as well as for receiving commands from the server.)
#|
#|       It also spawns additional servers as needed to listen on additional
#|       (node-specific) ports for connections from the nodes for sending
#|       auxilliary I/O and UART data streams.  It opens new terminal windows
#|       as needed for display of data streams and commanding of nodes.
#|       Future versions may feature a more extensive GUI.
#|
#|       Incoming data is logged to a set of files, possibly after performing
#|       some preprocessing of it.  Future versions may display visualizations
#|       of the incoming data in real-time.
#|
#|       The sensor node messages may be of these types defined so far:
#|
#|          POWERED_ON <nodenum> <ipaddr> <macaddr> - Declares that the node,
#|               which thinks it has node ID number <nodenum>, IP address
#|               string <ipaddr>, and MAC address string <macaddr>, has just
#|              powered up.  This should always be the very first message sent
#|              by the node after powering up.  The server should check to make
#|              sure the IP address reported matches the one the message was
#|              received from, as a sanity check for DHCP.  The server should
#|              also update the node's status in its records.  See also the
#|              FEDM_POWERUP message below.
#|          
#|           LOGMSG <nodenum> <level> <depth> <message...> - This simply transmits a
#|              diagnostic log message and associated log level to the server for
#|              processing and incorporation in the output stream and/or log file.
#|              The logging level <level> should be one of CRITICAL, UWSERR,
#|              ERROR, WARNING, NORMAL, INFO, or DEBUG corresponding to the
#|              logging levels we use.  The <message> may be any sequence of ASCII
#|              text words.  (Any whitespace will be treated as single spaces.)
#|              We create a log file for each node, in addition to the main log.
#|              The <depth> is a number indicating how deep the script was in its
#|              procedure-call stack at the time the log message was generated.
#|              This may be used for generating indents in the log file.
#|
#|          HEARTBEAT <nodenum> <hbnum> - This is a mesage that may be optionally
#|              transmitted by each node once per predefined interval (e.g. once a
#|              minute), just to declare that its CPU is still up and running.  We
#|              may want to do this more rarely or not at all, however, if we want
#|              to save power.  The heartbeat number should increment each time the
#|              heartbeat is sent; can be logged as a way to track roughly how long
#|              the node thinks it has been on.
#|
#|           BRIDGE_MODE <nodenum> <bmname> - The node's Wi-Fi module should send
#|               this message to the server each time its bridging configuration
#|               changes, since this affects how the server can communicate with
#|               the Wi-Fi module as well as to the host behind it.  The bridge
#|               mode name <bmname> is as defined in bridges.uwi in the Wi-Fi
#|               autorun script.  The server reacts to this message by simply
#|               remembering the change in its internal model of the Wi-Fi module.
#|
#|       The following message types have also been tentatively defined, but are
#|       not yet implemented or used anywhere so far.  They may or may not make
#|       it as-is into the final product.
#|           UPDATE 3/28/12: The below list is way out-of-date and needs to be
#|       updated to fit the actual present set of messages handled currently.
#|
#|       PONG <nodenum> <seqno> - Sent by the node in response to an explicit
#|           PING <seqno> command.  The <seqno> is a simple sequence number
#|           intended to distinguish responses to different PING requests.
#|
#|       FEDM_POWERUP <nodenum> - This simply tells the server that the node's
#|           Front-End Digitizer Module has also powered up correctly and is
#|           able to communicate with its wireless module.  The node sends this
#|           message after receiving the POWERUP (0x01) message from the FEDM.
#|           At this point (and no earlier!) it is OK for the operator to start
#|           the data collection run, by manually switching on the central
#|           timing unit.
#|
#|       FEDM_HEARTBEAT <nodenum> <hbnum> <status> - This is like HEARTBEAT,
#|           except that it communicates more specifically that the front-end
#|           digitizer module (FEDM) within the given node is itself sending
#|           its heartbeat.  <status> is a FEDM status indicator, where
#|           0 = powered up but 1st sync not yet detected, 1 = normal running,
#|           2 = synchronization lock has been lost, >2 = other condition.
#|
#|       1ST_SYNC <nodenum> - Declares that the node <nodenum> has just
#|           received its first clock synchronization
#|           pulse from the installation's CTU (Central Timing Unit).  Node
#|           number N (N=0,1,2,3) will pause 100*N ms after receiving the 1st
#|           sync pulse before sending it to the server, so that the first
#|           (node 0's) 1ST_SYNC message won't be slowed down by congestion
#|           from the others.  Instantly after receiving the 1ST_SYNC message
#|           from node 0, the central server will register the start time of
#|           the run with reference to the NTP clock.  The absolute time of
#|           all subsequent sensor events in this run are measured relative
#|           to this run start time, which should be correct within a few
#|           ms (dependent on the processing & network latency between sensor
#|           & server.  One second after receiving the first sync pulse, each
#|           node will begin collection of real data.
#|
#|       MISSING_SYNCS <nodenum> <howmany> - If a node fails to receive sync
#|           pulses at roughly
#|           the expected times (defined as every 409.6 us after the 1st),
#|           it should tally up these missing-sync events, and report their
#|           accumulated number to the central server periodically (at most
#|           once per second is recommended).  This is for purposes of error
#|           reporting.  Data doesn't need to be invalidated unless a large
#|           proportion (over 50%) of sync pulses aren't received over a given
#|           period, since this means that shower events occurring within that
#|           interval can't be timed relative to each other within the required
#|           ns accuracy.  Nodes should automatically fill in missing sync
#|           events.  (E.g., if a node's FPGA clock is 100MHz, then 40,960
#|           clock cycles after the previous sync event, it should pretend
#|           that another one has occurred, even if no sync pulse was received
#|           at all during that clock cycle.)
#|
#|       CALIBRATE_TIMING <nodenum> <syncs> - Every predefined interval (once per hour, say),
#|           regardless of shower activity, each node should send this message,
#|           which should contain the current count of the number of 409.6us
#|           sync intervals that have occurred since the start of the run.
#|           Node N should delay this message by 100N milliseconds in order
#|           to avoid network congestion.  The central server uses the 
#|           messages from each node to re-align that node's sync count with
#|           the absolute NTP reference.  All nodes' sync counts should
#|           always remain aligned (in absolute time) to well within the
#|           409.6 window; if not, this means that somehow the number of sync
#|           events at different nodes have become inconsistent, and all
#|           subsequent events from the node will fail to be alignable with
#|           the others.  This could happen if, for example, a node's view of
#|           the CTU's LED pulser was blocked for long enough for that node's
#|           clock to drift by a sync period or more relative to the other nodes.
#|
#|       PULSE_DATA <nodenum> ... - Each time a shower event pulse is received (or optionally,
#|           at periodic intervals, to save power in the wireless transmitter),
#|           a node transmits the raw digitized pulse shape information
#|           (together with the pulse timing information, consisting of sync
#|           event count, clock cycle count since the last sync pulse, and
#|           intervals from reference clock edges to the last sync pulse and
#|           the first level-crossing in the current shower pulse) to the
#|           central server.  The server logs the data, and optionally also
#|           does real-time processing & visualization of the data.
#|
#|       Other message types may be defined later, to communicate various error
#|       conditions which may occur.
#|
#|       Later on, an interactive web server interface may be added.
#|
#|
#|   Implementation notes:
#|
#|       We build this on top of the Python socketserver module, class
#|       TCPServer, together with the ThreadingMixIn helper class for
#|       multithreading support.  The GUI is based on TkInter with some
#|       additional custom modules to better support multithreading.
#|
#|   Revision history:
#|
#|       v0.1, 1/29/12 (Michael P. Frank) - Finally started a revision
#|           history.  The server has actually been evolving for a long
#|           time before this point.
#|
#|       v0.2, 2/15/12 (MPF) - I am currently in the middle of instrumenting
#|           the server towards the point of remotely configuring the GPS
#|           module in the CTU.
#|
#|   Coding to-do:
#|
#|       [ ] Add interactive commanding of the server via command lines
#|           typed on stdin.  (Later, additional GUI widgets can translate
#|           button presses, etc., to the appropriate command lines.)
#|
#|       [/] After receiving the power-on message for a node, we should set
#|           up some threads to begin listening on additional ports to
#|           receive bridged copies of their auxio and UART data streams.
#|           These streams can then be used to remotely command & monitor \
#|           the Wi-Fi board (viaauxio) and/or the FPGA board itself (via
#|           UART).
#|               UPDATE 9/18/09: The auxilliary servers have been
#|           implemented using the new Communicator class, but we still
#|           need to pop up terminal windows for them.  The TikiTerm class
#|           is available but noes not provide input and has not yet been
#|           integrated.
#|               UPDATE 2/15/12: This was implemented a long time ago and
#|           has been working fine (more or less) for a long time now.
#|
#|       [ ] For each node, keep track of when we last received a heartbeat
#|           from it, and what the last heartbeat number received was.
#|           (Ditto for PONGs.)
#|               UPDATE 9/18/09: This still needs to be done, and also the
#|           main server heartbeat needs to be moved to its own thread so
#|           that we can reserve the main thread for processing user input
#|           command lines from stdin.
#|               UPDATE 3/27/12: The main server heartbeat was moved to its
#|           own thread a long time ago.  We're still not bothering to
#|           monitor heartbeats from the Wi-Fi script - this is a low
#|           priority task right now, since the script is pretty stable.
#|           Likewise we're not bothering with the PING/PONG protocol yet.
#|
#|       [/] Want to give the interactive user the ability to remotely
#|           command the node.  Could be done (with delay) in replies to
#|           heartbeat messages, or more quickly by opening a reverse
#|           connection to the node's IP.  However, there doesn't appear
#|           to be an interrupt (event) in UWScript to detect incoming
#|           connections, other than via the web server.  We could busy-
#|           wait for them using nonblocking sockets, but this is probably
#|           inefficient with regards to power consumption.  We may have
#|           to resort to using the web interface for remote wireless
#|           control.
#|               UPDATE 9/18/09: The current plan is to use the return
#|           path of the AUXIO auxilliary I/O connection to send commands
#|           to the node.  A partial command interpreter in UWScript is
#|           already working.  We just need to implement the ability to
#|           accept user input in TikiTerm and pass it to the node.
#|               UPDATE 12/18/11: That was implemented earlier this year.
#|               UPDATE 2/15/12: The preferred method now to command nodes
#|           remotely is through the return path of the UART bridge
#|           connection when the Wi-Fi board is in TREFOIL mode, since this
#|           input channel goes to the Wi-Fi script's STDIN which is checked
#|           for data most often; these commands can then be interpreted by
#|           the Wi-Fi script and/or relayed to the sensor node host CPU.
#|
#|       [ ] Write command handler to respond to PONG and other
#|           unimplemented messages that may be received from nodes.
#|               UPDATE 9/18/09: All of the commands coming from the FEDM
#|           (FPGA board) (which we'll expect to receive on the UART-
#|           BRIDGE connection) still need to be implemented.  A means of
#|           displaying the UART data, systematically logging it, doing
#|           analysis & processing of it, and maybe an animated graphical
#|           display of shower direction triangulations and scatter plot
#|           of events on a galaxy map all still needs to be done.
#|               UPDATE 2/15/12: The PONG message has been descoped; we are
#|           working now on interpreting messages from the CTU & FEDM
#|           appropriately to execute a startup sequence for the whole
#|           system, which includes initializing the GPS module.
#|               UPDATE 3/27/12: GPS messages are handled now, and some
#|           skeleton code is there for handling the FEDM messages and the
#|           CTU's PPSCNTR message.  We still need to write the code to do
#|           something meaningful with that data.
#|
#|      [ ] See if I can figure out a way to instrument threads to catch
#|           exceptions causing them to exit, and politely close down their
#|           sockets.
#|               UPDATE 9/18/09: The listener threads can be made to exit
#|           by raising an exitRequested flag, and then making a transient
#|           connection to them from the local host to cause their listen
#|           loops to wake up.  Most of the other threads in the system
#|           do some form of command processing and can be terminated via
#|           similar mechanisms.  With care, we should be able to guarantee
#|           that all child threads get terminated before the main thread
#|           exits.  However, this is not implemented yet.
#|           
#|       [/] Rewrite the main server to use my new general Communicator
#|           interface. (After I'm sure Communicator is working properly.)
#|               UPDATE 9/18/09: Communicator seems to be working now, and
#|           it just needs to be updated to use the new Worker class to
#|           send replies, and to use the logging facility.
#|               UPDATE 9/24/09: This task is mostly done now, although
#|           not yet tested.
#|               UPDATE 2/15/12: This was completed a long time ago.  The
#|           MainServer is totally using Communicator, and this seems to
#|           work robustly.
#|
#|===============================================================================

RAW_DEBUG = 0

#if RAW_DEBUG:
#    if __name__ == "__main__":
#        print("Executing file [%s] as top-level module __main__..." % __file__)
#    else:
#        print("Importing file [%s] as module COSMICi_server..." % __file__)

    #=================================================================
    #   Imports					[code section]
    #
    #       Load and import names of (and/or names in) various
    #       other python modules and pacakges for use from the
    #       present module.
    #
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #================================================
	#   Imports of standard python library modules.
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

if __name__ == "__main__":
    if RAW_DEBUG: print("__main__: Importing standard Python library modules (time, sys, threading)...")

                        # Using entity in cur. module       Used names from imported module
                        # -----------------------------     -------------------------------
import time             # CosmicIServer.run()               time.sleep()
import sys              # main()                            sys.stdout, .stderr, etc.
import threading        # main()                            threading.active_count(), etc.


        #================================================
	#   Imports of custom modules.
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

if __name__ == "__main__": 
    if RAW_DEBUG:
        print("__main__: Importing custom modules (utils, logmaster, ",
            "guiapp, tikiterm, cosmogui, timestamp, commands, heart, worklist)...", file=sys.stderr)

                        # Using entity in cur. module       Used names from imported module
                        # -----------------------------     -------------------------------
#from ports import *     # ?                                 ?
import utils            # (module level)                    utils.get_hostname()
import logmaster        # main()                            logmaster.configLogMaster(), ...
import guiapp           # main()                            guiapp.initGuiApp(), .guibot, ...
import tikiterm         # main()                            tikiterm.TikiTerm()
import cosmogui         # main()                            cosmogui.setLogoImage
import timestamp        # CosmicIServer.__init__()          timestamp.CoarseTimeStamp()
import commands         # CosmicIServer.__init__()          commands.CommandHandler()
# The below is moved to later in the file, so it can see some of our module's globals.
#import mainserver       # CosmicIServer.run()               MainServer()
import heart            # CosmicIServer.run()               Heart()
import worklist         # CosmicIServer.run()               HireThread()
import communicator     #                                   StreamLineConnection
import mainserver       # run()                             mainserver.MainServer()
import model            # CosmicIServer.__init__()          model.SensorNet()
import broadcaster      # CosmicIServer.__init__()          broadcaster.Broadcaster()
import  runmgr          # CosmicIServer.__init__()          runmgr.RunManager()

# There are additional late imports interspersed later in this file...

    #=================================================================
    #   Exported names.                             [code section]
    #
    #       The special global constant __all__ defines the list
    #       of names from this module that will be imported into
    #       any other modules that do:
    #
    #           from COSMICi_server import *
    #
    #       Some of our submodules circularly import this module
    #       in order to access some of our module globals.
    #
    #       This also serves as documentation of the names that we
    #       expect other module will access, even if they don't do
    #       it using a 'from..import' statement like the above.
    #       In actuality, the other modules may usually just use:
    #
    #           import COSMICi_server
    #
    #       and then reference these names as module attributes.
    #       So the __all__ list may not actually be used.  But we
    #       keep it for documentation purposes, regardless.
    #
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

                                            # Used by:
                                            # ------------------------
__all__ = ['VERSION',                       # Nobody besides us yet.
           'console',                       # cosmogui.setLogoImage()
           'CosmicIServer',                 # (nobody else yet)
           'cosmicIServer',                 # commands.py
           'main'                           # (nobody else yet)
           ]


    #=================================================================
    #   Globals					[code section]
    #
    #       Declare and/or define various global variables and
    #       constants.
    #
    #       The globals used in this program are:
    #
    #           ...   
    #
    #=================================================================

        # I'm not sure these top-level global declarations are really doing anything.
        # (Actually, they do check to make sure these names are not previously used.)
        # And further, I guess they are useful as documentation, at least.

global  UWSERR_LEVEL, UWSERR, VERSION
global  logger, console, cosmicIServer


        #==========================================================
        #   Global constants.                   [code subsection]
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

            #============================================================
            #   New logging level(s).               [global constant(s)]
            #
            #       These are for use by the loghandler and logging
            #       modules.  So far, we only have one application-
            #       specific logging level, name UWSERR for UWScript
            #       errors sent to us by sensor nodes for logging.
            #
            #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # Define a new logging level for UWScript errors received from nodes.

global UWSERR_LEVEL, UWSERR
UWSERR_LEVEL = 45       # For UWScript errors from nodes.  Between ERROR and CRITICAL.
UWSERR = UWSERR_LEVEL
	# - Logging module will get informed about this later, in main().

global VERSION
VERSION = 0.1

        #=========================================================
	#   Global objects.                     [code subsection]
	#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
	
global logger       # A Logger instance that is specific to the current module.
logger = None       # This will get created later, in main().

global console      # The main GUI terminal window brought up by this application.
console = None      # Will get created later, in main().

global cosmicIServer    # A CosmicIServer object, gathers main state of server itself.
cosmicIServer = None    # Will get created in main().


    #=======================================================
    #   Class definitions.                  [code section]
    #=======================================================

        #========================================================================
        #   CosmicIServer                                               [class]
        #
        #       Main class for the core functions of the COSMICi server
        #       application.  The point of this is to gather together most
        #       of the state specific to the server itself (as opposed to
        #       the general application context), and provide it in a single
        #       global object that can be accessed from within different
        #       modules.  Typically, only one instance of this class will
        #       exist at a time in the application.  (However, in the future,
        #       we might support having multiple simultaneous instances
        #       monitoring different sensor networks on different IP
        #       addresses and/or different ports.)
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
                
class CosmicIServer():

    #-------------------------------------------------------------------------
    #   Instance data members:                              [documentation]
    #
    #       serverStartTime:CoarseTimeStamp
    #
    #           Indicates when this server object was first created,
    #           to within a few ms.
    #
    #           (NOTE: I don't know if we really need this - what's important
    #           is when the *run* starts, not when the server starts.)
    #
    #       broadcaster : broadcaster.Broadcaster
    #
    #           This thread object is responsible for broadcasting the
    #           server's IP address to all nodes on the local network,
    #           pretty much continually (once every second) forever
    #           (or until killed).
    #
    #       sensorNet:SensorNet
    #
    #           An object model that tracks the status of all the nodes in
    #           the local sensor net that we know about & are monitoring.
    #
    #           (Eventually, this should have persistent storage capabilities,
    #           so we can recover its state in case the server app needs to be
    #           restarted in the middle of a run.)
    #
    #       commandHandler:CommandHandler
    #
    #           The server's CommandHandler handles various text-format
    #           (and eventually also binary-format) commands that may be sent
    #           to the server telling it what to do, or giving it messages
    #           informing it of various events or conditions.  Currently, these
    #           messages are required to self-identify which node they are coming
    #           from, but in the future we may loosen this requirement (since
    #           nodes may often be identifiable from their IP addresses alone).
    #
    #       mainServer:MainServer
    #
    #           The MainServer takes care of handling the main server
    #           connections, which nodes use to initially get in touch with
    #           the server.  (Once a node's numeric ID is known, additional
    #           "bridge" servers are spawned to receive that specific node's
    #           AUXIO and UART-BRIDGE streams.)
    #
    #       consoleConn:StreamLineConnection
    #
    #           This is a "connection" to the human operator of the
    #           server console via STDIO.  This allows the operator to
    #           type server commands on STDIN, just like remotes nodes
    #           can send server commands via MAIN.
    #
    #------------------------------------------------------------------------

    #---------------------------------------------------------------
    #   Public instance methods.                    [class section]
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #------------------------------------------------------------------
        #   Instance initializer.               special instance method]
        #
        #       This special method is automatically used by python
        #       to initialize the state of any newly created object
        #       of class CosmicIServer.
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def __init__(inst):

        inst.mainServer = None      # Not yet created; do it later in run().
        
            # Remember what time we started the server at, in case we
            # need to know it later.  (Really, what matters most is the
            # timing of the 1st_sync message, later on.)
            
        inst.serverStartTime = timestamp.CoarseTimeStamp(time.time())
        logger.info('CosmicIServer: Server starting at %s.' % inst.serverStartTime)

            # Create the empty sensor net data structure, ready to be filled
            # with sensor nodes once they are detected.
            
        logger.info("Creating empty sensor net data structure...")
        inst.sensorNet = model.SensorNet(cosmiciserver = inst)

            # Create our command handler worker thread.  This guy will
            # respond to commands that may be sent to it from multiple
            # sources, controlling the state of the overall server.
            
        logger.info("Creating central server command handler...")
        inst.commandHandler = commands.CommandHandler(cosmiciserver = inst)

            # Create the StreamLineConnection for STDIO (stdin/stdout only),
            # which allows us to henceforth deal with the STDIO connection
            # to the console user in a manner that is structurally similar
            # to how we deal with MAIN connections from remote notes (in
            # mainserver.py).  In other words, incoming lines are treated
            # as commands to be executed.

        logger.info("Creating StreamLineConnection for operator input via STDIO...")
        inst.consoleConn = communicator.StreamLineConnection(-1,
                                instr=sys.stdin, outstr=sys.stdout,
                                role="cons.sndr", component="user")

            # Add a message handler to our console connection which causes
            # incoming lines of text on STDIN to be interpreted as commands
            # to the server, just as incoming lines of text on any MAIN
            # server connection would be.

        mainserver.cosmicIServer = inst     # Install us in mainserver module
        inst.consoleConn.addMsgHandler(mainserver.Command_MsgHndlr())

            # Before we start actually allowing nodes of the sensor network
            # to make connections, first we have to create & start a critical
            # internal worker thread, the RunManager.  This is because the
            # model proxies for the sensor-net components will try to inform
            # us of various state changes, and we'll need to pass that infor-
            # mation along to the RunManager object.

        inst.runmgr = runmgr.RunManager()   # Creates & starts this worker thread.

        inst.gps_time_good = False  # Don't assume GPS time is initially good.

    #__/ End CosmicIServer.__init__().

        #|--------------------------------------------------------------------
        #|
        #|      .enlistMainThread()            [public instance method]
        #|
        #|          This method transforms the current thread
        #|          (assumed to be the application's main thread)
        #|          into an imitation worker thread, which will
        #|          (after its .run() method is called) begin
        #|          executing tasks on its worklist, just like any
        #|          other worker thread.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def enlistMainThread(inst):

            # Following conditional ensures that we only enlist the main
            # thread at most once.
        
        if not hasattr(inst, 'mainThreadEnlisted') or not inst.mainThreadEnlisted:
            logger.info("Turning thread %s into an imitation Worker thread..." % threading.current_thread())
            worklist.HireThread(threading.current_thread())

            logger.info("%s will now accept tasks to be put on its to-do list..." % threading.current_thread())

            logmaster.setThreadRole("general")    # Meaning our role henceforth is to just do whatever commands we're given.

            inst.mainThreadEnlisted = True

        #<- End if (not already enlisted)
            
    #<- End def CosmicIServer.enlistMainThread().

        # Other entities (outside of the CosmicIServer class) should use these
        # methods to inform the overall server of various important changes to
        # the system state.  We pass this information on to various sub-modules
        # (currently, just the RunManager worker thread) that need to be made
        # aware of those changes.

    def     yo_CTU_is_ready(inst, ctu_node):
        
        logger.normal("The Central Timing Unit (CTU) is ready to accept commands.")

            # Tell the RunManager what node in the sensor network the CTU is at,
            # and tell it that the CTU is ready to accept commands.

        inst.runmgr.yo_CTU_is_ready(ctu_node)

    def     yo_FEDM_is_ready(inst, fedm_node):

        logger.normal("The Front-End Data-Acquisition Module (FEDAM) is ready to accept commands.")
        inst.runmgr.yo_FEDM_is_ready(fedm_node)

    def     yo_GPS_time_is_good(inst):

        if not inst.gps_time_good:
            logger.normal("The Global Positioning System (GPS) module has acquired at least one good time value.")
            inst.gps_time_good = True
            inst.runmgr.yo_GPS_time_is_good()

    def     yo_GPS_time_is_nogood(inst):

        if inst.gps_time_good:
            logger.warn("The GPS module's time value can no longer be assumed to be accurate within +/- 100 ns.")
            inst.gps_time_good = False
            inst.runmgr.yo_GPS_time_is_nogood()
        
        #---------------------------------------------------------------------
        #   .run()                               [public instance method]
        #
        #       This method starts the server actively running its
        #       main listening function.  We also start up the server's
        #       heart-beat function (in its own thread) and its IP address
        #       discovery service (in another thread).  Meanwhile, currently,
        #       the main thread just goes into a Worker loop, so it can be
        #       sent messages by other threads to have it do whatever.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def run(self):

            # Instantiate the server object for handing nodes' main connections.
            # (After this point, nodes or other external entities communicating
            # through them can send us commands along these connections.)

        logger.info("Creating socket server for receiving nodes' main server connections...")
        self.mainServer = mainserver.MainServer(cis=self)

            # Start the server running in a background thread.

        logger.info("Starting the main socket server...")
        self.mainServer.start()             

            # At this point, the server is able to receive and
            # process incoming connection requests from nodes.
            # Display visual confirmation that server is started.
            
        logger.normal("Server is started and is ready to handle incoming messages.")

##            # Create the Broadcaster object, which is responsible for
##            # broadcasting the server's IP address continually (once
##            # a second) on the local network.  It will automatically
##            # start doing its job as soon as it is created.  After
##            # this, nodes can discover us and start initiating
##            # connections.  NOTE: The broadcaster is instead now
##            # created by the DiscoveryService, below.
##
##        self.broadcaster = broadcaster.Broadcaster()

            #-----------------------------------------------------------
            # Start the discovery service, which broadcasts the server
            # IP for a short period whenever a request to do so is
            # detected on a broadcast UDP receive port.
            
        self.discoveryService = broadcaster.DiscoveryService()
        logger.normal("The server discovery service is now started.")
        
        print()     # Insert extra blank line for readability on console.

            # Create our heart "organ" & let it start beating (in its own
            # background thread).  This is just to provide evidence (on
            # screen and in the logs) that the server is still running over
            # a given time period over which nothing else may be happening. 

        logger.info("Creating our heart & letting it start beating...")
        self.heart = heart.Heart()  # Constructor automatically starts thread.

        #------------------------------------------------------------------
        # TO DO: Some other important server tasks that need to be spawned
        #   here are:
        #
        #   [ ] Set up a stdin reader to accept typed user commands
        #           on standard input.  (Really we want to first augment
        #           TikiTerm to provide a TextIOStream that we can
        #           install as the new stdin while the main TikiTerm
        #           console window is open.)
        #           UPDATE 2/16/12:  That last part is done, but we still
        #           haven't implemented any user commands yet, I think.
        #
        #   [ ] Set up a thread (possibly running in SensorNet) to
        #           perodically check nodes' last-received times to
        #           see which nodes to report as AWOL.
        #------------------------------------------------------------------

            # Turn the current (main) thread into an imitation Worker thread,
            # and start running its main loop.  This allows other threads to
            # send work items to the main thread as needed, to have it do
            # things that only the main thread can do, such as sending signals,
            # setting up signal handlers, exiting the process.  It also
            # provides a way for other threads to stop the main thread more
            # cleanly (but perhaps less quickly) than by using
            # _thread.interrupt_main(), which just sends a KeyboardInterrupt
            # exception to the main thread.

        self.enlistMainThread()

            # Should we try to catch exceptions here?  Is it worth it?
        threading.current_thread().run()    # Runs the Worker main loop, which waits for worklist items.

        logger.info("CosmicIServer.run(): Worker mainloop has exited; returning...")
    #__/ End method CosmicIServer.run().


    

        #--------------------------------------------------------------
        #   .shutdown()                     [public instance method]
        #
        #       This method tells the overall COSMICi server to
        #       shut itself down.  This entails the following:
        #
        #           1) Tell our sensorNet model to stop
        #               listening for new bridge connections
        #               from nodes, and to shut down its
        #               existing bridge connections.
        #           
        #           2) Tell the mainServer to stop listening
        #               for new connections, and to shut down
        #               its existing main connections.
        #
        #           3) Tell the CommandHandler thread to close
        #               out its worklist and shut itself down.
        #
        #           4) Shut down the heart (heartbeat thread).
        #
        #           5) Print a message acknowledging that we're
        #               exiting, and cause the server run()
        #               method to return to its caller.
        #

    # .shutdown() NOT YET IMPLEMENTED
        
#__/ End class ComicIServer.


    #=======================================================================
    #  Module-level function definitions.                   [code section]
    #
    #       These functions are not part of any particular class.
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #=========================================================================
        #   main()                                    [module public function]
        #
        #       Main routine of module.
        #
        #       This routine is traditionally called within a module's main
        #       body code, within the context of a conditional like
        #
        #           if __name__ == "__main__":
        #
        #       so it won't be automatically executed when this script is only
        #       being imported as a sub-module of a larger system.
        #
        #       In the case of the present (COSMICi-server) module, main()
        #       does the following:
        #
        #           1.  Initializes the logmaster logging facility.
        #           2.  Creates the guiapp.guibot worker thread for
        #                   managing the graphical user interface (GUI).
        #           3.  Opens a new virtual terminal window (also the
        #                   application's main window) and redirects
        #                   stdout/stderr to it.
        #           4.  Displays the project logo and a welcome message
        #                   as a splash display in the new console window.
        #           5.  Create the CosmicIServer object (which handles the
        #                   real work of the server) and start its main
        #                   loop running.  It should continue indefinitely,
        #                   or until commanded to stop.
        #           6.  Cleanly handles exits from the main loop (either by
        #                   command or by exception), systematically closing
        #                   windows, killing threads, shutting down the logging
        #                   facility, and so forth.
        #
        #       [NOTE: Systematic killing of all program threads in
        #            step 6 is not yet implemented.  This causes problems
        #            where background listener threads cause the python
        #            process to stick around as a zombie process and hold
        #            onto those ports.  This needs to be fixed someday.
        #            In the meantime, we can kill the python process by
        #            closing its Windows console window.]
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

def main():     # Main routine of module.

        # In python, we must explicitly declare all the globals that will get reassigned within 
        # this routine - or else the assignment will just create a new local variable instead!
    
    global logger, console, cosmicIServer

        # Comment out these diagnostic print() statements when development is complete...

    if RAW_DEBUG: print("__main__.main(): Entered application's main routine...")

        #|-------------------------------------------------------------------------
        #|  Configure the logging facility.  This is done first so that we
        #|  can (potentially) do debug logging in everything that follows.

    if RAW_DEBUG: print("__main__.main(): Configuring the 'logmaster' logging module...")

        # Uncomment one of the following three config statements, depending on your needs.
    
        # Don't produce debug output either on console or in log file.
    logmaster.configLogMaster(consdebug = False, logdebug = False, role="startup", component="cosmiApp")

##        # Produce debug output in log file but not on console.
##    logmaster.configLogMaster(consdebug = False, logdebug = True, role="startup", component="cosmiApp")

##        # Produce debug output on both console and log file.
##    logmaster.configLogMaster(consdebug = True, logdebug = True, role="startup", component="cosmiApp")

        #|--------------------------------------------------------------------------
        #|  Unconditionally display a message in the default Python console window
        #|  (usually named something like "C:\Python31\python.exe", depending on
        #|  where the executable for the Python interpreter lives), to explain to
        #|  the user the relevance of this now mostly-superfluous window.
        
    print("\n" +
          "You may now minimize this python.exe window; it's no longer needed.\n" +
          "NOTE: Closing this window will kill the COSMICi server application.\n")

        # In addition to the above configuration, also define a new
        # logging level for low-level UWScript errors on the Wi-Fi nodes.

    logmaster.logging.addLevelName(UWSERR_LEVEL, 'UWSERR')
    logmaster.logging.UWSERR = UWSERR_LEVEL     # This line may not be needed.

        #----------------------------------------------------------------------------
        # Note: Here is how we are planning to use the different
        # available logging levels, for the most part:
        #
        #   50 - CRITICAL - Errors forcing termination of the server app.
        #                       Log message always goes to console and log file.
        #   45 - UWSERR   - Low-level UWScript error.
        #                       Message always goes to console and log file.
        #   40 - ERROR    - Serious error.
        #                       Always goes to console and log file.
        #   35 - NORMAL   - Normal output messages.
        #                       Always goes to console and log file.
        #   30 - WARNING  - Warnings about minor unexpected conditions.
        #                       Always goes to log file, and to console unless console warnings are disabled.
        #   20 - INFO     - Verbose information.
        #                       Always goes to log file, unless verbose info is suppressed.
        #   10 - DEBUG    - Detailed debugging output.
        #                       Suppressed from log file and console, unless console or log debugging are enabled, respectively.
        #--------------------------------------------------------------------------

        # Get a child logger (really a NormalLoggerAdapter) that is specific
        # to the current application ('COSMICi.server').  The point of this is to
        # potentially in the future allow multiple concurrent applications within
        # the system to share a root logger (logging to a shared log file like
        # "COSMICi.log") but also each have their own individual log files (like
        # "COSMICi.server.log").  Nodes also have their own log files under the
        # general 'COSMICi' channel.  Also, this affects what is displayed in the
        # first field of column 3 in the default log file format (it would be "root"
        # for the root ("") logger otherwise).  Finally, different loggers can have
        # their own filters, loghandlers, log level settings, etc., so e.g. we can
        # turn on debugging for one component while leaving it off for another
        # component; echo one component's log messages to a separate file just for
        # that component, etc.  We are not using most of these features yet, but we
        # may need them down the road to help diagnose really complicated problems.

    logger = logmaster.appLogger

        # Log a little header at INFO level before actually doing any real logging.
        # This serves to visually separate different runs in the log file.

    logger.info('')   
    logger.info('='*80)
    logger.info('COSMICi Server is starting up...')

        #-----------------------------------------------------------------------------------
        # Declares (in the log file) that we are now working on behalf of the GUI component.

    logmaster.setComponent("GUI")
    
#    time.sleep(2)

        # Create & start the guiapp module's guibot worker thread.
        # (This is done after the above b/c it may produce debug log messages.)

    logger.info("Starting the GUI application's worker thread...")
#    time.sleep(2)
    guiapp.initGuiApp()         # This creates the guibot, in guiapp.guibot.
    guibot = guiapp.guibot      # Local variable copy
    
        # Create our main terminal window for interactive standard I/O to user.
        # This must be done after initGuiApp().

    logger.info("Creating new GUI-based console window...")
#    time.sleep(2)
    console = tikiterm.TikiTerm(title="COSMICi Server Console",
                       width=90, height=30, # 90x30 chars, a bit bigger than standard 80x24 console.
                           #- This is big enough to show our splash logo and some text below it.
                       )

    logger.info("Redirecting stdout & stderr streams to GUI-based console...")
#    time.sleep(2)

        # Before we actually reassign stdout/stderr streams to print to our
        # new console, we first make sure we have a record of our original
        # stdout/stderr streams (if any), so we can restore them later if/when
        # the console window closes.
    
    if sys.__stdout__ == None:          # If the default stdout is not already set (e.g. we're running under IDLE)
        sys.__stdout__ = sys.stdout         # Set it to our actual current stdout.
        
    if sys.__stderr__ == None:          # Likewise with stderr.
        sys.__stderr__ = sys.stderr
        
    if sys.__stdin__  == None:
        sys.__stdin__  = sys.stdin


        # Have our new console take over the stdout and stderr stream functions.       

    console.grab_stdio()    # stdin not yet supported.
    logmaster.updateStderr()    # Tells logmaster we have a new stderr now.
        # ^- Without this, we could not see abnormal log messages on our new console.

        # Display logo image in console window.
        
#    time.sleep(2)
    guibot(lambda:cosmogui.setLogoImage(console))
    print() # Ends the line that the image is on.

        # OK, GUI-related initial setup is done.  
        #----------------------------------------------------------------
        # Now we have to actually start the server itself.

    logmaster.setComponent("server")    # Log that we're working on the server component.

        # Print spash welcome message on stdout console.
        
#    time.sleep(2)
    print() # Initial newline for readability on console - not logged
    # Using normal() instead of print() in the below copies message to log file as well:
    logger.normal("Welcome to the COSMICi central server program, v%s." % str(VERSION))    
    logger.normal("Copyright (c)2009-2012 by the COSMICi Project.")
    logger.normal("All Rights Reserved.")
    print()

        # Create the main COSMICi server object.  This object will be
        # responsible for handling all the core server functions.

    logger.debug("Creating the master cosmicIServer object...")
#    time.sleep(2)
    cosmicIServer = CosmicIServer()

# Not yet working, so commented out for now
#
##        # The following tells the CosmicIServer that the main thread
##        # was already enlisted as a worker thread (in initGuiApp()),
##        # so we don't try to do it again when we get to the
##        # cosmicIServer.run() method.
##
##    cosmicIServer.mainThreadEnlisted = True

        # NOTE: To handle exceptions properly in subordinate threads,
        # each such thread should have a try/except statement in its
        # run() (or whatever target) method, and catch all exceptions
        # there.  If a fatal exception is caught, it should call
        # _thread.interrupt_main() to interrupt the main thread (below).
    
    try:
            # Start the COSMICi server running.  This sets up a threaded
            # listener on our input port and goes into a main loop where
            # we just log the current time periodically (heartbeat loop).
            # This method should never terminate unless the server
            # encounters a fatal error or is interrupted or otherwise
            # terminated.

        logger.debug("Going into cosmicIServer's main loop...")
#        time.sleep(2)
            # Note that here, instead of starting a new thread, we're just transferring control.
        cosmicIServer.run()
        
    except BaseException:
            # This is here to make sure that the exception will get logged in the log file,
            # in case nobody happens to see the console message.
        logger.exception("COSMICi-server.py: main(): Runtime exception occurred... Exiting.")
        raise   # Do whatever the exception would have normally done.

    finally:
        logmaster.setThreadRole("shutdown")     # Context info for log purposes - this is what we're doing now.
        logger.critical("Exited from cosmicIServer.run() main loop.")

            # Really, right here we should take steps to kill all the
            # leftover server threads (other than guibot and the main console's
            # outputDriver) that might be hanging around.  Need a method
            # like cosmicIServer.destroy() to take care of this for us.
        
        logger.critical("The main window will be automatically closed in 10 seconds.")
        logger.critical("You can review error messages in the COSMICi.server.log file.")
        logger.normal("Please note: The main console window is about to close.")
        time.sleep(10)   # Pause so user has a chance to follow what's happening...

            # Debug logging of this teardown code can now make use
            # of our new logmaster facility, which can be used from
            # within any module.

        logger.critical("Asking guibot to destroy main console window ASAP...")
#        print("theMainWin =",guiapp.theMainWin.__repr__(),"\n",file=sys.__stdout__)
        guibot(guiapp.shutdown, front=True)    # shutdown gui before doing anything else
        time.sleep(2)    # Pause so user has a chance to follow what's happening...

        logger.critical("Asking guibot to exit its main loop...")
        try:
            guibot.stop()           # Raise a flag requesting the guibot to halt.
        except ExitingByRequest:
            logger.info("Aha, the guibot is already in the process of exiting; never mind...")
        logger.critical("Waiting for guibot to finish exiting...")
        guibot.join()
        
        time.sleep(2)    # Pause so user has a chance to follow what's happening...

            # Check for zombie threads; warn user if any.

        if threading.active_count() > 1:
            logger.warn("Warning! Just before exiting, there are multiple threads still alive.")
            for thread in threading.enumerate():
                logger.info("\t\t%s still exists." % thread)
            logger.warn("\tBecause of them, this python interpreter may stick around as a zombie process.")
            logger.warn("\tYou may have to kill it manually to free up its ports.")
    
            # Do an orderly shutdown of the logging system to make sure
            # that all log buffers get flushed & written to disk, etc.

        logger.critical("Commencing orderly shutdown of logging system...")
        logmaster.logging.shutdown()
        time.sleep(2)    # Pause so user has a chance to follow what's happening...

            # At this point, the logging facility has died, so all we
            # can do is print stuff to stderr.
            
        print("__main__.main(): %s IS EXITING IN 2 SECONDS!\n" %
              threading.current_thread().name,
              file=sys.stderr)
        
        time.sleep(2)   # Pause so user has a chance to follow what's
            # happening, in case it's happening on the Windows console
            # for this COSMICi_server-cons.py, which will disappear
            # after we exit.
    
        if RAW_DEBUG:
            print("__main__.main(): Exiting from main()...", file=sys.stderr)
        # At this point, we fall off the end of the finally clause, and exit from main() and the script.

    # We should never get here - any exception should trigger the above
    # raise & finally clauses, and then pop right up & out of the entire
    # python script without ever getting to this next line.
        
    assert False, "__main__.main(): ERROR: Somehow, we returned normally from the server's run() method."

        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        #   End main().
        #=============================================================================


    #========================================================================
    #   Main script body.                                   [code section]
    #
    #       Above this should only be definitions and assignments.
    #       Below is the main executable body of the script.
    #       It just calls the main() function (if this script is
    #       not just being loaded as a module).
    #  
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

if __name__ == "__main__":
    if RAW_DEBUG:
        print("__main__: Entering main body of script...", file=sys.stderr)

    # Don't run the main body code if this script is just being
    # loaded as a module.

if __name__ == "__main__":
    is_top = 1                  # Remember that this module was loaded as the top-level module.
    if RAW_DEBUG: print("__main__: Top-level module is invoking main() routine of application...", file=sys.stderr)
    main()   # Do everything in main() routine.
    if RAW_DEBUG: print("__main__: Application's main() routine has exited.", file=sys.stderr)
    if RAW_DEBUG: print("__main__: Exiting top-level module...", file=sys.stderr)
#else:
#    if RAW_DEBUG: print("Done with recursive import of COSMICi_server...")

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   End of COSMICi_server.pyw / COSMICi_server-con.py script.
#===============================================================================
