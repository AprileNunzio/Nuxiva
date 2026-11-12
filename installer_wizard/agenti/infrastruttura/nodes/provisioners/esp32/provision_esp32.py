# Nuxiva OS v5.0.0 — ESP32 Provisioning & Firmware Configuration Generator
import json

def generate_config(wifi_ssid, wifi_pass, parent_ip, node_id="esp32-node"):
    return {
        "version": "5.0.0",
        "node_id": node_id,
        "wifi": {"ssid": wifi_ssid, "key": wifi_pass},
        "mesh": {"parent_ip": parent_ip, "telemetry_port": 8080, "p2p_stream": True},
        "sensors": {"temp_dht22": True, "mic_i2s": True}
    }

if __name__ == "__main__":
    print(json.dumps(generate_config("Nuxiva-Mesh", "secret", "192.168.1.10"), indent=2))
