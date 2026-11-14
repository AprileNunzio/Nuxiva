#pragma once

#include <stddef.h>
#include <stdint.h>

#include <array>
#include <string>

namespace nuxiva_node {

struct SignedHeaders {
    int64_t ts = 0;
    std::string nonce;
    std::string signature;
};

class DeviceKey {
public:
    DeviceKey() = default;
    ~DeviceKey();
    DeviceKey(const DeviceKey&) = default;
    DeviceKey& operator=(const DeviceKey&) = default;

    bool load(const uint8_t* seed, size_t length);
    bool loaded() const { return loaded_; }
    void wipe();

    std::string public_hex() const;
    std::string pairing_code() const;
    std::string fingerprint() const;
    std::array<uint8_t, 32> seed() const { return seed_; }

    bool sign(const std::string& node, const std::string& method, const std::string& path, const uint8_t* body,
              size_t body_length, int64_t ts, const std::string& nonce, SignedHeaders& out) const;

private:
    std::array<uint8_t, 32> seed_{};
    std::array<uint8_t, 32> public_{};
    bool loaded_ = false;
};

}
