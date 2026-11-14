#include "transport.h"

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <esp_system.h>
#include <sys/time.h>
#include <time.h>

#include "hexutil.h"
#include "http_date.h"
#include "settings.h"

namespace nuxiva_hw {

int64_t now_epoch() {
    return static_cast<int64_t>(time(nullptr));
}

void Transport::configure(const Stored* stored, const nuxiva_node::DeviceKey* key) {
    stored_ = stored;
    key_ = key;
}

std::string Transport::nonce() {
    uint8_t raw[16];
    esp_fill_random(raw, sizeof(raw));
    return nuxiva_node::hex_encode(raw, sizeof(raw));
}

void Transport::sync_clock(const std::string& date) {
    int64_t server = 0;
    if (!nuxiva_node::parse_http_date(date, server) ||
        !nuxiva_node::clock_needs_sync(now_epoch(), server, CLOCK_TOLERANCE_S)) {
        return;
    }
    struct timeval tv;
    tv.tv_sec = static_cast<time_t>(server);
    tv.tv_usec = 0;
    settimeofday(&tv, nullptr);
}

bool Transport::send(const std::string& path, const std::string& body, uint32_t timeout_ms, Reply& reply, bool authed,
                     bool (*sink)(const uint8_t*, size_t, void*), void* context) {
    if (stored_ == nullptr || stored_->ca_pem.empty()) {
        return false;
    }
    WiFiClientSecure client;
    client.setCACert(stored_->ca_pem.c_str());
    client.setTimeout(timeout_ms / 1000 + 1);
    HTTPClient http;
    http.setConnectTimeout(timeout_ms);
    http.setTimeout(timeout_ms);
    http.setReuse(false);
    const char* wanted[] = {"Date"};
    http.collectHeaders(wanted, 1);
    if (!http.begin(client, stored_->host.c_str(), stored_->port, path.c_str(), true)) {
        return false;
    }
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Nuxiva-Node", stored_->node_id.c_str());
    if (key_ != nullptr && key_->loaded()) {
        nuxiva_node::SignedHeaders signed_headers;
        const std::string n = nonce();
        if (key_->sign(stored_->node_id, "POST", path, reinterpret_cast<const uint8_t*>(body.data()), body.size(),
                       now_epoch(), n, signed_headers)) {
            http.addHeader("X-Nuxiva-Ts", std::to_string(static_cast<long long>(signed_headers.ts)).c_str());
            http.addHeader("X-Nuxiva-Nonce", signed_headers.nonce.c_str());
            http.addHeader("X-Nuxiva-Sig", signed_headers.signature.c_str());
        }
    }
    if (authed) {
        http.addHeader("Authorization", (String("Bearer ") + stored_->node_token.c_str()));
    }
    const int status = http.POST(reinterpret_cast<uint8_t*>(const_cast<char*>(body.data())), body.size());
    reply.status = status;
    if (status <= 0) {
        http.end();
        return false;
    }
    sync_clock(std::string(http.header("Date").c_str()));
    if (sink != nullptr && status == HTTP_CODE_OK) {
        WiFiClient* stream = http.getStreamPtr();
        uint8_t chunk[1024];
        int remaining = http.getSize();
        const uint32_t started = millis();
        while (http.connected() && (remaining > 0 || remaining == -1) && millis() - started < timeout_ms * 6) {
            const size_t available = stream->available();
            if (available == 0) {
                delay(2);
                continue;
            }
            const int read = stream->readBytes(chunk, available > sizeof(chunk) ? sizeof(chunk) : available);
            if (read <= 0) {
                break;
            }
            if (!sink(chunk, static_cast<size_t>(read), context)) {
                http.end();
                return false;
            }
            if (remaining > 0) {
                remaining -= read;
            }
        }
    } else {
        reply.body = std::string(http.getString().c_str());
    }
    http.end();
    return true;
}

bool Transport::post(const std::string& path, const std::string& body, uint32_t timeout_ms, Reply& reply, bool authed) {
    if (!send(path, body, timeout_ms, reply, authed, nullptr, nullptr)) {
        return false;
    }
    if (reply.status == 401 && reply.body.find("node.error.clock") != std::string::npos) {
        return send(path, body, timeout_ms, reply, authed, nullptr, nullptr);
    }
    return true;
}

bool Transport::get_stream(const std::string& path, uint32_t timeout_ms, const std::string& body,
                           bool (*sink)(const uint8_t*, size_t, void*), void* context, int& status) {
    Reply reply;
    const bool ok = send(path, body, timeout_ms, reply, true, sink, context);
    status = reply.status;
    return ok && reply.status == HTTP_CODE_OK;
}

}
