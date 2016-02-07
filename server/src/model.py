#|******************************************************************************************
#|                                  TOP OF FILE
#|******************************************************************************************
#|
#|      FILE:  model.py                             [python module source file]
#|
#|      SYSTEM CONTEXT:
#|
#|          This module is a component of the COSMICi server app;
#|          it is not intended to be executed as a standalone top-
#|          level Python program.
#|
#|      DESCRIPTION:
#|
#|          This file defines a Python module that provides an object-
#|          based model of the COSMICi sensor network, in particular
#|          its remote components (other than the server itself.
#|          The model objects serve as the server-side proxies for
#|          the remote components that they represent.  Conceptually, a
#|          given sensor net component can be viewed as having two major
#|          parts:  The actual remote physical node hardware/firmware,
#|          and the software that's inside the model object from this
#|          module, running on the server.  Of course, the model object
#|          will in general need to communicate with the remote hardware
#|          in order to actually carry out its function.
#|
#|      REVISION HISTORY:
#|
#|          v0.1, pre-1/28/12 (MPF) - Started revision history; created
#|              this tag subsuming all older revisions.  The actual file
#|              has been evolving for a while.
#|
#|          v0.2, 1/28/12 (MPF) - Now in the process of adding support
#|              for our new, more sophisticated object model of the
#|              actual sensor network.
#|
#|          v0.3, 2/22/12 (MPF) - Moving component-specific stuff out to
#|              new files wifi.py, ctu.py, gps.py, & fedm.py.
#|  
#|      TO DO:
#|          [ ] Implement WiFi_Module and Sensor_Host classes; instances
#|                  of these will then be members of each SensorNode
#|                  instance.  Sensor_Host will be further subclassed
#|                  into FEDM_Host and CTU_Host, for the two types of
#|                  host boards in our system.  CTU_Host might have an
#|                  additional member of class GPS_Module; this one would
#|                  route commands to the GPS kit to reconfigure it.  So
#|                  the object structure would look something like this:
#|
#|              cis.sensorNet (SensorNet):
#|
#|                  .nodes[0] (CTU_Node <- SensorNode):
#|                      .wifi_module (WiFi_Module)
#|                      .sensor_host (CTU_Host <- SensorHost)
#|                      .gps_module (GPS_Module)
#|
#|                  .nodes[1] (ShowerDetectorNode <- DetectorNode <- SensorNode):
#|                      .wifi_module (WiFi_Module)
#|                      .sensor_host (ShowerDetectorHost <- DetectorHost <- SensorHost)
#|                      .dac[0-5] (ThresholdDAC) - Or is this overkill?
#|
#|              Note here we also divided SensorNode into two subclasses,
#|              CTU_Node and ShowerDetectorNode, which is a type of detector
#|              node that receives data from multiple detector units and
#|              does coincidence filtering.
#|
#|              The above represents a major refactoring of some existing
#|              functionality, however, so we should be cautious and phase
#|              it in carefully, so we don't break the module in the meantime -
#|              or else develop it in a branch that we later merge with the
#|              main trunk.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    #|====================================================================================
    #|  Includes.                                                   [code section]
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        # System includes.

import  threading        # SensorNet.__init__() uses RLock().

        # User includes.

import  logmaster                   # module-level code uses getLogger(), appName.
import  communicator                # Message
import  timestamp                   # The CoarseTimeStamp class is used in multiple places below.
import  nmea                        # Defines stripNMEA().
import  flag                        # Defines Flag() type.
from    utils           import *    # MutableClass, etc.
import  wifi                        # Wi-Fi module - Contained in all nodes.

    #|====================================================================================
    #|  Global variables & constants.                               [code section]
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

__all__ = [         # Class definitions.  (Most of these are not actually defined yet.)
    'SensorNet',            # The entire local sensor network, as a whole.
    'SensorNode',           # A generic remote node in the sensor network. (Note that this server itself is not considered to be a sensor node.)
    'SensorHost',           # A component of a wireless SensorNode - the FPGA-based Nios host behind the Wi-Fi board.
    ]   # end __all__
    
logger = logmaster.getLogger(logmaster.sysName + '.model')   # 'COSMICi.model' = object model of COSMICi system

    #|=================================================================================
    #|  Class definitions.                                          [code section]
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        # Forward declarations - these are needed for code to compile.
        # They allow classes defined earlier to refer to the names of
        # classes defined later, e.g., in argument type declarators.

class SensorNet:            pass        # Implemented below.
class SensorNode:           pass        # Implemented below.
class SensorHost:           pass        # Not yet implemented.


        #|=====================================================================
        #|
        #|   SensorNet                                       [public class]
        #|
        #|      An object of class SensorNet represents an entire
        #|      local COSMICi sensor network: A set of detector
        #|      nodes at a given site, working in concert with each
        #|      other to provide us with information that allows us
        #|      to triangulate the direction of cosmic-ray showers.
        #|
        #|      So far, it just tracks basic features of the nodes'
        #|      state; which nodes have appeared, what their present
        #|      status is, etc.
        #|
        #|      Later, we will expand this class (and its components)
        #|      to maintain more detailed information e.g. about nodes'
        #|      history, data received, associated GUI components, and
        #|      so forth.
        #|
        #|  Special methods:
        #|
        #|      .__init__(cosmiciserver = None)     -   Initializer.
        #|      .__str__()                          -   String converter.
        #|
        #|  Public methods:
        #|
        #|      .nodeWithIP()   - Look up node by IP addr.
        #|      .nodeAt()       - Report sighting of node at an IP addr.
        #|      .verifyNode()   - Check node's IP address for consistency.
        #|      .logNode()      - Log node-specific program activity.
        #|      .nodeOn()       - Report node power-on event.
        #|
        #|  Public data members:
        #|
        #|      .writeLock  - Reentrant mutex lock for adding/removing nodes.
        #|      .nodes - Dictionary of sensor nodes, indexed by ID.
        #|      .cis - Pointer to the main CosmicIServer application managing
        #|          this sensor network.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class SensorNet:

    #------------------------------------------------------------------------
    #   Instance data members:
    #
    #       .writeLock - Threads should acquire this lock before adding
    #           new nodes to the sensor net, or removing nodes.  (But
    #           for modifying existing nodes, use the lock on the
    #           individual node instead, to reduce lock contention.)
    #
    #       .nodes - Dictionary of nodes seen since we last reinitialized
    #           the list.  In the future, the list of nodes will be saved
    #           persistently, so it does not have to be totally recreated
    #           from scratch each time the server starts up.
    #
    #       .cis - Pointer to the main CosmicIServer object managing this
    #           sensor network; it encapsulates the server-side functions,
    #           as opposed to the SensorNet object, which is a model of/
    #           proxy for the remote components in the local sensor network.
    #
    #------------------------------------------------------------------------


        #|-----------------------------------------------------------------
        #|   .__init__()                         [special instance method]
        #|
        #|       Default constructor.  Just creates an empty list of
        #|       nodes to start out.  (In future it may load from a
        #|       file or database, or other persistent structure.)
        #|
        #|  Arguments:
        #|
        #|      cosmiciserver : COSMICi_server:CosmicIServer
        #|
        #|          This is the main COSMICi server application object.
        #|          In other words, it represents the server application
        #|          that this sensor network will be talking to.  We
        #|          keep a pointer to this object so that we can invoke
        #|          it later - e.g., to process commands & data received
        #|          from the sensor network.
        #|
        #|  Used by:
        #|      COSMICi_server.CosmicIServer.__init__()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def __init__(self : SensorNet, cosmiciserver = None):
        # Don't need to acquire write lock b/c other threads can't see object yet.
        self.writeLock = threading.RLock()       # Create our write lock.
        with self.writeLock:
            self.cis = cosmiciserver
            self.nodes = dict()                     # Set the node 'list' to the empty dictionary initially.
            
#        logger.debug("Node list: [%s]" % self)

        #|------------------------------------------------------------------
        #|
        #|  .__str__()                          [special instance method]
        #|
        #|      Construct an informal string representation of the
        #|      sensor net.
        #|
        #|  Used by:
        #|      .nodeOn(), in debug output.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def __str__(self:SensorNet):
        str = ""
        for (id,node) in self.nodes.items():    
            str += "#%d(%s/%s): %s; " % (id, node.ipaddr, node.macaddr, node.status);
                # Is there a possible concurrency risk while iterating above?
                # Probably not, since all is done in CommandHandler thread.
        return str


        #|------------------------------------------------------------------
        #|
        #|  .nodeWithIP()                       [public instance method]
        #|
        #|       If there is a node with IP address <ip> in our node
        #|       list, return its ID, else None.
        #|
        #|  Called by:
        #|      .nodeAt()
        #|      
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def nodeWithIP(self:SensorNet, ip:str):                   # Possible concurrency risk while iterating?  Probably not, since all is done in CommandHandler thread.
        for (id,node) in self.nodes.items():
            if node.ipaddr == ip: return id
        return None


        #|--------------------------------------------------------------------
        #|  .nodeAt()                               [public instance method]
        #|
        #|      Record that node #<id> is transmitting from ip address
        #|      <ip>.  Adds the node to our list if not already there.
        #|
        #|  Called by:
        #|      .verifyNode()
        #|      .nodeOn()
        #|
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def nodeAt(self:SensorNet, id:int, ip:str):
        
            # If there is already an entry for this node in the list, just modify it.
            
        if id in self.nodes:

                # Check to see if IP address matches. If not, update it.

            if ip == self.nodes[id].ipaddr:
                logger.normal("Existing node %d at %s was powered on again." % (id, ip))
            else:
                logger.warning("Existing node %d has powered on from a new IP address %s." % (id, ip))
                logger.warning("...(This could happen, for example, if its DHCP lease changed.)")
                other = self.nodeWithIP(ip)
                if other != None:
                    logger.warning("Another node %d in our list is already using IP %s!" % (other,ip))
                self.nodes[id].reloc(ip)
        else:
                # This is a node not previously seen... Create initial data structure.
                # We lock the list to avoid concurrency problems while adding members.
                
            logger.normal("New node %d seen at IP address %s." % (id, ip))
            with self.writeLock:
                other = self.nodeWithIP(ip)
                if other != None:
                    logger.warning("Another node %d in our list is already using IP %s!  Replacing it..." % (other,ip))
                self.nodes[id] = SensorNode(id, ip, self)
                
    #<- End method SensorNet.nodeAt().


        #|------------------------------------------------------------------
        #|  .verifyNode()                       [public instance method]
        #|
        #|      Ensure that the node with id <id> is in our list with ip
        #|      address <ip>.  Also update it's last-seen time to <when>.
        #|
        #|  Called by:
        #|      commands.CommandHandler.handleLogMsg()
        #|      commands.CommandHandler.handleHeartbeat()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def verifyNode(self:SensorNet, id:int, ip:str, when):
        
            # Make sure time is in displayable CoarseTimeStamp format.
            
        if not isinstance(when, timestamp.CoarseTimeStamp):
            when = timestamp.CoarseTimeStamp(when)

            # Make sure the node is in our dictionary.
            
        if not (id in self.nodes):
            logger.warning("Received a request from %s claiming to be from node %d," % (ip, id))
            logger.warning("\tbut there is no node with that number in our list!")
            logger.warning("\tGoing ahead and adding it...")
            self.nodeAt(id, ip)     # Make a note that we saw the node at this IP address.
            
            # At this point, id must be in the dictionary.  Assert this.
            
        assert id in self.nodes, "Node %d is not in the dictionary even though we just ensured it would be!" % id

            # Check that the IP address is as expected, and that we saw this node previously.
        
        if self.nodes[id].ipaddr != ip:
            logger.warning("Received a request from %s claiming to be from node %d," % (ip,id))
            logger.warning("\tbut the IP address we have on file for that node is %s!" % self.nodes[id].ipaddr)
        elif self.nodes[id].status == 'UNSEEN':
            logger.warning("Received a request from %s claiming to be from node %d," % (ip,id))
            logger.warning("\tbut we haven't even seen that node's power-on message yet!")
                # We know it's on now, but we don't know when it was turned on.
            self.nodes[id].isOn()
#- The following is commented out b/c it is the expected behavior, not worth logging all the time.
#        else:
#            logger.debug("Looks like node %d is still sending from IP %s." % (id, ip))

            # Record that we saw a message from this node at this time.
            
        self.nodes[id].sawAt(when)

    #<- End method SensorNet.verifyNode().


        #|--------------------------------------------------------------------
        #|
        #|   .logNode()                             [public instance method]
        #|
        #|       Cause subsequent log messages to be labeled, in their
        #|       'component' field, with the name of the given node.
        #|       This allows for easier searching of node-related items
        #|       in the log.
        #|
        #|  Called by:
        #|      .nodeOn()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def logNode(self:SensorNet, num:int):

            # Compose component name string.
            
        compName = "node #%d" % num

            # Assuming that the current thread is a logging.ThreadActor,
            # (or at least a "hired" worker) set the component name
            # in the thread's logging context to the name.
            
        logmaster.setComponent(compName)
        
    # end def logNode


        #|---------------------------------------------------------------------
        #|
        #|  .nodeOn()                               [public instance method]
        #|
        #|      Record that node <num> at IP address <ip> with MAC address
        #|      <mac> turned on at time <when>.
        #|
        #|  Called by:
        #|      commands.CommandHandler.handleNodeOn()
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def nodeOn(self:SensorNet, num:int, ip:str, mac:str, when):

            # Temporarily set the component name in the current thread's logging
            # context to the node name.  We need to set it back to server later.
            # (This is redundant with parseNodeNum, but we leave it here since the
            # model could be called by someone other than the command handler.)

        self.logNode(num)

        
        logger.debug("SensorNet.nodeOn(): Noting that node %d powered on at IP address %s and MAC address %s at %s." %
                     (num, ip, mac, when))
        
            # First note the fact that node <num> is transmitting from addr <ip>.
            # This adds its model to the data structure if it was not there already.
            
        self.nodeAt(num, ip)
        
            # Also, note the node's MAC address.
            
        self.nodes[num].setMac(mac)
        
            # At this point we know that the node's data structure exists,
            # and that its recorded IP address & MAC address are current.
            # All that remains is to record the actual turn-on event.
            
            # Since the node has just turned on, it will be shortly trying
            # to create its AUXIO and UART bridge connections; the servers
            # to handle these are also created by this method.
            
        self.nodes[num].turnOn(when)
        
            # For debugging purposes, print the new node-list data structure.
            
        logger.debug("New node list: [%s]" % self)

    # End method SensorNet.nodeOn().
# End class SensorNet


        #|=========================================================================
        #|
        #|      SensorNode                                      [public class]
        #|
        #|          Class of objects whose instances represent individual
        #|          sensor nodes, within the local site's installation of
        #|          a COSMICi sensor network.  We use this to track the
        #|          state of any given node, and to send it commands using
        #|          this interface as a proxy.
        #|
        #|      Special methods:
        #|
        #|          .__init__(num, ip, net) - Instance initializer.
        #|
        #|      Public methods:
        #|
        #|          .reloc(ip) - Tell model the node relocated to a new IP address.
        #|          .isOn() - Tell model that this node is turned on.
        #|          .turnOn(when) - Tell model the node turned on at a specific time.
        #|          .sawAt(when) - Tell model we saw the node do something at a specific time.
        #|          .setMac(mac) - Tell model what this node's real MAC address is.
        #|
        #|      Private methods:
        #|
        #|          ._create_logger() - Set up the node-specific logger for
        #|              this node.
        #|
        #|          NOTE: THE FOLLOWING WAS MOVED TO WiFi_Module:
        #|                  ._setupBridgeServers() - Set up servers to listen for the
        #|                      AUXIO and UART-bridge data streams from this node.
        #|
        #|      TO DO:
        #|
        #|          [ ] Create subclasses of SensorNode for different types of nodes:
        #|               e.g. DetectorNode vs. CTU_Node.
        #|
        #|          [,] Move appropriate data members & code from here to the above
        #|               WiFi_Module and Sensor_Host classes, as appropriate.  (Since
        #|               the server will be talking directly to the FPGA board via
        #|               the bridged UART connection.) - UPDATE: WiFi_Module created,
        #|               Sensor_Host not yet.
        #|
        #|          [ ] Enable node state (including sensor state and Wi-Fi state)
        #|              to be saved to persistent storage, so that when server is
        #|              restarted up it doesn't have to re-learn all the node state
        #|              information from scratch.  This will make it easier to notice
        #|              when node information is actually changing (as opposed to just
        #|              a server restart or a new run starting).  It also allows for
        #|              potentially more graceful recovery in case the server has to be
        #|              restarted in the middle of the run.  (Currently we can't
        #|              really recover from a server shutdown except by restarting
        #|              the entire run, though...)
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class SensorNode(MutableClass):

    #|-----------------------------------------------------------------------------------
    #|
    #|   INSTANCE DATA MEMBERS:
    #|   
    #|       writelock:threading.RLock    [Add similar to WiFiBoard & FPGABoard.]
    #|
    #|           Threads should acquire this lock before modifying any
    #|           of the node's attributes.  NOTE: It's a re-entrant lock.
    #|
    #|       net:SensorNet
    #|
    #|           The overall SensorNet object that this node is a part of.
    #|
    #|       nodenum:int     
    #|
    #|           The node's index number, normally in the range 0-4, but
    #|           larger ID values may be allowed at some point.
    #|
    #|       ipaddr:str
    #|
    #|           The node's IP address on the LAN, as a string, like
    #|           "192.168.0.2".  The point of tracking this is so that (at
    #|           least in principle) nodes don't have to identify themselves
    #|           by their ID numbers every time - instead, we can just see
    #|           which IP address a given message is coming from.  (However,
    #|           at the moment we still expect nodes to provide their IDs
    #|           anyway.) (It's also useful for monitoring which nodes are
    #|           online using the router's web interface.)
    #|
    #|           [ ] TO DO: Move this to member class WiFi_Module.
    #|
    #|       macaddr:str
    #|
    #|           The node's MAC address, as a string, like "3e:af:2c:1d:08".
    #|           This can be considered a unique identifier for a given Wi-Fi
    #|           board.  If we remember this, it can be used to inform a node
    #|           of its node ID even if the node itself has forgotten.  (However,
    #|           a protocol for this has not yet been defined.)  In this meantime
    #|           This is just an interesting piece of FYI information that can
    #|           be compared with the Wi-Fi access point's reports of connected
    #|           clients.
    #|
    #|           [ ] TO DO: Move this to member class WiFi_Module.
    #|
    #|       status:str
    #|
    #|           The node's status, as far as we know, one of these strings:
    #|
    #|               UNSEEN - We haven't heard from this node at all
    #|                           yet in the current server session.
    #|
    #|               ON - We think that the node is powered on, but is
    #|                       not yet actively generating data for us.
    #|                       (Whether time data, or cosmic-ray data.)
    #|
    #|               RUNNING - We think that the node is powered on and
    #|                       is generating data for us on a regular basis.
    #|
    #|               ON_AWOL - We thought that the node was on, but we
    #|                       haven't heard from it in a while.  (A server
    #|                       heartbeat period or so.)  Not yet used.
    #|
    #|               RUNNING_AWOL - We thought that the node was turned on
    #|                       and was actively running, but we haven't
    #|                       heard from it in a while.
    #|
    #|       onAt:CoarseTimeStamp    [Move to WiFi_Module?]
    #|
    #|           The time at which we first heard that the node was turned on.
    #|           (Note this is not the same as the time that the run started,
    #|           which is later, when we see the 1ST_SYNC message.
    #|
    #|       lastSeen:CoarseTimeStamp    [Add similar to WiFi_Module & Sensor?]
    #|
    #|           The time at which we last received any message whatsoever
    #|           from the node.
    #|
    #|      wifi_module : WiFi_Module
    #|
    #|          This sub-object is a model of the EZURiO WISM Wi-Fi module
    #|          (which is really a whole development board that we're using).
    #|
    #|      sensor_host : SensorHost
    #|
    #|          This sub-object is a model of the main local host computer
    #|          running this sensor node.  In our case, this comprises a
    #|          Nios II soft-core CPU running inside a SOPC system design
    #|          running inside an Altera Stratix FPGA mounted on an FPGA
    #|          development board or prototype board.
    #|              Initially, the sensor_host object is of the generic base
    #|          class SensorHost, but as soon as we find out which specific
    #|          type of SensorHost it is, we transform this object into an
    #|          instance of the appropriate derived class, which in our case
    #|          is either CTU_Host or ShowerDetector_Host.
    #|
    #|      THE FOLLOWING FIELDS HAVE BEEN MOVED OUT INTO THE 'WiFi_Module' MEMBER CLASS:
    #|
    #|                 uartServer:bridge.BridgeServer      [/] Move to WiFi_Module class.
    #|
    #|                      A TCP server object (BridgeServer) set up specifically for
    #|                      us to remotely monitor and insert commands into the raw
    #|                      UART data stream coming from this node's internal RS-232
    #|                      interface to its FPGA-based sensor (Front-End Digitizer
    #|                      Module or CTU_GPS module).
    #|	
    #|                  auxioServer:bridge.BridgeServer     [/] Move to WiFi_Module class.
    #|
    #|                      A TCP server object (BridgeServer) set up specifically for
    #|                      us to remotely monitor and insert commands into the raw
    #|                      AUXIO (substitute for STDIO) data stream being used by the
    #|                      script running on this node's Wi-Fi board as a network-
    #|                      based replacement for STDIO.  (We can't use a bridge b/c
    #|                      the EZURiO can only create 1 bridge at a time!)
    #|
    #|       logger:logmaster.Logger
    #|
    #|           A special logger just for logging log messages sent by this
    #|           one node.  This is a child of the root logger, which I think
    #|           means that these messages will go to the main logger as well.
    #|
    #|----------------------------------------------------------------------------------------------------

        #|-----------------------------------------------------------------------------
        #|
        #|   SensorNode.__init__()                  [special instance method]
        #|
        #|       Initializer for new instances of class SensorNode.
        #|
        #|       NOTE:  At the time when a given SensorNode instance
        #|       is first created, and this method is called to init-
        #|       ialize it, we might not have actually seen the real
        #|       node yet - we might just be EXPECTING to see the node
        #|       (e.g., perhaps because we saw it in a previous run,
        #|       or because we are restoring the server state from
        #|       files after the server exited for some reason).
        #|
        #|       This initializer just initializes various data members,
        #|       & creates a logger for logging log messages sent from
        #|       the node to COSMICi.node[0-4].log.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def  __init__(self:SensorNode, num:int = None, ip:str = None, net:SensorNet = None):    

            # Initialize instance variables.
        
        self.writelock = threading.RLock()    # Create our write lock.       
                #-Don't need to acquire write lock right away b/c other threads can't see object yet.

            # But, do it anyway, out of paranoia.  (Maybe they got it between __new__ & __init__.)

        with self.writelock:

                # Here, we need to create the new .wifi_module component, and
                # delegate this work to it.  However, that needs to be tested,
                # since moving these attributes could break something elsewhere
                # in the program.  I should have defined them as private fields
                # originally, and then just defined properties to access them.
                # Oh well.  Refactoring code is always a pain.
            
            self.nodenum        = num       # Node number: Normally, 0-4 (maybe larger).
            self.ipaddr         = ip        # IP address of node on local WiFi net
            self.net            = net       # The SensorNet structure that this node is part of.
            self.status         = 'UNSEEN'  # Mark it as UNSEEN until we hear from it.
            
                # NOTE: Some of the above code may eventually be removed because
                # it will now be the responsibility of the new WiFi module below.
                
                # Create the node-specific logger (i.e., logging channel).

            self._create_logger()
            
                # Create a sub-object representing the Wi-Fi module component
                # of this node, initialized appropriately.
                
            self.wifi_module    = wifi.WiFi_Module(self, num, ip)

                # Create a sub-object representing the host (main computer)
                # at this sensor node; initialize this object appropriately.

            self.sensor_host    = SensorHost(self)

        #<- End 'with self.writelock'.

            # Insert a little header into the node's log file to delimit the start of the log.
        
        self.logger.normal("|------------------------------------------------------------|")
        self.logger.normal("|  Node %d log started.                                       |" % num)
        self.logger.normal("|VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV|")
        
    # End SensorNode.__init__().


        #|------------------------------------------------------------------------------------
        #|
        #|      METHOD:     SensorNode._create_logger()          [private instance method]
        #|
        #|          Sets up the node-specific logger for this node.
        #|          Called during node initialization, from __init__().
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def _create_logger(self):
        with self.writelock:
            loggername = logmaster.sysName + ('.node%d' % self.nodenum)     # This will look like 'COSMICi.node0'
            self.logger = logmaster.getLogger(loggername)                   # Create logger just for this node's log messages.            
            lfh = logmaster.logging.FileHandler(loggername + ".log")        # A filehandler to log this node's log messages to its own log file ('COSMICi.node0.log').
            lfh.setFormatter(logmaster.logFormatter)                        # Tell this filehandler to use logmaster's default log formatter.
            self.logger.logger.addHandler(lfh)                              # Tell our logger to use that new filehandler.
            self.logger.logger.setLevel(logmaster.logging.DEBUG)            # Have it log ALL log messages sent by this node (including debug).            
        

        #|---------------------------------------------------------------------------------
        #|
        #|   SensorNode.reloc()                      [public instance method]
        #|
        #|       Relocate an existing node to a new IP address.  This could
        #|       be needed, for example, if the router gets reset, or if
        #|       nodes' DHCP leases expire and get renewed differently from
        #|       how they were previously assigned.
        #|
        #|  TO DO:
        #|      [ ] Move this to WiFi_Module subclass.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def reloc(self, ip):
        with self.writelock:
            
                # The following line will eventually be removed because WiFi_Module will track IP instead.
                
            self.ipaddr = ip                # Remember this node's new IP address.
            
            self.wifi_module.isAt(ip)       # Tell the model of the WiFi board about the change.


        #|---------------------------------------------------------------------------------
        #|
        #|  SensorNode.isOn()                           [public instance method]
        #|
        #|       Inform the model node that the real node is in the "ON"
        #|       state (but we don't necessarily know exactly when it
        #|       first turned on, e.g. if we missed the POWERED_ON msg).
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def isOn(self):
        with self.writelock:
            self.status = 'ON'
    

        #|--------------------------------------------------------------------------------
        #|
        #|      SensorNode.turnOn()                         [public instance method]
        #|
        #|          Tell the model node that the real node was turned on at a
        #|          specific time.  (Actually this is just the time that the
        #|          turn-on message from it was received, but close enough.)
        #|
        #|      TO DO:
        #|          [ ] Move appropriate functionality from here into WiFi_Module
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def turnOn(self, when):
        
            # Make sure time is in displayable CoarseTimeStamp format.
        if  not isinstance(when, timestamp.CoarseTimeStamp):
            when = timestamp.CoarseTimeStamp(when)

            # Log this event at NORMAL level (also displays on console).    
        logger.normal("Node %d turned on at %s." % (self.nodenum, when))

            # Thread-safely initialize various fields.
            
        with  self.writelock:       # Acquire our write lock.
            
            self.isOn()                 # Mark node status as ON.
            self.onAt       = when      # Record node's turn-on time.
            self.lastSeen   = when      # Which is also its last-seen time.

            self.wifi_module.turnedOnAt(when)
                #- Tell the model Wi-Fi module that this node has turned on.
                #   This then creates the listeners for the expected new connections.
            
        #<-- End with node lock.
            
    #<-- End method SensorNode.turnOn().


        #|-------------------------------------------------------------------------------------
        #|
        #|      SensorNode.sawAt()                          [public instance method]
        #|
        #|          Make a note that we saw the node actively doing something
        #|          at a specific time.  This updates the node's status and
        #|          its last-seen time.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def sawAt(self, when):
        # Make sure time is in displayable CoarseTimeStamp format.
        if not isinstance(when, timestamp.CoarseTimeStamp):
            when = timestamp.CoarseTimeStamp(when)
#        logger.debug("Remembering that we saw node %d at time %s." % (self.nodenum, str(when)))
        with self.writelock:
            self.lastSeen = when
            # Also mark the node as no longer being AWOL, if it is so marked.
            if self.status == 'ON_AWOL':
                self.status = 'ON'
            elif self.status == 'RUNNING_AWOL':
                self.status = 'RUNNING'
#        logger.debug("Node %d's status is currently: %s" % (self.nodenum, self.status))


        #|---------------------------------------------------------------------------------
        #|
        #|      SensorNode.setMac()                         [public instance method]
        #|
        #|          Tells the model node what the real node's MAC address is.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def setMac(self, mac):
        
        logger.normal("Node %d reports its MAC address is %s." % (self.nodenum, mac))
        
        with self.writelock:       # Not necessary since assignment is atomic.
            
            self.macaddr = mac          # Set mac address to given value.

                # In future, the above line may be removed since the model of the Wi-Fi module
                # will henceforth be responsible for remembering the MAC address information.

            self.wifi_module.hasMac(mac)    # Tell the model of the Wi-Fi module what its MAC addr is.

        #<-- End with node lock.
            
    #<-- End method SensorNode.setMac().
            
#<-- End class SensorNode.

            
    #|--------------------------------------------------------------------
    #|
    #|      SensorHost                          [module public class]
    #|
    #|          Abstract base class for the main host CPUs
    #|          (which in our case, are always Nios II soft
    #|          cores embedded in Altera Stratix FPGAs).
    #|
    #|          A direct instance of this base class
    #|          represents a host whose subtype (CTU
    #|          vs. Detector) is not yet known.  Once
    #|          we find out its type, we mutate the
    #|          object into the appropriate subclass 
    #|          (CTU_Host or DetectorHost).
    #|
    #|      Public class data members:
    #|
    #|          sensorHostType (string) - A string representing
    #|              the type of sensor host this is.  Values are:
    #|
    #|                  'UNKNOWN' -  Type not yet known.  Base
    #|                      class has this value.  Derived classes
    #|                      should override it.
    #|
    #|                  'CTU_GPS' - Central Timing Unit host with
    #|                      support for absolute timing via GPS.
    #|
    #|                  'DETECTOR' - Pulse detector host (any type).
    #|
    #|                  'SHOWER_DETECTOR' - A detector host that
    #|                      detects pulses from multiple PMT input
    #|                      channels & does coincidence filtering.
    #|
    #|          hostType (string) - Raw host type string, as
    #|              reported by the host itself.  Current values are:
    #|
    #|                  None - Not yet known.
    #|
    #|                  'CTU_GPS' - Central timing unit host with
    #|                      support for GPS-based absolute timing.
    #|
    #|                  
    #|
    #|      Public instance data members:
    #|
    #|          _lock - Reentrant mutex lock for write access.
    #|
    #|          node - The node that this host is controlling.
    #|
    #|          nodenum - The ID number of this node.
    #|
    #|          starting - A flag indicating that this host is
    #|              currently in its startup sequence but is not yet
    #|              ready to begin processing input commands and
    #|              commencing normal operation.
    #|
    #|          ready - A flag indicating that this host has
    #|              completed its startup sequence and is ready to
    #|              begin processing input commands and to commence
    #|              normal operation.
    #|
    #|      Special instance methods:
    #|
    #|          __init__() - Instance initializer.  Routine setup.
    #|
    #|          _convertFrom() - 
    #|
    #|      Public instance methods:
    #|
    #|          isType(sensorHostType) - Tells the model that this
    #|              SensorHost is of the given type, identified by
    #|              a string, one of 'UNKNOWN', 'CTU_GPS', or
    #|              'SHOWER_DETECTOR'.
    #|
    #|          sentMessage(Communicator.Message:msg) - Informs the
    #|              model host that the real host just transmitted
    #|              the given message.
    #|
    #|      Private instance methods:
    #|
    #|          _handleHostStarting() - Handles the HOST_STARTING
    #|              message.
    #|
    #|          _handleHostReady() - Handles the HOST_READY message.
    #|
    #|          _handleHostMsg() - Handles a given message from
    #|              real host.  The message has already been parsed
    #|              and is really from the host itself, not relayed
    #|              from some other component node.
    #|
    #|          _handleMsg() - Handles a given message from the
    #|              real host.
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class SensorHost(MutableClass):

    sensorHostType = 'UNKNOWN'      # Direct instances of base class
        # are of unknown type initially.  They should become instances
        # of a derived class once we learn their type.

    def __init__(this, node:SensorNode):
        this._lock = threading.RLock()
        with this._lock:
            
            this.node = node                        # Remember the node object we're a part of.
            this.nodenum = node.nodenum             # Remember the node number.
            
            this.hostType = None                    # Host type is initially unknown.
#            this.sensorHostType = 'UNKNOWN'         # Same info in another form.
            
            this.starting = flag.Flag(this._lock)   # Create "starting" flag (initially false).
            this.ready = flag.Flag(this._lock)      # Create "ready" flag (initially false).

            MutableClass.__init__(this)     # Superclass initializer.

# Following is no longer needed now that SensorHost is a subclass of class MutableClass.

##                # The following line allows us to later say things like 
##                # "this.become(CTU_Host)" to dynamically change the class
##                # of instance <this> to class <CTU_Host> (once we learn
##                # what class it is).
##
##            this.become = bind(this, become)        # Install the universal "become" method.

    #<- End def __init__().

        #|--------------------------------------------------------------------
        #|
        #|      sentMessage()                   [public instance method]
        #|
        #|          Informs the host model that the real host
        #|          just sent the given message to the server.
        #|          Dispatches the message to an appropriate
        #|          handler.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def sentMessage(this, msg:communicator.Message):    # Not yet implemented
        this._handleMsg(msg)        # Dispatch to message handler.


        # Tells the sensor host model that the real host's type is the given string,
        # currently supported ones being:  'UNKNOWN' (treated as base class instance),
        # 'CTU_GPS' (treated as CTU_Host instance), and 'SHOWER_DETECTOR' (treated as
        # ShowerDetectorHost instance).  

    def isType(this, sensorHostType:str):

        with this._lock:

                # We know how to change a sensor host's type to CTU_GPS.
            
            if sensorHostType == 'CTU_GPS':
                logger.debug("Aha, now I realize that node #%d's host is a CTU host..." % this.nodenum)
                this.become(ctu.CTU_Host)                   # Change this object's class to CTU_Host.

                # We know how to change a sensor host's type to SHOWER_DETECTOR.

            elif sensorHostType == 'SHOWER_DETECTOR':
                logger.debug("Aha, now I realize that node #%d's host is a shower-detector host..." % this.nodenum)
                this.become(fedm.ShowerDetectorHost)         # Change this object's class to ShowerDetectorHost.

                # We don't know how to change a sensor host's type to any other type.

            else:
                logger.warn(("SensorHost.isType(): Don't know how to change the sensor " +
                             "host model to type %s.  Leaving type unchanged.") % sensorHostType)
                
            #<- End if sensorHostType ...
        #<- End with this._lock.
    #<- End def isType().

        # Send the host the given command/message line.  Of course, we dispatch this
        # to the node's Wi-Fi module.  It should forward the line to the host (if it's
        # not a Wi-Fi command).  Note: A more elegant approach would be for commands
        # to the host to call start with "HOST ..." or something like that.  Actually,
        # maybe that's not such a bad idea...  We'll let the .sendHost() module take
        # care of this, if necessary.

    def sendLine(this, line:str):   # Assume <line> is not yet newline-terminated.
        this.node.wifi_module.sendHost(line + "\n")

        # Handles the HOST_STARTING message.

    def _handleHostStarting(this, msgWords):

            # Make sure the argument list has the expected length.

        nArgs = len(msgWords) - 1
        if nArgs != 2:
            logger.error(("SensorHost._handleHostStarting(): I expected the HOST_STARTING " +
                          "message to have 2 arguments (<host_type>,<version_id>), but instead " +
                          "I got %d arguments %s... Ignoring message.") % (nArgs, msgWords[1:]))

        hostType = msgWords[1]      # 1st argument
        verID = msgWords[2]         # 2nd argument

        this.hostType = hostType        # Remember the raw host type.

        if hostType == 'CTU_GPS':                       # CTU_GPS host type, we recognize.
            sensorHostType = hostType                   # Preserve it as our sensorHostType.
            
        elif hostType == 'FEDM':                        # FEDM host type, we also recognize.
            sensorHostType = 'SHOWER_DETECTOR'          # For now, assume FEDM is configured as a ShowerDetector.

        else:   # Unknown host type.  Display an error.
            sensorHostType = 'UNKNOWN'
            logger.error(("SensorHost._handleHostStarting(): The host type %s is unknown.  " +
                          "I will be unable to do anything with data from this host.") % hostType)
            return

        logger.normal("Node #%d's host (type %s, firmware version %s) is starting up..." %
                      (this.nodenum, hostType, verID))

        this.isType(sensorHostType)     # Actually change the sensorHostType of this instance.
        this.starting.rise()            # Raise the "starting" flag for this host.
        
    #<- End def _handleHostStarting().

        #  Handles the HOST_READY message.  Right now, this just updates
        #  the starting/ready flags.

    def _handleHostReady(this):

        logger.normal("Node #%d's host is ready to accept commands." % this.nodenum)

        with this._lock:
            this.starting.fall()    # Lower the 'starting' flag for this host model.
            this.ready.rise()       # Raise the 'ready' flag for this host model.

        #|--------------------------------------------------------------------
        #|
        #|      _handleHostMsg()                [private instance method]
        #|
        #|          Handles a message from the real host, with
        #|          the following additional stipulations:
        #|
        #|              1. If the message is already of NMEA type
        #|                  (starting with '$'), the $ has already
        #|                  been stripped of and the checksum (if
        #|                  present) already verified and stripped.
        #|
        #|              2. The message has already been broken into
        #|                  words on comma (",") delimiters.
        #|
        #|              3. We have already verified that this is not
        #|                  a message of a type that the host is just
        #|                  passing through from a GPS module.  It is
        #|                  truly specific to the host itself.
        #|
        #|          The following messages are the only messages
        #|          understood by this generic host model; however,
        #|          additional message types may be interpreted within
        #|          subclasses.
        #|
        #|              HOST_STARTING,<type_id>,<version_id>  -  A host
        #|                  of the given type and firmware version ID
        #|                  is just starting up.  This message is sent
        #|                  right after the host initializes its serial
        #|                  port.  The type ID is one of the following:
        #|
        #|                      'CTU_GPS' - Central Timing Unit, GPS-capable.
        #|
        #|                      'FEDM' - Front-end digitizer module, currenly
        #|                          understood to be a SHOWER_DETECTOR.
        #|
        #|                  Our reaction to this message is to raise a
        #|                  flag indicating that the host is starting,
        #|                  and mutate the present host instance to
        #|                  reflect the particular subclass of SensorHost
        #|                  that is relevant.
        #|
        #|              HOST_READY - The host has completed its autonomous
        #|                  initialization sequence and is ready to begin
        #|                  processing input commands from the server and
        #|                  to commence normal operation.
        #|                      Our reaction to this message is simply to
        #|                  lower the 'starting' flag and raise the 'ready'
        #|                  flag.  A worker thread responsible for imple-
        #|                  menting the system startup sequence may want to
        #|                  wait for the 'ready' flag to be raised before
        #|                  proceeding with its work.
        #|                  
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _handleHostMsg(this, msgWords):     

        logger.debug("SensorHost._handleHostMsg(): Handling host message [%s]..." % str(msgWords))
    
            # We'll interpret the first field as the message type designator.

        msgType = msgWords[0]

            # Dispatch based on message type.

        if msgType == 'HOST_STARTING':
            this._handleHostStarting(msgWords)

        elif msgType == 'HOST_READY':
            this._handleHostReady()              # No arguments.

        elif msgType == 'ACK':      # Host acknowledging a message from the Wi-Fi (or from us).
            logger.info("SensorHost._handleHostMsg(): Host acknowledges receiving message %s." % str(msgWords[1:]))

        elif msgType == 'ERR':      # Host is reporting its own error condition that we can log.
            logger.error("SensorHost._handleHostMsg(): Sensor host reports a %s error with data [%s]." % (msgWords[1], msgWords[2]))
                #   |
                #  Really, what would make even more sense here would be to have created a logging channel just for
                #  host errors, with an associated log file.  The logging channel name would be something like
                #  COSMICi.node0.host.  The ERR messages could be extended to include logging-level information so
                #  we could handle them similarly to the LOGMSG messages received from the Wi-Fi script on the
                #  mainserver connection.  Likewise, there could be a logging channel COSMICi.node0.GPS to record
                #  GPS-related conditions.

        else:
            logger.warn("SensorHost._handleHostMsg(): Unknown host message type [%s]. Ignoring..." % msgType)

    #<- _handleHostMsg()

        # Parse an incoming message.  Processes NMEA decorations, checksum,
        # and fields.  Returns the sequence of message words.

    def _parseMsg(this, msg:communicator.Message):
        
            #|-----------------------------------------------------------------------
            #|
            #| Outline of message-parsing process:
            #|
            #|   1. Determine if it's an NMEA-type message (starting with '$').
            #|       If so, then verify its checksum & strip off the $* stuff.
            #|
            #|   2. Split the message string into words on comma delimiters (",").
            #|
            #|   3. Based on first word, dispatch to a handler for this specific
            #|       type of message.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        msgStr = msg.data           # Get message data string.
        msgStr = msgStr.strip()     # Strip off any leading/trailing whitespace.

            # First, make sure it's not an empty string.  (If so, emit a warning & return.)

        if msgStr == None or msgStr == "":
            logger.info("SensorHost._parseMsg(): Given empty message; ignoring...")
            return None

            # Next, if it's an NMEA-formatted sentence, strip the $* stuff off of it
            # and verify any checksum in the process.

        try:
            msgStr = nmea.stripNMEA(msgStr)     # Warning: This may throw an nmea.BadChecksum exception.
        except nmea.BadChecksum:
            logger.error("SensorHost._parseMsg(): Checksum failed on line [%s]; ignoring line..." % msgStr)
            return None     # Indicates no good data.            
                         
            # Really we ought to catch this here with a try/except and do something sensible with it.

        logger.debug("SensorHost._parseMsg(): After stripping any NMEA framing I got the message [%s]." % msgStr)

            # If nothing is left after stripping the NMEA decorations,
            # then return early.

        if msgStr == "":
            logger.warn("SensorHost._parseMsg(): Message empty after stripping away NMEA framing; ignoring...")
            return

            # Special case:  If the message begins with "PDMEHEADER",
            # then replace ": " with "," so that the following split()
            # will work to separate the message type name from the rest.

        if msgStr.startswith("PDMEHEADER"):
            msgStr = msgStr.replace(": ", ",")

            # At this point, we have a presumably comma-separated host message.
            # Split it at the commas.

        msgWords = msgStr.split(',')        # Create array of fields that were separated by commas.

            # Special case:  If the message begins with "CON_PULSE",
            # then unsplit everything after argument 6, since it is
            # a nested list of the form "(0,(1,(2,9),5),8)".

        if msgStr.startswith("CON_PULSE"):
            msgWords[7:] = [unsplit(msgWords[7:], ",")]

        return msgWords     # Return that sequence of words.

        #|--------------------------------------------------------------------
        #|
        #|      _handleMsg()                    [private instance method]
        #|
        #|          Appropriately handles a given incoming message
        #|          from the real host.  We parse the message into
        #|          fields and dispatch appropriately.  Based on
        #|          the message contents, we update properties of
        #|          the model host.
        #|
        #|          Subclasses may want to override this method.
        #|          E.g., this is done by CTU_Host below, to identify
        #|          messages originating from the GPS sub-module rather
        #|          than from the host itself.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _handleMsg(this, msg:communicator.Message):

        msgWords = this._parseMsg(msg)  # Parse the message into fields.

            # If message was empty, don't bother doing anything else.

        if msgWords == None:
            logger.info("SensorHost._handleMsg(): Empty message; ignoring...")
            return

            # We'll interpret the first field as the message type designator.

        msgType = msgWords[0]

            # Assume it's a message originated by the host, rather than
            # some other component, because since we don't know what type
            # of host this is yet, we don't know what other types of components
            # it might contain and thus what other message types to look for.

        this._handleHostMsg(msgWords)
            
    #<- End def SensorHost._handleMsg().

#<- End class SensorHost

    # Object-model modules for specific types of sub-components of the system.

import  ctu         # Central Timing Unit - A particular type of node.
import  fedm        # Front-End Digitizer Module - A particular type of node.

    # PLEASE NOTE:  The above imports (ctu & fedm at least) have to go at the END
    # of this file (model.py) instead of at the beginning, because ctu & fedm define
    # subclasses that inherit from a base class (SensorHost) defined in this module.

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# End module model.py.
#======================================================================================================
