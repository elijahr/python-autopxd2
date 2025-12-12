#pragma once
#include "feature_a.h"

typedef struct PointC {
    PointA base;
    double z;
} PointC;

double distance_c(PointC* p);
