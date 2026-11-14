#include "relay_bank.h"

namespace nuxiva_node {

RelayBank::RelayBank(uint8_t count, uint32_t max_on_ms)
    : count_(count > MAX_RELAYS ? MAX_RELAYS : count), max_on_ms_(max_on_ms == 0 ? 3600000UL : max_on_ms) {}

void RelayBank::set(uint8_t channel, bool on, bool timed, uint32_t deadline) {
    Slot& slot = slots_[channel];
    const bool changed = slot.on != on;
    slot.on = on;
    slot.timed = on && timed;
    slot.deadline = deadline;
    if (changed) {
        changes_.push_back({channel, on});
    }
}

bool RelayBank::apply(const Action& action, uint32_t now_ms) {
    if (action.kind != ActionKind::Relay || action.channel >= count_) {
        return false;
    }
    switch (action.mode) {
        case RelayMode::Off:
            set(action.channel, false, false, 0);
            return true;
        case RelayMode::Pulse:
            set(action.channel, true, true, now_ms + action.duration_ms);
            return true;
        case RelayMode::On: {
            const uint32_t limit = action.duration_ms == 0 || action.duration_ms > max_on_ms_ ? max_on_ms_ : action.duration_ms;
            set(action.channel, true, true, now_ms + limit);
            return true;
        }
    }
    return false;
}

void RelayBank::tick(uint32_t now_ms) {
    for (uint8_t i = 0; i < count_; ++i) {
        const Slot& slot = slots_[i];
        if (slot.on && slot.timed && static_cast<int32_t>(now_ms - slot.deadline) >= 0) {
            set(i, false, false, 0);
        }
    }
}

void RelayBank::failsafe() {
    for (uint8_t i = 0; i < count_; ++i) {
        set(i, false, false, 0);
    }
}

bool RelayBank::is_on(uint8_t channel) const {
    return channel < count_ && slots_[channel].on;
}

std::vector<RelayChange> RelayBank::take_changes() {
    std::vector<RelayChange> out;
    out.swap(changes_);
    return out;
}

}
