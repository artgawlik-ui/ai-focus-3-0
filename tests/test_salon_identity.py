"""Tests for conservative CRM matching; no network or production data."""
import unittest
from backend.salon_identity import instagram_username


class InstagramIdentityTests(unittest.TestCase):
    def test_matching_representations(self):
        for raw in ("@Salon.Test", "salon.test", " https://instagram.com/Salon.Test/ ",
                    "https://www.instagram.com/salon.test/?igsh=abc"):
            with self.subTest(raw=raw):
                self.assertEqual(instagram_username(raw), "salon.test")

    def test_distinct_accounts_stay_distinct(self):
        self.assertNotEqual(instagram_username("@salon_a"),
                            instagram_username("@salon.b"))

    def test_reject_non_profiles_and_other_hosts(self):
        for raw in ("", None, "https://instagram.com/p/abc/",
                    "https://instagram.com/reel/abc",
                    "https://instagram.com/direct/",
                    "https://evil.example/salon", "http://instagram.com/salon",
                    "https://instagram.com.evil.example/salon",
                    "instagram.com/salon", "@a b", "@salon/a",
                    "https://user:pass@instagram.com/salon"):
            with self.subTest(raw=raw):
                self.assertIsNone(instagram_username(raw))

    def test_no_contact_permission_inference(self):
        self.assertEqual(instagram_username("@example"), "example")
        # This is only a candidate match key, never an API peer ID or send approval.


if __name__ == "__main__":
    unittest.main()
