import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "maison_nspanel"))
import vigilance as v


class T(unittest.TestCase):
    def test_level(self):
        self.assertEqual(v.level_of("Orange"), 3)
        self.assertEqual(v.level_of(" rouge "), 4)
        self.assertEqual(v.level_of("n/a"), 0)
        self.assertEqual(v.level_of(None), 0)

    def test_find_source(self):
        ids = ["sensor.foo", "sensor.84_weather_alert", "sensor.2a_weather_alert"]
        self.assertEqual(v.find_source(ids), "sensor.2a_weather_alert")
        self.assertIsNone(v.find_source(["sensor.x"]))

    def test_compute_default_threshold(self):
        attrs = {"Orages": "Orange", "Vent violent": "Jaune", "Pluie-inondation": "Vert", "attribution": "Météo-France"}
        r = v.compute("Orange", attrs, "jaune")
        self.assertTrue(r["afficher"])
        self.assertEqual([p["nom"] for p in r["phenomenes"]], ["Orages", "Vent violent"])
        self.assertEqual(r["couleur"], "251,146,60")

    def test_thresholds(self):
        self.assertFalse(v.compute("Jaune", {}, "orange")["afficher"])
        self.assertTrue(v.compute("Rouge", {}, "orange")["afficher"])
        self.assertFalse(v.compute("Vert", {}, "jaune")["afficher"])
        self.assertTrue(v.compute("Vert", {}, "toujours")["afficher"])
        self.assertFalse(v.compute("Rouge", {}, "jamais")["afficher"])

    def test_unknown(self):
        r = v.compute(None, None, "jaune")
        self.assertFalse(r["afficher"])
        self.assertEqual(r["nom"], "inconnu")
        self.assertEqual(v.compute("Jaune", {"Pluie-inondation": "Jaune"}, "jaune")["phenomenes"][0]["nom"], "Pluie / inondation")


if __name__ == "__main__":
    unittest.main()
