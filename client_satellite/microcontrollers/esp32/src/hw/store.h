#pragma once

#include <stddef.h>
#include <stdint.h>

#include <string>

namespace nuxiva_hw {

struct Stored {
    std::string ssid;
    std::string pass;
    std::string server;
    std::string host;
    uint16_t port = 443;
    std::string ca_pem;
    std::string node_id;
    std::string name;
    std::string enroll_token;
    std::string node_token;
};

class Store {
public:
    bool load(Stored& out);
    bool save_provision(const Stored& data);
    bool save_node_token(const std::string& token);
    bool clear_enroll_token();
    bool load_seed(uint8_t seed[32]);
    bool save_seed(const uint8_t seed[32]);
    void wipe();
};

}
