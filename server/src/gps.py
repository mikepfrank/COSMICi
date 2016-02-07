#|*****************************************************************************|
#|                              START OF FILE                                  |
#|*****************************************************************************|
#|                                                                             |
#|      FILE NAME:  gps.py                      [python module source file]    |
#|                                                                             |
#|      DESCRIPTION:                                                           |
#|                                                                             |
#|          This file defines classes associated with GPS capabilities.
#|
#|          In particular, it defines a class GPS_Module that comprises
#|          an object model of the DeLorme GPS2058 Module Evaluation Kit.
#|
#|          It also implements a worker thread (defined by the GPS_Manager
#|          class) that remotely manages the state of the GPS module in a
#|          semi-intelligent way.  This includes initializing the module,
#|          getting it into a state where is acquiring a time fix, and
#|          doing ongoing monitoring of its state and (hopefully) maintain-
#|          ing the module in a "good" state, insofar as is possible.
#|
#|          One really intelligent thing to do might be to automatically
#|          invoke a hot, warm, or cold reboot depending on how much real
#|          time has passed since the module was last turned on &
#|          acquiring satellite data - this might help to prevent situa-
#|          tions where the module starts up with an incorrect date and
#|          fails to acquire satellites for a long time.  This is not yet
#|          implemented, however - first we're waiting to see if it's
#|          really necessary.
#|
#|          In the meantime, the current method is to try the different
#|          kinds of resets in order of increasing aggressiveness as
#|          necessary until we start acquiring satellites.  Theoretically,
#|          after a warm start, we should acquire a fix within 34 seconds
#|          if satellites are in view and the almanac is not more than about
#|          6 months old.  Even after a cold start, it shouldn't take more
#|          than 39 seconds ideally, but in practice it seems to sometimes
#|          take more like 10 or 20 minutes, perhaps due to the limited view
#|          out our window.  I'm not yet sure whether we also have to
#|          initialize the module with accurate initial time/location data
#|          provided by the server, but currently we try this initially and
#|          again after each reset if the time value is a more than about a
#|          minute off, since the docs say that setting the time after reset
#|          can decrease the TTFF (time to first fix).
#|
#|          With regards to monitoring/maintenance activities, currently we
#|          just display various status messages and warnings about the state
#|          of the module on the console.  In the future, it might be good to
#|          add a graphical display illustrating the GPS state.  E.g., a row
#|          of satellite icons with ones eliminated from the timing solution
#|          shown in yellow, and others in green.  There could be a running
#|          graph of the self-reported timing uncertainty figure.
#|
#|      REVISION HISTORY:
#|          v0.0, 2/22/12 (MPF) - Wrote initial version; still incomplete.
#|          v0.1, 2/23/12 (MPF) - Replaced private nested _GPS_Inbox class
#|              with a general-purpose class, utils.WatchBox.
#|          v0.2, 3/3/12 (MPF) - Much more sophisticated initialization.
#|              This version still needs to be tested.
#|          v0.3, 3/4/12 (MPF) - Partially exercised new code, fixed some
#|              compilation & runtime errors.  New initialization process
#|              still needs to be tested w. real GPS module.
#|          v0.4, 3/6/12 (MPF) - Some new code was tested and validated
#|              yesterday and remote monitoring messages were developed.
#|              Initialization code still needs to be exercised.  Currently
#|              updating comments.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    #|===================================================================
    #|  Module imports.                                 [code section]
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        # Imports of Python standard library modules.

import  threading                   # RLock
import  datetime                    # datetime class

        # Imports of custom user modules.

import  logmaster                   # getLogger(), etc.
import  flag                        # Flag class.
import  worklist                    # Worker class.
import  model                       # SensorNode class.
import  utils                       # unsplit(), WatchBox class.
import  nmea                        # makeNMEA(), etc.
import  publisher                   # Publisher, Issue classes.
import  sitedefs                    # GPS_ANT_LOC - GPS antenna location, for initialization.
import  earth_coords                # EarthCoords class.

    #|==============================================================================
    #|
    #|      Exported names.                                         [code section]
    #|
    #|          List of names publicly exported from the current module.      
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

__all__ = ['GPS_Manager',   # A worker thread to initialize/maintain state of GPS module.
           'GPS_Module'     # A object model/proxy for a certain component of a CTU_Node -
           ]                #   Namely, the DeLorme GPS module (evaluation kit)

    #|==============================================================================
    #|
    #|      Module globals.                                         [code section]
    #|
    #|          Initialize global variables and constants defined in &
    #|          used by this module.
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        # Create this module's logging channel.  Logically, we're a part of the
        # CTU module, which is itself part of the overall object model of the 
        # sensor network.

logger = logmaster.getLogger(logmaster.sysName + '.mdl.ctu.gps')


    #|================================================================================================
    #|
    #|      CLASS:  gps.GPS_Manager                         [module public class]
    #|
    #|      DESCRIPTION:
    #|
    #|          A GPS_Manager is a worker thread whose primary area of
    #|          responsibility is making sure that the GPS module gets
    #|          into a "good" state (where it is tracking satellites
    #|          and has an accurate time lock), and keeping it there.
    #|
    #|      Class variables:
    #|
    #|          .defaultRole (string) - Default role of this ThreadActor, for logs.
    #|
    #|      Public instance data members:
    #|
    #|          .node (model.SensorNode) - The node in the sensor network whose GPS
    #|                                      module we are supposed to be managing.
    #|
    #|      Special instance methods:
    #|
    #|          .__init__(node) - Initialize a GPS_Manager for a given node.
    #|                              Starts the new worker thread running.
    #|
    #|      Private instance methods:
    #|
    #|          The following methods are designed to be tasks (work items)
    #|          to be executed by the GPS_Manager worker thread.  (However, they
    #|          can also be directly called just like any normal method.)
    #|
    #|              ._queueStartupSequence() - This is the initial task.  It simply
    #|                      queues up a predetermined sequence of other tasks to carry
    #|                      out the overall startup sequence for the GPS manager.
    #|
    #|              ._waitHostReady() - Wait for the node's main host to be ready
    #|                                      to pass through commands to the GPS.
    #|
    #|              ._initializeGPS() - Schedule the sequence of tasks that need
    #|                                      to be performed in order to initialize
    #|                                      the GPS module properly.
    #|
    #|              ._monitorGPS() - Indefinitely, continue monitoring the status of
    #|                                  the GPS module, and possibly attempt repairs
    #|                                  if its state gets messed up somehow.
    #|
    #|          "Fanboy" methods; these are callbacks to handle delivery of
    #|          "magazine issues" (really, publications of messages from the GPS).
    #|          Note that these methods all run in the message-receiving thread, not
    #|          in the GPS Manager thread (unlike most other methods in this class):
    #|
    #|              ._checkTime() - This fanboy reads every issue of the GPRMC magazine
    #|                                  to make sure that the published date/time in it
    #|                                  is valid.  If it isn't, he complains loudly.
    #|
    #|              ._check_nSats() - This fanboy reads every issue of "GPGGA" magazine
    #|                                  to make sure it's still reporting more than 0
    #|                                  satellites are currently acquired.  If not, he
    #|                                  complains loudly.
    #|
    #|              ._checkTRAIM() - This fanboy reads every issue of the "PDMETRAIM" rag
    #|                                  to make sure it's reporting that we have a
    #|                                  reasonably accurate time lock.  If not, he gripes.
    #|
    #|          Other private instance methods:
    #|
    #|              ._setupTimeMonitoring()     - Configure ourselves to continuously monitor the GPS's clock.
    #|              ._initTimeIfNeeded()        - Initialize the GPS module's idea of the real time, if incorrect.
    #|              ._ensureSats()              - Ensure that some satellites have been acquired.
    #|              ._turnOnPOSHOLD()           - Turn on position-hold mode with given coordinates.
    #|              ._turnOnTRAIM()             - Turn on the module's timing-integrity monitoring algorithm.
    #|
    #|              ._hotRestartGPS()           - Force the GPS module to reset itself, with varying degrees of severity;
    #|              ._warmRestartGPS()          -   warm start forcibly invalidates the ephemeris data; 
    #|              ._coldRestartGPS()          -   cold start also invalidates the almanac, and the coordinate memory.
    #|
    #|          (The following ones still need to be implemented:)
    #|
    #|              ._initCoords()      - Initialize GPS module with correct time/position coordinates.
    #|              ._waitForSats()     - Wait for one or more satellites to be seen in GPGGA messages.
    #|              ._monitorGPS()      - Monitor the GPS data stream for problems; report and/or repair.
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class GPS_Manager(worklist.Worker):

        #|-------------------------------
        #|  Initialize class variables.
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    defaultRole = 'GPSmgr'  # Default role of this ThreadActor.  For logging purposes.

        #|------------------------
        #|  Method definitions.
        #|vvvvvvvvvvvvvvvvvvvvvvvv

            #|-----------------------------------------------------------------------------
            #|
            #|      GPS_Manager.__init__()                  [special instance method]
            #|
            #|          Creates and starts the GPS Manager worker thread.
            #|          The <node> argument is the node whose GPS module
            #|          we are supposed to manage.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def __init__(inst, node:model.SensorNode, *args, **kargs):
    #  \
    #   |
        inst._lock = threading.RLock()  # Reentrant mutex lock
            # For access to object structure.
        
        inst.node = node    # Remember which node's GPS we are managing.

    #   |   Set the defaultComponent attribute which determines the component
    #   |   field of this thread's log entries.  This records that our actions
    #   |   are associated with the node's GPS module component.

        inst.defaultComponent = 'node%d.gps' % node.nodenum

    #   |   Create the ".badTime" flag, which lets us track whether the GPS
    #   |   date/time (as reported in the GPRMC message) is "reasonably close"
    #   |   to the PC's system date/time.  Currently, "reasonably close" is
    #   |   considered to mean "within 10 seconds," to account for a possible
    #   |   delay of a few seconds for the GPS data to be relayed to the server.

        inst.badTime = flag.Flag(lock = inst._lock, initiallyUp = False)   # Don't assume it's bad.
    #   |   We don't assume the GPS time is bad until we actually see a bad
    #   |   time from it.

    #   |   Initialize some instance variables associated with TRAIM (timing
    #   |   integrity self-monitoring by the module.

        inst.TRAIM_threshold = 62e-9    # Accuracy threshold in seconds
        inst.turningOnTRAIM = flag.Flag(lock = inst._lock, initiallyUp = False)

    #   |   Initialize some instance variables associated with POSHOLD
    #   |   (position-hold mode) reporting.

        inst.turningOnPOSHOLD = flag.Flag(lock = inst._lock, initiallyUp = False)
        
    #   |   Set our initial task to be the _startupSequence() method, which 
    #   |   in turn queues up the main sequence of subtasks that we always
    #   |   execute on startup.

        inst.initialTask = worklist.WorkItem(inst._queueStartupSequence)

    #   |   Hand off control to the initializer for our parent class, Worker.

        worklist.Worker.__init__(inst, *args, **kargs)  # Starts Worker running.
    #  /
    #_/ End def GPS_Manager.__init__().


# These are not yet used.  We should perhaps remove them as soon as we're sure that we
# will not be using any of them.
#
##        # We will subscribe to GPRMC messages so that if the date/time goes way out of sync,
##        # we will notice and can reinitialize the GPS's date/time.
##
##    def _handleGPRMC(inst, issue):
##        pass
##
##        # We will subscribe to GPGGA messages so that we can monitor the number of satellites
##        # that are being acquired, so we can react appropriately if we stop acquiring them.
##
##    def _handleGPGGA(inst, issue):
##        pass
##
##        # We will subscribe to PDMETRAIM messages so that we can monitor the valid bit and
##        # the accuracy value, so we can react appropriately if they go bad.
##
##    def _handleTRAIM(inst, issue):
##        pass
##
##        # We will subscribe to PDMEPOSHOLD messages so that if poshold mode goes away
##        # somehow, we will be aware of it and can react appropriately.
##
##    def _handlePOSHOLD(inst, issue):
##        pass


            #|-----------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._queueStartupSequence()             [private instance method]
            #|
            #|          This is the preprogrammed initial task that the GPS Manager
            #|          worker thread will be get first on its worklist of tasks to
            #|          execute.  It simply queues up the three main tasks for
            #|          ourselves which comprise our (hard-coded) startup sequence.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _queueStartupSequence(self):
    #  \    
        self(self._waitHostReady)   # Wait for the embedded host to be ready to relay commands.
        self(self._initializeGPS)   # Massage the GPS module into the desired state.
        self(self._monitorGPS)      # Start the background monitoring task - this should run forever.
    #  /
    #_/ End def GPS_Manager._queueStartupSequence().


            #|------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._waitHostReady()            [private instance method]
            #|
            #|          This method simply waits for the node's host to enter
            #|          the "ready" state (in which it is ready to begin
            #|          receiving and processing commands from us).
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _waitHostReady(self):
    #  \
        logger.info("GPS_Manager._waitHostReady():  Waiting for host to be in the READY state.")
        self.node.sensor_host.ready.waitUp()    # Wait indefinitely for host's ready flag to be in the "up" state.
        logger.info("GPS_Manager._waitHostReady():  OK, host is in the READY state.")
    #  /
    #_/ End def GPS_Manager._waitHostReady().


            #|-----------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._initializeGPS()                [private instance method]
            #|
            #|          This worker task is to appropriately initialize the GPS
            #|          module so that it is appropriately collecting accurate
            #|          time data.  Our method for doing this is as follows.
            #|
            #|          Here's the new initialization strategy we're trying now:
            #|
            #|              (1) Subscribe to GPRMC messages, using a callback
            #|                      that alerts us if the time reported by the
            #|                      GPS module somehow gets more than 10 secs.
            #|                      away from our system (NTP-synchronized)
            #|                      time.  This will enable the _monitorGPS()
            #|                      task to respond to this situation.
            #|
            #|              (2) Go ahead and initialize the time now, if needed.
            #|
            #|              (3) Ensure that satellite signals are being acquired.
            #|                      If none are acquired within a few seconds,
            #|                      we try increasing levels of resets (hot, warm,
            #|                      cold) with appropriate delays between attempts.
            #|                      If a reset throws the unit's time clock off,
            #|                      we initialize it shortly afterwards.
            #|
            #|              (4) Turn on POSHOLD mode, with appropriate position.
            #|                      Wait for confirmation; make sure the given
            #|                      coordinates start appearing in PDMEPOSHOLD
            #|                      messages.
            #|
            #|              (5) Turn on TRAIM mode, with appropriate accuracy
            #|                      threshold.  Wait for confirmation.
            #|
            #|              (6) Wait for PDMETRAIM message to report a valid
            #|                      time value with a meaningful accuracy.  At
            #|                      this point we can start using the GPS time
            #|                      values.
            #|
            #|          Our previous strategy was:  To initialize the GPS
            #|          module, we assign ourselves (the GPS Manager worker
            #|          thread) to do the following sequence of steps:
            #|
            #|              (1) Warm-restart the GPS.  Wait briefly (for a
            #|                      confirmation or for a fixed delay).
            #|
            #|              (2) Tell the GPS what time it is, based on the
            #|                      server time.  Also give it our location.
            #|
            #|              (3) Keep watching the number of satellites from
            #|                      $GPGGA message.  Wait for it to start
            #|                      showing some satellites.
            #|
            #|              (4) Turn POSHOLD and TRAIM modes on.
            #|
            #|          A more intelligent future version of this module might do
            #|          the following more elaborate initialization sequence, instead:
            #|
            #|              (1) Wait for the first GPRMC message, which tells us what time
            #|                      and date the GPS module thinks it is.
            #|
            #|              (2) Compare this with the current system time & date.  If more
            #|                      than 6 months has passed, then the almanac data in the
            #|                      module are invalid, and a cold boot is necessary.  Else,
            #|                      if more than, say, 3 hours has passed, we assume that
            #|                      the ephemeris data is invalid, and do a warm restart.
            #|                      Otherwise, do a hot restart.
            #|
            #|              (3) Tell the GPS our actual position & the current time (what
            #|                      the server thinks it is, based on site definition and
            #|                      the current system clock, which should be slaved to a
            #|                      NIST NTP server to within +/- 10 ms).
            #|
            #|              (4) Watch the GPGGA messages and wait for satellites to be
            #|                      acquired.  According to the datasheet, this should
            #|                      take the following time, depending on whether a hot,
            #|                      warm, or cold restart was selected:
            #|
            #|                          Hot:    2.5 secs. (or less)
            #|                          Warm:   34 secs. (or less)
            #|                          Cold:   39 secs. (or less)
            #|
            #|                      If no satellites are acquired after a reasonable wait,
            #|                      complain in an error message and try re-initializing
            #|                      at a more aggressive level (hot -> warm -> cold).
            #|
            #|              (5) Turn on POSHOLD mode, with appropriate position info.
            #|
            #|              (6) Turn on TRAIM mode, with appropriate accuracy threshold.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _initializeGPS(self):
    #  \    
    #   |
    #   |   Set up time monitoring.  This subscribes to GPRMC messages, and on each one,
    #   |   we check the time/date against the system time/date; if it is way off, we raise
    #   |   a flag that triggers us to go into a mode where after resets we tell the GPS
    #   |   the correct current time, in the hope that this will help speed up acquisition.
    #   |
        self._setupTimeMonitoring()
    #   |
    #   |   Go ahead and initialize the unit's time now, if needed (generally, if it's
    #   |   more than a minute off).
    #   |
        self._initTimeIfNeeded()
    #   |
    #   |   Check to see if GPS is already receiving satellites; if not, try some resets & stuff.
    #   |
        self._ensureSats()
    #   |
    #   |   Turn on POSHOLD mode, using appropriate position info.
    #   |
        self._turnOnPOSHOLD()
    #   |
    #   |   Turn on TRAIM mode, using appropriate accuracy settings.
    #   |
        self._turnOnTRAIM()
    #  /
    #_/ End def GPS_Manager._initializeGPS().


            #|-------------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._setupTimeMonitoring()              [private instance method]
            #|
            #|          Arranges for the time reported by every single GPRMC message
            #|          to be monitored by us, to make sure it doesn't somehow drift
            #|          way far away from our system time (which is slaved to a NIST
            #|          atomic clock through an NTP server in Georgia, normally to
            #|          within +/- 10 milliseconds).  Generally we won't be complaining
            #|          though unless the discrepancy is more than 10 seconds at least,
            #|          to allow for up to several seconds of communication delay thru
            #|          the communication network (and in case the server's slow).
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
    def _setupTimeMonitoring(self):
        self.node.gps_module.publisher.subscribe(self._checkTime, 'GPRMC')
    #__/ End def GPS_Manager._setupTimeMonitoring()


            #|----------------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._initTimeIfNeeded()                     [private instance method]
            #|
            #|          Checks to see how far the current time/date reported by the GPS is
            #|          from the current system date & time according to the PC's own clock.
            #|          If it's more than 1 minute off (in either direction), we assume this
            #|          is a serious error that needs to be corrected, and we do so.  (Really,
            #|          though, I think it would probably have to be off by more like 20-40
            #|          minutes in order to really affect things like the list of satellites
            #|          that are expected to be in view.)
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _initTimeIfNeeded(self):    # Initialize the GPS's time with the system time, if it's way off.
    #  \
        td = self._get_GPS_timedelta()      # Get time delta between GPS and system clock.
    #   |
    #   |   Is GPS more than a minute off (in either direction)?  If so, then let's set it.
    #   |
        if td < datetime.timedelta(minutes = -1) or td > datetime.timedelta(minutes = +1):
    #   |  \
            self._init_GPS_time()   # Initialize the GPS module's time value.
    #   |  /
    #   |_/ End if (time is more than a minute off).
    #  /
    #_/ End def GPS_Manager._initTimeIfNeeded().
        

            #|------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._ensureSats()                   [private instance method]
            #|
            #|          This worker task tries to ensure that a non-zero number
            #|          of satellites gets acquired during GPS initialization.
            #|          Presently, it does not return until this is the case.
            #|          (However, nothing guarantees that the satellites won't
            #|          later be lost again.)
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _ensureSats(self):
    #  \
    #   |   This big nested IF checks whether we're acquiring satellites,
    #   |   and if not, attempts to acquire them using increasingly
    #   |   aggressive methods as necessary.
    #   |       NOTE: We should probably have structured this differently,
    #   |   using early returns or something, to avoid the excessive indents.
    #   |
        if self.node.gps_module.nSats == None or not self.node.gps_module.gotSats:     
    #   |  \    -No GPGGA messages received yet, or most recent one showed 00 satellites.
    #   |   |
            logger.info("GPS_Manager._ensureSats():  No satellites yet; waiting 5 secs...")
    #   |   |
    #   |   |   Give it 5 more seconds to see if the number of satellites increases to >= 1.
            gotem = self.node.gps_module.gotSats.waitUp(5)
    #   |   |
            if not gotem:       # Still no satellites.  Order a hot-restart & give it another 5 secs.
    #   |   |  \
                logger.warn("GPS_Manager._ensureSats():  Still no satellites after 5 secs; requesting a hot restart...")
    #   |   |   |
                self._hotRestartGPS()       # Tell the GPS to do a hot-restart.
    #   |   |   |   - This also initializes position/time again if the time is off.
    #   |   |   |
                logger.info("GPS_Manager._ensureSats():  Waiting another 5 seconds to receive satellites...")
    #   |   |   |
                gotem = self.node.gps_module.gotSats.waitUp(5)
    #   |   |   |
                if not gotem:   # Still no satellites!  Order a warm-restart and give it 40 seconds.
    #   |   |   |  \
                    logger.warn("GPS_Manager._ensureSats():  Still no satellites after hot-start + 5 secs.; requesting a warm-start...")
    #   |   |   |   |
                    self._warmRestartGPS()  # Tell GPS to do a warm-restart.
    #   |   |   |   |   - This also initializes position/time again if the time is off.
    #   |   |   |   |
                    logger.info("GPS_Manager._ensureSats():  Waiting 40 seconds for acquisition after warm-start...")
    #   |   |   |   |
                    gotem = self.node.gps_module.gotSats.waitUp(40)
    #   |   |   |   |
                    if not gotem:  # Still no satellites!  Order a cold-restart and give it 5 minutes.
    #   |   |   |   |  \
                        logger.error("GPS_Manager._ensureSats():  Still no satellites after warm-start + 40 secs.; requesting a cold-start...")
    #   |   |   |   |   |
                        self._coldRestartGPS()  # Tell GPS to do a cold-restart.
    #   |   |   |   |   |   - This also initializes position/time again if the time is off (it will be since cold start resets it).
    #   |   |   |   |   |
                        logger.info("GPS_Manager._ensureSats():  Waiting 5 minutes for acquisition after cold-start...")
    #   |   |   |   |   |
                        gotem = self.node.gps_module.gotSats.waitUp(5*60)   # 5*60 secs = 5 minutes
    #   |   |   |   |   |
                        if not gotem:  # Still no satellites!  Keep waiting forever...
    #   |   |   |   |   |  \
                            logger.error("GPS_Manager._ensureSats():  Still no satellites after cold-start + 5 minutes.; waiting indefinitely...")
    #   |   |   |   |   |   |
                            self.node.gps_module.gotSats.waitUp()
    #   |   |   |   |   |  /
    #   |   |   |   |   |_/ End if still got no sats after 5 min.
    #   |   |   |   |__/ End if still got no sats after 40 secs.
    #   |   |   |__/ End if still got no sats 5 secs. after hot-start.
    #   |   |__/ End if still got no sats 5 secs. after start of _ensureSats().
    #   |__/ End if got no sats initially.
    #   |
    #   |   If we get here, then the "gotSats" flag finally went up at some
    #   |   point; thus nSats should be >=1 by now.
        logger.normal("The GPS module is receiving signals from %d satellites." % self.node.gps_module.nSats)
    #  /
    #_/ End def GPS_Module.ensureSats().


            #|---------------------------------------------------------------------------------------
            #|
            #|      GPS_Module._checkTime()                             [private instance method]
            #|
            #|          Fanboy method to read "issues" of the GPRMC "magazine" and check 
            #|          their date/time to make sure it's valid.
            #|              NOTE: This method runs within the caller's thread (the one
            #|          that is invoking the publisher to distribute the issue), not in 
            #|          the GPS_Manager thread itself.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _checkTime(inst, issue):        # fanboy method
        
            #   Make sure this is really an issue of 'GPRMC' magazine and not some other title.
           
        if issue.title != 'GPRMC':
            logger.error(("GPS_Manager._checkTime(): Hey, I want to read GPRMC "+
                          "messages but someone gave me a [%s] message.  Ignoring.\n")
                         % issue.title)
            return
        #__/ End if title is GPRMC.
        
            #   This is an issue of 'GPRMC' magazine, so its content comprises a GPRMC data record.
        
        gprmc_rec = issue.content
       
            #   Compute the time delta between the GPS's idea of the time and the system's
            #   (i.e., server host's) idea of the time.  Due to various transmission delays,
            #   the GPS time might reasonably appear to be a few seconds behind the current
            #   system time even if it is actually correct.  (And it could conceivably also
            #   be a little bit ahead in some cases, say if the NTP connection to the NIST
            #   time server goes down temporarily and the system clock drifts out of sync
            #   with real time by a bit.)
    
        gpsDelta = inst._calc_GPS_timedelta(gprmc_rec)

            #   If the GPS time is more than 10 seconds ahead or behind the current system
            #   date/time, then display a warning, and set the badTime flag.

        if gpsDelta < datetime.timedelta(seconds = -10):
            logger.warn("GPS_Manager._checkTime(): GPS time is more than 10 seconds behind system time.")
            inst.badTime.rise()     # Raise the "bad time" flag.

        elif gpsDelta > datetime.timedelta(seconds = +10):
            logger.warn("GPS_Manager._checkTime(): GPS time is more than 10 seconds ahead of system time.")
            inst.badTime.rise()     # Raise the "bad time" flag.
                                            
        else:
            logger.debug("GPS_Manager._checkTime(): GPS time is within 10 seconds of system time.")
            inst.badTime.fall()     # Lower the "bad time" flag.

    #__/ End def GPS_Manager._checkTime().


    def _check_nSats(inst, issue):      # fanboy method

            # Make sure the mailman delivered the right magazine.
        
        if issue.title != 'GPGGA':
            logger.error(("GPS_Manager._check_nSats(): Hey, I want to read GPGGA "+
                          "messages but someone gave me a [%s] message.  Ignoring.\n")
                         % issue.title)
            return
        #__/ End if wrong magazine was delivered.

            # No need to retrieve issue content because GPS_Module._handleGPGGA()
            # will have already parsed out what we need.

        if inst.node.gps_module.gotSats():
            logger.normal("GPS Manager says:  The GPS module is receiving data from %d satellites."
                          % inst.node.gps_module.nSats)
        else:
            logger.warn("GPS_Manager._check_nSats():  GPS module is not receiving any satellite signals.")
        #__/ End if ...gotSats().
            
    #__/ End def _check_nSats().


        # Method to read "issues" of the 'PDMETRAIM' "magazine" and check
        # their fields to make sure they look good.  Note: This method runs
        # in the caller's thread, not in the GPS_Manager thread itself.

    def _checkTRAIM(inst, issue):       # fanboy method (calling convention for subscriber callbacks)

            # First, make sure that the courier really delivered us an issue
            # of 'PDMETRAIM' magazine, and not some other title.

        if issue.title != 'PDMETRAIM':
            logger.error(("GPS_Manager._checkTRAIM(): Hey, I want to read PDMETRAIM "+
                          "messages but someone gave me a [%s] message.  Ignoring.\n")
                         % issue.title)
            return

            # Next, initialize a local flag for calculating the overall "good/bad"
            # state of the TRAIM message within the context of this routine.  We'll
            # start out by optimistically assuming that the TRAIM message is good
            # unless/until we identify a specific issue with it.
            
        good_TRAIM = True       # Initialize to True; later code may make it False.

            # This is an issue of 'PDMETRAIM' magazine, so its content comprises
            # a PDMETRAIM data record.  (We assume - might be a good idea to verify
            # the object's class to make sure, but we're not doing that yet.)

        traim_rec = issue.content

            # First examine the value of the <Solution> status value.
            # This tells us the overall status of the self-reported
            # timing error (inaccuracy) computation.  Note that the
            # OVER_ALARM condition does not necessarily imply that the
            # timing solution is bad, since the elimination of "bad"
            # satellites from the solution (ones with inconsistent
            # time values which e.g. may be due to signal reflections)
            # may actually help to improve the real accuracy of the
            # timing solution.

        if traim_rec.solutNum == GPS_Module.TRAIM_SOL_UNDER_ALARM:

            logger.info(("GPS_Manager._checkTRAIM(): Timing error of all satellites " +
                         "vs. timing solution is under %d-ns alarm threshold.")
                        % (inst.TRAIM_threshold*1e9))

        elif traim_rec.solutNum == GPS_Module.TRAIM_SOL_OVER_ALARM:

            logger.warn(("GPS_Manager._checkTRAIM(): Timing error for some satellites " +
                         "vs. timing solution exceeds %d-ns alarm threshold.")
                        % (inst.TRAIM_threshold*1e9))

        elif traim_rec.solutNum == GPS_Module.TRAIM_SOL_UNKNOWN:

            logger.warn("GPS_Manager._checkTRAIM(): Error of satellites " +
                        "vs. timing solution cannot be determined.")

        else:

            logger.error("GPS_Manager._checkTRAIM(): Unrecognized timing solution status code %d." % traim_rec.solutNum)

            # Next, examine the value of the <Valid> status value.
            # This tells us whether the overall TRAIM data record
            # can be considered valid.  I think this just corresponds
            # to whether the PDMETRAIM mode is currently turned on,
            # or not - but I'm not 100% sure about that yet.  Need
            # to do more experiments to see in exactly what cases it
            # is set/unset.

        if traim_rec.validNum == GPS_Module.TRAIM_VALID_NO:

            logger.warn("GPS_Manager._checkTRAIM(): Timing integrity report is marked as invalid.")
            good_TRAIM = False  # Certainly in this case, we can't trust the time values
                # to still be accurate to the sub-100-ns level.

                # Maybe TRAIM mode just got turned off.  Try turning it back on (if not already trying to do that).

            with inst._lock:
                if not inst.turningOnTRAIM():
                    inst.turningOnTRAIM.rise()
                    inst(inst._turnOnTRAIM)     # Ask the actual GPS_Manager thread to try re-enabling TRAIM.
                        # Note this will happen later, in the other thread.

        elif traim_rec.validNum == GPS_Module.TRAIM_VALID_YES:

            logger.info("GPS_Manager._checkTRAIM(): Timing solution can be considered valid.")

        else:

            logger.error("GPS_Manager._checkTRAIM(): Unrecognized TRAIM validity code %d.")

            # Next, examine the number of satellites removed from
            # the timing solution due to accuracy threshold violation.
            # If all of the satellites are removed, this seems like
            # an error of some sort, and we no longer assume that the
            # time values are accurate.

        if traim_rec.nBadSats > 0:
            logger.warn("GPS_Manager._checkTRAIM(): %d out of %d satellites were removed from timing solution."
                        % (traim_rec.nBadSats, inst.node.gps_module.nSats))
            if traim_rec.nBadSats >= inst.node.gps_module.nSats:

                    # Occasionally, I think I've seen more satellites removed from the
                    # timing solution than the last GPRMC message indicated we had.
                    # This is weird; it may just mean that new satellites were acquired
                    # in the time between these messages, but report it specially anyway.
                
                if traim_rec.nBadSats > inst.node.gps_module.nSats:
                    logger.warn("GPS_Manager._checkTRAIM(): WTF? More satellites were removed than we actually have!")
                        # Not sure yet just how serious this problem is.
                else:
                    logger.warn("GPS_Manager._checkTRAIM(): All satellites were removed from timing solution?!?")
                        # This seems like it might be a malfunction - should we reset the module
                        # if this condition persists for a while?
                #__/ End if more than all bad sats removed
                        
                good_TRAIM = False      # This indicates that, with all satellites
                    # removed from timing solution, we can no longer assume that the
                    # actual absolute time error is within +/- 100 ns.
                    
            #__/ End if all sats removed
        #__/ End if there were bad sats
                

            # Give a warning if the self-reported accuracy is exactly 0,
            # since really that means the accuracy cannot be determined and
            # that the actual error is probably larger than desired.

        if traim_rec.timeError == 0:
            logger.warn("GPS_Manager._checkTRAIM(): GPS module is reporting null timing accuracy.")
            good_TRAIM = False      # Certainly a 0 value cannot be accepted as valid!
            
        else:
            logger.info("GPS_Manager._checkTRAIM(): GPS module's self-reported timing uncertainty is %d ns."
                        % ((traim_rec.timeError)*1e9))

            # If the self-reported accuracy is actually reported as being worse than
            # +/- 100 ns, then we won't accept this as a "good" TRAIM report (sufficient
            # to cause the RunManager to start the data-collection run).

        if traim_rec.timeError > 100e-9:
            logger.warn("GPS_Manager._checkTRAIM(): GPS module reports > +/- 100 ns timing uncertainty.")
            good_TRAIM = False

            # Display a "normal" type report of timing uncertainty if we think it's valid.

        if traim_rec.validNum == GPS_Module.TRAIM_VALID_YES and traim_rec.timeError > 0:
            logger.normal(("GPS Manager says:  The GPS module claims its timing solution " +
                           "has ±%d ns uncertainty.")
                          % ((traim_rec.timeError)*1e9))

            # OK, now, finally, if the TRAIM report looks good, and the actual time value
            # is good in the sense of being roughly consistent with the PC's system clock,
            # then we'll assume that everything is hunky-dory (for the moment at least)
            # with regards to the absolute time values we can derive from the GPS, and we
            # inform the top-level server object (CosmicIServer instance) of this fact so
            # that it can take appropriate actions such as informing the RunManager that
            # it's OK to actually commence the data-collection run at this time.  Otherwise,
            # there was something wrong either with the TRAIM message or the time value
            # itself, so make sure the main CosmicIServer object knows that the current
            # GPS time value cannot be assumed to be "good" (in the sense of being correct
            # to within the specified error tolerance of the module).

        if good_TRAIM and not inst.badTime:
            inst.node.net.cis.yo_GPS_time_is_good()
        else:
            inst.node.net.cis.yo_GPS_time_is_nogood()

    #__/ End def GPS_Manager._checkTRAIM().


    def _checkPOSHOLD(inst, issue):

            # First, make sure that the courier really delivered us an issue
            # of 'PDMEPOSHOLD' magazine, and not some other title.

        if issue.title != 'PDMEPOSHOLD':
            logger.error(("GPS_Manager._checkPOSHOLD(): Hey, I want to read PDMEPOSHOLD "+
                          "messages but someone gave me a [%s] message.  Ignoring.\n")
                         % issue.title)
            return
        
            # This is an issue of 'PDMEPOSHOLD' magazine, so its content comprises
            # a PDMEPOSHOLD data record.  (We assume - might be a good idea to verify
            # the object's class to make sure, but we're not doing that yet.)

        poshold_rec = issue.content

            # For now, just check the OnOff field to make sure that POSHOLD mode
            # didn't get turned off somehow (e.g. by a module reset).

        if poshold_rec.onOffNum != 1:
            
            logger.warn("GPS_Manager._checkPOSHOLD(): POSHOLD mode got turned off... Turning it back on.")

            with inst._lock:                       
                if not inst.turningOnPOSHOLD():
                    inst.turningOnPOSHOLD.rise()
                    inst(inst._turnOnPOSHOLD)     # Ask the actual GPS_Manager thread to try re-enabling POSHOLD.
                    # Note this will happen later, in the other thread.
        #__/

        
    #__/ End def GPS_Manager._checkPOSHOLD().
        

        # Calculate, as a datetime.timedelta object, the difference between the UTC date & time
        # from a given gprmc record and the current UTC time as reported by the system.

    def _calc_GPS_timedelta(self, gprmc_rec):

            # Extract the time and date fields that we care about from the gprmc_rec data structure.
        
        gpsDatetime = gprmc_rec.extract_datetime()

            # Get the current UTC date and time from the system.  We expect this to be accurate
            # to within about +/- 10 ms.

        sysDatetime = datetime.datetime.utcnow()

            # Compute the time delta between the GPS's idea of the time and the system's
            # idea of the time.  Due to various transmission delays, the GPS time might
            # be a few seconds behind the current system time.

        gpsDelta = gpsDatetime - sysDatetime

        return gpsDelta

    #<- End def GPS_Manager._calc_GPS_timedelta().

        # Determine and return the time offset of the GPS time relative to the system
        # clock.  Normally this will be within +/- a few seconds of 0 time difference.
        # However, if the GPS module lost its battery backup of its internal clock and
        # hasn't yet acquired satellites, this could be much farther off.

    def _get_GPS_timedelta(self):

            # Get a copy of the next GPRMC record to be received from the module.
        logger.info("GPS_Manager._get_GPS_timedelta():  Waiting for next GPRMC message.")
        gprmc_rec = self.node.gps_module.gprmc_inbox.wait()
        logger.info("GPS_Manager._get_GPS_timedelta():  Got a GPRMC message.")
        
            # Calculate & return its time delta relative to current system time.

        return self._calc_GPS_timedelta(gprmc_rec)
    
    #<- End def GPS_Manager._get_GPS_timedelta().


        # This method takes care of informing the GPS module of what the
        # present time is; this will hopefully help it in acquiring a lock
        # in case it is getting confused because its own idea of the time
        # is way off for some reason.

    def _init_GPS_time(self):

            # Unfortunately, we don't know a way to tell the GPS what time
            # it is without also telling it our location.  We take an assumed
            # location hard-coded in the sitedefs.py file.  (Really it should
            # probably be read from an easily-edited config file.)

        pos = sitedefs.GPS_ANT_LOC      # Hardcoded location of site's GPS antenna.

            # As for the time, we just fetch the current time in UTC from
            # the Python datetime library.  This will be only slightly out-
            # of date by the time the GPS module receives our command.

        time = datetime.datetime.utcnow()

        logger.normal("Initializing GPS module's clock to %s (UTC)." % time)

            # Finally, tell the node's GPS model/proxy to initialize its
            # position and time to these values - it will take care of
            # routing the appropriate command to the physical GPS module.

        self.node.gps_module.initPosTime(pos, time)

    #<- End def GPS_Manager._init_GPS_time().
    

            #|-----------------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._hotRestartGPS()                    [private instance method]
            #|
            #|          This worker task is to hot-restart the GPS module, that is,
            #|          restarting it under the assumption that the stored ephemeris
            #|          and almanac data are still valid.  This is generally a bad
            #|          assumption if the unit has been powered off for more than a
            #|          few hours.  Thus, this function should generally only be used
            #|          if we're pretty sure that the existing ephemeris & almanac
            #|          data are good.  Note that the unit's default power-up behavior
            #|          is to just do a hot start, which might not work if it has been
            #|          turned off for a while.  Thus, an explicit warm or cold restart
            #|          are generally needed instead.  However, this method is provided
            #|          in case we might find it useful later on for some purpose.
            #|
            #|              Nominally, the unit should acquire coordinates within 2.5
            #|          seconds after a hot start.  If this does not work, it could
            #|          either mean that no satellites are visible, or that the ephemeris
            #|          and possibly also the almanac are invalid, so that either a warm
            #|          or a cold start may be required.
            #|
            #|              This task is implemented by just calling the corresponding
            #|          method in our object model/proxy of the node's GPS module, which
            #|          takes care of the real work.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        
    def _hotRestartGPS(self):       # Hot-restart the GPS module of the node whose GPS we're managing.
        
        self.node.gps_module.hotStart()     # Tell model/proxy of GPS to hot-restart the unit.
            # (Sends hot-start command, & waits for confirmation/timeout.)

        self._initTimeIfNeeded()     # If the date/time after reset are way off, initialize them.

    #<- End def GPS_Manager._hotRestartGPS()


            #|-----------------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._warmRestartGPS()                   [private instance method]
            #|
            #|          This worker task is to warm-restart the GPS module, that is,
            #|          restarting it under the assumption that the stored ephemeris
            #|          data is invalid but that the stored almanac is valid.  This
            #|          may be a bad assumption if the unit has been turned off or
            #|          has for some other reason failed to acquire satellites for a
            #|          period of six months or longer.  If the unit fails to acquire
            #|          satellites within a few minutes after a warm restart, then
            #|          this may indicate that a cold restart may be required instead.
            #|
            #|              Nominally, the unit should acquire coordinates within 34
            #|          seconds after a hot start.  If this does not work, it could
            #|          either mean that no satellites are visible, or that the almanac
            #|          is invalid, so that a cold start may be required.  It might also
            #|          help to send the unit accurate time/position coordinates to start
            #|          out from shortly after restarting.
            #|
            #|              This task is implemented by just calling the corresponding
            #|          method in our object model/proxy of the node's GPS module, which
            #|          takes care of the real work.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _warmRestartGPS(self):      # Warm-restart the GPS module.
        
        self.node.gps_module.warmStart()    # Tell the model/proxy to warm-start the real module.

        self._initTimeIfNeeded()     # If the date/time after reset are way off, initialize them.

    #<- End def GPS_Manager._warmRestartGPS()


            #|--------------------------------------------------------------------------------------------
            #|
            #|      GPS_Manager._coldRestartGPS()                   [private instance method]
            #|
            #|          This worker task is to cold-restart the GPS module, that is,
            #|          restarting it under the assumption that neiter the stored
            #|          ephemeris nor almanac data is valid.  After a cold start,
            #|          theoretically the unit should always acquire coordinates
            #|          within about 39 seconds if satellites are in view.  (If not,
            #|          then it might help to send the unit accurate time/position
            #|          coordinates to start out from shortly after restarting.)
            #|
            #|              This task is implemented by just calling the corresponding
            #|          method in our object model/proxy of the node's GPS module, which
            #|          takes care of the real work.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv        

    def _coldRestartGPS(self):      # Cold-restart the GPS module.
        
        self.node.gps_module.coldStart()

        self._initTimeIfNeeded()     # If the date/time after reset are way off, initialize them.

    #<- End def GPS_Manager._coldRestartGPS()
        
# No longer plan to define these - code is structured differently now.        
#    def _initCoords(self):      pass        # Initialize GPS module with time/pos. coords. provided by server.
#    def _waitForSats(self):     pass        # Wait for one or more satellites to be acquired in GPGGA message.


        # Turn on position-hold (pure timing) algorithm.

    def _turnOnPOSHOLD(self):   # like $PDME,21,1,3025.694,N,08417.097,W,0040

        self.turningOnPOSHOLD.rise()    # This helps prevent redundant attempts.

            # Ask the module to hold its position at the (hard-coded)
            # GPS antenna location, and just calculate timing data.
            # NOTE:  Would it make more sense to set the location to
            # a value obtained from an actual GPS 3-D fix, assuming
            # that is available?  Or from the average of position fix
            # readings obtained over an extended period?  Which method
            # will produce more accurate timing results?  Need to think
            # about this issue in more depth sometime.

        self.node.gps_module.holdPos(sitedefs.GPS_ANT_LOC)

            # Subscribe to be notified of every subsequent PDMEPOSHOLD message
            # received from the GPS module, so that we can monitor them and react
            # appropriately to them, for example by turning POSHOLD mode back on
            # if it gets turned off somehow (e.g. because of a GPS module reset).

        if not hasattr(self,'subscribedToPOSHOLD'):        # Avoid redundant subscriptions
            self.node.gps_module.publisher.subscribe(self._checkPOSHOLD, 'PDMEPOSHOLD')
            self.subscribedToPOSHOLD = True

        self.turningOnPOSHOLD.fall()    # Announce we're done with that.

    #__/ End def GPS_Manager._turnOnPOSHOLD().


        # Turn on TRAIM (timing something something integrity monitoring) algorithm.
        
    def _turnOnTRAIM(self):

        self.turningOnTRAIM.rise()   # Raise the flag announcing we are turning on the TRAIM algorithm.

            # Enable the TRAIM algorithm, with an accuracy threshold parameter
            # that is suitable given that the view thru our window seems to
            # always make the module think it's sitting out on the lawn.

        self.node.gps_module.enableTRAIM(self.TRAIM_threshold)    # 62 ns accuracy target
            #                               |
            #  NOTE:  It's unclear what value of this threshold is most suitable.
            #           This value, 62 ns, is the uncertainty of the PPS signal
            #           according to the GPS2058-10 module's datasheet.  Sometimes
            #           we have also used 100 ns, or 50 ns.  25 ns is suggested at
            #           one point in the datasheet.  If the value is too small, it
            #           can result in too many satellites being eliminated from the
            #           solution.  If it is too large, it may fail to eliminate ones
            #           that are inaccurate (possibly due to signal reflections).
        
            # Subscribe to be notified of every subsequent PDMETRAIM message
            # received from the GPS module, so that we can react appropriately,
            # for example by displaying warnings if the status isn't good, and
            # perhaps automatically try turning TRAIM mode back on if it gets
            # turned off somehow.

        if not hasattr(self,'subscribedToTRAIM'):        # Avoid redundant subscriptions
            self.node.gps_module.publisher.subscribe(self._checkTRAIM, 'PDMETRAIM')
            self.subscribedToTRAIM = True

        self.turningOnTRAIM.fall()  # Lower the flag to announce we're done turning on the TRAIM algorithm.
        
    #<- End GPS_Manager._turnOnTRAIM
        
        # All of the the below GPS Manager tasks have not yet been defined.
    
    def _monitorGPS(self):
        # - Keep tabs on GPS status.  Produce alerts if problems arise.
        #   Attempt to repair some types of problems that may arise.

            # Subscribe to GPGGA messages, so that we can keep an eye on the number of satellites.
            # NOTE: Should we do this earlier, like as soon as we start up?  Currently, we don't
            # start doing this until we have finished the initialization sequence...

        self.node.gps_module.publisher.subscribe(self._check_nSats, 'GPGGA')
            # -Note that the fanboy method _check_nSats() will run in the message-receiving thread,
            #   not in this GPS_Manager thread itself.

        # We eventually need to do a lot more meaningful stuff here,
        # but this is as far as we've got for now.

    #<- End def GPS_Module._monitorGPS().

        # The following ones are not yet known to be needed.
    
    def _turnOffNMEA(self):     pass
    def _turnOffPOSHOLD(self):  pass
    def _turnOffTRAIM(self):    pass
    def _turnOnNMEA(self):      pass

#<- End class GPS_Manager.
    

    #|====================================================================================
    #|
    #|      gps.GPS_Module                                      [module public class]
    #|
    #|          An instance of this class is our model/proxy representation of
    #|          a remote GPS module located in a sensor node.  In the present
    #|          prototype system, this is the DeLorme 2058EV GPS development kit
    #|          and it is located only in the Central Timing Unit (CTU) node.
    #|
    #|          When the model is created, we also create a new worker thread
    #|          called GPS_Manager, whose job is to monitor the state of the
    #|          GPS module (as reflected in the present model/proxy) and to
    #|          attempt to get it into a "good" state, namely one in which it
    #|          is acquiring signals from several satellites (or at least one
    #|          in POSHOLD mode) and has a meaningful self-assessed accuracy
    #|          for its reported time values.
    #|
    #|      Private class variables (really constants):
    #|
    #|          PDME command codes:
    #|
    #|              _PDME_COLD_START         Cold-start the GPS module.
    #|              _PDME_WARM_START         Warm-start the GPS module.
    #|              _PDME_HOT_START          Hot-start the GPS module.
    #|              _PDME_GET_VERS_INFO      Get version information.
    #|              _PDME_GET_DIL_PREC       Get Dilution-of-Precision threshold values.
    #|              _PDME_SET_DIL_PREC       Set Dilution-of-Precision threshold values.
    #|              _PDME_GET_MASK_ANG       Get satellite masking angle.
    #|              _PDME_SET_MASK_ANG       Set satellite masking angle.
    #|              _PDME_INIT_POS_TIME      Initialize GPS position and time.
    #|              _PDME_NMEA_PORT_CTRL     NMEA port messaging controls.
    #|              _PDME_NMEA_MSG_CONF      NMEA messaging configuration.
    #|              _PDME_SYS_CTRL_SET_A     System control set A (various functions)
    #|              _PDME_SYS_CTRL_SET_B     System control set B (various functions)
    #|              _PDME_GPIO_READ          GPIO pin read.
    #|              _PDME_GPIO_WRITE         GPIO pin write.
    #|              _PDME_SW_CONF_SET        SW Config - Set a parameter
    #|              _PDME_SW_CONF_GET        SW Config - Get a parameter
    #|              _PDME_SW_CONF_SAVE       SW Config - Save ACTIVE parameter set to BACKUP
    #|              _PDME_SW_CONF_RESET      SW Config - Erase BACKUP config & restart in DEFAULT
    #|              _PDME_SW_CONF_SELECT     SW Config - Select parameter set used on startup
    #|              _PDME_POSHOLD_CTRL       Enable/Disable Position Hold (Timing) Mode
    #|              _PDME_TRAIM_CTRL         Enable/Disable TRAIM algorithm
    #|              _PDME_BINARY_MODE        Switch to binary protocol mode (Dangerous!)
    #|
    #|      Private instance data members:
    #|
    #|          ._lock - Reentrant mutex lock for write access.
    #|
    #|      Public instance data members:
    #|
    #|          .baud_rate (int) - The present serial baud rate at which the GPS
    #|              module is communicating with the sensor host, as an integer
    #|              representing bits per second.    
    #|
    #|          .POSHOLD_on : Flag - Raised if POSHOLD mode is presently turned on.
    #|
    #|          .TRAIM_on : Flag - Raised if TRAIM mode is presently turned on.
    #|
    #|          .NMEA_on : Flag - Raised if periodic NMEA output from the module
    #|              is presently turned on.
    #|
    #|          .pdme_inbox    : utils.WatchBox     - In these watchable boxes we
    #|          .gpgga_inbox   : utils.WatchBox         store the most-recently-
    #|          .gprmc_inbox   : utils.WatchBox         received message of each
    #|          .traim_inbox   : utils.WatchBox         type.  Other threads can
    #|          .poshold_inbox : utils.WatchBox         watch for these to change.
    #|
    #|      Special instance methods:
    #|
    #|          .__init__() - Instance initializer.
    #|
    #|      Public instance methods:
    #|
    #|          .sentMessage() - Inform model GPS that the real GPS sent a certain message.
    #|
    #|          .coldStart() - Cause the GPS to execute a cold-start.
    #|
    #|      Private instance methods:
    #|
    #|          Handler methods for various specific types of messages we expect
    #|          to receive from the GPS module:
    #|          
    #|              ._handleGPGGA()
    #|              ._handleGPRMC()
    #|              ._handlePDME()
    #|              ._handlePDMETRAIM()
    #|              ._handlePDMEPOSHOLD()
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class GPS_Module:

        #|------------------------------------------------------------------------------------
        #|
        #|      Class variable initializers.                   [class definition section]
        #|
        #|          In this section of the class definition, we initialize variable
        #|          (or constant) data members that are associated with the overall
        #|          GPS_Module class, rather than with any specific instance of it.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

            # Public constants for various status codes returned by GPS/PDME messages.

                # Status codes associated with the $PDMETRAIM status message.

                    # Values of the <Solution> parameter of $PDMETRAIM status message.

    TRAIM_SOL_UNDER_ALARM   =   0       # Error of TRAIM solution is under the alarm threshold.
    TRAIM_SOL_OVER_ALARM    =   1       # Error of TRAIM solution is over the alarm threshold.
    TRAIM_SOL_UNKNOWN       =   2       # Error of TRAIM solution cannot be determined.

                    # Values of the <Valid> parameter of $PDMETRAIM status message.

    TRAIM_VALID_NO          =   0       # Timing solution (or just TRAIM message data?) is considered valid.
    TRAIM_VALID_YES         =   1       # Timing solution (or just TRAIM message data?) is not considered valid.

            # Private constants for the various PDME command codes (DeLorme-specific $PDME NMEA messages).

    _PDME_COLD_START     = 0     # Cold-start the GPS module.
    _PDME_WARM_START     = 1     # Warm-start the GPS module.
    _PDME_HOT_START      = 2     # Hot-start the GPS module.
    _PDME_GET_VERS_INFO  = 4     # Get version information.
    _PDME_GET_DIL_PREC   = 5     # Get Dilution-of-Precision threshold values.
    _PDME_SET_DIL_PREC   = 6     # Set Dilution-of-Precision threshold values.
    _PDME_GET_MASK_ANG   = 7     # Get satellite masking angle.
    _PDME_SET_MASK_ANG   = 8     # Set satellite masking angle.
    _PDME_INIT_POS_TIME  = 9     # Initialize GPS position and time.
    _PDME_NMEA_PORT_CTRL = 10    # NMEA port messaging controls.
    _PDME_NMEA_MSG_CONF  = 11    # NMEA messaging configuration.
    _PDME_SYS_CTRL_SET_A = 12    # System control set A (various functions)
    _PDME_SYS_CTRL_SET_B = 13    # System control set B (various functions)
    _PDME_GPIO_READ      = 14    # GPIO pin read.
    _PDME_GPIO_WRITE     = 15    # GPIO pin write.
    _PDME_SW_CONF_SET    = 16    # SW Config - Set a parameter
    _PDME_SW_CONF_GET    = 17    # SW Config - Get a parameter
    _PDME_SW_CONF_SAVE   = 18    # SW Config - Save ACTIVE parameter set to BACKUP
    _PDME_SW_CONF_RESET  = 19    # SW Config - Erase BACKUP config & restart in DEFAULT
    _PDME_SW_CONF_SELECT = 20    # SW Config - Select parameter set used on startup
    _PDME_POSHOLD_CTRL   = 21    # Enable/Disable Position Hold (Timing) Mode
    _PDME_TRAIM_CTRL     = 22    # Enable/Disable TRAIM algorithm
    _PDME_BINARY_MODE    = 23    # Switch to binary protocol mode

        #|---------------------------------------------------------------------------------------
        #|
        #|      Nested class definitions.                       [class definition section]
        #|
        #|          In this section of the class definition, we define various
        #|          nested classes defined within this class's namespace.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

            # GPS record classes.  An instance of one of these classes represents the
            # data contents of an individual PDME, GPGGA, etc. message from a GPS module.
            # Attributes are filled in as appropriate when the incoming message is parsed.

    class   _PDMEHEADER_Record:     pass        # For storing data from a PDMEHEADER1 or PDMEHEADER2 message.

    class   _GPTXT_Record:          pass        # For storing data from a GPTXT message.

    class   _PDME_Record:           pass        # For storing data from a PDME command return message.
    
    class   _GPGGA_Record:          pass        # For storing data from a GPGGA message.
    
    class   _GPRMC_Record:
            # Importantly for our purposes, this record contains complete date & time information.
            # We define here a method to parse it.
        
        def extract_datetime(this):     # Extracts & returns a naive datetime object with integer seconds from GPRMC data.
            
                # Extract the time and date fields that we care about from the gprmc_rec data structure.

            gpsTime = this.PosUTC      # UTC time as a string in HHMMSS.mmm fmt (H=hrs, M=mins, S=secs, m=msecs)
            gpsDate = this.Date        # UTC date as a string in DDMMYY format (D=date, M=month, Y=year)

                # Break time and date into individual components.

            year    = 2000 + int(gpsDate[4:])   # Last 2 digits of year = Digits #4 and up.  Note this has a Y2100 problem unless the GPRMC format is extended.
            month   = int(gpsDate[2:4])         # Month of year, 1-12 = Digits #2-3.
            dayofmo = int(gpsDate[0:2])         # Day of month, 1-31 = Digits #0-1.

            hour24  = int(gpsTime[0:2])         # Hour of day, 0-23 = Digits #0-1.
            minute  = int(gpsTime[2:4])         # Minute of hour, 0-59 = Digits #2-3.
            second  = float(gpsTime[4:])        # Second of minute, 0.000 - 59.999 = Digits #4 and up.

                # Occasionally the second ends in 0.999 (or 0.998, or 0.997) instead of 0.000.
                # Round it to an integer.  NOTE TO SELF: Is this really the right thing to do here?
                # Or is the PPS edge really supposed to be marking an absolute time that may be a
                # few milliseconds before or after the start of the actual second?  I've been
                # assuming the value ought to be rounded, but I could be wrong...  Need to check.

            origsec = second
            second  = round(second)
            if second != origsec:
                diff = origsec - second
                    # The below was originally a warning but I changed it to an info
                    # since it happens all the time and the constant warnings are
                    # overkill/annoying.
                logger.info(("GPS_Module._GPRMC_Record.extract_datetime(): " +
                             "Reported time %d:%02d:%06.3f was offset %.03f " +
                             "from the exact start of a second.  Rounding off " +
                             "and ignoring discrepancy...")
                            % (hour24, minute, origsec, diff))
            #<- End if second != origsec.

                # If the second rolled over, roll up minutes.

            if second == 60:
                second = 0
                minute = minute + 1

                    # If the minutes rolled over, roll up hours.

                if minute == 60:
                    minute = 0
                    hour24 = hour24 + 1

                        # If the hours rolled over, roll up day.

                    if hour24 == 24:
                        hour24 = 0
                        dayofmo = dayofmo + 1

                            # If the day rolled over, roll up month.

                        if dayofmo >= 29:   # First possible rollover day

                                # First, figure out number of days in month.

                            moDays = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
                                # - 30 days hath September, April, June & November.
                                #   The rest have 31 except February, which is complicated.

                            daysInMo = moDays[month]

                                # February: Special case to adjust # of days in month.

                            if month == 2 and dayofmo == 29:
                                
                                    # First, we have to figure out if it's a leap year.
                                if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                                    isLeapYear = True
                                else:
                                    isLeapYear = False

                                if isLeapYear:
                                    daysInMo = daysInMo + 1     # Add leap day.

                                # Finally we can determine if the day has rolled over.

                            if dayofmo > daysInMo:
                                dayofmo = 1
                                month = month + 1

                                    # If month rolled over, then increment year.

                                if month > 12:
                                    month = 1
                                    year = year + 1

                                #<- End if month>12.
                            #<- End if dayofmo > daysInMo.
                        #<- End if dayofmo >= 29.
                    #<- End if hour24 = 24.
                #<- End if minute=60.
            #<-End if second=60.

                # At this point, we've finally finished rounding up the components of the month/day/year etc.
                # so that the number of seconds is an integer.  Now, stuff everything into a datetime structure.
                # (NOTE: datetime class has a year 10,000 problem.)

            gpsDatetime = datetime.datetime(year, month, dayofmo, hour24, minute, second, 0)
                # - We assume here that microseconds is always 0.

            return gpsDatetime
        
        #<- End def GPS_Module._GPRMC_Record.extract_datetime().
        
    #<- End class GPS_Module._GPRMC_Record.
            
    class   _TRAIM_Record:      pass
    class   _POSHOLD_Record:    pass

        # Instance initializer.
    
    def __init__(this, node):

        this._lock = threading.RLock()

        with this._lock:
        
            this.node = node    # Remember which sensor node this GPS module is part of.

            this.baud_rate = 57600      # Baud rate pre-programmed into our custom GPS config.

                # Create the signal flags associated with the state of this component.

            this.resetting      = flag.Flag(lock=this._lock, initiallyUp=False)      # True = Module is currently in the middle of executing a reset operation.
            this.NMEA_on        = flag.Flag(lock=this._lock, initiallyUp=True)
            this.TRAIM_on       = flag.Flag(lock=this._lock, initiallyUp=False)
            this.POSHOLD_on     = flag.Flag(lock=this._lock, initiallyUp=False)

                # Some important status variables.

            this.nSats = None       # Means, we don't yet know how many satellites have been acquired.
            this.last_nSats = None  # Previous value of nSats reported.

                # Some more informational status flags.

            this.gotSats = flag.Flag(lock=this._lock, initiallyUp=False)    # True = Receiving >=1 satellites.

                # TRAIM-associated status flags.

                    # These relate to the "alarm" status.

            this.TRAIM_allgood = flag.Flag(lock=this._lock, initiallyUp=False)
            this.TRAIM_somebad = flag.Flag(lock=this._lock, initiallyUp=False)
            this.TRAIM_unknown = flag.Flag(lock=this._lock, initiallyUp=False)

                    # These relate to whether the contents of the TRAIM message are valid or not.

            this.TRAIM_valid   = flag.Flag(lock=this._lock, initiallyUp=False)
            this.TRAIM_invalid = flag.Flag(lock=this._lock, initiallyUp=False)

                # Some special variables associated with the most recent TRAIM message.

            this.TRAIM_nBad   = 0
            this.TRAIM_uncert = 0.0

                # These flags are really just guesses, but are better than nothing.
                # NOTE: We aren't really using them yet, or setting them anywhere
                # besides here.  Need to fix this and start using them sometime.

            this.ephemeris_good     = flag.Flag(lock=this._lock, initiallyUp=False)     # Initially, assume the ephemeris is NOT good.
            this.almanac_good       = flag.Flag(lock=this._lock, initiallyUp=True)      # Initially, assume the almanac IS good.
                #   \
                #    \_ The idea here is that the depth of resetting we do (hot/warm/cold)
                #           on startup can be varied automatically depending on whether we
                #           think the existing almanac/ephemeric data in the module is good.
                #           If almanac is bad, we do cold start, else if ephemeris is bad,
                #           we do warm start, else we can just do a hot start.  (However, this
                #           behavior is not yet implemented; currently we always do warm start.)

                # Create "inboxes" for tracking the most recent incoming
                # message of each type from the real GPS.  They can all
                # share the overall object lock for the GPS model.

            this.pdme_inbox     = utils.WatchBox(lock=this._lock)
            this.gpgga_inbox    = utils.WatchBox(lock=this._lock)
            this.gprmc_inbox    = utils.WatchBox(lock=this._lock)
            this.traim_inbox    = utils.WatchBox(lock=this._lock)
            this.poshold_inbox  = utils.WatchBox(lock=this._lock)
            this.header_inbox   = utils.WatchBox(lock=this._lock)
            this.gptxt_inbox    = utils.WatchBox(lock=this._lock)

                # Create a "publisher" object to allow other entities to subscribe to
                # be notified of each message of a given type.  The advantage of this
                # over the WatchBox mechanism is that it guarantees that no messages
                # will be missed.

            this.publisher = publisher.Publisher()   # Create new publisher.

        #<- End with this._lock.

    #<- End def GPS_Module.__init__().

        #|----------------------------------------------------------------------------------------
        #|
        #|      GPS_Module.sentMessage()                            [public instance method]
        #|
        #|          Calling this method informs the model of the GPS module that the
        #|          real module just sent us a particular message, already parsed into
        #|          a sequence of words by the caller.  We then dispatch to handlers
        #|          for the following message types which we know how to handle:
        #|
        #|              GPRMC - Recommended minimum specific data.
        #|              GPGGA - GPS fix data; more precision than GPRMC.
        #|              PDME - Confirmations of miscellaneous PDME messages.
        #|              PDMETRAIM - Timing Receiver Autonomous Integrity Monitoring
        #|                  status message.
        #|              PDMEPOSHOLD - Position hold status message.
        #|              PDMEHEADER1, PDMEHEADER2 - Version info emitted on startup.
        #|              GPTXT - Configuration information emitted on startup.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def sentMessage(this, msgWords):

        msgType = msgWords[0]       # First word is the message type.

        if    msgType == 'GPRMC':           # Ex: $GPRMC,212143.013,V,3025.676,N,08417.112,W,0.0,0.0,161211,4.1,W*70
            
            this._handleGPRMC(msgWords)

        elif    msgType == 'GPGGA':         # Ex: $GPGGA,212559.000,3025.67523,N,08417.09543,W,0,00,99.0,083.67,M,-29.7,M,,*6C
            
            this._handleGPGGA(msgWords)

        elif    msgType == 'PDME':
            
            this._handlePDME(msgWords)

        elif    msgType == 'PDMETRAIM':
            
            this._handlePDMETRAIM(msgWords)

        elif    msgType == 'PDMEPOSHOLD':
            
            this._handlePDMEPOSHOLD(msgWords)

                # NOTE: The next two can't be parsed by the usual method because there is
                # no comma delimiting the end of the message type name.  This problem needs
                # to be repaired before .sendMessage() is called, or these elif's won't work.

        elif    msgType == 'PDMEHEADER1':

            this._handlePDMEHEADER1(msgWords)   # $PDMEHEADER1: DeLORME GPS2058_HW_1.0.1

        elif    msgType == 'PDMEHEADER2':       # $PDMEHEADER2: DeLORME GPS2058_FW_2.0.1
            
            this._handlePDMEHEADER2(msgWords)   

        elif    msgType == 'GPTXT':             # $GPTXT,COSMICi Custom_Config_0.0.3
            
            this._handleGPTXT(msgWords)

        else:
            logger.warn(("GPS_Module.sentMessage(): The GPS module sent a message of a type " +
                         "[%s] which I don't know how to handle.  Ignoring...") % msgType)

    #<- End def GPS_Module.sentMessage().


    def _handleGPRMC(this, msgWords):

            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 11:
            logger.error(("GPS_Module:_handleGPRMC(): I expected the $GPRMC message to have " +
                          "11 arguments but I received %d.  Ignoring message...") % nArgs)
            return

            # Parse out all the arguments into appropriately named variables.
            # NOTE: The latitude/longitude values here are less precise than 
            # those in the GPGGA message below.

        gprmc_rec = this._GPRMC_Record()     # Create new empty GPGGA record object.

        gprmc_rec.PosUTC      = msgWords[1]       # Coordinated universal time in HHMMSS.SSS format.
        gprmc_rec.PosStat     = msgWords[2]       # Position status ('A'=valid or 'V'=invalid)
        gprmc_rec.Lat         = msgWords[3]       # Absolute value of latitude in DDMM.MMM format.
        gprmc_rec.LatRef      = msgWords[4]       # 'N' in Northern hemisphere, 'S' in Southern.
        gprmc_rec.Lon         = msgWords[5]       # Absolute value of longitude in DDDMM.MMM format.
        gprmc_rec.LonRef      = msgWords[6]       # 'E' in Eastern hemisphere, 'W' in Western.
        gprmc_rec.Spd         = msgWords[7]       # Speed over ground in knots, x.x
        gprmc_rec.Hdg         = msgWords[8]       # "Heading track make good (degree true)" (WTF?) x.x
        gprmc_rec.Date        = msgWords[9]       # Date (GMT/UTC) in DDMMYY format.
        gprmc_rec.MagVar      = msgWords[10]      # Absolute value of magnetic variation (degrees), x.x
        gprmc_rec.MagRef      = msgWords[11]      # Magnetic variation direction, 'E' or 'W' (of North?)

        this.gprmc_inbox.contents = gprmc_rec       # Remember this record.  Alerts waiters.

        this.publisher.publish(publisher.Issue('GPRMC', gprmc_rec))   # Publish the record.

    #__/ End def GPS_Module._handleGPRMC().

        
    def _handleGPGGA(this, msgWords):
        
            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 14:
            logger.error(("GPS_Module:_handleGPGGA(): I expected the $GPGGA message to have " +
                          "14 arguments but I received %d.  Ignoring message...") % nArgs)
            return

            # Parse out all the arguments into appropriately named variables.

        gpgga_rec = this._GPGGA_Record()     # Create new empty GPGGA record object.

            # Populate the fields of the GPGGA record object.
        
        gpgga_rec.PosUTC      = msgWords[1]       # Coordinated universal time in HHMMSS.SSS format.
        gpgga_rec.Lat         = msgWords[2]       # Absolute value of latitude in DDMM.MMMMM format.
        gpgga_rec.LatRef      = msgWords[3]       # 'N' in Northern hemisphere, 'S' in Southern.
        gpgga_rec.Lon         = msgWords[4]       # Absolute value of longitude in DDDMM.MMMMM format.
        gpgga_rec.LonRef      = msgWords[5]       # 'E' in Eastern hemisphere, 'W' in Western.
        gpgga_rec.Qual        = msgWords[6]       # Quality indicator: 0=no fix; 1=GPS fix; 2=differential GPS.
        gpgga_rec.NbSat       = msgWords[7]       # Number of satellites in use.  XX  (2 digit decimal integer)
        gpgga_rec.HDOP        = msgWords[8]       # Horizontal dilution of precision.  X.X
        gpgga_rec.AltMsl      = msgWords[9]       # Antenna altitude above/below main sea level in meters, x.x
        gpgga_rec.Meters_1    = msgWords[10]      # Always 'M' for meters, ignored.
        gpgga_rec.GeoidSep    = msgWords[11]      # Geoidal separation in meters, x.x
        gpgga_rec.Meters_2    = msgWords[12]      # Always 'M' for meters, ignored.
        gpgga_rec.Null_1      = msgWords[13]      # Null field, ignored.
        gpgga_rec.Null_2      = msgWords[14]      # Null field, ignored.

        with this._lock:      # Ensure that the below manipulations of this structure are performed atomically.

                # Extract a key parameter:  Number of satellite signals currently acquired.

            this.nSats = int(gpgga_rec.NbSat)       # Convert number of satellites as an integer.

                # Generate an informative diagnostic message whenever the number of satellites changes.
            
            if this.nSats != this.last_nSats:
                if this.nSats == 0:
                    logger.warn("GPS_Module:_handleGPGGA():  I'm not receiving a GPS signal from any satellites.")
                else:
                    logger.info("GPS_Module:_handleGPGGA():  Now receiving GPS data from %d satellites."
                                % this.nSats)
                this.last_nSats = this.nSats
            elif this.nSats == 0:
                logger.warn("GPS_Module:_handleGPGGA():  Still no satellites...")
                
                # Adjust the value of the "gotSats" flag to indicate whether the # of satellites is nonzero.

            this.gotSats.up = (this.nSats >= 1)     # Set flag specifying whether we're acquiring sats.
            
        #__/ End with this._lock().

            # Update the last-received GPGGA record in case any clients are waiting for it to change.

        this.gpgga_inbox.contents = gpgga_rec     # Remember this record.  Alerts waiters.

            # Publish the record as a "magazine issue" through our "publisher" interface.

        this.publisher.publish(publisher.Issue('GPGGA', gpgga_rec))   # Publish the record.
    
    #__/ End def GPS_Module._handleGPGGA().

        
    def _handlePDME(this, msgWords):
        
            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs < 2:
            logger.error(("GPS_Module:_handlePDME(): I expected the $PDME message " +
                          "to have at least 2 arguments but I only received %d.  " +
                          "Ignoring message...") % nArgs)
            return

            # Parse out all the arguments into appropriately named variables.

        pdme_rec = this._PDME_Record()

        pdme_rec.cmdCode = msgWords[1]       # Code number of the PDME command being acknowledged.
        
        cmdNum = int(pdme_rec.cmdCode)

            # PDME commands 21 & 22 generate a second PDME return echoing
            # their arguments, in addition to the original "OK" return.
            # We ignore this second return for now (ideally we should
            # check it to make sure the arguments were read correctly).
            
        if cmdNum == this._PDME_POSHOLD_CTRL:
            if nArgs > 2 and msgWords[2] != "OK":     # Not the "OK" return?
                logger.info("GPS_Module:_handlePDME(): Received extended PDME return [%s], ignoring..." %
                            utils.unsplit(msgWords, ","))
                return

        if nArgs > 2 and cmdNum != this._PDME_TRAIM_CTRL:
            logger.error(("GPS_Module:_handlePDME(): I expected the $PDME,%d reply " +
                          "to have at most 2 arguments but I received %d.  " +
                          "Ignoring message...") % (cmdNum, nArgs))
            return
        
        pdme_rec.ok = msgWords[2]       # This should be "OK" if the command is acknowledged.

        if pdme_rec.ok != 'OK' and nArgs == 2:
            logger.warn("GPS_Module._handlePDME():  A $PDME,%d command reply returned [%s] instead of [OK]." %
                        (cmdNum, pdme_rec.ok))
        else:
            pdme_rec.ok = "OK"      # Just assume the command worked for now.

        #__/ End if pdme_rec.cmdCode is one that just returns "OK".

        # Really, here we should check POSHOLD and TRAIM control extended returns
        # as well to make sure they match the commands sent - but we're
        # not bothering with that yet.  Essentially, we assume that they worked.

            # Update the last-received PDME record in case any clients are waiting for it to change.
            
        this.pdme_inbox.contents = pdme_rec

            # Publish the record as a "magazine issue" through our "publisher" interface.

        this.publisher.publish(publisher.Issue('PDME', pdme_rec))     # Publish the record.
        
    #<- End def GPS_Module._handlePDME().

        
    def _handlePDMETRAIM(this, msgWords):
        
            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 16:
            logger.error(("GPS_Module:_handlePDMETRAIM(): I expected the $PDMETRAIM message to have " +
                          "16 arguments but I received %d.  Ignoring message...") % nArgs)
            return

        traim_rec = this._TRAIM_Record()
        
            # Parse out all the arguments into appropriately named variables.

        traim_rec.Solution        = msgWords[1]       # 0=UNDER_ALARM, 1=OVER_ALARM, 2=UNKNOWN
        traim_rec.Valid           = msgWords[2]       # 0=NOT_VALID, 1=VALID
        traim_rec.Time_Error      = msgWords[3]       # Time Error in secs, s.sssssssss (9 digits)
        traim_rec.Removed_SVIDs   = msgWords[4]       # Number of removed SVIDs (bad satellites)
        traim_rec.bad_sat_ids     = msgWords[5:]      # Array of bad satellite IDs, 0 for n/a.

            # Go ahead and parse a few numeric fields.  Should we do some
            # exception handling here, just in case there are some garbage
            # characters in the data?

        traim_rec.solutNum = int(traim_rec.Solution)          # Convert these numeric status 
        traim_rec.validNum = int(traim_rec.Valid)             # fields to numbers for easier
        traim_rec.nBadSats = int(traim_rec.Removed_SVIDs)     # use.
        traim_rec.timeError = float(traim_rec.Time_Error)     # Time error in seconds.

            # Update a few state variables in the model proxy.

        with this._lock:

                # Update flags based on the solution-status code.

            this.TRAIM_allgood.up = (traim_rec.solutNum == this.TRAIM_SOL_UNDER_ALARM)
            this.TRAIM_somebad.up = (traim_rec.solutNum == this.TRAIM_SOL_OVER_ALARM)
            this.TRAIM_unknown.up = (traim_rec.solutNum == this.TRAIM_SOL_UNKNOWN)

                # Update flags based on the time-valid code.

            this.TRAIM_valid   = (traim_rec.validNum == this.TRAIM_VALID_YES)
            this.TRAIM_invalid = (traim_rec.validNum == this.TRAIM_VALID_NO)

                # Update non-flag variables associated with status of TRAIM algorithm.

            this.TRAIM_nBad   = traim_rec.nBadSats
            this.TRAIM_uncert = traim_rec.timeError
            
        #<- End with this._lock

        this.traim_inbox.contents = traim_rec       # Remember this record.  Alerts waiters.

        this.publisher.publish(publisher.Issue('PDMETRAIM', traim_rec))   # Publish the record.
        
    #<- End def GPS_Module._handlePDMETRAIM().
            
        
    def _handlePDMEPOSHOLD(this, msgWords):

            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 6:
            logger.error(("GPS_Module:_handlePDMEPOSHOLD(): I expected the $PDMEPOSHOLD message to have " +
                          "6 arguments but I received %d.  Ignoring message...") % nArgs)
            return

        poshold_rec = this._POSHOLD_Record()

            # Parse out all the arguments into appropriately named variables.

        poshold_rec.OnOff       = msgWords[1]       # 0='OFF',1='ON' to describe POSITION HOLD mode status
        poshold_rec.Latitude    = msgWords[2]       # Absolute value of latitude in DDMM.MMM format.
        poshold_rec.LatRef      = msgWords[3]       # Latitude direction, 'N'=North, 'S'=South.
        poshold_rec.Longitude   = msgWords[4]       # Absolute value of longitude in DDDMM.MMM format.
        poshold_rec.LonRef      = msgWords[5]       # Longitude direction, 'E'=East, 'W'=West.
        poshold_rec.Height      = msgWords[6]       # Altitude in meters (-1500 to 18000), decimal.

            # Go ahead and parse a few numeric fields.  Should we do some
            # exception handling here, just in case there are some garbage
            # characters in the data?

        poshold_rec.onOffNum = int(poshold_rec.OnOff)

            # Announce the availability of the new message to appropriate waiters.

        this.poshold_inbox.contents = poshold_rec   # Remember this record.  Alerts waiters.

        this.publisher.publish(publisher.Issue('PDMEPOSHOLD', poshold_rec))     # Publish the record.

    #<- End def GPS_Module._handlePDMEPOSHOLD().

        # These next two still need to be implemented.

    def _handlePDMEHEADER1(this, msgWords):     # E.g., $PDMEHEADER1,DeLORME GPS2058_HW_1.0.1
        
            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 1:
            logger.error(("GPS_Module:_handlePDMEHEADER1(): I expected the $PDMEHEADER1 message to have " +
                          "1 argument but I received %d.  Ignoring message...") % nArgs)
            return

        with this._lock:
            this.resetting.rise()       # The module is doing a reset sequence, so make sure this flag is up.
            this.POSHOLD_on.fall()      # Since it's already started resetting, we can assume POSHOLD mode is no longer on.
            this.TRAIM_on.fall()        # Since it's already started resetting, we can assume TRAIM mode is no longer on.
            
            pdme_header_rec = this._PDMEHEADER_Record()

            pdme_header_rec.num         =   1               # To distinguish PDMEHEADER1 from PDMEHEADER2.
            pdme_header_rec.hw_vers     =   msgWords[1]     # Hardware version string, e.g., "DeLORME GPS2058_HW_1.0.1"

            this.header_inbox.contents = pdme_header_rec    # Remember this record.  Alerts waiters.

            this.publisher.publish(publisher.Issue('PDMEHEADER', pdme_header_rec))       # Publish the record.
    #  /
    #_/ End def GPS_Module._handlePDMEHEADER1().
        
    def _handlePDMEHEADER2(this, msgWords):     # E.g., $PDMEHEADER2,DeLORME GPS2058_FW_2.0.1
        
            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 1:
            logger.error(("GPS_Module:_handlePDMEHEADER2(): I expected the $PDMEHEADER2 message to have " +
                          "1 argument but I received %d.  Ignoring message...") % nArgs)
            return

        with this._lock:
            this.resetting.rise()

            pdme_header_rec = this._PDMEHEADER_Record()

            pdme_header_rec.num         =   2               # To distinguish PDMEHEADER1 from PDMEHEADER2.
            pdme_header_rec.fw_vers     =   msgWords[1]     # Firmware version string, e.g., "DeLORME GPS2058_FW_2.0.1"

            this.header_inbox.contents = pdme_header_rec    # Remember this record.  Alerts waiters.

            this.publisher.publish(publisher.Issue('PDMEHEADER', pdme_header_rec))       # Publish the record.
    #  /
    #_/ End def GPS_Module._handlePDMEHEADER2().

    def _handleGPTXT(this, msgWords):           # E.g., $GPTXT,COSMICi Custom_Config_0.0.3
            # Calculate & verify number of arguments.
            
        nArgs = len(msgWords) - 1   # -1 because message type isn't an argument.
        if nArgs != 1:
            logger.error(("GPS_Module:_handleGPTXT(): I expected the $GPTXT message to have " +
                          "1 argument but I received %d.  Ignoring message...") % nArgs)
            return

        gptxt_rec = this._GPTXT_Record()

        gptxt_rec.text     =   msgWords[1]     # Text string, e.g., "COSMICi Custom_Config_0.0.3"

        with this._lock:
            this.gptxt_inbox.contents = gptxt_rec    # Remember this record.  Alerts waiters.

            this.publisher.publish(publisher.Issue('GPTXT', gptxt_rec))      # Publish the record.

            this.resetting.fall()   # The GPTXT message is the last thing in the reset sequence.

    def sendLine(this, line:str):   # Assumes <line> is not yet newline-terminated.
        this.node.sensor_host.sendLine("GPS " + line)    # Send the line to the node's sensor host.

        # Sends a $PDME command string to the real GPS module.
        # First argument is command code; remaining arguments
        # depend on the command type.

    def _send_PDME_cmd(this, cmdCode:int, *args):

        cmdWords = ["PDME", "%d" % cmdCode]
        cmdWords[2:] = args

        cmdStr = utils.unsplit(cmdWords, ",")     # Rejoin the individual command words, comma-delimited.

        sentence = nmea.makeNMEA(cmdStr)     # Put it in NMEA sentence format.

        this.sendLine(sentence)         # Send the line to the GPS. (Will add newline)

    #<- End def GPS_Module._send_PDME_cmd().

        # Wait for a PDME reply confirming a given PDME command.
        # NOTE: It would probably make sense for this method to
        # raise an exception if the desired confirmation isn't
        # received within a certain time window.
        #   ALSO: The hot/warm/cold reset PDME commands will NEVER
        # generate a PDME reply, because the module will reset before
        # it gets around to replying.  We handle this with a special
        # case where instead we wait for the module to finish resetting
        # itself.

    def _wait_PDME_conf(this, cmdcode):

        with    this._lock:

                # First, a special case here for reset command-codes - instead of waiting for
                # a PDME return message, wait for the .resetting flag to fall, which should
                # happen at the end of processing the $GPTXT message.

            if cmdcode >= this._PDME_COLD_START and cmdcode <= this._PDME_HOT_START:
                logger.info("GPS_Module._wait_PDME_conf():  Waiting for the GPS module to finish resetting...")
                this.resetting.waitFall()       # Wait for the model's "resetting" flag to fall.
                    # This flag will be lowered after the model receives the GPTXT line.
                logger.info("GPS_Module._wait_PDME_conf():  PDME command %d confirmed by a completed reset." % cmdcode)
                return      # Rest of method is for handling the normal case.
            #__/ End if cmdcode is a hot/warm/cold start.
            
                # For other cases, we explicitly wait for a $PDME return message.
                # Really, we should do the below with a reasonable timeout, and report an
                # error if the confirmation isn't received within a few seconds.

            logger.info("GPS_Module._wait_PDME_conf():  Waiting to get a PDME command return...")
            pdme_rec = this.pdme_inbox.wait()     # Wait for the PDME inbox's "updated" flag to be touched.

            last_cmd    = int(pdme_rec.cmdCode)
            cmd_ok      = pdme_rec.ok

            if  last_cmd != cmdcode:

                logger.error(("GPS_Module._wait_PDME_conf(): Was waiting for PDME command " +
                              "%d to be confirmed, but got PDME command %d instead!")
                             % (cmdcode, last_cmd))

                # raise exception?

            elif  cmd_ok != 'OK':

                logger.error(("GPS_Module._wait_PDME_conf(): Got [%s] instead of [OK] from " +
                              "PDME command %d.") % (cmd_ok, cmdcode))

                # raise exception?

            # should there be a case here for if we timed out?

            else:

                logger.info("GPS_Module._wait_PDME_conf():  PDME command %d confirmed." % cmdcode)

            #<- End if (process PDME command acknowledgement)
                
        #<- End with this._lock

    #<- End def GPS_Module._wait_PDME_conf().
        

    def _do_PDME_cmd(this, code, *args):       # Send a command & wait for confirmation.
        this._send_PDME_cmd(code, *args)
            # If the code is 0-2 (restart), we need to do something different
            # here b/c we won't receive a PDME reply.
        this._wait_PDME_conf(code)
        
    def hotStart(this):             # note: $PDME,2
        this.resetting.rise()
        this._do_PDME_cmd(this._PDME_HOT_START)     # Do the hot-start command (command code 2)
    #<- End def hotStart().

    def warmStart(this):            # note: $PDME,1
        with this._lock:
            this.resetting.rise()
            this.ephemeris_good.fall()                  # Mark ephemeris as nogood (since we're about to reset it).
            this._do_PDME_cmd(this._PDME_WARM_START)
        
    def coldStart(this):            # note: $PDME,0
        with this._lock:
            this.resetting.rise()
            this.ephemeris_good.fall()                  # Mark ephemeris as nogood (since we're about to reset it).
            this.almanac_good.fall()                    # Mark almanac as nogood (since we're about to reset it).
            this._do_PDME_cmd(this._PDME_COLD_START)

    def holdPos(this, loc:earth_coords.EarthCoords):        # note: $PDME,21,...
                                    
            # Note: format of lat is DDMM.MMM, lon is DDDMM.MMM
            # Altitude is meters MMMM.  (Output format in PDME,21 message.)

        latdeg = loc.lat   # Latitude in degrees
        londeg = loc.long  # Longitude in degrees
        altmet = loc.alt   # Altitude in meters

            # Convert coordinates to format expected by PDME,21 command.
        
        lat = "%02d%02.3f" % earth_coords.deg_to_degmin(abs(latdeg))
        latref = "S" if latdeg<0 else "N"
        
        lon = "%03d%02.3f" % earth_coords.deg_to_degmin(abs(londeg))
        lonref = "W" if londeg<0 else "E"
        
        alt = "%04d" % altmet   # Implicit cast to int rounds towards zero.

        with this._lock:
            this._do_PDME_cmd(this._PDME_POSHOLD_CTRL, "1",
                              lat, latref, lon, lonref, alt)
            this.POSHOLD_on.rise()      # Raise flag announcing that POSHOLD mode is now on.

    #<- End def GPS_Module.holdPos().


    def enableTRAIM(this, accuracy):    # accuracy is floating-point seconds

            # NOTE: Really, the <accuracy> value only affects which satellites
            # are considered "out of bounds" and are reported as such and are
            # not included in the solution calculations.  It doesn't necessarily
            # actually keep the real accuracy of the result within the given range.

        traim_alarm = "%.9f" % accuracy

        with this._lock:

            this._do_PDME_cmd(this._PDME_TRAIM_CTRL, "1", traim_alarm)

            this.TRAIM_on.rise()        # Raise flag announcing that TRAIM mode is now on.

    #<- End def GPS_Module.enableTRAIM().


        # Initialize GPS position and time to given values.
        #   <pos> is position as an earth_coords.EarthCoords object.
        #   <dt> is a naive datetime object representing the desired UTC date & time.

    def initPosTime(this, pos, dt):      # Initialize GPS position & time; $PDME,9,...

            # Extract coordinates (latitude, longitude, altitude)
            # from the <pos> EarthCoords object.  Format them as
            # strings of the correct length, with leading 0's.

        lat     = "%02d" % pos.lat
        long    = "%03d" % pos.long
        alt     = "%d" % pos.alt

            # Here we are trying to compensate for a bug in the GPS
            # module where it always seems to end up about 17 seconds
            # (give or take a couple of seconds) behind the time we
            # tell it to set itself to.

        dt = dt + datetime.timedelta(seconds = 17)

            # Extract time parameters (year, month, day, hour, minute, sec)
            # from the <dt> datetime object.

        year    = "%04d" % dt.year
        month   = "%02d" % dt.month
        day     = "%02d" % dt.day
        hour    = "%02d" % dt.hour
        minute  = "%02d" % dt.minute
        sec     = "%06.3f," % (dt.second + dt.microsecond*1e-6)
            # Above we're trying to guess the exact seconds format expected
            # by the PDME,9 command.  It seems to be very picky.
            
#        sec     = "%02d," % round(dt.second + dt.microsecond*1e-6)
            # Round sec to nearest integer b/c $PDME,9 command apparently 
            # can't handle fractional seconds anyway.

            # Put the various coordinates in the order expected for
            # the arguments of the PDME_INIT_POS_TIME command.

        n1 = lat        # Latitude in (whole) degrees, + (E) or - (W)
        n2 = long       # Longitude in (whole) degrees, + (N) or - (S)
        n3 = alt        # Altitude in (whole) meters above sea level
        n4 = year       # Year (four digits)
        n5 = month      # Month (1-12)
        n6 = day        # Day of month (1-31)
        n7 = hour       # Hour of day (0-23)
        n8 = minute     # Minute of hour (0-59)
        n9 = sec        # Second of minute (0-59)

            # Send the command to the GPS module (& wait for confirmation).

        this._do_PDME_cmd(this._PDME_INIT_POS_TIME,
                          n1, n2, n3, n4, n5, n6, n7, n8, n9)

            # Raise the flag to announce that TRAIM algorithm is enabled.
    
        this.TRAIM_on.rise()
            # - NOTE: We really ought to lower this flag whenever we notice
            #   the module has been reset.

    #<- End def initPosTime().

        # The following were planned at one time but have not yet been
        # implemented and are not yet used.  They might not be needed.
    
    def turnOnNMEA(this):               pass    # note: $PDME,10,1  $PDME,10,2
    def turnOffNMEA(this):              pass    # note: $PDME,10,0
    def turnOffTRAIM(this):             pass    # note: $PDME,22,0
    
#<- End class GPS_Module

#|^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#|      END FILE:   gps.py
#|*****************************************************************************************************
