#pragma once

#include "signer.h"
#include "store.h"

namespace nuxiva_hw {

bool ensure_identity(Store& store, nuxiva_node::DeviceKey& key);

}
