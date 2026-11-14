#include "store.h"

#include <Preferences.h>

#include "provision.h"

namespace nuxiva_hw {

namespace {

constexpr char NAMESPACE[] = "nuxiva";

std::string get(Preferences& prefs, const char* key) {
    const String value = prefs.getString(key, "");
    return std::string(value.c_str());
}

}

bool Store::load(Stored& out) {
    Preferences prefs;
    if (!prefs.begin(NAMESPACE, true)) {
        return false;
    }
    out.ssid = get(prefs, "ssid");
    out.pass = get(prefs, "pass");
    out.server = get(prefs, "server");
    out.ca_pem = get(prefs, "ca");
    out.node_id = get(prefs, "id");
    out.name = get(prefs, "name");
    out.enroll_token = get(prefs, "enroll");
    out.node_token = get(prefs, "token");
    prefs.end();
    return nuxiva_node::parse_server(out.server, out.host, out.port) && !out.ssid.empty() && !out.node_id.empty() &&
           !out.ca_pem.empty();
}

bool Store::save_provision(const Stored& data) {
    Preferences prefs;
    if (!prefs.begin(NAMESPACE, false)) {
        return false;
    }
    const bool ok = prefs.putString("ssid", data.ssid.c_str()) > 0 && prefs.putString("pass", data.pass.c_str()) >= 0 &&
                    prefs.putString("server", data.server.c_str()) > 0 && prefs.putString("ca", data.ca_pem.c_str()) > 0 &&
                    prefs.putString("id", data.node_id.c_str()) > 0 && prefs.putString("name", data.name.c_str()) > 0 &&
                    prefs.putString("enroll", data.enroll_token.c_str()) > 0 && prefs.putString("token", "") >= 0;
    prefs.end();
    return ok;
}

bool Store::save_node_token(const std::string& token) {
    Preferences prefs;
    if (!prefs.begin(NAMESPACE, false)) {
        return false;
    }
    const bool ok = prefs.putString("token", token.c_str()) > 0;
    prefs.end();
    return ok;
}

bool Store::clear_enroll_token() {
    Preferences prefs;
    if (!prefs.begin(NAMESPACE, false)) {
        return false;
    }
    const bool ok = prefs.putString("enroll", "") >= 0;
    prefs.end();
    return ok;
}

bool Store::load_seed(uint8_t seed[32]) {
    Preferences prefs;
    if (!prefs.begin(NAMESPACE, true)) {
        return false;
    }
    const size_t read = prefs.getBytes("seed", seed, 32);
    prefs.end();
    return read == 32;
}

bool Store::save_seed(const uint8_t seed[32]) {
    Preferences prefs;
    if (!prefs.begin(NAMESPACE, false)) {
        return false;
    }
    const bool ok = prefs.putBytes("seed", seed, 32) == 32;
    prefs.end();
    return ok;
}

void Store::wipe() {
    Preferences prefs;
    if (prefs.begin(NAMESPACE, false)) {
        prefs.clear();
        prefs.end();
    }
}

}
