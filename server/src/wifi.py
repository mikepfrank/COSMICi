# wifi.py

import  threading

    # User includes.

import  logmaster
import  timestamp                   # The CoarseTimeStamp class is used in multiple places below.
import  communicator                # For communicating between proxy & real WiFi_Module 
from    communicator    import *    # Define "Connection"
import  ports                       # SensorNode._setupBridgeServers() uses LASER_PORT, MESON_PORT.
import  bridge                      # SensorNode._setupBridgeServers() uses bridge.BridgeServer().

import  model
#from    model           import *    # Define "SensorNode"

__all__ = [
    'WiFi_Module',          # A component of a wireless SensorNode - EZURiO Wi-Fi evaluation board.
    ]

    # Create logging channel for this module.
logger = logmaster.getLogger(logmaster.sysName + '.model.wifi')     # 'COSMICi.model.wifi' = object model of Wi-Fi modules

#class SensorNode:           pass        # Implemented below.
class WiFi_Module:          pass        # Partially implemented below.

    # Exception classes.

class BadBridgeMode(Exception): pass
    # The current Wi-Fi bridging mode does not support 


        #|===========================================================================
        #|
        #|      WiFi_Module                                 [public module class]
        #|
        #|          An instance of this class is an object model/proxy
        #|          representing a Wi-Fi communications module as one
        #|          of the components of a node.  (We assume there's
        #|          only a single Wi-Fi module associated with each
        #|          node, namely, the one registered as the value of
        #|          the node's .wifi_module attribute.)
        #|
        #|          The WiFi_Module structure is the appropriate place
        #|          to maintain information associated with the state
        #|          of the node's wireless communication capabilities,
        #|          such as its IP address, MAC address, node number
        #|          (which is used by the wireless script to identify
        #|          the node to the server upon power-up, etc.
        #|
        #|          Presently, the physical device associated with the
        #|          WiFi_Module proxy is a Laird EZURiO WISM module;
        #|          however, this could conceivably change in future
        #|          implementations of the COSMICi systems.
        #|
        #|          Attributes (both methods and data members) that are
        #|          associated with the networking state of the node
        #|          need to be delegated to or moved into this class
        #|          as appropriate.  (Previously these attributes were
        #|          all managed by the top-level SensorNode object.)
        #|
        #|          This module is not yet implemented.
        #|
        #|      PRIVATE NESTED CLASSES:
        #|
        #|          ._UART_MsgHandler   -   Class of message handlers for any messages
        #|                                      received on any UART-bridge connections
        #|                                      from a Wi-Fi module.
        #|
        #|          ._UART_ConnHandler  -   Class of connection handlers for any new
        #|                                      connections received on a UART bridge
        #|                                      server listening for connection requests
        #|                                      from a Wi-Fi module.
        #|      
        #|      SPECIAL INSTANCE METHODS:
        #|
        #|          .__init__()     -   Instance initializer.
        #|
        #|      PUBLIC INSTANCE METHODS:
        #|
        #|          .isAt(ip) - Inform the model that this Wi-Fi module is now communicating
        #|              from a new IP address.
        #|
        #|          .hasMac(mac) - Inform the model that this Wi-Fi module has a particular
        #|              MAC address.
        #|
        #|          .isOn() - Tell model that this node is turned on.
        #|          .turnedOnAt(when) - Tell model the node turned on at a specific time.
        #|          .sawAt(when) - Tell model we saw the node do something at a specific time.
        #|          .bridgeMode_is(bm) - Tell model the Wi-Fi board is in a certain bridge mode.
        #|
        #|          .sendHost(line:str) - Send the Wi-Fi module's local host the given text
        #|              line.  Based on the current bridge_mode, decides how to send the line
        #|              and whether it needs to be wrapped in another command.
        #|
        #|          [Add more stuph here...]
        #|
        #|      PRIVATE INSTANCE METHODS:
        #|
        #|          ._setupBridgeServers() - Sets up the two BridgeServer
        #|              instances, below, to handle the extra AUXIO and UART
        #|              connections from this specific Wi-Fi board.
        #|
        #|          ._setupAuxioServer() - This creates & configures a new
        #|              BridgeServer instance, for the purpose of allowing
        #|              the real Wi-Fi board to open an AUXIO connection to
        #|              the server.  The return path of such a connection
        #|              provides a way to send commands to the Wi-Fi board;
        #|              however, this connection is only polled every 100 ms,
        #|              so it is not the fastest way to send commands; for
        #|              that, use the UART bridge server when the Wi-Fi board
        #|              is configured in the Trefoil bridging mode.  (AUXIO is,
        #|              however, faster at responding to commands than the
        #|              MAIN connection, which is only polled by the Wi-Fi
        #|              board once every 200 ms.)
        #|
        #|          ._setupUartServer() - This creates & configures a new
        #|              BridgeServer instance, for the purpose of allowing
        #|              the real Wi-Fi board to open a UART-bridge connection
        #|              to the server, which may be in either bidirectional
        #|              mode or Trefoil mode, depending on how the Wi-Fi board
        #|              is configured.  Note that if this connection is in
        #|              Trefoil mode, then the UART bridge cannot be used to
        #|              send commands to the Wi-Fi board, and the AUXIO bridge
        #|              should be used instead; see below.  However, if the
        #|              connection is being bridged in Trefoil mode, then this
        #|              is the fastest way to send commands to the Wi-Fi
        #|              module, since it does not have to wait for a timer
        #|              event to poll it but executes as soon as characters
        #|              arrive over the bridge.  Therefore, it would be
        #|              beneficial for the Wi-Fi model to keep track of what
        #|              bridging mode the real board is in - see .bridge_mode
        #|              data member (below).
        #|
        #|      PUBLIC DATA MEMBERS:
        #|
        #|          .node : SensorNode
        #|
        #|              This attribute simply points upwards, towards the
        #|              larger SensorNode object that this WiFi module is
        #|              a component of.
        #|
        #|          .nodenum : int     
        #|
        #|              The node's ID or index number, as reported by the
        #|              WiFi module, based on the value recorded in the
        #|              nodeid.txt file loaded onto the WiFi module.
        #|              Normally this ID is in the range 0-4 (with node #0
        #|              nominally being the CTU), but larger ID values may
        #|              be allowed at some point in the future to accom-
        #|              modate sensor nets with larger number of detectors.
        #|              The present (stage 1) implementation actually only
        #|              uses two IDs, 0 (CTU) and 1 (Shower Detector).
        #|
        #|          .ipaddr : str
        #|
        #|              The module's IP address on the LAN, as a string, like
        #|              "192.168.0.2".  The point of tracking this is so that
        #|              (at least in principle) nodes don't have to identify
        #|              themselves by their ID numbers every time - instead,
        #|              we can just see which IP address a given message is
        #|              coming from.  (However, at the moment we still expect
        #|              nodes to provide their IDs anyway.)  This information
        #|              is also useful for monitoring which nodes are online
        #|              using the Wi-Fi router/access point's web interface.
        #|
        #|          .macaddr : str
        #|
        #|              The module's MAC address, as a string, like "3e:af:
        #|              2c:1d:08".  This can be considered a unique identity
        #|              for a given Wi-Fi board.  If we remember this, it can
        #|              be used to inform a node of its node ID even if the
        #|              node itself has forgotten this information somehow.
        #|              (However, a protocol for doing this has not yet been
        #|              defined.)  In this meantime, this is just an inter-
        #|              esting piece of FYI information that can be compared
        #|              with the Wi-Fi access point's reports of connected
        #|              clients.
        #|
        #|          .status:str
        #|
        #|              The Wi-Fi module's primary status (as far as we know),
        #|              one of these strings:
        #|
        #|                  UNSEEN     - We haven't heard from this node at all
        #|                              yet in the current server session.
        #|
        #|                  ON         - We think that the node is powered on.
        #|
        #|                  ON_AWOL    - We thought that the node was on, but we
        #|                              haven't heard from it in a while.
        #|                              (A server heartbeat period or so.)
        #|                              Not yet used.
        #|
        #|              (Should we have additional state variables to track
        #|              whether the AUXIO and UART connections are up?  Could
        #|              be useful...)
        #|
        #|          .onAt : CoarseTimeStamp
        #|
        #|              At what time did this node last turn on?  (Best estimate.)
        #|
        #|          .lastSeen : CoarseTimeStamp
        #|
        #|              At which time did we last receive any communication
        #|              from this node?
        #|
        #|          .mainConn : communicator.LineConnection (NOT YET IMPLEMENTED)
        #|
        #|              This TCP connection object is created when the node
        #|              initiates its connection to the MainServer; its
        #|              primary purpose is to allow the node to send server
        #|              commands directly to the server.  It is created as
        #|              soon as we receive the connection request, before we
        #|              even know which node is communicating with us.
        #|              However, once the node identifies itself, the 
        #|              connection object can be linked here from the model
        #|              of the node's Wi-Fi module, for easy access for
        #|              purposes of sending commands back to the Wi-Fi module
        #|              if other, faster channels are unavailable.  The Wi-Fi
        #|              autorun script should respond within about 200 ms to
        #|              messages sent back to it over the .mainConn.
        #|
        #|          .auxioServer : bridge.BridgeServer
        #|
        #|              A TCP server object (BridgeServer) set up specific-
        #|              ally for us to remotely monitor and insert commands
        #|              into the raw AUXIO (substitute for STDIO) data stream
        #|              being used by the script running on this node's Wi-Fi
        #|              board as a network-based replacement for STDIO, which
        #|              is unavailable since the module's UART is being bridged
        #|              to the server.  (We can't make another bridge for STDIO
        #|              b/c the EZURiO can only create 1 bridge at a time!)
        #|
        #|          .uartServer : bridge.BridgeServer
        #|
        #|              A TCP server object (BridgeServer) whose main purpose
        #|              is to relay raw data from node's local host to the
        #|              server via the Wi-Fi module's UART port which is
        #|              bridged directly to the TCP connection to this server.
        #|              If the Wi-Fi board is in Trefoil bridging mode, the
        #|              return connection may be used to send commands quickly
        #|              to the Wi-Fi script.  Otherwise, in the normal bridge
        #|              mode, the return connection gets relayed directly to
        #|              the node's host, i.e., to the firmware running on its
        #|              Nios core, and the data is never seen by the autorun
        #|              script.  Therefore, it is important for the model to
        #|              know which mode the Wi-Fi board is in, which leads to
        #|              the following data member, .bridge_mode (see below).
        #|                  Another thing:  After creating the .uartServer,
        #|              we need to add a MessageHandler to it that will
        #|              parse & interpret message lines coming in from the
        #|              host.  This is a bit tricky since messages may be in
        #|              slightly different formats depending on which host
        #|              they come from.  The early messages from each host
        #|              need to be in a common format so that we can parse
        #|              them without first knowing what kind of host it is.
        #|
        #|          .bridge_mode : str
        #|
        #|              This string may have any of several values denoting
        #|              what bridging mode the Wi-Fi board is currently in.
        #|              The complete set of bridge modes (BM_*) are defined
        #|              near the top of $(COSMICI_DEVEL_ROOT)/Wi-Fi Script/
        #|              modules/network/bridges.uwi.  For our present
        #|              purposes, however, these are the only bridging modes
        #|              that are relevant:
        #|
        #|                  'UNKNOWN'   -   The model doesn't yet know the bridge mode.
        #|
        #|                  'DEFAULT'   -   Corresponds to BM_NORMAL.  This is the mode
        #|                                      that the Wi-Fi module is in on powerup.
        #|                                      In this mode, the script's STDIO connects
        #|                                      to the UART, so we can relay commands to
        #|                                      the remote host via either the MAIN or
        #|                                      AUXIO connections (if they are active).
        #|
        #|                  'NONE'      -   Corresponds to BM_NONE.  In this mode, WiFi
        #|                                      STDIO & UART are both disconnected and
        #|                                      communication to the remote host is
        #|                                      impossible.
        #|
        #|                  'UNSUPPORTED' - Corresponds to BM_STDIO, BM_BOTH, or BM_HOSED.
        #|                                      These modes are not supported by the server,
        #|                                      in the sense that BM_STDIO and BM_BOTH
        #|                                      require an external terminal app (such as
        #|                                      UWTerminal, and BM_HOSED is some generic
        #|                                      'broken' state that we don't know what to
        #|                                      do with.
        #|
        #|                  'UART'      -   Corresponds to BM_UART.  In this mode, the
        #|                                      Wi-Fi board's UART is connected bi-
        #|                                      directionally to our UART bridge server
        #|                                      and so we can send & receive messages
        #|                                      to/from the remote host directly using
        #|                                      that connection.  To talk with the WiFi
        #|                                      script when in this mode, we must use
        #|                                      either the MAIN or AUXIO connections.
        #|
        #|                  'TREFOIL'   -   Corresponds to BM_TREFOIL.  This is the mode
        #|                                      that the present autorun script goes into
        #|                                      on a successful startup.  In this mode,
        #|                                      uartServer -> script STDIO -> UART ->
        #|                                      uartServer is the directed graph of
        #|                                      connections.  To talk to the remote host
        #|                                      we have to go through the script, using
        #|                                      either UART bridge (fastest), AUXIO bridge
        #|                                      (slower), or MAIN server (slowest), but the
        #|                                      remote host can talk to us directly via the
        #|                                      UART bridge connection without going through
        #|                                      the script at all.
        #|
        #|                  'FLYOVER'   -   Corresponds to BM_FLYOVER.  This mode is functionally
        #|                                      identical to UART mode except that it uses a
        #|                                      faster mechanism to relay data.  However, for
        #|                                      our purposes it behaves the same.
        #|
        #|              How does the WiFi_Module model know which bridging mode the
        #|              real module is in?  The most elegant solution is for the
        #|              Wi-Fi script to inform the server via its MAIN connection
        #|              whenever it changes its bridging mode.  This can be done via
        #|              a new message with the following format:
        #|
        #|                  BRIDGE_MODE 0 TREFOIL
        #|
        #|              where '0' is the node ID (as usual for MainServer commands)
        #|              and 'TREFOIL' is the name of the mode as specified in the
        #|              BMODE_NAME array in bridges.uwi.  The server can then
        #|              translate this to the appropriate name at our end and notify
        #|              the model via a new method, .bridgeMode_is().
        #|
        #|      PRIVATE DATA MEMBERS:
        #|
        #|          ._wlock : threading.RLock
        #|
        #|              A reentrant mutex lock to serialize modifications
        #|              to this structure.  Accessed internally by methods
        #|              that make changes to the structure.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class WiFi_Module:

        #|--------------------------------------------------------------------------------
        #|
        #|      WiFi_Module._UART_MsgHandler                    [private nested class]
        #|
        #|          Instances of this class are message handlers that know
        #|          what to do with messages received on the special UART
        #|          bridge connection that we expect to receive from each
        #|          Wi-Fi module.  This connection carries data relayed
        #|          from the UART serial connection from the sensor's main
        #|          host board (running our FPGA-based custom firmware).
        #|          We use the messages received over that connection to
        #|          update our knowledge about the nature and state of that
        #|          host, and our records of the data received by it.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    class _UART_MsgHandler(communicator.BaseMessageHandler):

            #|-----------------------------------------------------------------------------------
            #|
            #|      WiFi_Module._UART_MsgHandler.__init__()         [special instance method]
            #|
            #|          Initializer for new instances of the UART message handler class.
            #|          Causes the new message handler to remember which Wi-Fi module
            #|          it is serving, and what connection it is receiving messages on.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        def __init__(this, conn:Connection = None, wifi_module : WiFi_Module = None):

            logger.info("Creating message handler for incoming UART bridge connection for node #%d..."
                        % wifi_module.nodenum)

            this.wifi_module = wifi_module

            communicator.BaseMessageHandler.__init__(this, conn, name="Wi-Fi.UART")    # superclass initializer
            
        #<- End def WiFi_Module._UART_MsgHandler.__init__().

            #|--------------------------------------------------------------------------------
            #|
            #|      WiFi_Module._UART_MsgHandler.handle()           [public instance method]
            #|
            #|          All subclasses of communicator.BaseMessageHandler are supposed
            #|          to override its handle() method to provide the specific message-
            #|          handling functionality encapsulated by that subclass.
            #|              In our case, handling the message means doing whatever is
            #|          appropriate to do with text lines received over a UART-bridge
            #|          connection from a Wi-Fi board in a sensor node.  Namely, we
            #|          need to interpret them as messages relayed from the sensor host
            #|          (which they are) and respond to them accordingly.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            
        def handle(this, msg : Message):

            logger.debug("WiFi_Module._UART_MsgHandler.handle(): The Wi-Fi module relayed " +
                         "the message [%s] from the sensor host to the server.", msg.data.strip())

            # NOTE: We should probably add some code here to update the last-seen time
            # of this node.  (Or did we already do that in BridgeServer?)


                # Return early because the sensor_host model hasn't been
                # implemented yet, so we can't actually do the below code yet.
                # The .sensor_host instance needs to be created in response to
                # the HOST_STARTING message.
#            return
            
                # Basically, what we want to do here is make sure that it's an incoming
                # message, then dispatch it to the server's command handler together with
                # appropriate identifying information (i.e., which node did it come from).
                
            if msg.dir == communicator.DIR_IN:      # Incoming message from node?
                this.wifi_module.node.sensor_host.sentMessage(msg)
                    # \
                    #  \_ Translation: The embedded host operating the sensor node
                    #       that the Wi-Fi module that this message handler is
                    #       serving is a part of sent the server the message "msg".
                    #       This call informs the model of that host that it sent
                    #       us this message.  The host model then takes care of
                    #       interpreting the message as is appropriate for this
                    #       particular type of sensor (CTU vs. ShowerDetector).

                # Otherwise, if it's an outgoing message, we don't need to do anything
                # special with it.  (Outgoing messages are interpreted at the other end.)

        #<- End def WiFi_Module._UART_MsgHandler.handle().

    #<- End class WiFi_Module._UART_MsgHandler

        #|------------------------------------------------------------------------------
        #|
        #|      WiFi_Module._UART_ConnHandler               [private nested class]
        #|
        #|          Instances of this class are connection handlers that
        #|          know what to do with new UART-bridge connections from
        #|          a particular Wi-Fi module in the sensor network.
        #|              Specifically, what we need to do with these new
        #|          connections (besides the usual stuff that is done
        #|          with all new connections to any BridgeServer) is to
        #|          register a message handler that knows what to do with
        #|          the lines of text (a.k.a. messages) coming over that
        #|          connection, given that it is a UART bridge connection
        #|          from a particular node's Wi-Fi module.  The message
        #|          handler, in turn, will do the appropriate interpretation
        #|          and dispatching of individual messages as they come in.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    class _UART_ConnHandler(communicator.BaseConnectionHandler):

            #|------------------------------------------------------------------------------------
            #|
            #|      WiFi_Module._UART_ConnHandler.__init__()        [special instance method]
            #|
            #|          This method initializes newly-created instances of the class
            #|          WiFi_Module._UART_ConnHandler().  Basically all we do here is
            #|          remember which particular Wi-Fi module this particular
            #|          connection handler was created to serve, so that later when we
            #|          actually get a new connection, we will know which Wi-Fi module
            #|          to associate with the new message handler that we will create
            #|          to handle incoming messages sent over that connection.  Make
            #|          sense?
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
        def __init__(this, wifi_module : WiFi_Module = None):
            
            logger.info("Creating connection handler for new UART bridge connections for node #%d..."
                        % wifi_module.nodenum)

            this.wifi_module = wifi_module      # Remember what WiFi module this connection handler is serving

        #<- End def WiFi_Module._UART_ConnHandler.__init__()

            #|------------------------------------------------------------------------------
            #|
            #|      WiFi_Module._UART_ConnHandler.handle()      [public instance method]
            #|
            #|          Handles new connections on uartServer bridge server
            #|          in ways that are specific to the special UART-bridge
            #|          connection that the specific Wi-Fi module opens.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        def handle(this, conn : Connection):            # TO IMPLEMENT

                # All we need to do with each new connection is attach the appropriate
                # message handler to it.  One that knows how to handle messages coming
                # over the UART-bridge (that is, messages from the sensor host).

            conn.addMsgHandler(this.wifi_module._UART_MsgHandler(conn, this.wifi_module))
            
        #<- End def WiFi_Module._UART_ConnHandler.handle().
            
    #<- End nested class WiFi_Module._UART_ConnHandler.
            
        #|-----------------------------------------------------------------------------
        #|
        #|      WiFi_Module.__init__()                  [special instance method]
        #|
        #|          Initializer for new instances of class WiFi_Module.
        #|
        #|          NOTE:  At the time when a given WiFi_Module instance
        #|          is first created, and this method is called to init-
        #|          ialize it, we might not have actually seen the actual
        #|          node yet - we might just be EXPECTING to see the node
        #|          (e.g., perhaps because we saw it in a previous run,
        #|          or because we are restoring the server state from
        #|          files after the server exited for some reason).
        #|
        #|          This initializer just initializes various data members
        #|          as appropriate.
        #|
        #|      Called by:
        #|
        #|          SensorNode.__init__()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def __init__(this:WiFi_Module, node = None,
                 num:int = None, ip:str = None):

        this._wlock = threading.RLock()     # Create our write lock.  Use a re-entrant lock, in case we need it.     

        with this._wlock:                   # Acquire the write lock.

                # Initialize various data members appropriately.
            
            this.node           = node      # Remember our parent object (node).
            this.nodenum        = num       # Remember our node's ID #.
            this.ipaddr         = ip        # Remember our IP address.
            this.macaddr        = None      # We won't know the module's MAC address until the POWERED_UP message is seen.
            this.status         = 'UNSEEN'  # Mark node as 'unseen' until we definitely hear from it.
            this.mainConn       = None      # Will be reassigned shortly if node is connected...
            this.auxioServer    = None      # This won't be created until we get the POWERED_UP message.
            this.uartServer     = None      # Likewise for this guy.
            this.bridge_mode    = 'UNKNOWN' # We have no idea yet what the module's bridging mode is.
            
        #<- End with this._wlock
            
    #<- End def __init__()

        # Methods to query whether various communication streams to the node's
        # Wi-Fi module are currently connected.  Currently, we just assume that
        # if the corresponding attribute is non-null, then that connection is
        # still up and running.  This may be a bad assumption if a connection
        # gets interrupted somehow, so this probably should be made more soph-
        # isticated in the future.  (For example, certain exceptions when trying
        # to send data to a connection can trigger the model to mark that con-
        # nection as no longer available.)

    def _uartSrvConnected(this):    # Return True iff the .uartServer connection from this node's Wi-Fi module is active.
        
        return  this.uartServer != None         # If initialized, assume connection's still good.

    def _auxioSrvConnected(this):   # Return True iff the .auxioServer connection from this node's Wi-Fi module is active.
        
        return  this.auxioServer != None        # If initialized, assume connection's still good.

    def _mainSrvConnected(this):    # Return True iff the .mainConn connection from this node's Wi-Fi module is connected.
        
        return  this.mainConn != None           # If initialized, assume connection's still good.

        # Methods to send lines along various communication streams to the node's Wi-Fi module.

    def sendTo_uartSrv(this, line:str):

        if not this._uartSrvConnected():
            logger.error(("WiFi_Module.sendTo_uartSrv(): Can't send the line [%s] via the " +
                          "UART server because no connection from that node is open.") % line)
            return

        this.uartServer.send(line)

    def sendTo_auxioSrv(this, line:str):

        if not this._auxioSrvConnected():
            logger.error(("WiFi_Module.sendTo_auxioSrv(): Can't send the line [%s] via the " +
                          "AUXIO server because no connection from that node is open.") % line)
            return
        
        this.auxioServer.send(line)    

    def sendTo_mainSrv(this, line:str):

        if not this._mainSrvConnected():
            logger.error(("WiFi_Module.sendTo_mainSrv(): Can't send the line [%s] via the " +
                          "MAIN server because no connection from that node is open.") % line)
            return

        this.mainConn.sendOut(line)

        # Send a given command line to the Wi-Fi module's controlling script.
            
    def sendScript(this, line:str):

        if this.bridge_mode == 'TREFOIL' and this._uartSrvConnected():

            this.sendTo_uartSrv(line)

        elif this._auxioSrvConnected():

            this.sendTo_auxioSrv(line)

        elif this._mainSrvConnected():

            this.sendTo_mainSrv(line)

        else:
            logger.error(("WiFi_Module.sendScript(): Can't send the line [%s] to the " +
                          "Wi-Fi script because there are no open connections to it.") %
                         line)

        # Send a given command line to the Wi-Fi module's local sensor host.
        # We assume the line is already terminated with a newline character.

    def sendHost(this, line:str):

            #|--------------------------------------------------------------------
            #|  Here's how we decide how to send a given line to the sensor host:
            #|
            #|    1. If we're in UART or FLYOVER mode, then we send the raw line
            #|         directly through the uartServer.
            #|
            #|    2. Otherwise, we have to route thru the Wi-Fi script.  We package
            #|         up the line into a "HOST ..." line, and send it by one of
            #|         several means:
            #|
            #|       2a. If we're in TREFOIL mode, then send the packaged line to
            #|             the uartServer.
            #|
            #|       2b. Otherwise, if the auxioServer is available, then send
            #|             the line that way.
            #|
            #|       2c. Otherwise, send the line via the MAIN server connection
            #|             (.mainConn).

        if this.bridge_mode in ['UART', 'FLYOVER'] and this._uartSrvConnected():

                # send line directly via .uartServer (to implement)
            this.sendTo_uartSrv(line)

        elif this.bridge_mode in ['DEFAULT', 'TREFOIL', 'NONE']:
                # - The Wi-Fi board could be in mode NONE if it is in the
                #   middle of switching from DEFAULT mode to TREFOIL mode.
        
            line = "HOST " + line       # Package line into "HOST ..." command.

            this.sendScript(line)   # Send the packaged line to the Wi-Fi script.
                # - This uses the best connection available to send the line.

        else:
                # Somehow we got into a bridging mode like 'UNKNOWN',
                # or 'UNSUPPORTED'.  Give up in despair.  Smarter here would be
                # to instead send the Wi-Fi module a command to try to get it into
                # a more appropriate bridging mode, and then try again.
            
            logger.error("WiFi_Module.sendHost():  I don't know any way to communicate " +
                         "with the sensor host in the present briding mode.  Giving up.")

    #<- End def WiFi_Module.sendHost().
        

        #|---------------------------------------------------------------------------------
        #|
        #|      WiFi_Module.isAt()                          [public instance method]
        #|
        #|          Calling this method informs our model of the Wi-Fi
        #|          module that the module is now using a new IP address.
        #|          This could happen, for example, if the router gets
        #|          reset, or if nodes' DHCP leases expire and get renewed
        #|          differently from how they were previously assigned.
        #|          Or, if we replace a bad module, the replacement will
        #|          have a new MAC address, and thus will likely get
        #|          assigned a different IP address by the router.
        #|              All this method does is store the new address.
        #|
        #|      Called by:
        #|
        #|          SensorNode.reloc()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def isAt(this, ip):
        with this._wlock:           # Temporarily obtain exclusive write access to the model.
            this.ipaddr = ip            # Remember the new IP address for future reference.
        #<- End with this._wlock
    #<- End def isAt()


        #|--------------------------------------------------------------------------------
        #|
        #|      WiFi_Module.isOn()                          [public instance method]
        #|
        #|          Calling this method informs our model of the Wi-Fi
        #|          module that the module is presently turned on (at
        #|          least, it was last we knew).
        #|              At present, this just updates the 'status'
        #|          state variable (attribute, data member) to the 'ON'
        #|          state.  Later, if we don't hear from the node in a
        #|          while, it could get changed to 'ON_AWOL'.  (Not yet
        #|          implemented.)
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def isOn(this):
        with this._wlock:
            this.status = 'ON'

        #|---------------------------------------------------------------------------------
        #|
        #|      WiFi_Module.hasMac()                        [public instance method]
        #|
        #|          Calling this method informs our model of the Wi-Fi module
        #|          of what the module's MAC address is.  (This information is
        #|          contained in the POWERED_UP message, which is normally the
        #|          first message we receive from the node.)
        #|              All this method does is store the new address.
        #|
        #|      Called by:
        #|
        #|          SensorNode.setMac()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def hasMac(this, mac):        
        with this._wlock:           # Temporarily obtain exclusive write access to the model.
            this.macaddr = mac          # Remember the module's MAC address for future reference.
        #<- End with this._wlock
    #<- End def hasMac()

        #|--------------------------------------------------------------------------------
        #|
        #|      WiFi_Module.turnedOnAt()                        [public instance method]
        #|
        #|          Tell the model Wi-Fi Module that the real Wi-Fi module turned on
        #|          at a specific time.  (Actually this is just the time that the
        #|          turn-on message from it was received, but close enough.)
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def turnedOnAt(this, when):
            # Make sure time is in displayable CoarseTimeStamp format.
        if  not isinstance(when, timestamp.CoarseTimeStamp):
            when = timestamp.CoarseTimeStamp(when)

            # Thread-safely initialize various fields.
            
        with  this._wlock:       # Acquire our write lock.
            
            this.isOn()                 # Mark node status as ON.
            this.onAt       = when      # Record node's turn-on time.
            this.lastSeen   = when      # Which is also its last-seen time.

            logger.debug("Setting up our servers to listen to bridges from node %d..." % this.nodenum)
            
            this._setupBridgeServers()   # Try setting up our bridge servers.
                        

        #|----------------------------------------------------------------------------------
        #|
        #|      WiFi_Module.bridgeMode_is()                 [public instance method]
        #|
        #|          Calling this method informs our model of the Wi-Fi module
        #|          what bridging mode the module is currently in.  This info
        #|          is sent to us by the node is a BRIDGE_MODE message.  All
        #|          that this method does is store the new mode string, which
        #|          is required to be one of the following:
        #|
        #|                  'UNKNOWN'   -   The model doesn't yet know the bridge mode.
        #|
        #|                  'DEFAULT'   -   BM_NORMAL, UART <-> STDIO
        #|
        #|                  'NONE'      -   Corresponds to BM_NONE.  STDIO+UART disconnected.
        #|
        #|                  'UNSUPPORTED' - Corresponds to BM_STDIO, BM_BOTH, or BM_HOSED.
        #|                                      These modes are not supported by the server.
        #|
        #|                  'UART'      -   Corresponds to BM_UART.  UART <-> uartServer.
        #|
        #|                  'TREFOIL'   -   Corresponds to BM_TREFOIL.  In this mode,
        #|                                      uartServer -> script STDIO -> UART ->
        #|                                      uartServer.
        #|
        #|                  'FLYOVER'   -   Corresponds to BM_FLYOVER.  Functionally identical
        #|                                      to UART mode, but faster.
        #|
        #|          However, presently we do no error checking to enforce this.
        #|
        #|              The purpose of tracking the bridge mode is that is allows the
        #|          server to most intelligently send messages to the Wi-Fi script.
        #|          knowing the bridge mode tells us what the most efficient way to
        #|          message the script is.  In UART & TREFOIL modes, the fastest way
        #|          is to use the uartServer's return connection.  In other modes, this
        #|          option is not available, and the fastest way is to use the AUXIO
        #|          return connection is it is available, and the MainServer's if not.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def bridgeMode_is(this, bmstr):
        with this._wlock:
            this.bridge_mode = bmstr
            logger.normal("Node %d's bridge mode is now %s." % (this.nodenum, bmstr))

        #|---------------------------------------------------------------------------------------------
        #|
        #|      WiFi_Module._setupBridgeServers()            [private instance method]
        #|
        #|          Establishes the AUXIO and UART BridgeServers which will
        #|          accept these extra connections from this node's Wi-Fi
        #|          module.
        #|
        #|          These are commandable, logging TCP servers listening for
        #|          raw text or data to arrive from node's AUXIO and UART
        #|          interfaces.
        #|
        #|      CALLED BY:
        #|          WiFi_Module.turnedOnAt()
        #|
        #|      TO DO:
        #|
        #|          [/] Make it so that TikiTerm windows are popped up for
        #|               each of these servers as well.  Perhaps within
        #|               BridgeServer?  -- UPDATE: Done.
        #|
        #|          [/] Move this method from SensorNode to WiFi_Module?
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
              
    def _setupBridgeServers(self):       # Make sure node is write-locked before calling.

        logger.debug("Setting up bridge servers for node %d..." % self.nodenum)

        self._setupAuxioServer()    # Auxilliary I/O from Wi-Fi script, at port LASER+ (52,737+).
        self._setupUartServer()     # Bridged connection from host's UART, port MESON+ (63,766+).
            
    #<-- End method SensorNode._setupBridgeServers().

        #|------------------------------------------------------------------------------
        #|
        #|      WiFi_Module._setupAuxioServer()             [private instance method]
        #|
        #|          Creates & starts up the 'AUXIO' bridge server object that
        #|          will handle auxilliary I/O connections from this Wi-Fi board.
        #|
        #|      CALLED BY:
        #|          WiFi_Module._setupBridgeServers()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _setupAuxioServer(this):

            #|------------------------------------------------------------------------------
            #|  Setup the AUXIO server on the "LASER" (52,737) port number (plus node ID).
            
        if (this.auxioServer == None):      # No auxio server yet?

                # Calculate the port number that the new AUXIO server should listen at.
            
            base_auxio_port = ports.LASER_PORT
            auxio_port = base_auxio_port + this.nodenum
            
            logger.normal("Starting AUXIO server for node %d on port %d..."
                          % (this.nodenum, auxio_port))

            with this._wlock:            
                this.auxioServer = bridge.BridgeServer(base_auxio_port, this.nodenum, "auxio")
            
            this.auxioServer.node = this.node    # Point the lil' guy back at mommy
           
            this.auxioServer.start()        # Go ahead and start up the newly created server.
            
        #<- End of case where there is no auxio server yet.
    #<- End def _setupAuxioServer 

        #|------------------------------------------------------------------------------
        #|
        #|      WiFi_Module._setupUartServer()             [private instance method]
        #|
        #|          Creates & starts up the 'UART' bridge server object that
        #|          will handle UART bridge connections from this Wi-Fi board.
        #|
        #|      CALLED BY:
        #|          WiFi_Module._setupBridgeServers()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _setupUartServer(this):

            #|------------------------------------------------------------------------------
            #|  Setup the UART server on the "MESON" (63,766) port number (plus node ID).
            
        if (this.uartServer == None):       # No uart server yet?
            
            base_uart_port = ports.MESON_PORT
            uart_port = base_uart_port + this.nodenum
            
            logger.normal("Starting UART server for node %d on port %d..."
                          % (this.nodenum, uart_port))
            
            with this._wlock:            
                this.uartServer = bridge.BridgeServer(base_uart_port, this.nodenum, "uart")
            
            this.uartServer.node = this.node    # Point the lil' guy back at mommy

                # At this point, we need to add a message handler that will read lines
                # from the node looking for a $NODE_TYPE message, and respond accordingly.
                # (Create an appropriate object representing the node's sensor.)  Actually,
                # since the connection doesn't exist yet, all we can do at this point is
                # to add a connection handler that will add the message handler for us later
                # (after the connection exists).
                
            this.uartServer.addConnHandler(this._UART_ConnHandler(this))
            
            this.uartServer.start()     # Go ahead and start up the newly created server.
            
        #<-- End if case where there is no uart server yet.
    #<- End def _setupUartServer

# End class WiFi_Module

