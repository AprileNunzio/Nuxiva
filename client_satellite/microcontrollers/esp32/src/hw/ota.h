#pragma once

#include <string>

#include "transport.h"

namespace nuxiva_hw {

enum class OtaResult { Disabled, Unreachable, UpToDate, Rejected, Failed, Applied };

OtaResult ota_check_and_apply(Transport& transport, const std::string& current_version);
const char* ota_result_code(OtaResult result);

}
