#pragma once

#include <stdint.h>

#include <string>

namespace nuxiva_node {

bool parse_http_date(const std::string& text, int64_t& epoch_seconds);
bool clock_needs_sync(int64_t local_epoch, int64_t server_epoch, int64_t tolerance_seconds);

}
