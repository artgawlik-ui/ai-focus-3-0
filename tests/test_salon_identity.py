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

    def test_unicode_lowercase_cannot_alias_an_ascii_profile(self):
        # Kelvin sign lowercases to ASCII k; rejecting it before lower() avoids
        # silently merging an unrecognized reference with the distinct @salonk.
        for raw in ("@salon\u212a", "salon\u212a", "https://instagram.com/salon\u212a/"):
            with self.subTest(raw=raw):
                self.assertIsNone(instagram_username(raw))
        self.assertEqual(instagram_username("@SALONK"), "salonk")

    def test_control_characters_are_rejected_before_url_parser_or_trim(self):
        for raw in ("\n@salon", "@salon\r", "https://insta\ngram.com/salon",
                    "https://instagram.com/sa\tlon", "https://instagram.com/salon?x=\n",
                    "@salon\x00", "@salon\x7f"):
            with self.subTest(raw=raw):
                self.assertIsNone(instagram_username(raw))

    def test_ambiguous_path_and_empty_userinfo_do_not_become_profile_keys(self):
        for raw in ("https://instagram.com///salon///", "https://instagram.com/salon//",
                    "https://@instagram.com/salon", "https://:@instagram.com/salon"):
            with self.subTest(raw=raw):
                self.assertIsNone(instagram_username(raw))


if __name__ == "__main__":
    unittest.main()

