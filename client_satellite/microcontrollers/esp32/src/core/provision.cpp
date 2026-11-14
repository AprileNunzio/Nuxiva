#include "provision.h"

#include <ArduinoJson.h>

#include "digest.h"
#include "hexutil.h"

namespace nuxiva_node {

namespace {

constexpr char PEM_BEGIN[] = "-----BEGIN CERTIFICATE-----";
constexpr char PEM_END[] = "-----END CERTIFICATE-----";

bool printable(const std::string& value, size_t min_length, size_t max_length) {
    if (value.size() < min_length || value.size() > max_length) {
        return false;
    }
    for (char c : value) {
        const unsigned char u = static_cast<unsigned char>(c);
        if (u < 0x20 || u == 0x7F) {
            return false;
        }
    }
    return true;
}

bool in_set(char c, bool lower, bool upper, bool digit, const char* extra) {
    if (lower && c >= 'a' && c <= 'z') {
        return true;
    }
    if (upper && c >= 'A' && c <= 'Z') {
        return true;
    }
    if (digit && c >= '0' && c <= '9') {
        return true;
    }
    for (const char* p = extra; *p != '\0'; ++p) {
        if (*p == c) {
            return true;
        }
    }
    return false;
}

bool all_in(const std::string& value, bool lower, bool upper, bool digit, const char* extra) {
    for (char c : value) {
        if (!in_set(c, lower, upper, digit, extra)) {
            return false;
        }
    }
    return true;
}

bool valid_password(const std::string& pass) {
    if (pass.empty()) {
        return true;
    }
    if (pass.size() < 8 || pass.size() > 63) {
        return false;
    }
    for (char c : pass) {
        const unsigned char u = static_cast<unsigned char>(c);
        if (u < 0x20 || u > 0x7E) {
            return false;
        }
    }
    return true;
}

bool valid_node_id(const std::string& id) {
    if (id.size() < 3 || id.size() > 48) {
        return false;
    }
    const char first = id[0];
    if (!((first >= 'a' && first <= 'z') || (first >= '0' && first <= '9'))) {
        return false;
    }
    return all_in(id, true, false, true, "-");
}

int b64_value(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }
    if (c >= 'a' && c <= 'z') {
        return c - 'a' + 26;
    }
    if (c >= '0' && c <= '9') {
        return c - '0' + 52;
    }
    if (c == '+') {
        return 62;
    }
    if (c == '/') {
        return 63;
    }
    return -1;
}

}

const char* provision_error_code(ProvisionError error) {
    switch (error) {
        case ProvisionError::Ok: return "ok";
        case ProvisionError::TooLarge: return "too_large";
        case ProvisionError::Json: return "json";
        case ProvisionError::Command: return "command";
        case ProvisionError::Ssid: return "ssid";
        case ProvisionError::Password: return "password";
        case ProvisionError::Server: return "server";
        case ProvisionError::CaCertificate: return "ca_certificate";
        case ProvisionError::CaPin: return "ca_pin";
        case ProvisionError::Token: return "token";
        case ProvisionError::NodeId: return "node_id";
        case ProvisionError::Name: return "name";
        case ProvisionError::Pin: return "pin";
    }
    return "unknown";
}

bool base64_decode(const std::string& text, std::vector<uint8_t>& out) {
    out.clear();
    uint32_t buffer = 0;
    int bits = 0;
    size_t padding = 0;
    for (char c : text) {
        if (c == '\n' || c == '\r' || c == ' ' || c == '\t') {
            continue;
        }
        if (c == '=') {
            ++padding;
            continue;
        }
        const int value = b64_value(c);
        if (value < 0 || padding > 0) {
            out.clear();
            return false;
        }
        buffer = (buffer << 6) | static_cast<uint32_t>(value);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out.push_back(static_cast<uint8_t>((buffer >> bits) & 0xFF));
        }
    }
    if (padding > 2 || out.empty()) {
        out.clear();
        return false;
    }
    return true;
}

bool pem_to_der(const std::string& pem, std::vector<uint8_t>& der) {
    der.clear();
    if (pem.size() > MAX_CA_PEM) {
        return false;
    }
    const size_t begin = pem.find(PEM_BEGIN);
    const size_t end = pem.find(PEM_END);
    if (begin != 0 || end == std::string::npos || end <= sizeof(PEM_BEGIN)) {
        return false;
    }
    const size_t tail = end + sizeof(PEM_END) - 1;
    for (size_t i = tail; i < pem.size(); ++i) {
        const char c = pem[i];
        if (c != '\n' && c != '\r' && c != ' ' && c != '\0') {
            return false;
        }
    }
    const std::string body = pem.substr(sizeof(PEM_BEGIN) - 1, end - (sizeof(PEM_BEGIN) - 1));
    return base64_decode(body, der);
}

bool parse_server(const std::string& url, std::string& host, uint16_t& port) {
    static const std::string scheme = "https://";
    host.clear();
    port = 443;
    if (url.size() <= scheme.size() || url.size() > 270 || url.compare(0, scheme.size(), scheme) != 0) {
        return false;
    }
    const std::string rest = url.substr(scheme.size());
    const size_t colon = rest.find(':');
    host = colon == std::string::npos ? rest : rest.substr(0, colon);
    if (host.empty() || host.size() > 253 || !all_in(host, true, true, true, ".-") || host.front() == '.' ||
        host.front() == '-' || host.back() == '-') {
        host.clear();
        return false;
    }
    if (colon != std::string::npos) {
        const std::string digits = rest.substr(colon + 1);
        if (digits.empty() || digits.size() > 5 || !all_in(digits, false, false, true, "")) {
            host.clear();
            return false;
        }
        const long value = strtol(digits.c_str(), nullptr, 10);
        if (value < 1 || value > 65535) {
            host.clear();
            return false;
        }
        port = static_cast<uint16_t>(value);
    }
    return true;
}

ProvisionError parse_provision(const std::string& line, Provision& out) {
    if (line.size() > MAX_PROVISION_LINE) {
        return ProvisionError::TooLarge;
    }
    JsonDocument doc;
    if (deserializeJson(doc, line) != DeserializationError::Ok || !doc.is<JsonObject>()) {
        return ProvisionError::Json;
    }
    const std::string cmd = doc["cmd"] | "";
    if (cmd != "provision" || (doc["v"] | 0) != 1) {
        return ProvisionError::Command;
    }
    Provision p;
    p.ssid = std::string(doc["ssid"] | "");
    p.pass = std::string(doc["pass"] | "");
    p.server = std::string(doc["server"] | "");
    p.ca_pem = std::string(doc["ca"] | "");
    p.token = std::string(doc["token"] | "");
    p.node_id = std::string(doc["id"] | "");
    p.name = std::string(doc["name"] | "");
    p.pin = std::string(doc["pin"] | "");
    if (!printable(p.ssid, 1, 32)) {
        return ProvisionError::Ssid;
    }
    if (!valid_password(p.pass)) {
        return ProvisionError::Password;
    }
    if (!parse_server(p.server, p.host, p.port)) {
        return ProvisionError::Server;
    }
    if (!is_lower_hex(p.pin, 64)) {
        return ProvisionError::Pin;
    }
    std::vector<uint8_t> der;
    if (!pem_to_der(p.ca_pem, der)) {
        return ProvisionError::CaCertificate;
    }
    const Digest digest = sha256(der.data(), der.size());
    if (!constant_time_equal(hex_encode(digest.data(), digest.size()), p.pin)) {
        return ProvisionError::CaPin;
    }
    if (p.token.size() < 20 || p.token.size() > 128 || !all_in(p.token, true, true, true, "_-")) {
        return ProvisionError::Token;
    }
    if (!valid_node_id(p.node_id)) {
        return ProvisionError::NodeId;
    }
    if (!printable(p.name, 1, 60)) {
        return ProvisionError::Name;
    }
    out = p;
    return ProvisionError::Ok;
}

}
