#pragma once

#include <stddef.h>
#include <stdint.h>

#include <vector>

#include "action.h"

namespace nuxiva_node {

struct RelayChange {
    uint8_t channel;
    bool on;
};

class RelayBank {
public:
    RelayBank(uint8_t count, uint32_t max_on_ms);
    bool apply(const Action& action, uint32_t now_ms);
    void tick(uint32_t now_ms);
    void failsafe();
    bool is_on(uint8_t channel) const;
    uint8_t count() const { return count_; }
    std::vector<RelayChange> take_changes();

private:
    struct Slot {
        bool on = false;
        bool timed = false;
        uint32_t deadline = 0;
    };

    void set(uint8_t channel, bool on, bool timed, uint32_t deadline);

    uint8_t count_;
    uint32_t max_on_ms_;
    Slot slots_[MAX_RELAYS];
    std::vector<RelayChange> changes_;
};

}
