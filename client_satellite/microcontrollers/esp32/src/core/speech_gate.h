#pragma once

#include <stddef.h>
#include <stdint.h>

#include <vector>

namespace nuxiva_node {

struct GateConfig {
    size_t frame_samples = 320;
    float gate_db = 9.0f;
    float min_floor_db = -80.0f;
    uint32_t hangover_frames = 25;
    uint32_t preroll_frames = 15;
    uint32_t max_utterance_frames = 1500;
};

enum class GateEvent { Idle, Start, Speech, End };

class DcBlocker {
public:
    int16_t process(int32_t sample);

private:
    float previous_in_ = 0.0f;
    float previous_out_ = 0.0f;
};

class SpeechGate {
public:
    explicit SpeechGate(const GateConfig& config = GateConfig());
    GateEvent feed(const int16_t* frame, size_t length);
    std::vector<int16_t> take_preroll();
    float floor_db() const { return floor_db_; }
    void reset();

private:
    GateConfig config_;
    std::vector<int16_t> ring_;
    size_t ring_head_ = 0;
    size_t ring_filled_ = 0;
    float floor_db_ = -80.0f;
    bool primed_ = false;
    bool active_ = false;
    uint32_t silent_frames_ = 0;
    uint32_t active_frames_ = 0;
};

float frame_energy_db(const int16_t* frame, size_t length);

}
