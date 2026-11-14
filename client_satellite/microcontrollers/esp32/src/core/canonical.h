#pragma once

#include <stdint.h>

#include <string>

namespace nuxiva_node {

constexpr char DOMAIN[] = "nuxiva-node-v1";
constexpr size_t MAX_FIELD = 256;

bool canonical(const std::string& node, const std::string& method, const std::string& path, int64_t ts,
               const std::string& nonce, const std::string& body_sha256, std::string& out);

}
