#|=============================================================================
#|
#|      FILE:   ports.py                    [Python module source code]
#|
#|      SYNOPSIS:
#|
#|          The purpose of this module is simply to define
#|          some easy-to-remember constants naming the port
#|          numbers used by this application.
#|
#|      SYSTEM CONTEXT:
#|
#|          This file is part of the central server
#|          application for the COSMICi project.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

    # Names exported from this package.

__all__ = [     'COSMO_PORT',           # Global constant port numbers.
                'LASER_PORT',
                'MESON_PORT',
                'DISCO_PORT'    ]

    # Global declaration.

global      COSMO_PORT, LASER_PORT, MESON_PORT

    #|===========================================================
    #|   Port numbers.                       [global constants]
    #|
    #|       Define some handy global port numbers based on
    #|       easy-to-remember touch-tone mnemonics.
    #|
    #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

        #|-----------------------------------------------------------------
        #|
        #|      COSMO_PORT                          [global constant]
        #|
        #|          This is the main port on which we listen
        #|          for the main (initial) connection from
        #|          each remote node in the local sensor net.
        #|          We process server commands sent to it.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    
COSMO_PORT = 26766


        #|-------------------------------------------------------------------
        #|
        #|      LASER_PORT                              [global constant]
        #|
        #|          We listen at this port number (and subsequent
        #|          ones) for the AUXIO (STDIO replacement) stream
        #|          from each remote node (used for diagnostics &
        #|          user interaction with the remote command
        #|          processor).  This is the base port number (for
        #|          node #0), the node number gets added to it to
        #|          find the port number to be used by other nodes.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

LASER_PORT = 52737      # Use this port and subsequent ones for bridged AUXIO connections to the UWscript.


        #|-------------------------------------------------------------------
        #|
        #|      MESON_PORT                              [global constant]
        #|
        #|          We listen at this port number (and subsequent
        #|          ones) for the bridged UART data stream from
        #|          each remote node.  This is the base port number
        #|          (for node #0), the node number gets added to it
        #|          to find the port number for other nodes.
        #|
        #|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

MESON_PORT = 63766      # Use this port and subsequent ones for bridged UART connections to the digitizer boards.

DISCO_PORT = 34726      # Use this port for server IP address discovery.

#|^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#|  END FILE:   ports.py
#|----------------------------------------------------------------------
