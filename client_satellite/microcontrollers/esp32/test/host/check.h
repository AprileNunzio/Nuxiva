#pragma once

#include <stdio.h>

namespace check {

inline int& failures() {
    static int count = 0;
    return count;
}

inline int& total() {
    static int count = 0;
    return count;
}

}

#define CHECK(expr)                                                                   \
    do {                                                                              \
        ++check::total();                                                             \
        if (!(expr)) {                                                                \
            ++check::failures();                                                      \
            fprintf(stderr, "FAIL %s:%d  %s\n", __FILE__, __LINE__, #expr);           \
        }                                                                             \
    } while (0)

#define CHECK_EQ(a, b)                                                                \
    do {                                                                              \
        ++check::total();                                                             \
        if (!((a) == (b))) {                                                          \
            ++check::failures();                                                      \
            fprintf(stderr, "FAIL %s:%d  %s == %s\n", __FILE__, __LINE__, #a, #b);    \
        }                                                                             \
    } while (0)
