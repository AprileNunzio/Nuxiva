#include "action.h"

#include <ArduinoJson.h>

namespace nuxiva_node {

namespace {

constexpr uint32_t MAX_ON_REQUEST_MS = 24UL * 3600UL * 1000UL;

}

bool parse_command(const std::string& name, Action& out) {
    out = Action();
    if (name == "identify") {
        out.kind = ActionKind::Identify;
    } else if (name == "restart") {
        out.kind = ActionKind::Restart;
    } else if (name == "update") {
        out.kind = ActionKind::Update;
    } else {
        return false;
    }
    return true;
}

bool parse_action(const std::string& json, Action& out) {
    out = Action();
    if (json.empty() || json.size() > MAX_ACTION_BYTES) {
        return false;
    }
    JsonDocument doc;
    if (deserializeJson(doc, json) != DeserializationError::Ok || !doc.is<JsonObject>()) {
        return false;
    }
    const std::string type = doc["type"] | "";
    if (type != "relay") {
        return parse_command(type, out);
    }
    if (!doc["channel"].is<int>()) {
        return false;
    }
    const int channel = doc["channel"].as<int>();
    if (channel < 0 || channel >= MAX_RELAYS) {
        return false;
    }
    const std::string state = doc["state"] | "";
    Action action;
    action.kind = ActionKind::Relay;
    action.channel = static_cast<uint8_t>(channel);
    const bool has_ms = doc["ms"].is<long>();
    const long ms = has_ms ? doc["ms"].as<long>() : 0;
    if (state == "off") {
        action.mode = RelayMode::Off;
    } else if (state == "on") {
        action.mode = RelayMode::On;
        if (has_ms) {
            if (ms < 0 || static_cast<unsigned long>(ms) > MAX_ON_REQUEST_MS) {
                return false;
            }
            action.duration_ms = static_cast<uint32_t>(ms);
        }
    } else if (state == "pulse") {
        if (!has_ms || ms < static_cast<long>(MIN_PULSE_MS) || ms > static_cast<long>(MAX_PULSE_MS)) {
            return false;
        }
        action.mode = RelayMode::Pulse;
        action.duration_ms = static_cast<uint32_t>(ms);
    } else {
        return false;
    }
    out = action;
    return true;
}

}
