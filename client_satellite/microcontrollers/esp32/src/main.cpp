#include <Arduino.h>

#include "hw/node.h"

void setup() {
    nuxiva_hw::node().setup();
}

void loop() {
    nuxiva_hw::node().loop();
}
