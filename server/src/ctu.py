#|******************************************************************************
#|                                  TOP OF FILE
#|******************************************************************************
#|
#|      FILE NAME:  ctu.py                          [python module source file]
#|
#|          This file defines a Python module implementing our
#|          overall object model of/server-side proxy for the
#|          Central Timing Unit (CTU) embedded system.
#|
#|          This includes two classes:  CTU_Node, representing the
#|          entire sensor node that includes the CTU application,
#|          and CTU_Host, representing the embedded microcontroller
#|          system that has primary responsibility for interfacing
#|          with and directly controlling the CTU hardware.
#|
#|          Presently, we are not really using the CTU_Node class
#|          at all.  We do use the CTU_Host class; when we change
#|          into this class, it creates a GPS_Module sub-object to
#|          model the GPS development kit, and it handles the
#|          PPSCNTR message emitted by the CTU (currently we just
#|          display a diagnostic message when it arrives.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # User includes.

import  logmaster           # .getLogger() function
import  communicator        # .Message class
import  model               # .SensorHost class
import  gps
import  utils               # .WatchBox class
import  publisher           # .Publisher class

    # Export public names.

__all__ = [
    'CTU_Node',             # Subclass of SensorNode for the Central Timing Unit.
    'CTU_Host',             # A component of a CTU_Node - The CTU GPS app, now running on the DE3 board (Stratix III FPGA).
    ]

    # Create module's logging channel.

logger = logmaster.getLogger(logmaster.sysName + '.model.ctu')

class CTU_Node(model.SensorNode): pass  # Forward declaration

    #|--------------------------------------------------------------------------
    #|
    #|      CTU_Host                                [module public class]
    #|
    #|          Provides our object model/server-side proxy for the
    #|          Central Timing Unit (CTU).
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class CTU_Host(model.SensorHost):

    sensorHostType = 'CTU_HOST'     # Override default value from parent class.

        # Tells the model CTU host to tell the real CTU host to
        # go ahead and commence normal operations at this time.
        # This is what actually begins a data-collection run,
        # since only after this point can data records be
        # properly time-tagged with time values that can be
        # referenced back to an absolute time derived from GPS.

    def start(this):
        this.sendLine("START")      # Intelligently relays START command to host.
    #__/ End def CTU_Host.start().
        
        #|----------------------------------------------------------------------
        #|
        #|      _convertFrom()                     [private instance method]
        #|
        #|          This special instance method (user-defined in
        #|          utils.MutableClass, not defined by Python) has
        #|          the job of converting instances of other classes
        #|          into instances of the current class.
        #|
        #|              In the present system context, we only expect
        #|          this method to be called on objects previously of
        #|          class SensorHost, and only at the moment that we
        #|          discover that they are class CTU_Host.  So, we can
        #|          ignore <oldClass> for the time being.
        #|
        #|              One thing that we do need to do here, however,
        #|          is to create our node's data member .gps_module,
        #|          which is the model proxy for the DeLorme GPS
        #|          development kit, part of the node hardware being
        #|          managed by a host of this type.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _convertFrom(this, oldClass:type):

        logger.debug("CTU_Host._convertFrom(): Converting self from class %s to class CTU_Host..." % str(oldClass))

            # Create the model/proxy for the node's GPS module.

        this.node.gps_module = gps.GPS_Module(this.node)

            # Create the GPS Manager object to manage the state of the node's GPS module.

        this.node.gps_manager = gps.GPS_Manager(this.node)

            # Create an "inbox" (really, WatchBox) to track the most recently-
            # received PPSCNTR message from the real CTU.

        this.pps_inbox  = utils.WatchBox(lock = this._lock)

            # Create a "publisher" object to allow other entities to subscribe
            # to be notified of each message from the CTU of a given type
            # (currently, it only produces messages of type 'PPSCNTR').  The
            # advantage of this over the WatchBox mechanism is that it
            # guarantees that no messages will be missed.

        this.publisher = publisher.Publisher()

            # Change the node's class as well.

        this.node.become(CTU_Node)

    #__/ End def CTU_Host._convertFrom().


        # Override _handleHostReady() to add some behavior specific to the CTU host.

    def _handleHostReady(this):
        
        model.SensorHost._handleHostReady(this)     # Relay method call to superclass.
        
            # Send CTU an UNMUTE command to make sure GPS pass-thru is turned on.
            # At this point we can start processing status messages from the GPS.
        this.sendLine("UNMUTE")

            # Tell the application's main object (the CosmicIServer instance)
            # that the CTU is now ready.  (It needs to be made aware of this
            # so that it can start using the CTU.)  (Note this code implcitly
            # assumes there is only one CTU node in the sensor network.)

        this.node.net.cis.yo_CTU_is_ready(this.node)
        
    #__/ End def CTU_Host._handleHostReady().

        # A nested class to represent the data contents of an individual
        # PPSCNTR message.

    class   _PPSCNTR_Record:    pass    # For storing data from a PPSCNTR message.

        # Handle the custom "PPSCNTR" message generated by the CTU host.
        # Really, this message should be called "CTPPS" or something like
        # that to conform with NMEA naming conventions (CT=speaker ID,
        # PPS=msg type).  Anyway... For now, all we do with this message
        # is display (and log) a normal console message reporting it.
        # And publish it to WatchBox waiters and magazine subscribers.

    def _handlePPSCNTR(this, msgWords):

            # Calculate & verify number of arguments provided.

        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 2:
            logger.error(("CTU_Host._handlePPSCNTR(): I expected the PPSCNTR " +
                          "message to have 2 arguments but it had %d.  " +
                          "Ignoring message...") % nArgs)

            # Parse out all the arguments into appropriately named
            # attributes of a _PPSCNTR_Record instance.

        ppscntr_rec = this._PPSCNTR_Record()    # Create new empty PPSCNTR record object.

        ppscntr_rec.pps_num  = msgWords[1]   # Sequence number of a PPS rising edge from the GPS.
        ppscntr_rec.fast_cnt = msgWords[2]   # Sequence number of our fast time counter
            # (currently a 750 Mcps dual-edge triggered counter clocked by a 350 MHz PLL
            # clock derived from the 10 MHz OCXO clock)

        logger.normal(("CTU received PPS rising edge #%d from " +
                       "GPS at time-counter value %d.") %
                      (int(ppscntr_rec.pps_num), int(ppscntr_rec.fast_cnt)))

        this.pps_inbox.contents = ppscntr_rec   # Remember this record.  

        this.publisher.publish(publisher.Issue('PPSCNTR', ppscntr_rec))
            # Publish the record to any subscribers. 

    #__/ End def CTU_Host._handlePPSCNTR().


    def _handleHostMsg(this, msgWords):

        logger.debug("CTU_Host._handleHostMsg(): Handling host message [%s]..." % str(msgWords))

        msgType = msgWords[0]

        if msgType == 'PPSCNTR':
            this._handlePPSCNTR(msgWords)
        else:   # Dispatch to parent class.
            model.SensorHost._handleHostMsg(this, msgWords)

    def _handleMsg(this, msg:communicator.Message):

        logger.debug("CTU_Host._handleMsg: Handling message [%s]..." % msg.data.strip())

        msgWords = this._parseMsg(msg)  # Parse the message into fields.

        if msgWords == None:
            logger.info("CTU_Host._handleMsg: Empty message; ignoring...")
            return
        
        msgType = msgWords[0]           # Interpret first field as message type designator.
        
            # Formally, the first two characters of an NMEA message type are the
            # "talker ID" (e.g. "GP" for GPS), and the remaining characters are
            # the message type.  However, our way of categorizing messages is
            # simpler:
            #
            #       1. If it begins with "GP" it is a standard GPS message.
            #           Dispatch it to the GPS subsystem model.
            #
            #       2. If it begins with "PDME" then it's one of DeLorme's
            #           extensions.  Dispatch those to the GPS subsystem
            #           model also.
            #
            #       3. All other message types are assumed to be initiated
            #           by the host itself.  Dispatch those to _handleHostMsg().

        typeLen = len(msgType)

        logger.debug("CTU_Host._handleMsg: The length of the message type name is %d." % typeLen)

        isFromGPS = False       # Default assumption until we know otherwise.
        
        if typeLen >= 2:

            logger.debug("CTU_Host._handleMsg:  If this is an NMEA message, its talker ID is [%s]." % msgType[0:2])

            if msgType[0:2] == "GP":
                logger.debug("CTU_Host._handleMsg:  This is a standard GPS message.")
                isFromGPS = True
                
            elif typeLen >=4 and msgType[0:4] == "PDME":
                logger.debug("CTU_Host._handleMsg:  This is a DeLorme custom message.")
                isFromGPS = True

        if isFromGPS:
            logger.debug("CTU_Host._handleMsg:  Dispatching to GPS module proxy...")
            this.node.gps_module.sentMessage(msgWords)

        else:
            logger.debug("CTU_Host._handleMsg:  I don't think this message is from the GPS; I'm treating it as a normal host message...")
            this._handleHostMsg(msgWords)

    #<- End def CTU_Host._handleMsg().
            
#<- End class CTU_Host.


class CTU_Node(model.SensorNode):       

        #   CTU_Node.start()                            [public instance method]
        # This method tells the server-side model/proxy for the CTU node
        # (and through it, the real node, itself) to commence normal
        # operations.  This entails a few things:  (1) Counting time
        # internally in what is presently 750 Mcps = 4/3 ns increments
        # using its internal PLL clock slaved to the 1 ppb frequency-
        # stability OCXO clock; (2) Reporting to the server via the
        # PPSCNTR message the exact time of each rising edge of the PPS
        # signal from the GPS in terms of the internal fast clock cycles;
        # this tells us where the GPS is marking the start of the "real"
        # seconds (although the Timekeeper should probably still make
        # adjustments to that by averaging, to further improve the
        # accuracy); (3) Periodically (currently every 2^18 counter values
        # or every 349.52533... microseconds) send a > 50 ns long timing
        # sync pulse out to the other node(s) in the system; currently this
        # goes over an SMA cable directly to our single Front-End Data-
        # Acquisition Module (FEDAM), which is a 3-scintillator-detector
        # ShowerDetector board.
    
    def start(inst):

        inst.sensor_host.start()    # Relay this command to the node's host.

    #__/ End def CTU_Node.start().

#__/ End class CTU_Node.
        
