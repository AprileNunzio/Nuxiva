#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>

namespace nuxiva_node {

constexpr uint32_t MAX_FIRMWARE_BYTES = 3u * 1024u * 1024u;
constexpr size_t MAX_MANIFEST_BYTES = 1024;

struct FirmwareManifest {
    std::string version;
    uint32_t size = 0;
    std::string sha256;
    std::string signature;
};

bool parse_version(const std::string& text, uint32_t& major, uint32_t& minor, uint32_t& patch);
bool is_newer(const std::string& candidate, const std::string& current);
bool parse_manifest(const std::string& json, FirmwareManifest& out);
std::string manifest_message(const FirmwareManifest& manifest);
bool verify_manifest(const FirmwareManifest& manifest, const std::string& public_key_hex);

}
