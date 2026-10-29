"""Vérifie que le panneau JS est présent et référencé par panel.py."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "maison_nspanel"


class PanelFiles(unittest.TestCase):
    def test_js_defini(self):
        js = (ROOT / "www" / "maison-editeur.js").read_text(encoding="utf-8")
        self.assertIn('customElements.define("maison-nspanel-editeur"', js)
        self.assertIn("maison_nspanel/set_sections", js)

    def test_python_coherent(self):
        py = (ROOT / "panel.py").read_text(encoding="utf-8")
        self.assertIn('PANEL_COMPONENT = "maison-nspanel-editeur"', py)
        self.assertIn("maison_nspanel/get_sections", py)


if __name__ == "__main__":
    unittest.main()
