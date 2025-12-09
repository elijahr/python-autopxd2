// Simple C++ header for testing (no standard library dependencies)
#ifndef SIMPLE_CPP_HPP
#define SIMPLE_CPP_HPP

struct Point {
    int x;
    int y;
};

class Widget {
public:
    int width;
    int height;

    void resize(int w, int h);
    bool isValid() const;
};

int computeDistance(const Point& a, const Point& b);

#endif
