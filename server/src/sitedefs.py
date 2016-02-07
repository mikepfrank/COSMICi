#|==============================================================================
#|
#|      FILE:   sitedefs.py                         [Python module source]
#|
#|      SYNOPSIS:
#|
#|          This module provides site-specific definitions of key
#|          constants.  In particular, it hardcodes the server's IP
#|          address.  (Ideally, we should probably just look up the
#|          system's default interface instead, which will usually
#|          be right, but for now this is simpler.)
#|
#|          UPDATE 4/6/12:  At the moment, we actually do just query
#|          the default IP address on all machines except for the
#|          main COSMICI server in the lab.
#|
#|          This module now also provides a 2nd constant, namely
#|          the 3D Earth-relative coordinates of the GPS antenna,
#|          for purposes of setting up the POSHOLD mode correctly,
#|          so we can still get valid (& reasonably accurate) time
#|          values even when there is only one satellite in view.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # Imports.

import  utils           # We use utils.get_my_ip() to compute MY_IP at top level.
import  earth_coords    # Defines class EarthCoords

    # Exported names.
                                    # Used by:
__all__     =   [   'MY_IP', 'GPS_ANT_LOC'   ]       # mainserver.py, bridge.py

    #|=================================================================
    #|   Globals					[code section]
    #|
    #|       Declare and/or define various global variables and
    #|       constants.
    #|
    #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # Declare globals.

global  MY_IP, GPS_ANT_LOC

        #==========================================================
        #   Global constants.                   [code subsection]
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

            #|==================================================================
            #|
            #|      MY_IP                                       [global constant]
            #|
            #|          The IP address, on the sensor net's wireless network,
            #|          of the host that this server is running on.
            #|
            #|          NOTE: This is really only needed when the server has
            #|          more than one active network interface card, each with
            #|          its own IP address.  Otherwise, the utils.get_my_ip()
            #|          function can determine the IP address satisfactorily.
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # utils.get_my_ip() would work fine in this case (the machine has only 1 NIC)
    # but this assignment is still here as a piece of legacy code
    
if  utils.get_hostname() == 'COSMICi':     # Dell Precision T3400 on Mike's desk in APCR-DRDL lab.
    MY_IP = "192.168.0.2"       # The static private IP address that is assigned to the central
                                # server node in our wireless router's DHCP config.
                                
#elif  utils.get_hostname() == 'Linux-PC':   # This was the Acer, but it's now no longer 
#    MY_IP = "192.168.0.4"                   # in use as a server.

    # The below is commented out because get_my_ip() works fine on this machine instead.
#elif  utils.get_hostname() == 'Theo':    # Mike's home office desktop.
    #MY_IP = '192.168.0.102'   # This is Theo's IP address when using my router at home.

else:
    MY_IP = utils.get_my_ip()   # Would this work in the above cases too?  Need to test.

            #|=================================================================
            #|
            #|  GPS_ANT_LOC                             [global constant]
            #|
            #|      Location of this site's main GPS antenna, as an
            #|      EarthCoords object.  (Latitude in degrees North,
            #|      longitude in degrees East, altitude in meters.)
            #|
            #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

GPS_ANT_LOC = earth_coords.EarthCoords(30.428236, -84.285, 40)
    # - These are the estimated coordinates of the GPS antenna in
    #   the middle of the windowsill of the Westernmost window in
    #   the Astroparticle & Cosmic Radiation Detector Research &
    #   Development Laboratory, which is room 420 in the Frederick
    #   S. Humphries Science & Research Center, at 1515 S. Martin
    #   Luther King, Jr., Blvd., Tallahassee, FL, USA.

#GPS_ANT_LOC = earth_coords.EarthCoords(30.42, -84.3180555, 40)
    #   -   These are the approximate coordinates of the temporary
    #       location of the GPS antenna that we used during the
    #       Senior Design Fair on 4/5/12, just outside the door at
    #       the middle of the connector between buildings A&B at
    #       the College of Engineering, at 2525 Pottsdamer St.,
    #       Tallahassee, FL, USA.

#|^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#|      END FILE:   sitedefs.py
#|======================================================================================================
