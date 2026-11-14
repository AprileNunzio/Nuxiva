#include "ear_link.h"

#include <esp_websocket_client.h>

namespace nuxiva_hw {

namespace {

constexpr char HELLO[] = "{\"type\":\"client\",\"page\":\"node\",\"visible\":\"node\"}";
constexpr int SEND_TIMEOUT_MS = 200;

void on_event(void* args, esp_event_base_t, int32_t event_id, void* data) {
    EarLink* link = static_cast<EarLink*>(args);
    esp_websocket_event_data_t* event = static_cast<esp_websocket_event_data_t*>(data);
    switch (event_id) {
        case WEBSOCKET_EVENT_CONNECTED:
            esp_websocket_client_send_text(event->client, HELLO, sizeof(HELLO) - 1, SEND_TIMEOUT_MS / portTICK_PERIOD_MS);
            link->set_connected(true);
            break;
        case WEBSOCKET_EVENT_DISCONNECTED:
        case WEBSOCKET_EVENT_ERROR:
        case WEBSOCKET_EVENT_CLOSED:
            link->set_connected(false);
            break;
        default:
            break;
    }
}

}

void EarLink::set_connected(bool value) {
    connected_ = value;
}

bool EarLink::begin(const Stored& stored) {
    end();
    ca_ = stored.ca_pem;
    uri_ = "wss://" + stored.host + ":" + std::to_string(stored.port) + "/ws/ear";
    headers_ = "X-Nuxiva-Node: " + stored.node_id + "\r\nAuthorization: Bearer " + stored.node_token + "\r\n";
    esp_websocket_client_config_t config = {};
    config.uri = uri_.c_str();
    config.cert_pem = ca_.c_str();
    config.headers = headers_.c_str();
    config.transport = WEBSOCKET_TRANSPORT_OVER_SSL;
    config.buffer_size = 4096;
    config.task_stack = 6144;
    config.network_timeout_ms = 10000;
    config.reconnect_timeout_ms = 5000;
    config.disable_auto_reconnect = false;
    config.skip_cert_common_name_check = false;
    client_ = esp_websocket_client_init(&config);
    if (client_ == nullptr) {
        return false;
    }
    esp_websocket_register_events(client_, WEBSOCKET_EVENT_ANY, on_event, this);
    if (esp_websocket_client_start(client_) != ESP_OK) {
        esp_websocket_client_destroy(client_);
        client_ = nullptr;
        return false;
    }
    return true;
}

void EarLink::end() {
    connected_ = false;
    if (client_ != nullptr) {
        esp_websocket_client_stop(client_);
        esp_websocket_client_destroy(client_);
        client_ = nullptr;
    }
}

bool EarLink::send_audio(const int16_t* pcm, size_t samples) {
    if (client_ == nullptr || !connected_ || pcm == nullptr || samples == 0) {
        return false;
    }
    const int sent = esp_websocket_client_send_bin(client_, reinterpret_cast<const char*>(pcm),
                                                   static_cast<int>(samples * sizeof(int16_t)),
                                                   SEND_TIMEOUT_MS / portTICK_PERIOD_MS);
    return sent > 0;
}

}
