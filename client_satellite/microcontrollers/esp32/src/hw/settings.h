#pragma once

#include <stdint.h>

#ifndef NUXIVA_FIRMWARE_VERSION
#define NUXIVA_FIRMWARE_VERSION "1.0.0"
#endif

#ifndef NUXIVA_I2S_BCLK
#define NUXIVA_I2S_BCLK 14
#endif

#ifndef NUXIVA_I2S_WS
#define NUXIVA_I2S_WS 15
#endif

#ifndef NUXIVA_I2S_DIN
#define NUXIVA_I2S_DIN 16
#endif

#ifndef NUXIVA_I2S_SHIFT
#define NUXIVA_I2S_SHIFT 14
#endif

#ifndef NUXIVA_RELAY_PIN_LIST
#define NUXIVA_RELAY_PIN_LIST 4, 5
#endif

#ifndef NUXIVA_RELAY_ACTIVE_LOW
#define NUXIVA_RELAY_ACTIVE_LOW 0
#endif

#ifndef NUXIVA_RELAY_MAX_ON_MS
#define NUXIVA_RELAY_MAX_ON_MS 3600000UL
#endif

#ifndef NUXIVA_FAILSAFE_MS
#define NUXIVA_FAILSAFE_MS 300000UL
#endif

#ifndef NUXIVA_FW_PUBKEY_HEX
#define NUXIVA_FW_PUBKEY_HEX ""
#endif

#ifndef NUXIVA_STREAM_ALWAYS
#define NUXIVA_STREAM_ALWAYS 0
#endif

#ifndef NUXIVA_RESET_PIN
#define NUXIVA_RESET_PIN 0
#endif

namespace nuxiva_hw {

constexpr uint32_t SAMPLE_RATE = 16000;
constexpr size_t FRAME_SAMPLES = 320;
constexpr uint32_t HEARTBEAT_MS = 30000;
constexpr uint32_t HTTP_TIMEOUT_MS = 10000;
constexpr uint32_t INBOX_TIMEOUT_MS = 40000;
constexpr uint32_t RESET_HOLD_MS = 5000;
constexpr uint32_t UPDATE_CHECK_MS = 6UL * 3600UL * 1000UL;
constexpr int64_t CLOCK_TOLERANCE_S = 5;

}
