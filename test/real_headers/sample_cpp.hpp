// Sample C++ header for testing
#ifndef SAMPLE_CPP_HPP
#define SAMPLE_CPP_HPP

#include <cstdint>

namespace mylib {

enum class ErrorCode {
    Ok = 0,
    NotFound = 1,
    InvalidArg = 2
};

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

} // namespace mylib

#endif
