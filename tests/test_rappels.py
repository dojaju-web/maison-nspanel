"""Tests de la logique des rappels (python -m unittest discover tests)."""
import importlib.util
import pathlib
import unittest
from datetime import datetime

spec = importlib.util.spec_from_file_location(
    "rappels",
    pathlib.Path(__file__).parent.parent / "custom_components" / "maison_nspanel" / "rappels.py",
)
rappels = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rappels)

LUNDI = datetime(2026, 10, 12, 10, 0)   # lundi
MARDI = datetime(2026, 10, 13, 10, 0)   # mardi


class TestRappels(unittest.TestCase):
    def test_defaut_lundi_seulement(self):
        r = rappels.DEFAULT_REMINDER
        self.assertTrue(rappels.is_active(r, LUNDI))
        self.assertFalse(rappels.is_active(r, MARDI))

    def test_plage_horaire(self):
        r = {**rappels.DEFAULT_REMINDER, "heure_debut": "18:00:00", "heure_fin": "23:00:00"}
        self.assertFalse(rappels.is_active(r, datetime(2026, 10, 12, 9, 0)))
        self.assertTrue(rappels.is_active(r, datetime(2026, 10, 12, 18, 0)))
        self.assertTrue(rappels.is_active(r, datetime(2026, 10, 12, 23, 0)))
        self.assertFalse(rappels.is_active(r, datetime(2026, 10, 12, 23, 1)))

    def test_plage_passant_minuit(self):
        r = {**rappels.DEFAULT_REMINDER, "heure_debut": "20:00:00", "heure_fin": "06:00:00"}
        self.assertTrue(rappels.is_active(r, datetime(2026, 10, 12, 22, 0)))
        self.assertTrue(rappels.is_active(r, datetime(2026, 10, 12, 5, 0)))
        self.assertFalse(rappels.is_active(r, datetime(2026, 10, 12, 12, 0)))

    def test_desactive_ou_sans_texte(self):
        self.assertFalse(rappels.is_active({**rappels.DEFAULT_REMINDER, "actif": False}, LUNDI))
        self.assertFalse(rappels.is_active({**rappels.DEFAULT_REMINDER, "texte": "  "}, LUNDI))

    def test_plusieurs_jours(self):
        r = {**rappels.DEFAULT_REMINDER, "jours": ["mon", "thu"]}
        self.assertTrue(rappels.is_active(r, datetime(2026, 10, 15, 8, 0)))   # jeudi
        self.assertFalse(rappels.is_active(r, datetime(2026, 10, 14, 8, 0)))  # mercredi

    def test_format_dashboard(self):
        out = rappels.active_reminders([rappels.DEFAULT_REMINDER], LUNDI)
        self.assertEqual(out, [{"texte": "Sortir les poubelles", "icone": "mdi:trash-can-outline", "couleur": "250,204,21"}])
        self.assertEqual(rappels.active_reminders([rappels.DEFAULT_REMINDER], MARDI), [])

    def test_normalisation(self):
        n = rappels.normalize({"couleur": [300, -5], "jours": ["mon", "xxx"], "heure_debut": None})
        self.assertEqual(n["couleur"], [255, 0, 0])
        self.assertEqual(n["jours"], ["mon"])

    def test_description(self):
        self.assertIn("Lun.", rappels.describe(rappels.DEFAULT_REMINDER))


if __name__ == "__main__":
    unittest.main()
