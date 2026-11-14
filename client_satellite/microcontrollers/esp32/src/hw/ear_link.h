#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>

#include "store.h"

typedef struct esp_websocket_client* esp_websocket_client_handle_t;

namespace nuxiva_hw {

class EarLink {
public:
    bool begin(const Stored& stored);
    void end();
    bool connected() const { return connected_; }
    bool send_audio(const int16_t* pcm, size_t samples);
    void set_connected(bool value);

private:
    esp_websocket_client_handle_t client_ = nullptr;
    volatile bool connected_ = false;
    std::string uri_;
    std::string headers_;
    std::string ca_;
};

}
