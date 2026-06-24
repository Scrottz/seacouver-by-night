import unittest
from pathlib import Path

from lib.utils import derive_name_from_slug, extract_index, extract_slug


class TestUtils(unittest.TestCase):

    def test_extract_index(self):
        # Case: Standard NPC
        self.assertEqual(extract_index(Path("npc/albert_hitchens_1.jpg")), 1)
        # Case: Complex slug with double underscores
        self.assertEqual(extract_index(Path("pc/roxanne__roxy__cross_2.png")), 2)
        # Case: Long slug with multiple underscores
        self.assertEqual(extract_index(Path("npc/schbbeldidudeldiedei_doedel__lolwoot__test_5.png")), 5)
        # Case: No index (should return 0)
        self.assertEqual(extract_index(Path("npc/eduardo_torres.jpg")), 0)

    def test_extract_slug(self):
        # Case: Standard NPC
        self.assertEqual(extract_slug(Path("npc/albert_hitchens_1.jpg")), "albert_hitchens")
        # Case: Complex slug
        self.assertEqual(extract_slug(Path("pc/roxanne__roxy__cross_2.png")), "roxanne__roxy__cross")
        # Case: Slug with no index
        self.assertEqual(extract_slug(Path("npc/eduardo_torres.jpg")), "eduardo_torres")

    def test_derive_name_from_slug(self):
        # Case: Standard name
        self.assertEqual(derive_name_from_slug("albert_hitchens"), "Albert Hitchens")
        # Case: Roxy rule (double underscore -> quotes)
        self.assertEqual(derive_name_from_slug("roxanne__roxy__cross"), 'Roxanne "Roxy" Cross')
        # Case: Complex multi-word quote
        self.assertEqual(derive_name_from_slug("lui__the_gambler__doedelhausen"), 'Lui "The Gambler" Dödelhausen')
        # Case: Title case check
        self.assertEqual(derive_name_from_slug("lt_charles_hopkins"), "Lt Charles Hopkins")

if __name__ == '__main__':
    unittest.main()
