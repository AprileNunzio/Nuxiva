#include "http_date.h"

#include <string.h>

namespace nuxiva_node {

namespace {

const char* const MONTHS[12] = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};

bool digits(const std::string& text, size_t at, size_t count, int& value) {
    if (at + count > text.size()) {
        return false;
    }
    value = 0;
    for (size_t i = 0; i < count; ++i) {
        const char c = text[at + i];
        if (c < '0' || c > '9') {
            return false;
        }
        value = value * 10 + (c - '0');
    }
    return true;
}

int64_t days_from_civil(int64_t y, int64_t m, int64_t d) {
    y -= m <= 2;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const int64_t yoe = y - era * 400;
    const int64_t doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const int64_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + doe - 719468;
}

}

bool parse_http_date(const std::string& text, int64_t& epoch_seconds) {
    if (text.size() != 29 || text[3] != ',' || text[4] != ' ' || text[7] != ' ' || text[11] != ' ' || text[16] != ' ' ||
        text[19] != ':' || text[22] != ':' || text.compare(25, 4, " GMT") != 0) {
        return false;
    }
    int day, year, hour, minute, second;
    if (!digits(text, 5, 2, day) || !digits(text, 12, 4, year) || !digits(text, 17, 2, hour) ||
        !digits(text, 20, 2, minute) || !digits(text, 23, 2, second)) {
        return false;
    }
    int month = 0;
    for (int i = 0; i < 12; ++i) {
        if (text.compare(8, 3, MONTHS[i]) == 0) {
            month = i + 1;
        }
    }
    if (month == 0 || day < 1 || day > 31 || hour > 23 || minute > 59 || second > 60 || year < 2024 || year > 2200) {
        return false;
    }
    epoch_seconds = days_from_civil(year, month, day) * 86400 + hour * 3600 + minute * 60 + (second > 59 ? 59 : second);
    return true;
}

bool clock_needs_sync(int64_t local_epoch, int64_t server_epoch, int64_t tolerance_seconds) {
    const int64_t delta = local_epoch > server_epoch ? local_epoch - server_epoch : server_epoch - local_epoch;
    return delta > tolerance_seconds;
}

}
