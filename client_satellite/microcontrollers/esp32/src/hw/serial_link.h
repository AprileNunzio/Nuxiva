#pragma once

#include <string>

namespace nuxiva_hw {

class SerialLink {
public:
    bool poll(std::string& line);
    void reply(const std::string& json);

private:
    std::string buffer_;
    bool overflow_ = false;
};

}
