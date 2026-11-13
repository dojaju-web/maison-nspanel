"""Réglages du panneau et détection des capteurs de l'aspirateur (sans Home Assistant)."""
import importlib
import os
import sys
import types
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "custom_components")
pkg = types.ModuleType("maison_nspanel")
pkg.__path__ = [os.path.join(ROOT, "maison_nspanel")]
sys.modules.setdefault("maison_nspanel", pkg)
settings = importlib.import_module("maison_nspanel.settings")
vacuum = importlib.import_module("maison_nspanel.vacuum")


class Entry:
    def __init__(self, options=None, data=None):
        self.options = options or {}
        self.data = data or {}


class Settings(unittest.TestCase):
    def test_defaults(self):
        s = settings.current_settings(Entry(data={"weather_entity": "weather.maison"}))
        self.assertEqual(s["weather_entity"], "weather.maison")
        self.assertEqual(s["style"], "verre")
        self.assertTrue(s["air_enabled"])
        self.assertEqual(s["vacuum_entity"], "")
        self.assertEqual(len(s["sections"]), 2)

    def test_clean_rejects(self):
        with self.assertRaises(ValueError):
            settings.clean_settings({"style": "rose"})
        with self.assertRaises(ValueError):
            settings.clean_settings({"vac_battery": "pasuneentite"})
        with self.assertRaises(ValueError):
            settings.clean_settings({"vigilance_min": "bleu"})

    def test_apply_and_clear(self):
        clean = settings.clean_settings({
            "vacuum_entity": " vacuum.cookie ", "vac_battery": "sensor.b", "style": "ardoise",
            "air_enabled": False, "inconnu": 1,
            "rappels": [{"texte": "Poubelles", "jours": ["mon", "xx"]}],
        })
        self.assertNotIn("inconnu", clean)
        opts = settings.apply_settings({"vac_fan": "select.x"}, clean)
        self.assertEqual(opts["vacuum_entity"], "vacuum.cookie")
        self.assertEqual(opts["vac_battery"], "sensor.b")
        self.assertEqual(opts["style"], "ardoise")
        self.assertIs(opts["air_enabled"], False)
        self.assertEqual(opts["rappels"][0]["jours"], ["mon"])
        self.assertEqual(opts["vac_fan"], "select.x")  # non touché
        opts = settings.apply_settings(opts, settings.clean_settings({"vacuum_entity": "", "vac_battery": ""}))
        self.assertNotIn("vacuum_entity", opts)
        self.assertNotIn("vac_battery", opts)


class Detection(unittest.TestCase):
    def test_pick(self):
        rows = [
            {"entity_id": "vacuum.cookie", "device_class": None, "name": "Cookie", "unit": None},
            {"entity_id": "sensor.cookie_battery_level", "device_class": "battery", "name": "Battery Level", "unit": "%"},
            {"entity_id": "select.cookie_fan_level", "device_class": None, "name": "Suction level", "unit": None},
            {"entity_id": "select.cookie_water_level", "device_class": None, "name": "Water level", "unit": None},
            {"entity_id": "sensor.cookie_clean_area", "device_class": None, "name": "Cleaning area", "unit": "m²"},
            {"entity_id": "sensor.cookie_clean_time", "device_class": "duration", "name": "Cleaning time", "unit": "min"},
            {"entity_id": "sensor.cookie_error", "device_class": None, "name": "Error", "unit": None},
        ]
        f = vacuum.pick(rows)
        self.assertEqual(f["vac_battery"], "sensor.cookie_battery_level")
        self.assertEqual(f["vac_fan"], "select.cookie_fan_level")
        self.assertEqual(f["vac_area"], "sensor.cookie_clean_area")
        self.assertEqual(f["vac_time"], "sensor.cookie_clean_time")
        self.assertEqual(f["vac_alert"], "sensor.cookie_error")

    def test_pick_mode_et_reservoirs_miot(self):
        p = "sensor.xtl_de_1172154057_xm2216_"
        rows = [
            {"entity_id": p + n, "device_class": None, "name": None, "unit": None}
            for n in (
                "clean_type_status_p_17_9", "clean_mode_p_17_10", "water_mode_p_17_12", "fan_mode_p_17_13",
                "clean_count_p_17_14", "clean_water_cistern_p_17_51", "drain_cistern_p_17_52", "robot_status_p_17_49",
            )
        ]
        f = vacuum.pick(rows)
        self.assertEqual(f["vac_mode"], p + "clean_mode_p_17_10")
        self.assertEqual(f["vac_water"], p + "clean_water_cistern_p_17_51")
        self.assertEqual(f["vac_drain"], p + "drain_cistern_p_17_52")
        self.assertEqual(f["vac_status"], p + "robot_status_p_17_49")

    def test_pick_vide(self):
        self.assertEqual(vacuum.pick([]), {})


if __name__ == "__main__":
    unittest.main()
