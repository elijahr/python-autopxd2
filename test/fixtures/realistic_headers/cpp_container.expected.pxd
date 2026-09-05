cdef extern from "cpp_container.hpp":

    cdef struct Point:
        int x
        int y

    cdef cppclass Vector2D:
        double x
        double y
        double magnitude() const
        void normalize()
        Vector2D operator+(Vector2D& other) const
        Vector2D operator-(Vector2D& other) const
        double dot(Vector2D& other) const

    cdef cppclass Rectangle:
        Point origin
        int width
        int height
        int area() const
        bool contains(Point& p) const
        bool intersects(Rectangle& other) const

    Vector2D make_vector(double x, double y)

    Rectangle make_rectangle(int x, int y, int w, int h)

    double distance(Point& a, Point& b)

    double distance(Vector2D& a, Vector2D& b)
