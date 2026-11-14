#include "node.h"

#include <Arduino.h>
#include <algorithm>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <esp_flash_encrypt.h>

#include "digest.h"
#include "hexutil.h"
#include "identity.h"
#include "ota.h"
#include "provision.h"
#include "relay_io.h"
#include "settings.h"
#include "speech_gate.h"

namespace nuxiva_hw {

namespace {

constexpr uint32_t WIFI_RETRY_MS = 15000;
constexpr uint32_t ENROLL_RETRY_MS = 30000;
constexpr size_t PACKET_FRAMES = 4;

void audio_entry(void*) {
    node().audio_loop();
    vTaskDelete(nullptr);
}

void inbox_entry(void*) {
    node().inbox_loop();
    vTaskDelete(nullptr);
}

}

Node& node() {
    static Node instance;
    return instance;
}

Node::Node() : relays_(relay_count(), NUXIVA_RELAY_MAX_ON_MS) {}

void Node::touch_ok() {
    ok_stamp_ = millis();
}

void Node::blink() {
#ifdef LED_BUILTIN
    pinMode(LED_BUILTIN, OUTPUT);
    for (int i = 0; i < 6; ++i) {
        digitalWrite(LED_BUILTIN, i % 2 == 0 ? HIGH : LOW);
        delay(120);
    }
    digitalWrite(LED_BUILTIN, LOW);
#endif
}

void Node::boot_reset_check() {
    pinMode(NUXIVA_RESET_PIN, INPUT_PULLUP);
    if (digitalRead(NUXIVA_RESET_PIN) != LOW) {
        return;
    }
    const uint32_t started = millis();
    while (digitalRead(NUXIVA_RESET_PIN) == LOW) {
        if (millis() - started >= RESET_HOLD_MS) {
            store_.wipe();
            serial_.reply("{\"event\":\"wiped\"}");
            delay(200);
            ESP.restart();
        }
        delay(20);
    }
}

void Node::announce_info(const char* event) {
    JsonDocument doc;
    doc["event"] = event;
    doc["fw"] = NUXIVA_FIRMWARE_VERSION;
    doc["provisioned"] = provisioned_;
    doc["enrolled"] = !stored_.node_token.empty();
    doc["pub"] = key_.public_hex();
    doc["pairing_code"] = key_.pairing_code();
    doc["fingerprint"] = key_.fingerprint();
    doc["flash_encrypted"] = esp_flash_encryption_enabled();
    doc["relays"] = relay_count();
    std::string out;
    serializeJson(doc, out);
    serial_.reply(out);
}

void Node::setup() {
    Serial.begin(115200);
    relay_init();
    boot_reset_check();
    provisioned_ = store_.load(stored_);
    if (!ensure_identity(store_, key_)) {
        serial_.reply("{\"event\":\"error\",\"code\":\"identity\"}");
    }
    transport_.configure(&stored_, &key_);
    announce_info("ready");
    if (provisioned_) {
        WiFi.mode(WIFI_STA);
        WiFi.setSleep(false);
        WiFi.setAutoReconnect(true);
    }
    touch_ok();
}

void Node::provision(const std::string& line) {
    nuxiva_node::Provision parsed;
    const nuxiva_node::ProvisionError error = nuxiva_node::parse_provision(line, parsed);
    if (error != nuxiva_node::ProvisionError::Ok) {
        serial_.reply(std::string("{\"event\":\"error\",\"code\":\"") + nuxiva_node::provision_error_code(error) + "\"}");
        return;
    }
    if (provisioned_ && !stored_.node_token.empty()) {
        serial_.reply("{\"event\":\"error\",\"code\":\"already_enrolled\"}");
        return;
    }
    Stored data;
    data.ssid = parsed.ssid;
    data.pass = parsed.pass;
    data.server = parsed.server;
    data.ca_pem = parsed.ca_pem;
    data.node_id = parsed.node_id;
    data.name = parsed.name;
    data.enroll_token = parsed.token;
    if (!store_.save_provision(data)) {
        serial_.reply("{\"event\":\"error\",\"code\":\"storage\"}");
        return;
    }
    provisioned_ = store_.load(stored_);
    announce_info("provisioned");
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.setAutoReconnect(true);
}

void Node::handle_serial() {
    std::string line;
    if (!serial_.poll(line)) {
        return;
    }
    JsonDocument doc;
    if (deserializeJson(doc, line) == DeserializationError::Ok && std::string(doc["cmd"] | "") == "hello") {
        announce_info("info");
        return;
    }
    provision(line);
}

bool Node::connect_wifi() {
    if (WiFi.status() == WL_CONNECTED) {
        return true;
    }
    if (millis() - last_wifi_try_ < WIFI_RETRY_MS && last_wifi_try_ != 0) {
        return false;
    }
    last_wifi_try_ = millis();
    WiFi.begin(stored_.ssid.c_str(), stored_.pass.empty() ? nullptr : stored_.pass.c_str());
    return false;
}

bool Node::enroll() {
    if (!stored_.node_token.empty()) {
        return true;
    }
    if (stored_.enroll_token.empty()) {
        return false;
    }
    if (millis() - last_enroll_try_ < ENROLL_RETRY_MS && last_enroll_try_ != 0) {
        return false;
    }
    last_enroll_try_ = millis();
    JsonDocument body;
    body["token"] = stored_.enroll_token;
    body["id"] = stored_.node_id;
    body["name"] = stored_.name;
    body["type"] = "esp32";
    body["pubkey"] = key_.public_hex();
    std::string payload;
    serializeJson(body, payload);
    Reply reply;
    if (!transport_.post("/api/nodes/enroll", payload, HTTP_TIMEOUT_MS, reply, false)) {
        serial_.reply("{\"event\":\"enroll\",\"ok\":false,\"code\":\"unreachable\"}");
        return false;
    }
    JsonDocument parsed;
    if (reply.status != 200 || deserializeJson(parsed, reply.body) != DeserializationError::Ok) {
        JsonDocument event;
        event["event"] = "enroll";
        event["ok"] = false;
        event["status"] = reply.status;
        std::string out;
        serializeJson(event, out);
        serial_.reply(out);
        return false;
    }
    const std::string token = std::string(parsed["token"] | "");
    if (token.size() < 20 || !store_.save_node_token(token)) {
        return false;
    }
    store_.clear_enroll_token();
    stored_.node_token = token;
    stored_.enroll_token.clear();
    serial_.reply("{\"event\":\"enroll\",\"ok\":true}");
    return true;
}

void Node::start_services() {
    if (services_) {
        return;
    }
    services_ = true;
    ear_.begin(stored_);
    xTaskCreatePinnedToCore(audio_entry, "nuxiva-audio", 8192, nullptr, 3, nullptr, 1);
    xTaskCreatePinnedToCore(inbox_entry, "nuxiva-inbox", 12288, nullptr, 2, nullptr, 0);
}

std::string Node::heartbeat_body() {
    JsonDocument doc;
    doc["version"] = NUXIVA_FIRMWARE_VERSION;
    doc["hostname"] = stored_.node_id;
    JsonArray caps = doc["capabilities"].to<JsonArray>();
    caps.add("audio");
    caps.add("sensor");
    if (relay_count() > 0) {
        caps.add("relay");
    }
    JsonObject metrics = doc["metrics"].to<JsonObject>();
    metrics["uptime"] = millis() / 1000.0;
    metrics["ram"] = 100.0 * (1.0 - static_cast<double>(ESP.getFreeHeap()) / static_cast<double>(ESP.getHeapSize()));
    metrics["temp"] = temperatureRead();
    JsonObject announce = doc["announce"].to<JsonObject>();
    JsonArray scopes = announce["capabilities"].to<JsonArray>();
    scopes.add<JsonObject>()["scope"] = "telemetry.report";
    scopes.add<JsonObject>()["scope"] = "audio.capture";
    scopes.add<JsonObject>()["scope"] = "sensor.read";
    JsonObject hardware = announce["hardware"].to<JsonObject>();
    hardware["cpu_cores"] = ESP.getChipCores();
    hardware["ram_mb"] = ESP.getHeapSize() / (1024 * 1024);
    std::string out;
    serializeJson(doc, out);
    return out;
}

void Node::flush_relays() {
    std::lock_guard<std::mutex> guard(relay_lock_);
    for (const nuxiva_node::RelayChange& change : relays_.take_changes()) {
        relay_write(change);
    }
}

void Node::apply(const nuxiva_node::Action& action) {
    switch (action.kind) {
        case nuxiva_node::ActionKind::Relay: {
            std::lock_guard<std::mutex> guard(relay_lock_);
            relays_.apply(action, millis());
            break;
        }
        case nuxiva_node::ActionKind::Identify:
            blink();
            break;
        case nuxiva_node::ActionKind::Restart:
            restart_requested_ = true;
            break;
        case nuxiva_node::ActionKind::Update:
            update_requested_ = true;
            break;
        case nuxiva_node::ActionKind::None:
            break;
    }
    flush_relays();
}

void Node::heartbeat() {
    Reply reply;
    if (!transport_.post("/api/nodes/heartbeat", heartbeat_body(), HTTP_TIMEOUT_MS, reply, true) || reply.status != 200) {
        return;
    }
    touch_ok();
    JsonDocument doc;
    if (deserializeJson(doc, reply.body) != DeserializationError::Ok) {
        return;
    }
    for (JsonVariant command : doc["commands"].as<JsonArray>()) {
        nuxiva_node::Action action;
        if (nuxiva_node::parse_command(std::string(command | ""), action)) {
            apply(action);
        }
    }
    for (JsonVariant item : doc["actions"].as<JsonArray>()) {
        std::string raw;
        serializeJson(item, raw);
        nuxiva_node::Action action;
        if (nuxiva_node::parse_action(raw, action)) {
            apply(action);
        }
    }
}

void Node::inbox_loop() {
    uint32_t backoff = 2000;
    for (;;) {
        Reply reply;
        if (WiFi.status() != WL_CONNECTED || stored_.node_token.empty()) {
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }
        const bool ok = transport_.post("/api/nodes/inbox", "{}", INBOX_TIMEOUT_MS, reply, true);
        if (!ok || reply.status != 200) {
            vTaskDelay(pdMS_TO_TICKS(backoff));
            backoff = backoff < 30000 ? backoff * 2 : 30000;
            continue;
        }
        backoff = 2000;
        touch_ok();
        JsonDocument doc;
        if (deserializeJson(doc, reply.body) != DeserializationError::Ok) {
            continue;
        }
        for (JsonVariant item : doc["actions"].as<JsonArray>()) {
            std::string raw;
            serializeJson(item, raw);
            nuxiva_node::Action action;
            if (nuxiva_node::parse_action(raw, action)) {
                apply(action);
            }
        }
    }
}

void Node::audio_loop() {
    AudioIn audio;
    while (!audio.begin()) {
        serial_.reply("{\"event\":\"error\",\"code\":\"i2s\"}");
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
    nuxiva_node::SpeechGate gate;
    int16_t frame[FRAME_SAMPLES];
    int16_t packet[FRAME_SAMPLES * PACKET_FRAMES];
    size_t queued = 0;
    bool active = false;
    for (;;) {
        if (!audio.read_frame(frame, FRAME_SAMPLES, 100)) {
            continue;
        }
        if (!ear_.connected()) {
            gate.reset();
            active = false;
            queued = 0;
            continue;
        }
        if (NUXIVA_STREAM_ALWAYS) {
            ear_.send_audio(frame, FRAME_SAMPLES);
            continue;
        }
        const nuxiva_node::GateEvent event = gate.feed(frame, FRAME_SAMPLES);
        if (event == nuxiva_node::GateEvent::Start) {
            const std::vector<int16_t> preroll = gate.take_preroll();
            size_t sent = 0;
            while (sent < preroll.size()) {
                const size_t chunk = std::min(preroll.size() - sent, FRAME_SAMPLES * PACKET_FRAMES);
                ear_.send_audio(preroll.data() + sent, chunk);
                sent += chunk;
            }
            active = true;
        }
        if (!active) {
            continue;
        }
        for (size_t i = 0; i < FRAME_SAMPLES; ++i) {
            packet[queued++] = frame[i];
        }
        const bool ended = event == nuxiva_node::GateEvent::End;
        if (queued >= FRAME_SAMPLES * PACKET_FRAMES || ended) {
            ear_.send_audio(packet, queued);
            queued = 0;
        }
        if (ended) {
            active = false;
        }
    }
}

void Node::loop() {
    handle_serial();
    if (!provisioned_) {
        delay(10);
        return;
    }
    if (restart_requested_) {
        delay(300);
        ESP.restart();
    }
    {
        std::lock_guard<std::mutex> guard(relay_lock_);
        relays_.tick(millis());
    }
    flush_relays();
    if (static_cast<int32_t>(millis() - ok_stamp_) > static_cast<int32_t>(NUXIVA_FAILSAFE_MS)) {
        {
            std::lock_guard<std::mutex> guard(relay_lock_);
            relays_.failsafe();
        }
        flush_relays();
    }
    if (!connect_wifi() || !enroll()) {
        delay(50);
        return;
    }
    start_services();
    if (millis() - last_heartbeat_ >= HEARTBEAT_MS || last_heartbeat_ == 0) {
        last_heartbeat_ = millis();
        heartbeat();
    }
    if (update_requested_ || millis() - last_update_check_ >= UPDATE_CHECK_MS) {
        update_requested_ = false;
        last_update_check_ = millis();
        const OtaResult result = ota_check_and_apply(transport_, NUXIVA_FIRMWARE_VERSION);
        if (result == OtaResult::Applied) {
            serial_.reply("{\"event\":\"update\",\"result\":\"applied\"}");
            delay(500);
            ESP.restart();
        }
    }
    delay(20);
}

}
