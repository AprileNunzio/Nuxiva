#include <stdio.h>

#include "RNG.h"

RNGClass::RNGClass() {}

RNGClass::~RNGClass() {}

void RNGClass::rand(uint8_t* data, size_t len) {
    FILE* source = fopen("/dev/urandom", "rb");
    if (source == nullptr) {
        return;
    }
    if (fread(data, 1, len, source) != len) {
        fclose(source);
        return;
    }
    fclose(source);
}

RNGClass RNG;
