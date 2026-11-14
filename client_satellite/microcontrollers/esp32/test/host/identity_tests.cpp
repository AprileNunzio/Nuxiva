#include <ArduinoJson.h>

#include <fstream>
#include <sstream>

#include "canonical.h"
#include "check.h"
#include "firmware_manifest.h"
#include "hexutil.h"
#include "signer.h"

using namespace nuxiva_node;

namespace {

std::string slurp(const char* path) {
    std::ifstream in(path, std::ios::binary);
    std::stringstream buffer;
    buffer << in.rdbuf();
    return buffer.str();
}

std::vector<uint8_t> bytes(const std::string& hex) {
    std::vector<uint8_t> out;
    hex_decode(hex, out);
    return out;
}

}

void run_identity_tests(const char* vectors_path) {
    JsonDocument doc;
    CHECK(deserializeJson(doc, slurp(vectors_path)) == DeserializationError::Ok);

    for (JsonObject item : doc["identity"].as<JsonArray>()) {
        DeviceKey key;
        const std::vector<uint8_t> seed = bytes(item["seed"].as<std::string>());
        CHECK(key.load(seed.data(), seed.size()));
        CHECK_EQ(key.public_hex(), item["public"].as<std::string>());
        CHECK_EQ(key.pairing_code(), item["pairing_code"].as<std::string>());
        CHECK_EQ(key.fingerprint(), item["fingerprint"].as<std::string>());
    }

    for (JsonObject item : doc["signatures"].as<JsonArray>()) {
        DeviceKey key;
        const std::vector<uint8_t> seed = bytes(item["seed"].as<std::string>());
        CHECK(key.load(seed.data(), seed.size()));
        const std::string body = item["body"].as<std::string>();
        SignedHeaders out;
        CHECK(key.sign(item["node"].as<std::string>(), item["method"].as<std::string>(), item["path"].as<std::string>(),
                       reinterpret_cast<const uint8_t*>(body.data()), body.size(), item["ts"].as<int64_t>(),
                       item["nonce"].as<std::string>(), out));
        CHECK_EQ(out.signature, item["signature"].as<std::string>());
        CHECK_EQ(out.ts, item["ts"].as<int64_t>());
    }

    JsonDocument wire;
    JsonObject vector = doc["manifest"].as<JsonObject>();
    wire["version"] = vector["version"];
    wire["size"] = vector["size"];
    wire["sha256"] = vector["sha256"];
    wire["sig"] = vector["sig"];
    std::string wire_json;
    serializeJson(wire, wire_json);
    FirmwareManifest manifest;
    const std::string signer_public = vector["public"].as<std::string>();
    CHECK(parse_manifest(wire_json, manifest));
    CHECK(verify_manifest(manifest, signer_public));
    FirmwareManifest forged = manifest;
    forged.version = "1.2.1";
    CHECK(!verify_manifest(forged, signer_public));
    forged = manifest;
    forged.size += 1;
    CHECK(!verify_manifest(forged, signer_public));
    forged = manifest;
    forged.sha256[0] = forged.sha256[0] == 'a' ? 'b' : 'a';
    CHECK(!verify_manifest(forged, signer_public));
    CHECK(!verify_manifest(manifest, std::string(64, '1')));
    CHECK(!verify_manifest(manifest, "zz"));

    DeviceKey key;
    uint8_t seed[32] = {7};
    CHECK(!key.load(seed, 31));
    CHECK(!key.load(nullptr, 32));
    CHECK(key.load(seed, 32));
    SignedHeaders out;
    const uint8_t body[1] = {0};
    CHECK(!key.sign("ab", "POST", "/x", body, 0, 1, "0123456789abcdef", out));
    CHECK(!key.sign("node-1", "post", "/x", body, 0, 1, "0123456789abcdef", out));
    CHECK(!key.sign("node-1", "POST", "", body, 0, 1, "0123456789abcdef", out));
    CHECK(!key.sign("node-1", "POST", "/x", body, 0, 1, "short", out));
    CHECK(!key.sign("node-1", "POST", "/x", body, 0, 1, "bad nonce chars!!!", out));
    CHECK(!key.sign("node-1", "POST", "/x\n", body, 0, 1, "0123456789abcdef", out));
    CHECK(key.sign("node-1", "POST", "/x", body, 0, 1, "0123456789abcdef", out));
    key.wipe();
    CHECK(!key.loaded());
    CHECK(!key.sign("node-1", "POST", "/x", body, 0, 1, "0123456789abcdef", out));
    CHECK(key.public_hex().empty());

    std::string message;
    CHECK(canonical("pc-uno", "POST", "/a", 5, "0123456789abcdef", std::string(64, 'a'), message));
    CHECK_EQ(message, std::string("nuxiva-node-v1\npc-uno\nPOST\n/a\n5\n0123456789abcdef\n") + std::string(64, 'a'));
    CHECK(!canonical("pc-uno", "POST", "/a", 5, "0123456789abcdef", std::string(64, 'A'), message));
    CHECK(!canonical(std::string(257, 'n'), "POST", "/a", 5, "0123456789abcdef", std::string(64, 'a'), message));
}
