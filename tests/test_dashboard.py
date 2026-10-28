import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "maison_nspanel"))
import dashboard as d


class T(unittest.TestCase):
    def test_prefix(self):
        self.assertEqual(d.prefix_of("climate.salon_clim"), "salon_clim")
        self.assertEqual(d.prefix_of(None), d.DEFAULT_PREFIX)

    def test_render(self):
        src = "a climate.sejour_climatisation b switch.sejour_climatisation_climate_react c sensor.sejour_climatisation_co2"
        out = d.render(src, "climate.salon_clim")
        self.assertEqual(out, "a climate.salon_clim b switch.salon_clim_climate_react c sensor.salon_clim_co2")
        self.assertEqual(d.render(src, None), src)

    def test_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp)
            self.assertFalse(d.sync(f, "climate.x"))  # pas de modèle
            (f / d.MODELE).write_text("climate.sejour_climatisation", encoding="utf-8")
            self.assertTrue(d.sync(f, "climate.salon"))
            self.assertEqual((f / d.CIBLE).read_text(encoding="utf-8"), "climate.salon")
            self.assertFalse(d.sync(f, "climate.salon"))  # inchangé
            self.assertTrue(d.sync(f, None))              # retour au défaut
            self.assertEqual((f / d.CIBLE).read_text(encoding="utf-8"), "climate.sejour_climatisation")


class Sections(unittest.TestCase):
    def test_defaults_sans_interrupteur_dans_le_compte(self):
        secs = d.normalize_sections(None)
        self.assertIn("switch.outlet_1", d.all_entities(secs))
        self.assertNotIn("switch.outlet_1", d.light_entities(secs))
        self.assertEqual(len(d.light_entities(secs)), 4)

    def test_normalize(self):
        secs = d.normalize_sections([{"nom": " Salon ", "lumieres": ["light.a", "light.a", "x", {"entity": "light.b", "nom": "B"}]}])
        self.assertEqual(secs[0]["nom"], "Salon")
        self.assertEqual([l["entity"] for l in secs[0]["lumieres"]], ["light.a", "light.b"])

    def test_render_sections(self):
        src = "ids: __LIGHTS_IDS__\ntrig: __LIGHTS_TRIG__\njs: [__LIGHTS_JS__]\nq: [__LIGHTS_JSQ__]\n__SECTIONS__\n"
        out = d.render(src, None, [{"nom": "Salon", "lumieres": ["light.a", "switch.b"]}])
        self.assertIn('ids: ["light.a"]', out)
        self.assertIn('trig: ["light.a", "switch.b"]', out)
        self.assertIn("js: ['light.a']", out)
        self.assertIn("q: [''light.a'']", out)
        self.assertIn('text: "SALON"', out)
        self.assertIn("columns: 2", out)
        self.assertNotIn("__", out)

    def test_vide(self):
        out = d.render("t: __LIGHTS_TRIG__\nids: __LIGHTS_IDS__\n__SECTIONS__", None, [])
        self.assertIn('t: ["sun.sun"]', out)
        self.assertIn("ids: []", out)


if __name__ == "__main__":
    unittest.main()
