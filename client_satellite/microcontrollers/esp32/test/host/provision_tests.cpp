#include <ArduinoJson.h>

#include <string>

#include "check.h"
#include "digest.h"
#include "firmware_manifest.h"
#include "hexutil.h"
#include "provision.h"

using namespace nuxiva_node;

namespace {

std::string base64(const std::vector<uint8_t>& data) {
    static const char table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    size_t i = 0;
    for (; i + 2 < data.size(); i += 3) {
        const uint32_t v = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
        out += table[(v >> 18) & 63];
        out += table[(v >> 12) & 63];
        out += table[(v >> 6) & 63];
        out += table[v & 63];
    }
    if (i + 1 == data.size()) {
        const uint32_t v = data[i] << 16;
        out += table[(v >> 18) & 63];
        out += table[(v >> 12) & 63];
        out += "==";
    } else if (i + 2 == data.size()) {
        const uint32_t v = (data[i] << 16) | (data[i + 1] << 8);
        out += table[(v >> 18) & 63];
        out += table[(v >> 12) & 63];
        out += table[(v >> 6) & 63];
        out += '=';
    }
    return out;
}

struct Fixture {
    std::string pem;
    std::string pin;
};

Fixture fixture() {
    std::vector<uint8_t> der;
    for (int i = 0; i < 700; ++i) {
        der.push_back(static_cast<uint8_t>((i * 37 + 11) & 0xFF));
    }
    const std::string body = base64(der);
    std::string pem = "-----BEGIN CERTIFICATE-----\n";
    for (size_t i = 0; i < body.size(); i += 64) {
        pem += body.substr(i, 64) + "\n";
    }
    pem += "-----END CERTIFICATE-----\n";
    const Digest d = sha256(der.data(), der.size());
    return {pem, hex_encode(d.data(), d.size())};
}

std::string line(const Fixture& f, const char* key = nullptr, const char* value = nullptr) {
    JsonDocument doc;
    doc["cmd"] = "provision";
    doc["v"] = 1;
    doc["ssid"] = "Casa Nuxiva";
    doc["pass"] = "correct horse battery";
    doc["server"] = "https://nuxiva.local:8443";
    doc["ca"] = f.pem;
    doc["token"] = "abcdefghijklmnopqrstuvwxyz012345";
    doc["id"] = "esp32-cucina";
    doc["name"] = "Cucina";
    doc["pin"] = f.pin;
    if (key != nullptr) {
        doc[key] = value;
    }
    std::string out;
    serializeJson(doc, out);
    return out;
}

}

void run_provision_tests() {
    const Fixture f = fixture();
    Provision p;
    CHECK(parse_provision(line(f), p) == ProvisionError::Ok);
    CHECK_EQ(p.host, std::string("nuxiva.local"));
    CHECK_EQ(p.port, 8443);
    CHECK_EQ(p.node_id, std::string("esp32-cucina"));

    Provision untouched;
    CHECK(parse_provision(line(f, "pin", std::string(64, '0').c_str()), untouched) == ProvisionError::CaPin);
    CHECK(untouched.node_id.empty());
    CHECK(parse_provision(line(f, "pin", "XYZ"), untouched) == ProvisionError::Pin);
    CHECK(parse_provision(line(f, "ssid", ""), untouched) == ProvisionError::Ssid);
    CHECK(parse_provision(line(f, "pass", "short"), untouched) == ProvisionError::Password);
    CHECK(parse_provision(line(f, "server", "http://nuxiva.local"), untouched) == ProvisionError::Server);
    CHECK(parse_provision(line(f, "server", "https://nuxiva.local/path"), untouched) == ProvisionError::Server);
    CHECK(parse_provision(line(f, "server", "https://nuxiva.local:0"), untouched) == ProvisionError::Server);
    CHECK(parse_provision(line(f, "server", "https://nuxiva.local:99999"), untouched) == ProvisionError::Server);
    CHECK(parse_provision(line(f, "token", "short"), untouched) == ProvisionError::Token);
    CHECK(parse_provision(line(f, "token", "abcdefghijklmnopqrstuvwxyz0123!!"), untouched) == ProvisionError::Token);
    CHECK(parse_provision(line(f, "id", "Bad Id"), untouched) == ProvisionError::NodeId);
    CHECK(parse_provision(line(f, "id", "ab"), untouched) == ProvisionError::NodeId);
    CHECK(parse_provision(line(f, "name", ""), untouched) == ProvisionError::Name);
    CHECK(parse_provision(line(f, "ca", "not a pem"), untouched) == ProvisionError::CaCertificate);
    CHECK(parse_provision(line(f, "cmd", "wipe"), untouched) == ProvisionError::Command);
    CHECK(parse_provision("{not json", untouched) == ProvisionError::Json);
    CHECK(parse_provision("[]", untouched) == ProvisionError::Json);
    CHECK(parse_provision(std::string(MAX_PROVISION_LINE + 1, 'a'), untouched) == ProvisionError::TooLarge);

    std::string host;
    uint16_t port = 0;
    CHECK(parse_server("https://192.168.1.10", host, port) && port == 443 && host == "192.168.1.10");
    CHECK(!parse_server("https://", host, port));
    CHECK(!parse_server("https://-bad.example", host, port));
    CHECK(!parse_server("https://exa mple.com", host, port));
    CHECK(!parse_server("ftp://x.example", host, port));

    std::vector<uint8_t> out;
    CHECK(base64_decode("TWFu", out) && out.size() == 3);
    CHECK(base64_decode("TWE=", out) && out.size() == 2);
    CHECK(!base64_decode("TW!u", out));
    CHECK(!base64_decode("TW=u", out));
    CHECK(!base64_decode("", out));
    CHECK(!pem_to_der(f.pem + "trailing", out));
    CHECK(!pem_to_der("x" + f.pem, out));
}

void run_manifest_tests() {
    CHECK(is_newer("1.2.0", "1.1.9"));
    CHECK(is_newer("2.0.0", "1.99.99"));
    CHECK(!is_newer("1.0.0", "1.0.0"));
    CHECK(!is_newer("1.0.0", "1.0.1"));
    CHECK(!is_newer("garbage", "1.0.0"));
    CHECK(is_newer("1.0.1", "garbage"));
    uint32_t a, b, c;
    CHECK(!parse_version("1.2", a, b, c));
    CHECK(!parse_version("1.2.3.4", a, b, c));
    CHECK(!parse_version("1..3", a, b, c));
    CHECK(!parse_version("a.b.c", a, b, c));
    CHECK(parse_version("10.20.30", a, b, c) && a == 10 && b == 20 && c == 30);

    FirmwareManifest m;
    const std::string good = std::string("{\"version\":\"1.2.0\",\"size\":1000,\"sha256\":\"") + std::string(64, 'a') +
                             "\",\"sig\":\"" + std::string(128, 'b') + "\"}";
    CHECK(parse_manifest(good, m));
    CHECK_EQ(m.size, 1000u);
    CHECK(!parse_manifest("{}", m));
    CHECK(!parse_manifest(std::string(MAX_MANIFEST_BYTES + 1, ' '), m));
    CHECK(!parse_manifest(std::string("{\"version\":\"1.2.0\",\"size\":0,\"sha256\":\"") + std::string(64, 'a') +
                              "\",\"sig\":\"" + std::string(128, 'b') + "\"}", m));
    CHECK(!parse_manifest(std::string("{\"version\":\"1.2.0\",\"size\":99999999,\"sha256\":\"") + std::string(64, 'a') +
                              "\",\"sig\":\"" + std::string(128, 'b') + "\"}", m));
    CHECK(!verify_manifest(m, std::string(64, 'c')));
}
