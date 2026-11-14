#include "relay_io.h"

#include <Arduino.h>

#include "settings.h"

namespace nuxiva_hw {

namespace {

constexpr uint8_t PINS[] = {NUXIVA_RELAY_PIN_LIST};
constexpr uint8_t COUNT = sizeof(PINS) / sizeof(PINS[0]);

uint8_t level(bool on) {
    const bool high = NUXIVA_RELAY_ACTIVE_LOW ? !on : on;
    return high ? HIGH : LOW;
}

}

uint8_t relay_count() {
    return COUNT > nuxiva_node::MAX_RELAYS ? nuxiva_node::MAX_RELAYS : COUNT;
}

void relay_init() {
    for (uint8_t i = 0; i < relay_count(); ++i) {
        digitalWrite(PINS[i], level(false));
        pinMode(PINS[i], OUTPUT);
        digitalWrite(PINS[i], level(false));
    }
}

void relay_write(const nuxiva_node::RelayChange& change) {
    if (change.channel < relay_count()) {
        digitalWrite(PINS[change.channel], level(change.on));
    }
}

}
