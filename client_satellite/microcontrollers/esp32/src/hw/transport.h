#pragma once

#include <stdint.h>

#include <string>

#include "signer.h"
#include "store.h"

namespace nuxiva_hw {

struct Reply {
    int status = 0;
    std::string body;
};

class Transport {
public:
    void configure(const Stored* stored, const nuxiva_node::DeviceKey* key);
    bool post(const std::string& path, const std::string& body, uint32_t timeout_ms, Reply& reply, bool authed);
    bool get_stream(const std::string& path, uint32_t timeout_ms, const std::string& body,
                    bool (*sink)(const uint8_t*, size_t, void*), void* context, int& status);

private:
    std::string nonce();
    bool send(const std::string& path, const std::string& body, uint32_t timeout_ms, Reply& reply, bool authed,
              bool (*sink)(const uint8_t*, size_t, void*), void* context);
    void sync_clock(const std::string& date);

    const Stored* stored_ = nullptr;
    const nuxiva_node::DeviceKey* key_ = nullptr;
};

int64_t now_epoch();

}
