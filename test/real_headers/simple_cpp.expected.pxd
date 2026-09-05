cdef extern from "simple_cpp.hpp":

    cdef struct Point:
        int x
        int y

    cdef cppclass Widget:
        int width
        int height
        void resize(int w, int h)
        bool isValid() const

    int computeDistance(Point& a, Point& b)
