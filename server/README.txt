|================================================================|
|                                                                |
|    FILE NAME:     README.txt               [documentation]     |
|                                                                |
|    IN FOLDER:                                                  |
|                                                                |
|         $(COSMICI_DEVELOPMENT_ROOT)/Server Code/               |
|                                                                |
|    SYSTEM CONTEXT:                                             |
|                                                                |
|         This file is part of the source code & documen-        |
|         tation file hierarchy for the Central Server           |
|         application, a software component of the COSMICi       |
|         system for doing distributed particle astronomy.       |
|                                                                |
|    DESCRIPTION:                                                |
|                                                                |
|         This is the top-level README file for the file         |
|         subhierarchy for the Central Server application        |
|         in the COSMICi System.  This file documents the        |
|         file hierarchy tree relating to the Central            |
|         Server subsystem.                                      |
|                                                                |
|    FILE FORMAT:                                                |
|                                                                |
|         * Encoding:         7-bit ASCII, plain text.           |
|         * Display using:    Fixed-width font.                  |
|         * Tab width:        5 characters                       |
|                                                                |
|    REVISION HISTORY:                                           |
|                                                                |
|         v0.1, 1/28/2012 (Michael P. Frank)                     |
|              - Initial version.                                |
|         v0.2, 1/29/2012 (MPF)                                  |
|              - Adding sections on platforms, startup, & use.   |
|         v0.3, 3/6/2012 (MPF)                                   |
|              - Added mention of new file startserver.bat.      |
|                                                                |
|    COPYRIGHT NOTICE:                                           |
|                                                                |
|         This file is copyright (C) 2011 by the                 |
|         Astroparticle & Cosmic Radiation Detector              |
|         Research & Development Laboratory (APCR-DRDL)          |
|         in the Department of Physics at Florida A&M            |
|         University (FAMU), Tallahassee, Florida, USA.          |
|         All rights reserved.                                   |
|                                                                |
|         The collection of all COSMICi related files,           |
|         as a whole, except for files that are reference        |
|         copies of documents supplied by outside vendors,       |
|         is also copyright (C) 2009-2011 by the APCR-DRDL       |
|         lab, all rights reserved.                              |
|                                                                |
|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv|


          README File For the COSMICi Central Server
          ==========================================

TABLE OF CONTENTS.
------------------
     1.  Folder name.
     2.  Folder locations.
     3.  Folder contents.
     4.  Platforms.
     5.  Server startup.
     6.  Server operation.
     

1.  FOLDER NAME.
----------------

     The top-level folder of all materials associated with the 
Central Server application is presently (as of this writing,
1/28/12) named "Server Code".  However, in the future, this may
be renamed to something more descriptive such as "Local_Server",
since this is the server associated with a single local COSMICi 
sensor network (with one CTU and one pulse-detector subsystem).  

     Note this application is separate from any higher-level 
servers for gathering data from multiple sites scattered over 
wide area networks which may be developed in the future.  The 
word "Code" in the folder name is somewhat inappropriate, since 
this folder contains not just the server code, but also 
associated documentation, analysis scripts, and archived data 
files.

     Also, please note that the present server does not yet 
function as a node in a peer-to-peer (P2P) network of sensor 
subnets, although this capability may be added in the future.  
At that point, the folder might be appropriately renamed to 
"P2P_Node" or something of that nature.


2.  FOLDER LOCATIONS.
---------------------

     Presently (1/28/12) during development, copies of this
folder (of various ages) exist in several locations:

     * As a shared folder on Dropbox, shared between
          all project developers (created by MPF).
          
     * As a local folder on various desktop computers
          in use by the primary developer (MPF).  Some of
          these locations may also contain other related 
          files.
          
          Examples of some of these older locations
          (note this is an incomplete list):
          
          - On Theo (Mike's home office desktop PC; a Dell
            Dimension 3000 running Windows XP Professional):
          
               -- On F:\ (232 GB external Seagate drive):
               
                    \My\Archives\organized\Work\FAMU\-
                    COSMICi\Central Server\ 
               
                         = Copy of 1/28/12, next to some folders of older code:
                              == old versions\old code\ - Last edited 2/3/11.
                              == Server Code 2\ - Last run 1/27/11; last edited 11/9/10.
               
                    \My\Archives\organized\s
                    
                         = Old backup copy,
                              Last edited 10/1/2009,
                              Last run 10/11/2009.
               
               -- On C:\ (80 GB internal hard drive):
               
                    \\THEO\Mike's Documents\Files\Current\-
                    Cosmic Ray's project\COSMICi Project\-
                    Software Development\Central Server\
               
                         = Last edited on 9/28/2009.
                         = Last run on 1/27/2011.
                         
                    \LOCAL\Work\FAMU\COSMICi\
                    
                         = Backup copy of 1/28/12.
          
     Generally, the Dropbox folder will be kept up-to-date
with the latest stable working copy of the code.  However,
certain older files that are no longer in use may not be 
included in the Dropbox folder currently, and may only exist
scattered on the hard drive(s) of MPF's various desktops.

     In the near future, we may move towards a Subversion or
other online repository to facilitate parallel development.
In the past, this was not necessary, since all previous
development work on this subsystem was done by a single 
developer (MPF).


3.   FOLDER CONTENTS.
---------------------

Presently (1/28/12), the contents of this folder are as follows:

     * README.txt (this file) - README file for central server.
     
     * startserver.bat - MS-DOS batch file that starts the server.
     
     * docs/ - Additional central server documentation.
     
          - Code Workshop/ - Slides presented by MPF to the students 
               at the server code workshop, Jan. 2012.
          
          - Communicator class hierarchy/ - Notes on method inheritance 
               in the Communicator class, etc.
     
     * src/ - Subfolder containing Python source code (.py) & compiled (.pyc) files.
     
          - conflicts/ - Conflicted versions of source files generated by Dropbox.
          
          - images/ - The application requires these files to exist when it starts up.
               = COSMICi-logo.ppm - Banner displayed in the main console window on startup.
               = purple-beam.gif - Line element at the bottom of each TikiTerm widget,
                    separating the input line from the output area.
                    
          - appdefs.{py,pyc}            - Shared application-specific definitions.
          - bridge.{py,pyc}             - Server class for generic data streams from nodes.
          - commands.{py,pyc}           - Parsing, dispatch & execution of server commands.
          - communicator.{py,pyc}       - Custom framework for multithreaded TCP servers.
          - COSMICi_server.{py,pyc}     - Main top-level module of server application.
          - cosmogui.{py,pyc}           - Application-specific GUI elements.
          - desque.{py,pyc}             - Double-ended synchronized queue class.
          - flag.{py,pyc}               - Waitable, checkable boolean state variables for concurrency.
          - guiapp.{py,pyc}             - Framework for multithreaded TkInter applications.
          - heart.{py,pyc}              - Generates server heartbeat events.
          - logmaster.{py,pyc}          - Customized logging facility.
          - mainserver.{py,pyc}         - Server class for initial command streams from nodes.
          - model.{py,pyc}              - Object-oriented proxy for sensor network components.
          - pinger.py                   - Module to ping nodes (incomplete, obsolete).
          - ports.{py,pyc}              - Definitions of port numbers used by applications.
          - sitedefs.{py,pyc}           - Site-specific definitions (IP addresses).
          - terminal.{py,pyc}           - Generic framework/factory for terminal widgets.
          - tikiterm.{py,pyc}           - A terminal widget based on the TkInter toolkit.
          - timestamp.{py,pyc}          - Coarse-grained (later also fine-grained) timestamps.
          - utils.{py,pyc}              - Miscellaneous (network-related) utility functions.
          - worklist.{py,pyc}           - Work queues facilitating inter-thread communication.
               
          (Others still to be added to this list.)

     * data/ - Archive of miscellaneous old data files.  Includes
          both raw logs/transcripts as well as some processed data,
          and some graphs derived from analysis.
          
          [TO DO: Document the more interesting subfolders.]
          
     * analysis/ - Code and results for data analysis.
     
          - Data Analysis/ - Miscellaneous data & graphs associated with
               data analysis.  This mostly relates to the characterization
               of GPS accuracy that we were working on in Spring 2011.
          
          - Scilab analysis scripts/ - 
          
               = anal-pulses.sce - Old analysis for server-side coincidence detection.
               = analysis.sce - One-time calculation of coincidence probability.


4.   PLATFORMS
--------------

As of this writing (1/29/12), the server app has only ever been 
confirmed to work under Python 3.1.1 on two OS platforms:

     Microsoft Windows Vista Professional
     Microsoft Windows XP Professional
     
Theoretically, Python will run on any modern Windows, Mac or Linux
platform, but operation on other platforms has not yet been thor-
oughly tested.  A preliminary test on an older iMac failed to work.
The cause of the problem has not yet been diagnosed.

     The server also still needs to be tested under newer versions 
of Python itself.  On 1/29/12, I (MPF) tested it under 3.2.2 and it
did NOT work (the first error was logging-related).  So some porting 
work would be necessary to bring it up to 3.2.  It works fine in 
3.1.4, however (so far).


5.   SERVER STARTUP
-------------------

To start the server, simply execute the main file, COSMICi_server.py.
Python automatically compiles .py files to produce the corresponding
.pyc files as needed, so the user does not need to worry about that
process.

     A window system (Windows on a Microsoft machine, or the X Window
System on Linux, or the Cocoa UI on MacOS X) must be running in order
for the server to start, because it requires the ability to open up
interactive GUI windows.  

     When the server starts up, the first window opened is the Windows
console (80x24 text window), which is used as the Python console, and 
on which the logmaster module displays several diagnostic messages while 
it is configuring the logging system.  After this, this window is no 
longer used (except briefly during server shutdown) and it may be 
minimized.  However, DO NOT CLOSE this window or you will kill the 
server - in fact, this is the recommended way to shut down the 
server at present.

     The second window opened is a TikiTerm top-level window titled
"COSMICi Server Console [Main Window]".  Standard I/O (including 
standard error) from the Python program are redirected to this window.
Various diagnostic messages as well as normal server status messages
(basically, all condition reports at or above warning level) are 
displayed in this window.  Python errors will also appear in this 
window (due to the redirection of stderr).  The first thing displayed
in a window is a graphical banner image comprising the COSMICi project
logo.  Next is a normal-level log message "Welcome to the COSMICi
central server program."

     On a given host computer (really, on a given network interface),
only one instance of the server application can run at a time, since
it grabs the COSMO (26766) TCP port to listen for incoming connections
from nodes.  If you have problems starting, it may mean that a previous 
invocation of the server process is not yet completely dead, and is a 
"zombie" process still sitting on the port.  To solve this problem, 
bring up a list of all processes on your system (e.g. with the Windows 
Task Manager) and manually kill off any lingering python processes.
This will (after a few seconds) free up the ports and allow you to
start a new instance of the server.


6.  SERVER OPERATION
--------------------

     The server operation is primarily reactive; that is, in normal
circumstances after being started up, all it does is sit and wait for 
connections from sensor nodes, that is, from those nodes' Wi-Fi modules.

     In the current system design, those Wi-Fi modules are Laird EZURiO 
modules running a custom autorun script written in the UWScript scripting
language; this script will (if configured correctly for the present site)
automatically initiate several connections to the server shortly after it is 
powered up (usually within 30 seconds or less).

     The first connection made by all nodes is always a connection to our 
main TCP server object which is listening at port COSMO (port #26,766).
When this connection is made, the server pops up a new TikiTerm terminal 
window displaying all data sent and received over the connection; this window
has a title like "Main Server Connection #0 from 192.168.0.8:49646."  The
server is expecting server commands to come in via this connection; it watches
for, parses, and executes them as they occur.

     The first message sent by the Wi-Fi script is always a powerup message,
with a format like the following example:

          POWERED_ON 1 192.168.0.8 00:1E:3D:33:FE:0D
          
The space-separated fields here are:

     1. The node's ID #, which in this case is 1.  In general, node IDs can
          be any non-negative integer.  Currently, we only use two IDs, by
          convention: Node 0 for the CTU, and node 1 for the shower detector.
          
     2. The node's IP address, assigned to it by the local access point's
          DHCP server.  In the example above, the address is 192.168.0.8, in
          a private IP address space.
          
     3. The node's MAC (medium access control) layer address, which is hard-
          coded into the Wi-Fi module's firmware at the time of manufacture
          (although it could be modified by the script if desired, iirc).

The server's response to this message is to associate this connection with
the particular node ID, and create an internal object model of/proxy for the
node, and remember the above information associated with the node.  It also 
creates two new "bridge" servers to listen for "AUXIO" and "UART bridge" 
connections from this node.
     
00000000001111111111222222222233333333334444444444555555555566666666667777777777
01234567890123456789012345678901234567890123456789012345678901234567890123456789
