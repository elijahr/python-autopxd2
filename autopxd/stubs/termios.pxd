# autopxd/stubs/termios.pxd
#
# Cython declarations for <termios.h>
# Source: POSIX.1-2017 (IEEE Std 1003.1)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when termios.h is included.

cdef extern from "<termios.h>":
    ctypedef unsigned int tcflag_t
    ctypedef unsigned char cc_t
    ctypedef unsigned int speed_t

    enum: NCCS

    cdef struct termios:
        tcflag_t c_iflag
        tcflag_t c_oflag
        tcflag_t c_cflag
        tcflag_t c_lflag
        cc_t c_cc[20]  # NCCS is typically 20

    # Functions
    int tcgetattr(int fd, termios *termios_p)
    int tcsetattr(int fd, int optional_actions, const termios *termios_p)
    int tcsendbreak(int fd, int duration)
    int tcdrain(int fd)
    int tcflush(int fd, int queue_selector)
    int tcflow(int fd, int action)

    speed_t cfgetispeed(const termios *termios_p)
    speed_t cfgetospeed(const termios *termios_p)
    int cfsetispeed(termios *termios_p, speed_t speed)
    int cfsetospeed(termios *termios_p, speed_t speed)

    # Constants
    enum:
        TCSANOW
        TCSADRAIN
        TCSAFLUSH
