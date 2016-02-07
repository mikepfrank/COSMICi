# earth_coords.py
#
#   For coordinates relative to Earth's surface,
#   in terms of latitude, longitude, and altitude.
#   All stored as floats.
#
#   E.g., the GPS antenna in our window in the APCR-DRDL lab is at:
#       latitude = 30.428236 degrees (N)
#       longitude = -84.285 degrees (W)
#       altitude = 40 meters (above sea level, estimated)
#
#   Note that lat and long are stored as simple float degrees.
#   To get minutes or seconds, use the appropriate functions.

__all__ = ['EarthCoords']

class EarthCoords:

    def __init__(this, lat, long, alt):

        this.lat   = lat    # Store latitude in floating-point degrees.
        this.long  = long   # Store longitude in floating-point degrees.
        this.alt   = alt    # Store altitude in floating-point meters above sea level.

    # Convert floating-point degrees to a pair of integer degrees
    # and floating-point minutes.  (You can also cheat & use this
    # to convert from floating-point minutes to a pair of integer
    # minutes and floating-point seconds.)

def deg_to_degmin(degrees):

    intdeg = int(degrees)               # This isn't floor; it rounds towards 0.
    fracdeg = abs(degrees - intdeg)     # Fractional part, expressed as if positive.
    minutes = fracdeg*60
    
    return (intdeg, minutes)

    # Uses deg_to_degmin() twice to convert floating-point degrees
    # to integer degrees, integer minutes, floating-point seconds.
    # Returned as a triple.

def deg_to_degminsec(degrees):
    
    (intdeg, minutes) = deg_to_degmin(degrees)
    (intmin, seconds) = deg_to_degmin(minutes)

    return (intdeg, intmin, seconds)
