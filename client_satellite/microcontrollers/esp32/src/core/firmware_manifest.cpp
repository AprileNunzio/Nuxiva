#include "firmware_manifest.h"

#include <ArduinoJson.h>
#include <Ed25519.h>

#include "hexutil.h"

namespace nuxiva_node {

bool parse_version(const std::string& text, uint32_t& major, uint32_t& minor, uint32_t& patch) {
    uint32_t parts[3] = {0, 0, 0};
    size_t index = 0;
    size_t digits = 0;
    if (text.empty() || text.size() > 24) {
        return false;
    }
    for (char c : text) {
        if (c >= '0' && c <= '9') {
            if (++digits > 6) {
                return false;
            }
            parts[index] = parts[index] * 10 + static_cast<uint32_t>(c - '0');
        } else if (c == '.' && digits > 0 && index < 2) {
            ++index;
            digits = 0;
        } else {
            return false;
        }
    }
    if (index != 2 || digits == 0) {
        return false;
    }
    major = parts[0];
    minor = parts[1];
    patch = parts[2];
    return true;
}

bool is_newer(const std::string& candidate, const std::string& current) {
    uint32_t a[3];
    uint32_t b[3];
    if (!parse_version(candidate, a[0], a[1], a[2])) {
        return false;
    }
    if (!parse_version(current, b[0], b[1], b[2])) {
        return true;
    }
    for (size_t i = 0; i < 3; ++i) {
        if (a[i] != b[i]) {
            return a[i] > b[i];
        }
    }
    return false;
}

bool parse_manifest(const std::string& json, FirmwareManifest& out) {
    if (json.empty() || json.size() > MAX_MANIFEST_BYTES) {
        return false;
    }
    JsonDocument doc;
    if (deserializeJson(doc, json) != DeserializationError::Ok || !doc.is<JsonObject>()) {
        return false;
    }
    FirmwareManifest m;
    m.version = std::string(doc["version"] | "");
    m.sha256 = std::string(doc["sha256"] | "");
    m.signature = std::string(doc["sig"] | "");
    uint32_t major, minor, patch;
    if (!parse_version(m.version, major, minor, patch) || !is_lower_hex(m.sha256, 64) || !is_lower_hex(m.signature, 128) ||
        !doc["size"].is<unsigned long>()) {
        return false;
    }
    const unsigned long size = doc["size"].as<unsigned long>();
    if (size == 0 || size > MAX_FIRMWARE_BYTES) {
        return false;
    }
    m.size = static_cast<uint32_t>(size);
    out = m;
    return true;
}

std::string manifest_message(const FirmwareManifest& manifest) {
    return "nuxiva-fw-v1\n" + manifest.version + "\n" + std::to_string(manifest.size) + "\n" + manifest.sha256;
}

bool verify_manifest(const FirmwareManifest& manifest, const std::string& public_key_hex) {
    std::vector<uint8_t> key;
    std::vector<uint8_t> signature;
    if (!hex_decode(public_key_hex, key) || key.size() != 32 || !hex_decode(manifest.signature, signature) ||
        signature.size() != 64) {
        return false;
    }
    const std::string message = manifest_message(manifest);
    return Ed25519::verify(signature.data(), key.data(), message.data(), message.size());
}

}
