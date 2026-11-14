#include "canonical.h"

#include "hexutil.h"

namespace nuxiva_node {

namespace {

bool clean(const std::string& value, size_t min_length) {
    if (value.size() < min_length || value.size() > MAX_FIELD) {
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

bool nonce_chars(const std::string& nonce) {
    for (char c : nonce) {
        const bool ok = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '-' || c == '_';
        if (!ok) {
            return false;
        }
    }
    return true;
}

bool upper_method(const std::string& method) {
    if (method.empty() || method.size() > 8) {
        return false;
    }
    for (char c : method) {
        if (c < 'A' || c > 'Z') {
            return false;
        }
    }
    return true;
}

}

bool canonical(const std::string& node, const std::string& method, const std::string& path, int64_t ts,
               const std::string& nonce, const std::string& body_sha256, std::string& out) {
    out.clear();
    if (!clean(node, 3) || !clean(path, 1) || !clean(nonce, 16) || !upper_method(method) || !nonce_chars(nonce) ||
        !is_lower_hex(body_sha256, 64)) {
        return false;
    }
    out.reserve(160 + node.size() + path.size());
    out += DOMAIN;
    out += '\n';
    out += node;
    out += '\n';
    out += method;
    out += '\n';
    out += path;
    out += '\n';
    out += std::to_string(static_cast<long long>(ts));
    out += '\n';
    out += nonce;
    out += '\n';
    out += body_sha256;
    return true;
}

}
