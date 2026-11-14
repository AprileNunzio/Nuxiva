#include "serial_link.h"

#include <Arduino.h>

#include "provision.h"

namespace nuxiva_hw {

bool SerialLink::poll(std::string& line) {
    while (Serial.available() > 0) {
        const int c = Serial.read();
        if (c < 0) {
            break;
        }
        if (c == '\n' || c == '\r') {
            if (overflow_) {
                overflow_ = false;
                buffer_.clear();
                line = "{\"cmd\":\"overflow\"}";
                return true;
            }
            if (!buffer_.empty()) {
                line.swap(buffer_);
                buffer_.clear();
                return true;
            }
            continue;
        }
        if (buffer_.size() >= nuxiva_node::MAX_PROVISION_LINE) {
            overflow_ = true;
            continue;
        }
        buffer_.push_back(static_cast<char>(c));
    }
    return false;
}

void SerialLink::reply(const std::string& json) {
    Serial.write(reinterpret_cast<const uint8_t*>(json.data()), json.size());
    Serial.write('\n');
}

}
