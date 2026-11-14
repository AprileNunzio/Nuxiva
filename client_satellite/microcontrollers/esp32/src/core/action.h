#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>

namespace nuxiva_node {

constexpr size_t MAX_ACTION_BYTES = 512;
constexpr uint8_t MAX_RELAYS = 8;
constexpr uint32_t MIN_PULSE_MS = 50;
constexpr uint32_t MAX_PULSE_MS = 10000;

enum class ActionKind { None, Relay, Identify, Restart, Update };
enum class RelayMode { Off, On, Pulse };

struct Action {
    ActionKind kind = ActionKind::None;
    uint8_t channel = 0;
    RelayMode mode = RelayMode::Off;
    uint32_t duration_ms = 0;
};

bool parse_action(const std::string& json, Action& out);
bool parse_command(const std::string& name, Action& out);

}
