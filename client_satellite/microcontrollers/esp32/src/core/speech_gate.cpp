#include "speech_gate.h"

#include <math.h>

namespace nuxiva_node {

namespace {

constexpr float FALL = 0.9f;
constexpr float RISE = 0.001f;
constexpr float DC_POLE = 0.995f;

}

float frame_energy_db(const int16_t* frame, size_t length) {
    if (frame == nullptr || length == 0) {
        return -100.0f;
    }
    double sum = 0.0;
    for (size_t i = 0; i < length; ++i) {
        const double v = static_cast<double>(frame[i]) / 32768.0;
        sum += v * v;
    }
    const double mean = sum / static_cast<double>(length);
    return static_cast<float>(10.0 * log10(mean + 1e-10));
}

int16_t DcBlocker::process(int32_t sample) {
    const float x = static_cast<float>(sample);
    const float y = x - previous_in_ + DC_POLE * previous_out_;
    previous_in_ = x;
    previous_out_ = y;
    float clamped = y;
    if (clamped > 32767.0f) {
        clamped = 32767.0f;
    } else if (clamped < -32768.0f) {
        clamped = -32768.0f;
    }
    return static_cast<int16_t>(clamped);
}

SpeechGate::SpeechGate(const GateConfig& config) : config_(config) {
    if (config_.frame_samples == 0) {
        config_.frame_samples = 320;
    }
    if (config_.preroll_frames == 0) {
        config_.preroll_frames = 1;
    }
    ring_.assign(config_.frame_samples * config_.preroll_frames, 0);
    floor_db_ = config_.min_floor_db;
}

void SpeechGate::reset() {
    ring_.assign(config_.frame_samples * config_.preroll_frames, 0);
    ring_head_ = 0;
    ring_filled_ = 0;
    floor_db_ = config_.min_floor_db;
    primed_ = false;
    active_ = false;
    silent_frames_ = 0;
    active_frames_ = 0;
}

std::vector<int16_t> SpeechGate::take_preroll() {
    std::vector<int16_t> out;
    const size_t frames = ring_filled_;
    out.reserve(frames * config_.frame_samples);
    const size_t capacity = config_.preroll_frames;
    const size_t start = (ring_head_ + capacity - frames) % capacity;
    for (size_t i = 0; i < frames; ++i) {
        const size_t slot = (start + i) % capacity;
        const int16_t* src = ring_.data() + slot * config_.frame_samples;
        out.insert(out.end(), src, src + config_.frame_samples);
    }
    ring_filled_ = 0;
    return out;
}

GateEvent SpeechGate::feed(const int16_t* frame, size_t length) {
    if (frame == nullptr || length != config_.frame_samples) {
        return GateEvent::Idle;
    }
    const float energy = frame_energy_db(frame, length);
    if (!primed_) {
        floor_db_ = energy < config_.min_floor_db ? config_.min_floor_db : energy;
        primed_ = true;
    } else if (energy < floor_db_) {
        floor_db_ = floor_db_ * FALL + energy * (1.0f - FALL);
    } else if (!active_) {
        floor_db_ += RISE * (energy - floor_db_);
    }
    if (floor_db_ < config_.min_floor_db) {
        floor_db_ = config_.min_floor_db;
    }
    const bool voiced = energy > floor_db_ + config_.gate_db;

    if (!active_) {
        if (voiced) {
            active_ = true;
            silent_frames_ = 0;
            active_frames_ = 1;
            return GateEvent::Start;
        }
        int16_t* slot = ring_.data() + ring_head_ * config_.frame_samples;
        for (size_t i = 0; i < length; ++i) {
            slot[i] = frame[i];
        }
        ring_head_ = (ring_head_ + 1) % config_.preroll_frames;
        if (ring_filled_ < config_.preroll_frames) {
            ++ring_filled_;
        }
        return GateEvent::Idle;
    }

    ++active_frames_;
    silent_frames_ = voiced ? 0 : silent_frames_ + 1;
    if (silent_frames_ >= config_.hangover_frames || active_frames_ >= config_.max_utterance_frames) {
        active_ = false;
        silent_frames_ = 0;
        active_frames_ = 0;
        ring_filled_ = 0;
        return GateEvent::End;
    }
    return GateEvent::Speech;
}

}
