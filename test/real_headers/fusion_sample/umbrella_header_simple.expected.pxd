cdef extern from "umbrella_header_simple.h":

    ctypedef struct PointA:
        double x
        double y

    int process_a(PointA* p)

    ctypedef struct PointB:
        int id
        char name[32]

    void process_b(PointB* p)

    ctypedef struct PointC:
        PointA base
        double z

    double distance_c(PointC* p)
