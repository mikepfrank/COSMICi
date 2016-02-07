#|******************************************************************************
#|
#|      FILE NAME:  nmea.py                     [python module source file]
#|
#|      DESCRIPTION:
#|          This file defines functions associated with processing
#|          of NMEA-formatted 'sentences' or message lines.
#|
#|vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

__all__ = ['BadChecksum',   # Exceptions
           'isNMEA',        # Functions.
           'getCRC',
           'calcCRC',
           'stripNMEA',
           'makeNMEA',
           ]

class BadChecksum(Exception): pass      # NMEA checksum doesn't match.

    # Given a string, is it potentially an NMEA-formatted sentence?

def isNMEA(line:str):
    return line != "" and line[0] == '$'

    # Given an NMEA-formatted sentence, return the two-nibble hex
    # checksum at the end of it, if present.  The value is returned
    # as an integer in the range 0-255.

def getCRC(sent:str):

    length = len(sent)  # Get the length of the string.
    
    if length < 3:      # Less than 3 characters?  Can't have a checksum.
        return None

    if sent[-3] != '*': # If 3rd character from end of string isn't an asterisk,
        return None     # then there's no checksum and we're done.

    last2 = sent[-2:]     # Get the last two characters of the string.

    return int(last2, 16)   # Convert to integer as base-16.

    # Calculate and return the NMEA CRC/checksum (xor of byte values)
    # of the given string (not already decorated with $*).

def calcCRC(bareStr:str):
    codes = bareStr.encode()    # Convert string to byte array.
    crc = 0                     # Initialize checksum to 0.
    for byte in codes:          # Go through array,
        crc ^= byte             # XOR'ing each byte into checksum.
    return crc                  # Return result.

    # Given a possible NMEA sentence, with or without a checksum
    # present, if the checksum is present then verify it (and
    # throw a BadChecksum exception if it doesn't match), and
    # return the "bare" string (without the '$', the '*', or the
    # checksum).
    #   The input is assumed to be a single line (containing no
    # line-end characters) with any initial/final whitespace
    # already stripped off.

def stripNMEA(line:str):

        # First, if the line doesn't begin with a dollar sign '$'
        # then it's not an NMEA sentence at all; just return it.

    if not isNMEA(line):
        return line

        # At this point we know that there's a dollar sign at the
        # start.  Let's go ahead and strip it off (we don't need
        # it any more.

    line = line[1:]   # All chars from 2nd to last.

        # OK, so at this point we know we have an NMEA-type
        # sentence, but with the '$' already stripped off.
        # Let's see if it has a CRC code ("*XX") at the end.

    crc = getCRC(line)

        # If it has no CRC code, then all we have to do is
        # return the line, which already has the '$' stripped.

    if crc == None:
        return line

        # OK, so at this point we have a CRC code, and a line
        # with the '$' stripped off the front.  We know the
        # last 3 characters are "*XX", so strip those off too.

    line = line[:-3]   # All but last 3 characters of string.

        # Now we have a "bare" line (with $* stuff stripped away).
        # Calculate its CRC value and compare it to the one given.
        # If they don't match, raise an exception.

    if calcCRC(line) != crc:
        raise BadChecksum       # Raise a "bad checksum" exception.

        # At this point the line is bare and we've verified that
        # the checksum matches.  Just return the bare line.

    return line

    # Given a string, return the NMEA sentence equivalent.
    # Include a checksum if and only if makeChecksum is true (default False).
    # Does not add any line-end character(s).

def makeNMEA(line:str, makeChecksum:bool=False):

    if makeChecksum:
        crcNum = calcCRC(line)
        crcStr = "*%02x" % crcNum
        line = line + crcStr

    return ("$%s" % line)
