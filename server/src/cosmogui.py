#*****************************************************************************
#                               TOP OF FILE
#   cosmogui.py                                 [python module source code]
#
#       GUI elements specific to the COSMICi system.
#
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

import tkinter          #   setLogoImage()  uses    PhotoImage
import guiapp           #   setLogoImage()  uses    ambot(), guibot
#import COSMICi_server   #   setLogoImage()  uses    console
    #-> This is commented out b/c it didn't seem to work.  Not sure why.

__all__ = ['setLogoImage',  # used by COSMICi_server.main().
           'logoimage'      # export just in case other modules need it - of course, this is useless b/c it's not actually defined yet at import time.  :(
           ]

        #=========================================================
        #   setLogoImage()              [public module function]
        #
        #       Loads the COSMICi project logo from the file
        #       COSMICi-logo.ppm (binary portable pixmap file),
        #       and puts it in the main server console window,
        #       which must be passed in as an argument.
        #
        #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

def setLogoImage(console):
    global logoimage

        # Make sure we're in the guibot thread.

    if not guiapp.ambot():              # If not in the guibot thread,
        guiapp.guibot(setLogoImage)         # re-call this function in it.
        return                              # Work is done.

        # Create the TkInter image object for our logo.

    logoimage = tkinter.PhotoImage(file="images/COSMICi-logo.ppm")
            #-It was a real pain in the butt to create the ppm;
            # I compiled & used libpng and libpnm on the xserve.

        # Insert the image (like a large character of text)
        # on the console.
        
    console.image_create("endout", image=logoimage)

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   End cosmogui.py
#==============================================================================
