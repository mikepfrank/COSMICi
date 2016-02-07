#|==============================================================================
#|
#|      FILE NAME:  broadcaster.py              [Python module source file]
#|
#|          This file defines a Python module that provides a facility
#|      for continually (10x a second) broadcasting the local host's
#|      IP address on the broadcast address of the local network (which
#|      is normally 255.255.255.255) via UDP datagrams with the format:
#|
#|          "COSMICi_server host=xxx.xxx.xxx.xxx(EOT)"
#|
#|      where xxx.xxx.xxx.xxx is the main IP address of the network
#|      interface on which the server app will be listening (at port
#|      COSMO=26766) for the initial 'main' connections from nodes in
#|      the sensor network.  "(EOT)" here is the ASCII "end of trans-
#|      mission" character, used here to delimit the end of the
#|      message.
#|
#|          NOTE: The implementation of part of this module is very
#|      similar to heart.py; it might make sense to eventually define
#|      a new class that abstracts the common functionality of both
#|      into a new module, called something like "repeater", that they
#|      then can both just inherit from.  A repeater would be any
#|      thread that just executes some predefined function at periodic
#|      intervals.
#|
#|      REVISION HISTORY:
#|          v0.1, 2/5/12 (MPF) - Initial version.  Got it working at home.
#|          v0.2, 2/7/12 (MPF) - Minor tweaks while testing in lab.
#|          v0.3, 2/9/12 (MPF) - Turn broadcast rate up from 1 Hz to 10 Hz.
#|                                  Decrease active interval from 10 sec. to 5 sec.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # System includes.

import  time            # Used for the sleep() function.
from socket import *    # Low-level socket interface.
import  threading       # Used for RLock, etc.

    # User includes.

from logmaster import *   # Custom logging class, also defines ThreadActor.
    # - The broadcaster object will be (an instance of a subclass of)
    #   ThreadActor. (Making it a full-fledged Worker object would be overkill.)

import  sitedefs    # Defines MY_IP.
import  flag        # Used for interaction between broadcaster & other threads.
import  ports       # Defines special port numbers, DISCO_PORT in our case.

    #|=====================================================================
    #|
    #|      Symbol exports.                             [code section]
    #|
    #|          These names will get copied to any module that
    #|          does "from broadcaster import *".
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

__all__ = [
    'SECS_BTWN_MSGS',   # Global; how many seconds to pause between broadcasts.
    'Broadcaster',      # Main class we define
    'theBroadcaster',   # The global Broadcaster object we create
    ]

    #|=====================================================================
    #|
    #|      Module globals.                             [code section]
    #|
    #|          Defines global variables defined in/used by/
    #|          associated with the present module.  NOTE: Care
    #|          must be taken when accessing these globals from
    #|          external modules; importing the names only creates
    #|          a COPY of the module's global variable; subsequently
    #|          changing the copy does NOT change the original.
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        # Public globals.  These names get exported to other modules.

global SECS_BTWN_MSGS, theBroadcaster

#SECS_BTWN_MSGS = 1      # By default, broadcast server address once a second.
SECS_BTWN_MSGS = 0.1     # By default, broadcast server address 10x a second.

theBroadcaster = None
    # - Global Broadcaster instance does not exist yet at module load time.

        # Private globals.  These names are only intended to be used
        # internally within this module.

logger = getLogger(appName + '.bcast')    # This module's logging channel.

#_BCAST_ADDR = ("255.255.255.255", 0)     # Address for broadcasting to local network
_BCAST_ADDR = ("<broadcast>", 0)

_MSG_FMT_STR = "COSMICi,SRVR_IP=%s"  # Format string for broadcast message.
#_MSG_FMT_STR = "COSMICi_server host=%s"  # Format string for broadcast message.

    #|---------------------------------------------------------------------
    #|
    #|      Broadcaster                         [module public class]
    #|
    #|          An instance of class Broadcaster is a thread
    #|          that does one thing only:  Periodically (by
    #|          default once a second) it broadcasts a message
    #|          to the local network's broadcast address that
    #|          announces the IP address of our main server.
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

class   Broadcaster(ThreadActor):       # A thread with extra logging capabilities.

        #|----------------------------------------------------------------------
        #|
        #|      Class variables.                [section of class definition]
        #|
        #|          These variables are attributes of the overall
        #|          class Broadcaster, but are also accessible from
        #|          within its instances.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    defaultRole = 'bcaster'
        # - Subclasses of ThreadActor are supposed to override this class
        #   variable to determine how the thread's role gets reported in
        #   log entries.

    defSecsBtwMsgs = SECS_BTWN_MSGS     # Class variable: Default # of secs between messages.

        #|----------------------------------------------------------------------
        #|
        #|      Instance variables.             [section of class definition]
        #|
        #|          Instances of class Broadcaster have the following
        #|          attributes (data members, instance variables):
        #|
        #|          Public instance variables:
        #|
        #|              .lock [threading.RLock] -
        #|
        #|                  Reentrant mutex lock for thread-safely
        #|                  guarding modification of the instance.
        #|
        #|              .secsBtwMsgs [non-negative number] -
        #|
        #|                  Number of seconds to pause after each
        #|                  broadcast message is sent before the
        #|                  next one is sent.
        #|
        #|              .pauseAt [float]
        #|
        #|                  A time (in seconds since the epoch) at
        #|                  which the broadcaster should automatically
        #|                  pause its broadcast (or None if it should
        #|                  continue indefinitely.
        #|
        #|              .pause [flag.Flag] -
        #|      
        #|                  This flag may be raised by other threads
        #|                  who want the broadcaster to temporarily
        #|                  stop broadcasting.
        #|
        #|              .paused [flag.Flag] -
        #|
        #|                  The broadcaster raises this flag to
        #|                  inform other threads that it has stopped
        #|                  broadcasting temporarily.
        #|
        #|          Private instance variables:
        #|
        #|              ._sock [socket socket] -
        #|
        #|                  The socket we use to transmit broadcast
        #|                  datagram (UDP) packets.
        #|
        #|              ._msg [bytes] -
        #|
        #|                  The message packet (sequence of bytes)
        #|                  that we will broadcast each time.
        #|
        #|----------------------------------------------------------------------

        #|======================================================================
        #|
        #|      Instance methods.               [section of class definition]
        #|
        #|          The following is a list of all instance methods
        #|          defined for members of class Broadcaster:
        #|
        #|          Public instance methods:
        #|
        #|              .__init__() - Instance initializer. Starts thread.
        #|              .run() - Main body of thread.
        #|              .suspend() - Pause the broadcast temporarily.
        #|              .resume() - Resume the broadcast.
        #|              .end() - End the broadcast.
        #|
        #|          Private instance methods:
        #|
        #|              ._openSocket() - Opens a socket for sending broadcasts.
        #|              ._doBroadcast() - Send the broadcast announcement once.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #|----------------------------------------------------------------------
        #|
        #|      Broadcaster.__init__()                [special instance method]
        #|
        #|          Initializer for new instances of class Broadcaster.
        #|
        #|          If the optional argument <period> is provided, it
        #|          sets the time between broadcasts in seconds;
        #|          otherwise, the period is taken from the value of
        #|          the class variable .defSecsBtwMsgs at the time the
        #|          new instance is created.
        #|
        #|          Note that at the time this method is called, the
        #|          new thread has not yet been started.  It causes 
        #|          the new thread to start running immediately.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def __init__(inst, initiallyPaused=False, period=None, socket=None, *args, **kargs):
        
        global theBroadcaster       # We'll overwrite it later.

            # If the <period> argument is unspecified or None, then
            # use the class variable as its default value instead.

        if None == period:  period = inst.defSecsBtwMsgs

            # Diagnostic output.

        logger.info("__init__(): Begin broadcasting server address at %d-second intervals..." % period)

            # Copy this object to the module global.  (We only expect
            # there will be one broadcaster in the whole application.)
            # (We could do error-checking here and complain if the
            # global's already been assigned a value other then "None".)

        theBroadcaster = inst

            # Create the re-entrant mutex lock which will guard
            # multithreaded access to this instance's state.

        inst.lock = threading.RLock()

        with inst.lock:

                # Initialize misc. instance variables.
            
            inst.secsBtwMsgs = period       # Remember broadcast interval.
            inst.pauseAt = None             # Initially, no preprogrammed pause time.

                # Create our control/status flags.

            inst.pause  =   flag.Flag(lock=inst.lock)   # Should broadcasting pause?
            inst.paused =   flag.Flag(lock=inst.lock)   # Is broadcasting paused?
            inst.ended  =   flag.Flag(lock=inst.lock)   # Has broadcaster terminated?

                # Create the network socket for sending broadcasts.
                # (Unless an existing socket to use is being passed in.)

            if socket == None:
                inst._openSocket()
            else:
                inst._sock = socket

                # Compose the message packet that we will send in each broadcast.

            inst._msg = bytes(_MSG_FMT_STR % sitedefs.MY_IP, 'ascii')

                # Complete ThreadActor initialization.

            ThreadActor.__init__(inst, *args, **kargs)

                # If we were asked to start the Broadcaster in the paused state, do so.

            if initiallyPaused:
                inst.pause.rise()   # Can't use .suspend() method b/c thread not running yet.

                # Finally, start the new Broadcaster thread running.
            
            inst.start()    

        #|----------------------------------------------------------------------
        #|
        #|      Broadcaster.run()                     [public instance method]
        #|
        #|          Broadcaster, being a subclasses of threading.thread,
        #|          must override this method to provide the main code
        #|          of the thread.  In our case, it does the work of
        #|          repeatedly broadcasting the server's IP address.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def run(self):
        with self.lock:
            try:                # Make sure to run finally clause on exit.
                while True:         # Indefinitely,
                    
                    if self.pauseAt != None and time.time() > self.pauseAt:
                        self.pause.rise()               # Pause ourselves.

                        # The following implements a preprogrammed
                        # delay that can also be interrupted by an
                        # immediate request (e.g., a request to pause).
                        # (More generally, if this were a Worker thread,
                        # the request could be anything, including a
                        # request to terminate the thread.)  For now,
                        # a request to terminate is implemented by
                        # requesting pause again while already paused.
                        
                        # Wait till we are told to pause, but do not
                        # wait any more than the number of seconds
                        # that there's supposed to be between
                        # broadcasts.

                    pause = self.pause.wait(timeout = self.secsBtwMsgs)
                        #-> Return value indicates whether pause flag was raised.

                    if pause:   # If we were actually asked to pause,
                        logger.info("Broadcaster.run():  Broadcast is pausing.")
                        self.paused.rise()  # Announce we are pausing.
                            # Wait indefinitely for the 'pause' flag to be
                            # touched (in any way) a second time.
                        self.pause.waitTouch()
                        if self.pause:      # If the pause flag is still up,
                                # then it was 'waved' (raised while raised), which
                                # means pause forever, or die.
                            return              # Do finally clause & exit thread.
                            # Otherwise, pause flag was lowered - we can resume.
                        logger.info("Broadcaster.run():  Broadcast is resuming.")
                        self.paused.fall()  # Announce we're no longer paused.
                            # Now we just go back to the start of the loop.
                    #<- end if pause

                    if not self.pause:       # If we weren't just asked to pause, 
                        self._doBroadcast()     # Send the broadcast announcement.

                    # If we get here, it means the pause flag was not
                    # raised, and instead we just timed out of the .wait().
                    # So, just go back up to the top of the loop & do the
                    # broadcast again.

                # If the main loop exits, whether due to an .end() call or
                # just an uncaught exception, announce the broadcaster has died.
            finally:
                logger.info("Broadcaster.run(): Broadcaster is terminating.")
                self.ended.rise()   # Raise flag announcing broadcaster terminated.

        #|---------------------------------------------------------------------------
        #|
        #|      Broadcaster.suspend()                       [public instance method]
        #|
        #|          Asks the broadcaster to please suspend its broadcasting
        #|          activity temporarily.  When this routine returns, the
        #|          broadcaster has paused (although another thread could
        #|          immediately restart it, if it's not still locked).
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def suspend(inst):
        with inst.lock:
            if inst.ended:
                logger.warn("Broadcaster.pause(): Can't pause the broadcast, because it's already been terminated.  Ignoring request.")
                return
            if inst.paused:
                logger.warn("Broadcaster.pause(): Pausing the broadcaster while it's already paused would terminate it.  Ignoring request.")
                return
            inst.pause.rise()   # Ask the broadcaster to pause.
            inst.paused.wait()  # Wait for it to actually pause.


        #|-------------------------------------------------------------------------
        #|  
        #|      Broadcaster.resume()                    [public instance method]
        #|
        #|          If the broadcaster is paused, start it broadcasting
        #|          again.  When this returns, the broadcast has resumed.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            
    def resume(inst):
        with inst.lock:
            if inst.ended:
                logger.warn("Broadcaster.resume(): Can't resume broadcast b/c broadcaster has terminated.  Ignoring request.")
                return
            if not inst.paused:
                logger.info("Broadcaster.resume(): Can't resume broadcast b/c it isn't paused.  Ignoring request.")
                return
            inst.pause.fall()       # Take down the pause flag.
            inst.paused.waitDown()  # Wait for the broadcast to no longer be paused.


        #|-----------------------------------------------------------------------------------
        #|
        #|      Broadcaster.end()
        #|
        #|          Tells the broadcaster to stop broadcasting and permanently
        #|          cease operation.  Once ended, the broadcaster cannot be
        #|          re-started.  (Causes the broadcaster thread to terminate.)
        #|
        #|      EXAMPLE USAGE:
        #|
        #|          foxNews = Broadcaster()
        #|          ...
        #|          foxNews.end()   # Die forever, and never be heard from again.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            
    def end(inst):
        with inst.lock:
            if inst.ended:
                logger.warn("Broadcaster.die(): Broadcaster can't end b/c it's already terminated.  Ignoring request.")
                return
            if not inst.paused:
                inst.pause()    # First, pause the broadcaster.
            inst.pause.rise()   # Pause it again while it's already paused - this kills it.
            inst.ended.wait()   # Wait for it to die.
            inst.join()         # Wait further for the broadcaster thread to actually exit.


        #|-------------------------------------------------------------------------------------
        #|
        #|      Broadcaster._openSocket()                           [private instance method]
        #|
        #|          Creates and opens a socket for the purpose of sending our
        #|          broadcast announcement.  The socket stays open until the
        #|          broadcaster is terminated.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _openSocket(inst):

                # Create a new socket, for the Internet address family,
                # of the Datagram type.
        
            inst._sock = socket(AF_INET, SOCK_DGRAM)

                # Set the socket option, at the socket layer, to
                # create broadcast output, no value arg needed.
            
            inst._sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

        #|-------------------------------------------------------------------------------------
        #|
        #|      Broadcaster._doBroadcast()                          [private instance method]
        #|
        #|          Sends one UDP datagram packet in the following format
        #|          to the local network's broadcast address:
        #|
        #|              "COSMICi_server host=xxx.xxx.xxx.xxx(EOT)"
        #|
        #|          where the xxx... is the local host's IP address (i.e.,
        #|          the address of its default network interface).
        #|              After sending the message, if it is past the time
        #|          at which the broadcast was programmed to pause, then
        #|          pause it.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    def _doBroadcast(self):
        rc = self._sock.sendto(self._msg, _BCAST_ADDR)
        logger.debug("Sent message [%s] to addr %s -> %s" % (self._msg.decode(), str(_BCAST_ADDR), str(rc)))


class DiscoveryService(ThreadActor):
    
    defaultRole = "discsvc"
    
    def __init__(inst, *args, **kwargs):

            # Create a socket capable of receiving broadcast packets.
            
        inst._sock = socket(AF_INET, SOCK_DGRAM)    # Create a datagram (i.e. UDP) IP socket.
        inst._sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)  # Is this necessary to receive broadcast packets?
        inst._sock.bind(('', ports.DISCO_PORT))    # Receive on IP INADDR_ANY, messages for socket DISCO=34726

# Scraps of stuff I tried earlier that didn't work...
#        inst._sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # Since other sockets on system may receive broadcast packets too.
#        inst._sock.bind(('<broadcast>', 53005))
#        inst._sock.bind(('192.168.28.255', 12345))

            # Create a broadcaster that is initially paused (until we receive
            # the first discovery request).
        
        inst.broadcaster = Broadcaster(initiallyPaused=True)

            # Dispatch to our superclass's initializer to complete instance initialization.
        ThreadActor.__init__(inst, *args, **kwargs)

            # Go ahead and start running the discovery service immediately upon initialization.
        inst.start()

    def run(self):
        while True:
            #buf = bytearray(128)
            #(nbytes, addr) = self._sock.recvfrom_into(buf)    # Receive a broadcast datagram up to 128 bytes long.
            data = self._sock.recv(128)                         # Receive a data packet at most 128 bytes long
            msg = data.decode() # Decode it as an ASCII string.
            logger.info("Received message [%s]." % msg)
            if msg == 'COSMICi,REQ_SRVR_IP':
                #logger.info("DiscoveryService.run(): Discovery request received; enabling IP broadcast for 10 seconds.")
                logger.normal("Broadcasting server's IP address in response to a discovery request...")
                self.broadcaster.pauseAt = time.time() + 5      # Pause broadcast in 5 seconds.
                self.broadcaster.resume()                        # Resume broadcast (if paused).
        

#|^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#|      END FILE:   broadcaster.py
#|==============================================================================

