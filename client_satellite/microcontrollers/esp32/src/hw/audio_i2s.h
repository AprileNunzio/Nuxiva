#pragma once

#include <stddef.h>
#include <stdint.h>

#include "speech_gate.h"

namespace nuxiva_hw {

class AudioIn {
public:
    bool begin();
    void end();
    bool read_frame(int16_t* out, size_t samples, uint32_t timeout_ms);

private:
    nuxiva_node::DcBlocker blocker_;
    bool running_ = false;
};

}
