#|********************************************************************************
#|                              TOP OF FILE
#|********************************************************************************
#|
#|      FILE NAME:  runmgr.py                       [python module source file]
#|
#|      DESCRIPTION:
#|
#|          This module provides a class definition for a
#|          worker thread whose area of responsibility is
#|          to start up and maintain an overall data-
#|          collection run.  This involves going through
#|          roughly the following sequence of steps:
#|
#|              1.  Wait for the CTU node to attach,
#|                      identify itself, and declare
#|                      itself ready to accept commands.
#|
#|              2.  Wait for the FEDM (ShowerDetector)
#|                      node to attach, identify itself,
#|                      and declare itself ready to
#|                      accept commands.
#|
#|              3.  Wait for the GPS_Manager associated
#|                      with the CTU to report at least
#|                      one valid TRAIM reading with non-
#|                      null accuracy and where not all
#|                      satellites being received have
#|                      been eliminated from the timing
#|                      solution.
#|
#|              4.  Start up the TimeKeeper worker thread,
#|                      whose job is to archive & process
#|                      the absolute time-reference data
#|                      received from the CTU.
#|
#|              5.  Start up the DataCollector worker thread,
#|                      whose job is to archive & process
#|                      the time-stamped particle data received
#|                      from the FEDM.
#|
#|              6.  Start the CTU running.
#|
#|      REVISION HISTORY:
#|
#|          v0.0, 3/27/12 (MPF) - Started writing module; wrote
#|              file description; still needs implementing.
#|          v0.1, 4/3/12 (MPF) - Preconditions & starting CTU have
#|              been implemented; but they still need to be tested.
#|              Once that code is debugged, the server should
#|              automatically start the data-collection run after
#|              all the components (CTU and FEDM) are turned on.
#|              The TimeKeeper & DataCollector modules have not yet
#|              been implemented, however, so we are still not doing
#|              anything meaningful with the time-tagged data.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

import  threading                   # RLock()

        # Imports of custom user modules.

import  logmaster                   # getLogger(), etc.
import  worklist                    # Worker class.
import  flag                        # Flag class.


__all__ = ['RunManager'     # A worker thread to setup/monitor data-collection run.
           ]


logger = logmaster.getLogger(logmaster.sysName + '.runmgr')


class   RunManager(worklist.Worker):

        # Class variables:
    
    defaultRole = 'runmgr'      # Override value from parent class.

    # Public instance data members:
    #
    #   The following are input flags for dynamically communicating important
    #   changes of system state to the RunManager.
    #
    #       ctu_ready   - Raise this flag when CTU is ready to accept commands.
    #       fedm_ready  - Raise this flag when FEDM is ready to accept commands.
    #       good_time   - Raise this flag when GPS has a valid time lock.
    #       

    def     __init__(inst, *args, **kargs):

        inst._lock = threading.RLock()      # Reentrant mutex lock for thread-safe access to object data.

        with    inst._lock:
            
            inst.defaultComponent = 'server'

                # Create flags for tracking various bits of state that we depend on.

            inst.ctu_ready  = flag.Flag(lock = inst._lock, initiallyUp = False)
            inst.fedm_ready = flag.Flag(lock = inst._lock, initiallyUp = False)
            inst.good_time  = flag.Flag(lock = inst._lock, initiallyUp = False)

                # Create our initial task:  Start a run going as soon as we can.

            inst.initialTask = worklist.WorkItem(inst._queueStartupSequence)

                # Hand off control to the initializer for our parent class.
                
            worklist.Worker.__init__(inst, *args, **kargs)      # This starts the Worker thread running.

        # Other threads should call this method to tell us the CTU
        # is ready (and give us a link to it).

    def     yo_CTU_is_ready(inst, ctu_node):

        with    inst._lock:

            inst.ctu_node = ctu_node
            inst.ctu_ready.rise()   # Raise our flag indicating that the CTU is ready.
                # This wakes up any waiters (such as RunManager thread in ._wait_good_time().)

    def yo_FEDM_is_ready(inst, fedm_node):
        with inst._lock:
            inst.fedm_node = fedm_node
            inst.fedm_ready.rise()  # Raise our flag indicating that the FEDM is ready.
                # This wakes up any waiters (such as RunManager thread in ._wait_good_time().)

    def yo_GPS_time_is_good(inst):
        inst.good_time.rise()   # Raise our flag indicating GPS time is good.
            # This wakes up any waiters (such as RunManager thread in ._wait_good_time().)

    def yo_GPS_time_is_nogood(inst):
        inst.good_time.fall()   # Lower our flag indicating GPS time is good.
            # This wakes up any waiters (such as RunManager thread in ._wait_good_time().)

        # This task method (intended to be run only by the RunManager worker thread itself)
        # queues up the individual steps of the startup sequence on our worklist.  The point
        # of this is that it allows the startup sequence to be interrupted (sort of) by
        # another thread by (for example) inserting some other task at the head of our
        # worklist, which will then be done before the next step of the startup sequence.

    def     _queueStartupSequence(self):

                # First we just wait for various preconditions of starting the run to be
                # satisfied.  Other threads should take care of raising these flags for us
                # once they have determined that these conditions are satisfied.

        self(self._wait_CTU_ready)          # Wait for the CTU to be ready to accept commands.
        self(self._wait_FEDM_ready)         # Wait for the FEDM to be ready to accept commands.
        self(self._wait_good_time)          # Wait for the GPS to be producing valid time data.

                # After that, do the actual steps needed to actually start the run.
        
        self(self._startTimekeeper)         # Start up the Timekeeper worker thread.
        self(self._startDataCollector)      # Start up the DataCollector worker thread.
        self(self._start_CTU)               # Tell the Central Timing Unit to start marking time.

    def     _wait_CTU_ready(self):

        logger.info("RunManager._wait_CTU_ready():  Waiting for the CTU to be ready to accept commands.")
        self.ctu_ready.waitUp()     # Wait for the CTU to be ready to accept commands.
        logger.info("RunManager._wait_CTU_ready():  OK, the CTU is ready to accept commands now.")

    def     _wait_FEDM_ready(self):

        logger.info("RunManager._wait_FEDM_ready():  Waiting for the FEDM to be ready to accept commands.")
        self.fedm_ready.waitUp()     # Wait for the FEDM to be ready to accept commands.
        logger.info("RunManager._wait_FEDM_ready():  OK, the FEDM is ready to accept commands now.")
        
    def     _wait_good_time(self):

        logger.info("RunManager._wait_good_time():  Waiting for the GPS to achieve a good time fix.")
        self.good_time.waitUp()     # Wait for the GPS to be producing valid time data.
        logger.info("RunManager._wait_good_time():  OK, the GPS has achieved at least one good time fix.")

    def     _startTimekeeper(self):     # Not yet implemented.
        logger.warn("RunManager._startTimekeeper():  At this point, I would be starting " +
                      "the Timekeeper worker thread, but it hasn't been implemented yet.")

    def     _startDataCollector(self):  # Not yet implemented.
        logger.warn("RunManager._startTimekeeper():  At this point, I would be starting " +
                      "the DataCollector worker thread, but it hasn't been implemented yet.")

        # NOTE: Before starting the CTU, the following conditions should be satisfied:
        #
        #  (1) The CTU's host should be ready to accept commands;
        #  (2) The other nodes in the system should be ready to capture timing-sync
        #       pulses from the CTU.
        #  (3) The CTU's GPS time reference should be producing accurate time values,
        #
        # The whole purpose of the present module is to ensure that the above conditions
        # are satisfied and then (and ONLY then) call the below method.  So, don't call
        # it in other circumstances!

    def     _start_CTU(self):           # Not yet implemented.
        logger.normal("Starting the Central Timing Unit.")
        self.ctu_node.start()       # Tell the CTU node to commence normal operations.
    
    # still need to implement entire rest of RunManager class

