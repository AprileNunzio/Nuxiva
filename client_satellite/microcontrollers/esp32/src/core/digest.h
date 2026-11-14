#pragma once

#include <stddef.h>
#include <stdint.h>

#include <array>
#include <memory>

class SHA256;

namespace nuxiva_node {

using Digest = std::array<uint8_t, 32>;

class Sha256Stream {
public:
    Sha256Stream();
    ~Sha256Stream();
    Sha256Stream(const Sha256Stream&) = delete;
    Sha256Stream& operator=(const Sha256Stream&) = delete;
    void update(const uint8_t* data, size_t length);
    Digest finish();

private:
    std::unique_ptr<SHA256> impl_;
};

Digest sha256(const uint8_t* data, size_t length);

}
