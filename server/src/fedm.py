#|******************************************************************************
#|                                  TOP OF FILE
#|******************************************************************************
#|
#|      FILE NAME:  fedm.py                         [python module source file]
#|
#|          This module implements our object model of / server-side
#|          proxy for a FEDM (Front-End Digitizer Module) sensor node.
#|
#|          This includes the following classes:
#|
#|              DetectorNode        - Generic class for particle-detector nodes.
#|              DetectorHost        - Generic class for the host in a DetectorNode.
#|              ShowerDetectorNode  - Coincidence-filtering shower-detector nodes.
#|              ShowerDetectorHost  - The host in a ShowerDetectorNode.
#|              Threshold_DAC       - Peripheral interface to the digital-analog 
#|
#|          Eventually, we should also add a ScintillatorDetector as a
#|          component of a DetectorNode.  These have locations in real
#|          physical space (3D coordinates, e.g. latitude/longitude/
#|          altitude).  These locations will have to be hard-coded in
#|          some kind of site-config file (or in the sitedefs.py source
#|          module).
#|              Associated with each ScintillatorDetector could be a
#|          PulseformChannel object, which we can maintain the following
#|          properties for (among others):
#|
#|              * Cumulative # of non-coincidence pulses received.
#|              * Cumulative # of hardware FIFO-full events received.
#|              * Cumulative # of candidate coincidence pulses received.
#|              * Cumulative # of pulses discarded due to a full SW buffer.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

import  logmaster
import  model           # Define ".SensorNode" class
import  utils           # .WatchBox class
import  publisher       # .Publisher class

__all__ = [
    
    'DetectorNode',         # Subclass of SensorNode for an actual particle-detecting node.
    'ShowerDetectorNode',   # Subclass of Detector_Node for multi-sensor coincidence-filtering nodes (like the FEDM, as presently configured).
    
    'DetectorHost',         # A component of a Detector_Node - A detector app, now running on the FEDM board (Stratix II FPGA).
    'ShowerDetectorHost',   # A component of a ShowerDetector_Node - Subclass of Detector_Host for coincidence-filtering shower-detection mode.
    
    'Threshold_DAC',        # A component of a Detector_Node - A DAC setting detection threshold levels.
    'PulseformChannel',     # A component of a Detector_Host - An input channel on which we can receive digitized, timestamped pulse shapes.
    ]

    # Create module's logging channel.

logger = logmaster.getLogger(logmaster.sysName + '.model.fedm')

    # Advance declarations.

class DetectorNode(model.SensorNode):       pass

    # Not using this intermediate class for anything yet.
class DetectorHost(model.SensorHost):       pass        # Not yet implemented

    # Shouldn't the following really be a nested class within ShowerDetectorHost?

class PulseformChannel:
    # Data members:
    #   chan_id - The channel's ID #, an integer 1-3.

    def __init__(inst, chan):
        inst.chan_id = chan     # Channel identifier, in the range 1-3. (1-4 in the future)
        inst.cum_ncp = 0        # Cumulative number of non-coincidence pulses received on this channel.
        inst.cum_ffe = 0        # Cumulative number of FIFO-full events that have occurred on this channel.
        inst.cum_ccp = 0        # Cumulative number of candidate coincidence pulses received on this channel.
        inst.cum_lsp = 0        # Cumulative number of pulses lost (discarded) due to a full software buffer.
    

class ShowerDetectorHost(DetectorHost):

    sensorHostType = 'SHOWER_DETECTOR'

    def _convertFrom(this, oldClass:type):

        logger.debug("ShowerDetectorHost._convertFrom(): Converting self from class %s to class ShowerDetectorHost..." % str(oldClass))

        # TODO: Create sub-objects representing the various threshold-level DACs.
        # Also, create sub-objects representing the various input channels.

            # Create a fixed tuple of sub-objects representing the three pulse-
            # form input channels.  They are all initialized to a state indicating
            # that no data has yet been received on that channel.

        this.input_channels = (
            PulseformChannel(1),
            PulseformChannel(2),
            PulseformChannel(3))
            # NOTE: These are not yet used.

            # These watch-boxes allow inspecting the last message that occurred
            # of a given type, or waiting for the next one to occur.

        this.daclevs_inbox  = utils.WatchBox(lock = this._lock)
        this.ncpuls_inbox   = utils.WatchBox(lock = this._lock)
        this.fifull_inbox   = utils.WatchBox(lock = this._lock)
        this.conpuls_inbox  = utils.WatchBox(lock = this._lock)
        this.lostpuls_inbox = utils.WatchBox(lock = this._lock)

            # The Publisher interface allows subscribers to register callbacks
            # to be called on every message of a given type.
        
        this.publisher = publisher.Publisher()

    #__/ End def ShowerDetectorHost._convertFrom().


        # Override _handleHostReady() to add some behavior specific to the FEDM host.

    def _handleHostReady(this):
        
        DetectorHost._handleHostReady(this)     # Relay method call to superclass.
        
            # Tell the application's main object (the CosmicIServer instance)
            # that the FEDM is now ready.  (It needs to be made aware of this
            # so that it can start using the FEDM.)  (Note this code implcitly
            # assumes there is only one FEDM node in the sensor network - which
            # is only true for the present FEDM, which is a ShowerDetectorNode
            # that receives input from all the PMTs in the local sensor net.
            # (For stage 2 FEDMs, we'll have to do something more complex.)

        this.node.net.cis.yo_FEDM_is_ready(this.node)
        
        # A "_TimeSync_Ref" or time synchronization reference consists of
        # a sequence counter for the most recent time-sync pulse received
        # from the CTU, and a clock cycle number for the local high-speed
        # PLL clock cycle counter.  Our goal is to count time at 500 Mcps.
        # (Mcps = Million counts per second), in which case the cycle
        # counter is counting time using approx. 2 ns time units.
        #   The _TimeSync_Ref data type will be used as part of the raw
        # data structures for all 3 of the messages received from the FEDM:
        # NC_PULSES, FIFO_FULL, and CON_PULSE.

    class _TimeSync_Ref:        pass
        # Fields will be:
        #   .sync_num (natural) - Sequence number of last synchronization pulse received.
        #   .pll_cyc (natural)  - Sequence number of corresponding clock cycle for the fast PLL on the FEDM.
    #__/ End class _TimeSync_Ref
        

        # Examples of message formats:
        #   DAC_LEVELS,-0.200,-2.500,-0.299,-0.447,-0.669,-1.000
        #   NC_PULSES,1618,3352941653,3352948689,115,68,203
        #   FIFO_FULL,2392,3407048110,3,1
        #   CON_PULSE,3186,3462552667,3,1,3462608072,2,(0,(2,2),5)
        #   LOST_PULSES,2,1

    class _DAC_LEVELS_Record:   pass        # For storing data from a DAC_LEVELS message.  To be implemented.

    class _NC_PULSES_Record:    pass        # For storing data from an NC_PULSES message.  To be implemented.

    class _FIFO_FULL_Record:    pass        # For storing data from a FIFO_FULL message.  To be implemented.

    class _CON_PULSE_Record:    pass        # For storing data from a CON_PULSE message.  To be implemented.

    class _LOST_PULSES_Record:  pass        # For storing data from a LOST_PULSES message.  To be implemented.


        # TODO: Implement these methods!  Do something useful with these messages.
        # At minimum, publish them to subscribers via the publisher interface.
        # Then, various other database & visualization modules can listen for these
        # messages and do whatever they want with them.

    def _handle_DAC_LEVELS(this, msgWords):  #   e.g., DAC_LEVELS,-0.200,-2.500,-0.299,-0.447,-0.669,-1.000

            # Calculate & verify number of arguments provided.

        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 6:
            logger.error(("ShowerDetectorHost._handle_DAC_LEVELS(): " +
                          "I expected the DAC_LEVELS message to have 6 " +
                          "arguments, but it had %d.  Ignoring message...")
                         % nArgs)

        daclevs_rec = this._DAC_LEVELS_Record()
            # Create new empty DAC_LEVELS record object.

        daclevs_rec.level1 = msgWords[1]    # Voltage level of 1st threshold DAC.
        daclevs_rec.level2 = msgWords[2]    # Voltage level of 2nd threshold DAC.
        daclevs_rec.level3 = msgWords[3]    # Voltage level of 3rd threshold DAC.
        daclevs_rec.level4 = msgWords[4]    # Voltage level of 4th threshold DAC.
        daclevs_rec.level5 = msgWords[5]    # Voltage level of 5th threshold DAC.
        daclevs_rec.level6 = msgWords[6]    # Voltage level of 6th threshold DAC.

        logger.normal("Threshold levels are: [%f,%f,%f,%f,%f] (Volts)" %
                      (float(daclevs_rec.level1),
                       float(daclevs_rec.level3),   # skip DAC#2 'cuz it broke
                       float(daclevs_rec.level4),
                       float(daclevs_rec.level5),
                       float(daclevs_rec.level6)
                       ))

        this.daclevs_inbox.contents = daclevs_rec   # Remember this record.

        this.publisher.publish(publisher.Issue('DAC_LEVELS', daclevs_rec))
            # Publish the record to any subscribers.

        # TODO: Dispatch data to model sub-objects for the various DACs.
        # Also, DAC levels should be used in pulse-shape reconstruction & in the GUI.
        
    #__/

    
    def _handle_NC_PULSES(this, msgWords):  #   e.g., NC_PULSES,1618,3352941653,3352948689,115,68,203

            # Calculate & verify number of arguments provided.

        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 6:
            logger.error(("ShowerDetectorHost._handle_NS_PULSES(): " +
                          "I expected the NC_PULSES message to have 6 " +
                          "arguments, but it had %d.  Ignoring message...")
                         % nArgs)

        ncpuls_rec = this._NC_PULSES_Record()
            # Create new empty NC_PULSES record object.

        ncpuls_rec.time_ref = this._TimeSync_Ref()      # Create time-reference sub-object of the data record.
        ncpuls_rec.time_ref.sync_num    = msgWords[1]       # Sequence number of last synchronization pulse received.
        ncpuls_rec.time_ref.pll_cyc     = msgWords[2]       # Sequence number of clock cycle for the fast PLL on the FEDM.
        ncpuls_rec.last_pllcyc          = msgWords[3]       # PLL counter value of last pulse skipped.
        ncpuls_rec.chan1_npuls          = msgWords[4]       # Number of non-coincidence pulses skipped from PMT input channel #1.
        ncpuls_rec.chan2_npuls          = msgWords[5]       # Number of non-coincidence pulses skipped from PMT input channel #2.
        ncpuls_rec.chan3_npuls          = msgWords[6]       # Number of non-coincidence pulses skipped from PMT input channel #3.

        this.ncpuls_inbox.contents = ncpuls_rec     # Remember this record.

        this.publisher.publish(publisher.Issue('NC_PULSES', ncpuls_rec))
            # Publish the record to any subscribers.

        # TO DO: Perhaps route the data to model sub-objects for the specific channels.

    #__/

    
    def _handle_FIFO_FULL(this, msgWords):  #   e.g., FIFO_FULL,2392,3407048110,3,1

            # Calculate & verify number of arguments provided.

        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 4:
            logger.error(("ShowerDetectorHost._handle_FIFO_FULL(): " +
                          "I expected the FIFO_FULL message to have 4 " +
                          "arguments, but it had %d.  Ignoring message...")
                         % nArgs)

            # Parse out the individual arguments into named fields of a data structure.

        fifull_rec = this._FIFO_FULL_Record()

        fifull_rec.time_ref = this._TimeSync_Ref()      # Create time-reference sub-object of the data record.
        fifull_rec.time_ref.sync_num    = msgWords[1]       # Sequence number of last synchronization pulse received.
        fifull_rec.time_ref.pll_cyc     = msgWords[2]       # Sequence number of clock cycle for the fast PLL on the FEDM.
        fifull_rec.chan_id              = msgWords[3]       # Channel # (1-3) of the channel that generated this event.
        fifull_rec.n_events             = msgWords[4]       # The number of distinct FIFO_FULL events on this channel that occurred since the last report.

        this.fifull_inbox.contents = fifull_rec     # Remember this record.

        this.publisher.publish(publisher.Issue('FIFO_FULL', fifull_rec))
            # Distribute the record to subscribers.

        # TO DO: Perhaps route the data to model sub-objects for the specific channels.

    #__/

        # NOTE: In the following method, we assume that the list of level-crossing times
        # is passed as a single string.  The caller must ensure this as a special case
        # (splitting on "," isn't sufficient).
    
    def _handle_CON_PULSE(this, msgWords):  #   e.g., CON_PULSE,3186,3462552667,3,1,3462608072,2,(0,(2,2),5)

            # Calculate & verify number of arguments provided.

        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 7:
            logger.error(("ShowerDetectorHost._handle_CON_PULSE(): " +
                          "I expected the CON_PULSE message to have 7 " +
                          "arguments, but it had %d.  Ignoring message...")
                         % nArgs)

        conpuls_rec = this._CON_PULSE_Record()

            # Parse out the individual arguments into named fields of a data structure.

        conpuls_rec.time_ref = this._TimeSync_Ref()      # Create time-reference sub-object of the data record.
        conpuls_rec.time_ref.sync_num    = msgWords[1]       # Sequence number of last synchronization pulse received.
        conpuls_rec.time_ref.pll_cyc     = msgWords[2]       # Sequence number of clock cycle for the fast PLL on the FEDM.
        conpuls_rec.chan_id              = msgWords[3]       # Channel # (1-3) of the channel this pulse was received on.
        conpuls_rec.pulse_num            = msgWords[4]       # Sequence number of candidate coincidence pulses sent for this channel.
        conpuls_rec.start_pllcyc         = msgWords[5]       # PLL cycle # for 1st leading edge in this pulse.
        conpuls_rec.deltas_list          = msgWords[6]       # Nested parenthesized list of PLL cycle-count deltas, e.g., "(0,(2,2),5)".

        this.conpuls_inbox.contents = conpuls_rec   # Remember this record.

        this.publisher.publish(publisher.Issue('CON_PULSE', conpuls_rec))

        # TO DO: Perhaps route the data to model sub-objects for the specific channels.

    #__/

    
    def _handle_LOST_PULSES(this, msgWords):    #   e.g., LOST_PULSES,2,1

            # Calculate & verify number of arguments provided.

        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 2:
            logger.error(("ShowerDetectorHost._handle_LOST_PULSES(): " +
                          "I expected the LOST_PULSE message to have 2 " +
                          "arguments, but it had %d.  Ignoring message...")
                         % nArgs)

        lostpuls_rec = this._LOST_PULSES_Record()
        
            # Parse out the individual arguments into named fields of a data structure.

        lostpuls_rec.chan_id    = msgWords[1]   # Channel # (1-3) of the channel whose software pulse buffer overflowed.
        lostpuls_rec.n_lost     = msgWords[2]   # Number of pulses on this channel that had to be discarded since the last report.

        this.lostpuls_inbox.contents = lostpuls_rec     # Remember this record.

        this.publisher.publish(publisher.Issue('LOST_PULSES', lostpuls_rec))

        # TO DO: Perhaps route the data to model sub-objects for the specific channels.
        
    #__/


        # Override parent class's definition of this method to add some specific
        # message types that this subclass knows how to handle.

    def _handleHostMsg(this, msgWords):

        logger.debug("ShowerDetectorHost._handleHostMsg(): Handling host message [%s]..." % str(msgWords))

        msgType = msgWords[0]

            # Look for ShowerDetectorHost (FEDM) specific messages
            # and dispatch them to the appropriate handler methods.

        if      msgType == 'DAC_LEVELS':            # Reports current voltage-level settings of the on-board threshold D2A converters.
                                                    # Currently, these are negative decimal numbers (with 3 digits after the decimal 
            this._handle_DAC_LEVELS(msgWords)       # point) representing the DAC output voltage in volts relative to a +2.5V reference.
            
        elif    msgType == 'NC_PULSES':             # Reports number of non-coincidence pulses skipped on each input channel.
                                                    # (These are pulses that are not within the coincidence time-window of any
            this._handle_NC_PULSES(msgWords)        # pulses arriving on any of the other channels.)
            
        elif    msgType == 'FIFO_FULL':             # Reports that some pulses may be lost due to a full hardware FIFO on a channel.
                                                    # This may happen if an intense burst of many pulses arrives on that channel,
            this._handle_FIFO_FULL(msgWords)        # and pulses arrive more quickly than the ISR can drain the queue.
            
        elif    msgType == 'CON_PULSE':             # Reports detailed timestamp & pulse-shape data for a co-incident pulse.
                                                    # (That is, a pulse arriving within a certain time window of other pulses.)
            this._handle_CON_PULSE(msgWords)        # NOTE: We need to do something special here to process the last argument...
            
        elif    msgType == 'LOST_PULSES':           # Reports that pulses from a channel were discarded due to a full software buffer.
                                                    # (This usually happens because one of the other input channels is disconnected;
            this._handle_LOST_PULSES(msgWords)      # with no pulses on that channel, we can't categorize pulses on other channels.)
            
        else:   # Dispatch to parent class.
            model.SensorHost._handleHostMsg(this, msgWords)

    #__/ End def ShowerDetectorHost._handleHostMsg().

# *** TODO: Still need to implement all the other classes of the new
#       object model!  Including all the below classes...  ***

class DetectorNode(model.SensorNode):       pass        # Not yet implemented
class ShowerDetectorNode(DetectorNode):     pass        # Not yet implemented

class Threshold_DAC:                        pass        # Not yet implemented
