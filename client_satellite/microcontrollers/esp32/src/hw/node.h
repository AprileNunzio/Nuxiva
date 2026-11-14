#pragma once

#include <stdint.h>

#include <mutex>
#include <string>

#include "action.h"
#include "audio_i2s.h"
#include "ear_link.h"
#include "relay_bank.h"
#include "serial_link.h"
#include "signer.h"
#include "store.h"
#include "transport.h"

namespace nuxiva_hw {

class Node {
public:
    Node();
    void setup();
    void loop();

    void audio_loop();
    void inbox_loop();

private:
    void boot_reset_check();
    void handle_serial();
    void provision(const std::string& line);
    void announce_info(const char* event);
    bool connect_wifi();
    bool enroll();
    void start_services();
    void heartbeat();
    void apply(const nuxiva_node::Action& action);
    void flush_relays();
    void blink();
    std::string heartbeat_body();
    void touch_ok();

    Store store_;
    Stored stored_;
    nuxiva_node::DeviceKey key_;
    Transport transport_;
    EarLink ear_;
    SerialLink serial_;
    nuxiva_node::RelayBank relays_;
    std::mutex relay_lock_;
    bool provisioned_ = false;
    bool services_ = false;
    bool update_requested_ = false;
    bool restart_requested_ = false;
    uint32_t last_heartbeat_ = 0;
    uint32_t last_ok_ = 0;
    uint32_t last_update_check_ = 0;
    uint32_t last_wifi_try_ = 0;
    uint32_t last_enroll_try_ = 0;
    volatile uint32_t ok_stamp_ = 0;
};

Node& node();

}
