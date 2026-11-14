#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace nuxiva_node {

std::string hex_encode(const uint8_t* data, size_t length);
bool hex_decode(const std::string& text, std::vector<uint8_t>& out);
bool is_lower_hex(const std::string& text, size_t length);
bool constant_time_equal(const std::string& a, const std::string& b);

}
