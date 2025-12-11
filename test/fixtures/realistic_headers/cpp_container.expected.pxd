cdef extern from "cpp_container.hpp":

    cdef struct Point:
        int x
        int y

    cdef cppclass Vector2D:
        double x
        double y
        double magnitude()
        void normalize()
        Vector2D operator+(const Vector2D & other)
        Vector2D operator-(const Vector2D & other)
        double dot(const Vector2D & other)

    cdef cppclass Rectangle:
        Point origin
        int width
        int height
        int area()
        bool contains(const Point & p)
        bool intersects(const Rectangle & other)

    Vector2D make_vector(double x, double y)

    Rectangle make_rectangle(int x, int y, int w, int h)

    double distance(const Point & a, const Point & b)
