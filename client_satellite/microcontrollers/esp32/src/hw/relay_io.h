#pragma once

#include <stdint.h>

#include "relay_bank.h"

namespace nuxiva_hw {

uint8_t relay_count();
void relay_init();
void relay_write(const nuxiva_node::RelayChange& change);

}
