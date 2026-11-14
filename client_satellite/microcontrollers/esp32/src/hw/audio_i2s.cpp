#include "audio_i2s.h"

#include <Arduino.h>
#include <driver/i2s.h>

#include "settings.h"

namespace nuxiva_hw {

namespace {

constexpr i2s_port_t PORT = I2S_NUM_0;

}

bool AudioIn::begin() {
    if (running_) {
        return true;
    }
    i2s_config_t config = {};
    config.mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_RX);
    config.sample_rate = SAMPLE_RATE;
    config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    config.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    config.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    config.dma_buf_count = 8;
    config.dma_buf_len = FRAME_SAMPLES;
    config.use_apll = false;
    config.tx_desc_auto_clear = false;
    config.fixed_mclk = 0;
    i2s_pin_config_t pins = {};
    pins.mck_io_num = I2S_PIN_NO_CHANGE;
    pins.bck_io_num = NUXIVA_I2S_BCLK;
    pins.ws_io_num = NUXIVA_I2S_WS;
    pins.data_out_num = I2S_PIN_NO_CHANGE;
    pins.data_in_num = NUXIVA_I2S_DIN;
    if (i2s_driver_install(PORT, &config, 0, nullptr) != ESP_OK) {
        return false;
    }
    if (i2s_set_pin(PORT, &pins) != ESP_OK) {
        i2s_driver_uninstall(PORT);
        return false;
    }
    i2s_zero_dma_buffer(PORT);
    running_ = true;
    return true;
}

void AudioIn::end() {
    if (running_) {
        i2s_driver_uninstall(PORT);
        running_ = false;
    }
}

bool AudioIn::read_frame(int16_t* out, size_t samples, uint32_t timeout_ms) {
    if (!running_ || samples == 0 || samples > FRAME_SAMPLES) {
        return false;
    }
    int32_t raw[FRAME_SAMPLES];
    size_t wanted = samples * sizeof(int32_t);
    size_t filled = 0;
    uint8_t* target = reinterpret_cast<uint8_t*>(raw);
    const uint32_t started = millis();
    while (filled < wanted) {
        size_t got = 0;
        if (i2s_read(PORT, target + filled, wanted - filled, &got, pdMS_TO_TICKS(timeout_ms)) != ESP_OK) {
            return false;
        }
        filled += got;
        if (got == 0 && millis() - started > timeout_ms) {
            return false;
        }
    }
    for (size_t i = 0; i < samples; ++i) {
        out[i] = blocker_.process(raw[i] >> NUXIVA_I2S_SHIFT);
    }
    return true;
}

}
