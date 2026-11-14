#include "identity.h"

#include <bootloader_random.h>
#include <esp_system.h>

namespace nuxiva_hw {

bool ensure_identity(Store& store, nuxiva_node::DeviceKey& key) {
    uint8_t seed[32];
    bool ok = store.load_seed(seed);
    if (!ok) {
        bootloader_random_enable();
        esp_fill_random(seed, sizeof(seed));
        bootloader_random_disable();
        ok = store.save_seed(seed);
    }
    ok = ok && key.load(seed, sizeof(seed));
    volatile uint8_t* wipe = seed;
    for (size_t i = 0; i < sizeof(seed); ++i) {
        wipe[i] = 0;
    }
    return ok;
}

}
