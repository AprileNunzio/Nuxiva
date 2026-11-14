#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

namespace nuxiva_node {

constexpr size_t MAX_PROVISION_LINE = 6144;
constexpr size_t MAX_CA_PEM = 4096;

struct Provision {
    std::string ssid;
    std::string pass;
    std::string server;
    std::string host;
    uint16_t port = 443;
    std::string ca_pem;
    std::string token;
    std::string node_id;
    std::string name;
    std::string pin;
};

enum class ProvisionError {
    Ok,
    TooLarge,
    Json,
    Command,
    Ssid,
    Password,
    Server,
    CaCertificate,
    CaPin,
    Token,
    NodeId,
    Name,
    Pin,
};

const char* provision_error_code(ProvisionError error);
bool base64_decode(const std::string& text, std::vector<uint8_t>& out);
bool pem_to_der(const std::string& pem, std::vector<uint8_t>& der);
bool parse_server(const std::string& url, std::string& host, uint16_t& port);
ProvisionError parse_provision(const std::string& line, Provision& out);

}
