#include <math.h>

#include "action.h"
#include "check.h"
#include "http_date.h"
#include "relay_bank.h"
#include "speech_gate.h"

using namespace nuxiva_node;

namespace {

std::vector<int16_t> tone(size_t samples, float amplitude, float hz, size_t offset) {
    std::vector<int16_t> out(samples);
    for (size_t i = 0; i < samples; ++i) {
        out[i] = static_cast<int16_t>(amplitude * 32767.0f * sinf(2.0f * 3.14159265f * hz * static_cast<float>(i + offset) / 16000.0f));
    }
    return out;
}

}

void run_action_tests() {
    Action a;
    CHECK(parse_action("{\"type\":\"relay\",\"channel\":2,\"state\":\"on\"}", a));
    CHECK(a.kind == ActionKind::Relay && a.channel == 2 && a.mode == RelayMode::On && a.duration_ms == 0);
    CHECK(parse_action("{\"type\":\"relay\",\"channel\":0,\"state\":\"pulse\",\"ms\":500}", a));
    CHECK(a.mode == RelayMode::Pulse && a.duration_ms == 500);
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":0,\"state\":\"pulse\"}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":0,\"state\":\"pulse\",\"ms\":10}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":0,\"state\":\"pulse\",\"ms\":999999}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":8,\"state\":\"on\"}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":-1,\"state\":\"on\"}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":\"1\",\"state\":\"on\"}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":1,\"state\":\"toggle\"}", a));
    CHECK(!parse_action("{\"type\":\"relay\",\"channel\":1,\"state\":\"on\",\"ms\":-5}", a));
    CHECK(!parse_action("{\"type\":\"exec\",\"cmd\":\"rm\"}", a));
    CHECK(a.kind == ActionKind::None);
    CHECK(!parse_action("", a));
    CHECK(!parse_action("[1]", a));
    CHECK(!parse_action(std::string(MAX_ACTION_BYTES + 1, 'x'), a));
    CHECK(parse_action("{\"type\":\"restart\"}", a) && a.kind == ActionKind::Restart);
    CHECK(parse_command("identify", a) && a.kind == ActionKind::Identify);
    CHECK(parse_command("update", a) && a.kind == ActionKind::Update);
    CHECK(!parse_command("adapt", a));
}

void run_relay_tests() {
    RelayBank bank(2, 10000);
    Action on;
    on.kind = ActionKind::Relay;
    on.channel = 0;
    on.mode = RelayMode::On;
    CHECK(bank.apply(on, 1000));
    CHECK(bank.is_on(0));
    CHECK_EQ(bank.take_changes().size(), 1u);
    CHECK(bank.apply(on, 2000));
    CHECK(bank.take_changes().empty());
    bank.tick(10999);
    CHECK(bank.is_on(0));
    bank.tick(12000);
    CHECK(!bank.is_on(0));
    auto changes = bank.take_changes();
    CHECK(changes.size() == 1 && !changes[0].on);

    Action pulse = on;
    pulse.channel = 1;
    pulse.mode = RelayMode::Pulse;
    pulse.duration_ms = 300;
    CHECK(bank.apply(pulse, 5000));
    bank.tick(5299);
    CHECK(bank.is_on(1));
    bank.tick(5300);
    CHECK(!bank.is_on(1));
    bank.take_changes();

    Action bad = on;
    bad.channel = 2;
    CHECK(!bank.apply(bad, 0));
    Action none;
    CHECK(!bank.apply(none, 0));

    Action longer = on;
    longer.duration_ms = 3600000;
    CHECK(bank.apply(longer, 0));
    bank.tick(10000);
    CHECK(!bank.is_on(0));
    bank.take_changes();

    CHECK(bank.apply(on, 4294967000u));
    bank.tick(4294967000u + 9000u);
    CHECK(bank.is_on(0));
    bank.tick(4294967000u + 10000u);
    CHECK(!bank.is_on(0));
    bank.take_changes();

    bank.apply(on, 0);
    pulse.channel = 1;
    bank.apply(pulse, 0);
    bank.take_changes();
    bank.failsafe();
    CHECK(!bank.is_on(0) && !bank.is_on(1));
    CHECK_EQ(bank.take_changes().size(), 2u);

    RelayBank clamped(200, 0);
    CHECK_EQ(clamped.count(), MAX_RELAYS);
}

void run_gate_tests() {
    GateConfig config;
    SpeechGate gate(config);
    size_t offset = 0;
    auto feed = [&](float amp, int frames, int* starts, int* ends, int* speech) {
        for (int i = 0; i < frames; ++i) {
            const std::vector<int16_t> frame = tone(config.frame_samples, amp, 440.0f, offset);
            offset += config.frame_samples;
            switch (gate.feed(frame.data(), frame.size())) {
                case GateEvent::Start: ++*starts; break;
                case GateEvent::End: ++*ends; break;
                case GateEvent::Speech: ++*speech; break;
                case GateEvent::Idle: break;
            }
        }
    };
    int starts = 0, ends = 0, speech = 0;
    feed(0.002f, 100, &starts, &ends, &speech);
    CHECK_EQ(starts, 0);
    feed(0.3f, 40, &starts, &ends, &speech);
    CHECK_EQ(starts, 1);
    const std::vector<int16_t> preroll = gate.take_preroll();
    CHECK(preroll.empty() || preroll.size() % config.frame_samples == 0);
    feed(0.002f, 60, &starts, &ends, &speech);
    CHECK_EQ(ends, 1);
    CHECK_EQ(starts, 1);

    SpeechGate fresh(config);
    int idle_starts = 0;
    for (int i = 0; i < 200; ++i) {
        const std::vector<int16_t> frame = tone(config.frame_samples, 0.004f, 300.0f, static_cast<size_t>(i) * 320);
        if (fresh.feed(frame.data(), frame.size()) == GateEvent::Start) {
            ++idle_starts;
        }
    }
    CHECK_EQ(idle_starts, 0);
    for (int i = 0; i < 20; ++i) {
        const std::vector<int16_t> frame = tone(config.frame_samples, 0.004f, 300.0f, static_cast<size_t>(i) * 320);
        fresh.feed(frame.data(), frame.size());
    }
    const std::vector<int16_t> loud = tone(config.frame_samples, 0.5f, 300.0f, 0);
    CHECK(fresh.feed(loud.data(), loud.size()) == GateEvent::Start);
    const std::vector<int16_t> pre = fresh.take_preroll();
    CHECK_EQ(pre.size(), config.frame_samples * config.preroll_frames);
    CHECK(fresh.take_preroll().empty());

    const std::vector<int16_t> wrong(100, 0);
    CHECK(fresh.feed(wrong.data(), wrong.size()) == GateEvent::Idle);
    CHECK(fresh.feed(nullptr, 320) == GateEvent::Idle);

    GateConfig capped;
    capped.max_utterance_frames = 10;
    SpeechGate limited(capped);
    for (int i = 0; i < 30; ++i) {
        const std::vector<int16_t> silent(capped.frame_samples, 3);
        limited.feed(silent.data(), silent.size());
    }
    int cap_ends = 0;
    for (int i = 0; i < 40; ++i) {
        const std::vector<int16_t> frame = tone(capped.frame_samples, 0.5f, 300.0f, static_cast<size_t>(i) * 320);
        if (limited.feed(frame.data(), frame.size()) == GateEvent::End) {
            ++cap_ends;
        }
    }
    CHECK(cap_ends >= 1);

    DcBlocker blocker;
    int32_t last = 0;
    for (int i = 0; i < 4000; ++i) {
        last = blocker.process(8000);
    }
    CHECK(last < 50 && last > -50);
    CHECK_EQ(blocker.process(2000000000), 32767);
}

void run_date_tests() {
    int64_t t = 0;
    CHECK(parse_http_date("Sat, 14 Nov 2026 15:38:06 GMT", t));
    CHECK_EQ(t, 1794670686);
    CHECK(parse_http_date("Thu, 01 Jan 2026 00:00:00 GMT", t));
    CHECK_EQ(t, 1767225600);
    CHECK(parse_http_date("Tue, 29 Feb 2028 23:59:59 GMT", t));
    CHECK_EQ(t, 1835481599);
    CHECK(!parse_http_date("Sat, 14 Nov 2026 15:38:06 UTC", t));
    CHECK(!parse_http_date("Sat, 14 Foo 2026 15:38:06 GMT", t));
    CHECK(!parse_http_date("Sat, 14 Nov 2026 25:38:06 GMT", t));
    CHECK(!parse_http_date("Sat, 14 Nov 1999 15:38:06 GMT", t));
    CHECK(!parse_http_date("", t));
    CHECK(clock_needs_sync(1000, 1100, 60));
    CHECK(clock_needs_sync(1100, 1000, 60));
    CHECK(!clock_needs_sync(1000, 1030, 60));
}
