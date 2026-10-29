import socket
import unittest
from unittest.mock import patch

from url_safety import validate_public_http_url


class UrlSafetyTests(unittest.TestCase):
    def test_rejects_non_http_schemes(self):
        with self.assertRaisesRegex(ValueError, "HTTP and HTTPS"):
            validate_public_http_url("file:///etc/passwd")

    def test_rejects_loopback_addresses(self):
        with self.assertRaisesRegex(ValueError, "public IP"):
            validate_public_http_url("http://127.0.0.1/admin")

    def test_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            validate_public_http_url("https://user:password@example.com/")

    def test_rejects_hostname_resolving_to_private_address(self):
        private_record = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.5", 443))
        with patch("url_safety.socket.getaddrinfo", return_value=[private_record]):
            with self.assertRaisesRegex(ValueError, "public IP"):
                validate_public_http_url("https://example.test/")

    def test_accepts_public_address_and_drops_fragment(self):
        public_record = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        with patch("url_safety.socket.getaddrinfo", return_value=[public_record]):
            self.assertEqual(
                validate_public_http_url("https://example.test/path?q=1#section"),
                "https://example.test/path?q=1",
            )


if __name__ == "__main__":
    unittest.main()
