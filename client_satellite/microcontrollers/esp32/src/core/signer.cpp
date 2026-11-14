#include "signer.h"

#include <Ed25519.h>
#include <stdio.h>
#include <string.h>

#include "canonical.h"
#include "digest.h"
#include "hexutil.h"

namespace nuxiva_node {

namespace {

void zero(void* data, size_t length) {
    volatile uint8_t* p = static_cast<volatile uint8_t*>(data);
    for (size_t i = 0; i < length; ++i) {
        p[i] = 0;
    }
}

}

DeviceKey::~DeviceKey() {
    wipe();
}

bool DeviceKey::load(const uint8_t* seed, size_t length) {
    wipe();
    if (seed == nullptr || length != 32) {
        return false;
    }
    memcpy(seed_.data(), seed, 32);
    Ed25519::derivePublicKey(public_.data(), seed_.data());
    loaded_ = true;
    return true;
}

void DeviceKey::wipe() {
    zero(seed_.data(), seed_.size());
    zero(public_.data(), public_.size());
    loaded_ = false;
}

std::string DeviceKey::public_hex() const {
    return loaded_ ? hex_encode(public_.data(), public_.size()) : std::string();
}

std::string DeviceKey::pairing_code() const {
    if (!loaded_) {
        return std::string();
    }
    const Digest digest = sha256(public_.data(), public_.size());
    uint64_t head = 0;
    for (size_t i = 0; i < 8; ++i) {
        head = (head << 8) | digest[i];
    }
    char buffer[8];
    snprintf(buffer, sizeof(buffer), "%06lu", static_cast<unsigned long>(head % 1000000ULL));
    return std::string(buffer);
}

std::string DeviceKey::fingerprint() const {
    if (!loaded_) {
        return std::string();
    }
    const Digest digest = sha256(public_.data(), public_.size());
    std::string hex = hex_encode(digest.data(), 6);
    std::string out;
    for (size_t i = 0; i < hex.size(); ++i) {
        if (i > 0 && i % 4 == 0) {
            out.push_back('-');
        }
        out.push_back(static_cast<char>(hex[i] >= 'a' && hex[i] <= 'f' ? hex[i] - 32 : hex[i]));
    }
    return out;
}

bool DeviceKey::sign(const std::string& node, const std::string& method, const std::string& path, const uint8_t* body,
                     size_t body_length, int64_t ts, const std::string& nonce, SignedHeaders& out) const {
    if (!loaded_) {
        return false;
    }
    const Digest body_digest = sha256(body, body_length);
    std::string message;
    if (!canonical(node, method, path, ts, nonce, hex_encode(body_digest.data(), body_digest.size()), message)) {
        return false;
    }
    uint8_t signature[64];
    Ed25519::sign(signature, seed_.data(), public_.data(), message.data(), message.size());
    out.ts = ts;
    out.nonce = nonce;
    out.signature = hex_encode(signature, sizeof(signature));
    zero(signature, sizeof(signature));
    return true;
}

}
