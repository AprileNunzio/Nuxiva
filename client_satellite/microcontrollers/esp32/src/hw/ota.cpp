#include "ota.h"

#include <Arduino.h>
#include <Update.h>

#include "digest.h"
#include "firmware_manifest.h"
#include "hexutil.h"
#include "settings.h"

namespace nuxiva_hw {

namespace {

struct Download {
    nuxiva_node::Sha256Stream hash;
    size_t written = 0;
    size_t limit = 0;
    bool failed = false;
};

bool sink(const uint8_t* data, size_t length, void* context) {
    Download* download = static_cast<Download*>(context);
    if (download->written + length > download->limit) {
        download->failed = true;
        return false;
    }
    if (Update.write(const_cast<uint8_t*>(data), length) != length) {
        download->failed = true;
        return false;
    }
    download->hash.update(data, length);
    download->written += length;
    return true;
}

}

const char* ota_result_code(OtaResult result) {
    switch (result) {
        case OtaResult::Disabled: return "disabled";
        case OtaResult::Unreachable: return "unreachable";
        case OtaResult::UpToDate: return "up_to_date";
        case OtaResult::Rejected: return "rejected";
        case OtaResult::Failed: return "failed";
        case OtaResult::Applied: return "applied";
    }
    return "unknown";
}

OtaResult ota_check_and_apply(Transport& transport, const std::string& current_version) {
    const std::string key = NUXIVA_FW_PUBKEY_HEX;
    if (key.size() != 64) {
        return OtaResult::Disabled;
    }
    Reply reply;
    if (!transport.post("/api/nodes/firmware/esp32/manifest", "{}", HTTP_TIMEOUT_MS, reply, true) || reply.status != 200) {
        return OtaResult::Unreachable;
    }
    nuxiva_node::FirmwareManifest manifest;
    if (!nuxiva_node::parse_manifest(reply.body, manifest) || !nuxiva_node::verify_manifest(manifest, key)) {
        return OtaResult::Rejected;
    }
    if (!nuxiva_node::is_newer(manifest.version, current_version)) {
        return OtaResult::UpToDate;
    }
    if (!Update.begin(manifest.size, U_FLASH)) {
        return OtaResult::Failed;
    }
    Download download;
    download.limit = manifest.size;
    int status = 0;
    const bool fetched = transport.get_stream("/api/nodes/firmware/esp32/image", HTTP_TIMEOUT_MS, "{}", sink, &download, status);
    const nuxiva_node::Digest digest = download.hash.finish();
    const bool intact = fetched && !download.failed && download.written == manifest.size &&
                        nuxiva_node::constant_time_equal(nuxiva_node::hex_encode(digest.data(), digest.size()), manifest.sha256);
    if (!intact) {
        Update.abort();
        return OtaResult::Failed;
    }
    if (!Update.end(false)) {
        return OtaResult::Failed;
    }
    return OtaResult::Applied;
}

}
