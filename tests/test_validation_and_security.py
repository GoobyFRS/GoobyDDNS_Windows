import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from goobyddns.config import DNSConfig, is_valid_ip_address, load_runtime_config, save_runtime_config, validate_fqdn


class ValidationAndSecurityTests(unittest.TestCase):
    def test_valid_ipv4_and_ipv6_are_accepted(self):
        self.assertTrue(is_valid_ip_address("1.2.3.4"))
        self.assertTrue(is_valid_ip_address("2001:db8::1"))

    def test_invalid_ip_is_rejected(self):
        self.assertFalse(is_valid_ip_address("not-an-ip"))

    def test_valid_fqdn_is_normalized(self):
        self.assertEqual(validate_fqdn(" ddns.example.org "), "ddns.example.org")

    def test_invalid_fqdn_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_fqdn("bad host")

    def test_config_loader_prefers_environment_over_file(self):
        with patch.dict(os.environ, {
            "LINODE_API_KEY": "env-key",
            "DOMAIN_RECORD_ID": "env-domain-id",
            "SUBDOMAIN_RECORD_ID": "env-subdomain-id",
            "FQDN": "env.example.org",
        }, clear=False):
            config = load_runtime_config()
            self.assertEqual(config.linode_api_key, "env-key")
            self.assertEqual(config.domain_record_id, "env-domain-id")
            self.assertEqual(config.subdomain_record_id, "env-subdomain-id")
            self.assertEqual(config.fqdn, "env.example.org")

    def test_utf16_config_file_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = pathlib.Path(temp_dir) / "running_config.ini"
            config_path.write_text(
                "[linode]\nLINODE_API_KEY=from-utf16\nLINODE_API_VERSION=v4\nDOMAIN_RECORD_ID=abc\nSUBDOMAIN_RECORD_ID=def\n\n[dns]\nFQDN=ddns.example.org\n",
                encoding="utf-16",
            )
            loaded = load_runtime_config(config_path)
            self.assertEqual(loaded.linode_api_key, "from-utf16")
            self.assertEqual(loaded.fqdn, "ddns.example.org")

    def test_runtime_config_writer_persists_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = pathlib.Path(temp_dir) / "running_config.ini"
            configuration = DNSConfig(
                linode_api_key="saved-key",
                linode_api_version="v4",
                domain_record_id="domain-id",
                subdomain_record_id="subdomain-id",
                fqdn="ddns.example.org",
            )

            saved_path = save_runtime_config(configuration, config_path)
            self.assertEqual(saved_path, config_path)

            loaded = load_runtime_config(config_path)
            self.assertEqual(loaded.linode_api_key, "saved-key")
            self.assertEqual(loaded.domain_record_id, "domain-id")
            self.assertEqual(loaded.subdomain_record_id, "subdomain-id")
            self.assertEqual(loaded.fqdn, "ddns.example.org")


if __name__ == "__main__":
    unittest.main()
