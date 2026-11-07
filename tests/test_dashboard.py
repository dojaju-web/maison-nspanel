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


class Aspirateur(unittest.TestCase):
    SRC = (
        "cols: __NAVCOLS__\nnav:\n  cards:\n    - a\n    __VAC_NAV__\n"
        "pages:\n  __VAC_PAGE__\n\nfin\n"
    )
    FRAG = {
        "__VAC_NAV__": "- b:\n    x: 1\n",
        "__VAC_PAGE__": "- title: Aspirateur\n  entity: __VACUUM__\n  bat: __VAC_BATTERY__\n  trig: [__VAC_TRIG__]\n  __VAC_FAN_TAP__\n",
    }

    def test_sans_aspirateur(self):
        out = d.render(self.SRC)
        self.assertIn("cols: 2", out)
        self.assertNotIn("Aspirateur", out)
        self.assertNotIn("__", out)

    def test_avec_aspirateur(self):
        out = d.render(self.SRC, None, None, "vacuum.cookie", self.FRAG, {"vac_battery": "sensor.bat"})
        self.assertIn("cols: 3", out)
        self.assertIn("entity: vacuum.cookie", out)
        self.assertIn("bat: sensor.bat", out)
        self.assertIn('trig: ["vacuum.cookie", "sensor.bat"]', out)
        self.assertIn("    - b:\n        x: 1", out)
        self.assertIn("vacuum.set_fan_speed", out)  # pas de select : l'aspirateur lui-même
        self.assertNotIn("__", out)

    def test_aspiration_via_select(self):
        out = d.render(self.SRC, None, None, "vacuum.cookie", self.FRAG, {"vac_fan": "select.mode"})
        self.assertIn("select.select_next", out)
        self.assertIn("entity_id: select.mode", out)
        self.assertNotIn("vacuum.set_fan_speed", out)


class Menu(unittest.TestCase):
    SRC = "a:\n  custom_fields:\n    __MENU__\n  styles:\n    __MENU_STYLE__\n"

    def test_menu_toujours_rendu(self):
        out = d.render(self.SRC)
        self.assertIn("menu:", out)
        self.assertIn("t3:", out)  # 4 onglets sans aspirateur : t0..t3
        self.assertNotIn("t4:", out)
        self.assertNotIn("__", out)

    def test_menu_flottant_liquid(self):
        out = d.render(self.SRC)
        self.assertIn("position: absolute", out)
        self.assertIn("backdrop-filter: blur(30px)", out)
        self.assertIn("style === 'liquid'", out)

    def test_menu_avec_aspirateur(self):
        field, style = d.gen_menu(True, vacuum="vacuum.cookie")
        self.assertIn("states['vacuum.cookie']", field)
        self.assertIn("[__LIGHTS_JS__]", field)
        self.assertIn("rgb(12,12,16)", field)
        self.assertIn("t4:", field)
        self.assertIn("/aspirateur", field)
        self.assertIn("repeat(5, 1fr)", field)
        self.assertIn("z-index", style)


if __name__ == "__main__":
    unittest.main()
