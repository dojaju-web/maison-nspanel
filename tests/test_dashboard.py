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
        self.assertIn("t2:", out)  # 3 onglets sans aspirateur : t0..t2
        self.assertNotIn("t3:", out)
        self.assertNotIn("__", out)

    def test_menu_flottant_liquid(self):
        out = d.render(self.SRC)
        self.assertIn("position: absolute", out)
        self.assertIn("backdrop-filter: blur(12px)", out)
        self.assertIn("style === 'liquid'", out)

    def test_un_seul_liserere(self):
        out = d.render(self.SRC)
        self.assertNotIn("lg-refract", out)
        self.assertIn("border-color: rgba(255,255,255,.30)", out)

    def test_menu_avec_aspirateur(self):
        field, style = d.gen_menu(True, vacuum="vacuum.cookie")
        self.assertIn("states['vacuum.cookie']", field)
        self.assertIn("[__LIGHTS_JS__]", field)
        self.assertIn("rgb(255,255,255)", field)
        self.assertIn("t3:", field)
        self.assertIn("/aspirateur", field)
        self.assertIn("repeat(4, 1fr)", field)
        self.assertIn("z-index", style)


class LiquidContenu(unittest.TestCase):
    """Couche contenu du thème iOS : surfaces plates, palette système, mouvement réduit."""

    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parent.parent / "custom_components" / "maison_nspanel" / "dashboard"
        cls.modele = (base / "modele.yaml").read_text(encoding="utf-8")
        cls.asp = (base / "aspirateur_page.yaml").read_text(encoding="utf-8")

    def _tpl(self, name):
        start = self.modele.index(f"\n  {name}:\n")
        end = self.modele.find("\n  tile_", start + 5)
        return self.modele[start:end if end > 0 else len(self.modele)]

    def test_tuiles_ont_une_branche_liquid(self):
        for name in ("tile_light", "tile_base", "tile_vac"):
            self.assertIn("style === 'liquid'", self._tpl(name), name)

    def test_tuiles_plates_sans_verre(self):
        for name in ("tile_light", "tile_base", "tile_vac"):
            self.assertIn("rgba(44,44,46,.80)", self._tpl(name), name)
        self.assertNotIn("backdrop-filter", self._tpl("tile_light"))

    def test_palette_systeme_et_contraste(self):
        t = self._tpl("tile_light")
        self.assertIn("[0,145,255]", t)
        self.assertIn("#1C1C1E", t)  # glyphe sombre sur couleur claire

    def test_etat_pas_porte_par_la_couleur_seule(self):
        self.assertIn("2px solid", self._tpl("tile_base"))
        self.assertIn("'Allumée", self._tpl("tile_light"))

    def test_mouvement_reduit(self):
        for name in ("tile_light", "tile_base", "tile_vac"):
            self.assertIn("prefers-reduced-motion", self._tpl(name), name)
        self.assertIn("prefers-reduced-motion", self.asp)

    def test_police_minimale(self):
        # le liquid ne descend pas sous 11 px et évite les graisses légères
        self.assertIn(".av-lq .av-metric-label {font-size:11px", self.asp)
        self.assertNotIn("font-weight:300", self.asp)

    def test_accueil_contenu_plat_menu_verre(self):
        # le verre est réservé aux contrôles flottants : plus de flou sur bulles/pastilles
        self.assertNotIn("blur(10px)", self.modele)
        self.assertIn("rgba(44,44,46,.80)", self.modele)
        _, style = d.gen_menu(False)
        self.assertIn("left: 14px", style)
        self.assertIn("backdrop-filter", d.gen_menu(False)[0])

    def test_style_beta(self):
        self.assertIn("\"beta\"", (Path(__file__).resolve().parent.parent / "custom_components" / "maison_nspanel" / "const.py").read_text(encoding="utf-8"))
        for name in ("tile_light", "tile_base", "tile_vac"):
            self.assertIn("style === 'beta'", self._tpl(name), name)
        self.assertGreaterEqual(self.modele.count("style === 'beta'"), 40)
        self.assertIn("style === 'beta'", self.asp)

    def test_duree_en_minutes_depuis_secondes(self):
        # sensor.*_clean_time (Xiaomi Miot) = 6006 sans unité : secondes → 1 h 40, minutes sous 1 h, sinon « 1 h 40 »
        self.assertIn("unit_of_measurement).toLowerCase() : 's') : 'min'", self.asp)
        self.assertIn("tot >= 60 ? Math.floor(tot / 60) + ' h '", self.asp)
        self.assertIn(": tot + ' min'", self.asp)

    def test_mode_et_reservoirs(self):
        self.assertIn("Aspiration + lavage", self.asp)
        self.assertIn("'Mode : ' + modeTxt", self.asp)
        for tok in ("__VAC_MODE__", "__VAC_WATER__", "__VAC_DRAIN__"):
            self.assertIn(tok, self.asp)
        for lab in ("Niveau bas", "Absent", "Inutilisable"):
            self.assertIn(lab, self.asp)

    def test_etat_robot_sur_station(self):
        for tok in ("__VAC_STATUS__", "Lavage de la serpillière", "Séchage à air chaud", "Vidage des poussières"):
            self.assertIn(tok, self.asp)
        self.assertIn("s === 'docked' && rsTxt", self.asp)

    def test_aspirateur_liquid(self):
        self.assertIn("av-lq", self.asp)
        self.assertIn("#8E8E93", self.asp)


if __name__ == "__main__":
    unittest.main()
