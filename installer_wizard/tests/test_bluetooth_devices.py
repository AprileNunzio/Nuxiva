import unittest

from features.bluetooth import classes, schema, store
from features.bluetooth.adapter import parse_info
from features.bluetooth.router import choose
from features.bluetooth.service import gamepads

MAC_A = "AA:BB:CC:DD:EE:01"
MAC_B = "AA:BB:CC:DD:EE:02"
INFO = """Device AA:BB:CC:DD:EE:01 (public)
	Name: Pad
	Alias: Wireless Controller
	Class: 0x00002508
	Icon: input-gaming
	Paired: yes
	Bonded: yes
	Trusted: yes
	Blocked: no
	Connected: yes
	UUID: Human Interface Device... (00001124-0000-1000-8000-00805f9b34fb)
	Battery Percentage: 0x4b (75)
	RSSI: -52
"""


def device(mac: str, kind: str, connected: bool = True, **extra) -> dict:
    caps = classes.capabilities({"uuids": []}, kind)
    return {"mac": mac, "name": extra.pop("name", kind), "kind": kind, "capabilities": caps, "connected": connected,
            "paired": True, **extra}


class ClassifyTest(unittest.TestCase):
    def test_parse_info_extracts_hid_details(self):
        dev = classes.describe(parse_info(MAC_A, INFO))
        self.assertEqual(dev["kind"], "gamepad")
        self.assertEqual(dev["capabilities"], ["gamepad"])
        self.assertEqual(dev["battery"], 75)
        self.assertEqual(dev["rssi"], -52)
        self.assertEqual(dev["name"], "Wireless Controller")

    def test_class_of_device_detects_peripherals(self):
        self.assertEqual(classes.kind_of({"cod": 0x002580, "name": "MX"}), "mouse")
        self.assertEqual(classes.kind_of({"cod": 0x002540, "name": "K380"}), "keyboard")
        self.assertEqual(classes.kind_of({"cod": 0x002504, "name": "Stick"}), "joystick")
        self.assertEqual(classes.kind_of({"cod": 0x240414, "name": "Box"}), "speaker")
        self.assertEqual(classes.kind_of({"cod": 0x240404, "name": "Ear"}), "headset")

    def test_name_promotes_hid_to_gamepad(self):
        self.assertEqual(classes.kind_of({"icon": "input-keyboard", "name": "8BitDo Pro 2"}), "gamepad")

    def test_uuid_fallback_adds_audio(self):
        dev = classes.describe({"name": "x", "uuids": ["0000110b", "0000111e"]})
        self.assertEqual(dev["kind"], "headset")
        self.assertEqual(dev["capabilities"], ["audio_out", "audio_in"])


class SchemaTest(unittest.TestCase):
    def test_settings_apply_only_to_matching_capabilities(self):
        keys = {s["key"] for s in schema.SETTINGS if schema.applies(s, ["gamepad"])}
        self.assertIn("deadzone", keys)
        self.assertIn("alias", keys)
        self.assertNotIn("voice_input", keys)
        self.assertNotIn("profile", {s["key"] for s in schema.SETTINGS if schema.applies(s, ["audio_out"])})

    def test_update_validates_and_clamps(self):
        result = schema.update({}, {"deadzone": 99, "invert_y": True, "alias": "  <b>Volante</b>\u0007 "})
        self.assertEqual(result["deadzone"], 40)
        self.assertTrue(result["invert_y"])
        self.assertEqual(result["alias"], "bVolante/b")
        for bad in ({"deadzone": "5"}, {"invert_y": 1}, {"voice_input": "always"}, {"nope": 1}, [1]):
            with self.assertRaises(ValueError):
                schema.update({}, bad)

    def test_legacy_role_is_migrated(self):
        self.assertEqual(schema.resolve({"role": "input"})["output_use"], "never")
        self.assertEqual(schema.resolve({"role": "off"})["voice_input"], "never")


class StoreTest(unittest.TestCase):
    def setUp(self):
        store.SEALED.data_path.unlink(missing_ok=True)
        store.LEGACY_FILE.unlink(missing_ok=True)

    def test_store_is_encrypted_and_round_trips(self):
        store.update_device(MAC_A, {"voice_input": "preferred"})
        raw = store.SEALED.data_path.read_bytes()
        self.assertNotIn(MAC_A.encode(), raw)
        self.assertEqual(store.settings(store.load(), MAC_A)["voice_input"], "preferred")

    def test_legacy_plaintext_is_migrated_and_removed(self):
        store.LEGACY_FILE.write_text('{"devices": {"%s": {"role": "output"}}, "output_order": ["%s"]}' % (MAC_A, MAC_A))
        data = store.load()
        self.assertFalse(store.LEGACY_FILE.exists())
        self.assertEqual(data["output_order"], [MAC_A])
        self.assertEqual(store.settings(data, MAC_A)["voice_input"], "never")

    def test_globals_reject_unknown_or_bad_values(self):
        for bad in ({"auto_switch": "yes"}, {"output_order": ["nope"]}, {"devices": {}}, [1]):
            with self.assertRaises(ValueError):
                store.update_globals(bad)


class RoutingTest(unittest.TestCase):
    def data(self, **devices) -> dict:
        return {"devices": devices, "output_order": [MAC_A, MAC_B], "input_order": [MAC_A, MAC_B],
                "auto_switch": True, "auto_connect": True, "announce": True}

    def test_preferred_microphone_wins_over_order(self):
        devs = [device(MAC_A, "headset"), device(MAC_B, "microphone")]
        choice = choose(devs, self.data(**{MAC_B: {"voice_input": "preferred"}}))
        self.assertEqual(choice["input"], MAC_B)
        self.assertEqual(choice["output"], MAC_A)

    def test_never_and_auto_switch_off(self):
        devs = [device(MAC_A, "speaker"), device(MAC_B, "speaker")]
        data = self.data(**{MAC_A: {"output_use": "never"}})
        self.assertEqual(choose(devs, data)["output"], MAC_B)
        data["auto_switch"] = False
        self.assertIsNone(choose(devs, data)["output"])

    def test_quality_profile_excludes_headset_mic(self):
        devs = [device(MAC_A, "headset")]
        self.assertIsNone(choose(devs, self.data(**{MAC_A: {"profile": "quality"}}))["input"])


class GamepadTest(unittest.TestCase):
    def setUp(self):
        store.SEALED.data_path.unlink(missing_ok=True)

    def test_only_connected_enabled_gamepads_are_published(self):
        store.update_device(MAC_A, {"player_slot": 2, "invert_y": True})
        store.update_device(MAC_B, {"games_enabled": False})
        devs = [device(MAC_A, "gamepad", name="Pad"), device(MAC_B, "joystick"), device("AA:BB:CC:DD:EE:03", "mouse")]
        pads = gamepads(devs)
        self.assertEqual(len(pads), 1)
        self.assertEqual(pads[0]["slot"], 2)
        self.assertTrue(pads[0]["invert_y"])


if __name__ == "__main__":
    unittest.main()
