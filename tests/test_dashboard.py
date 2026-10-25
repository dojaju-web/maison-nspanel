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


if __name__ == "__main__":
    unittest.main()
