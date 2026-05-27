import unittest
from unittest.mock import patch

from main import (
    _APP_CONFIG,
    _build_nexent_download_urls,
    _get_advertised_host,
    _get_listen_host,
    _get_server_port,
)


class NexentDownloadUrlTests(unittest.TestCase):
    def test_bare_s3_attachment_uses_exposed_minio_before_legacy_dns_fallback(self):
        with patch("main._MINIO_PUBLIC_URL", "http://localhost:9010"), patch("main._FILE_GATEWAY", ""):
            urls = _build_nexent_download_urls(
                "s3://nexent/attachments/user_id/example.docx"
            )

        self.assertEqual(
            urls[0],
            "http://localhost:9010/nexent/attachments/user_id/example.docx",
        )
        self.assertIn("https://nexent/attachments/user_id/example.docx", urls)

    def test_presigned_proxy_path_is_left_as_proxy_url(self):
        proxy = (
            "http://localhost:5013/api/nb/v1/file/fetch?"
            "presigned_url=http%3A%2F%2Fnexent-minio%3A9000%2Fnexent%2Fobject.docx"
        )

        self.assertEqual(_build_nexent_download_urls(proxy)[0], proxy)

    def test_container_runtime_environment_overrides_server_addresses(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "PAPER_AGENT_ADVERTISED_HOST": "paper.example.test",
                    "PAPER_AGENT_HOST": "0.0.0.0",
                    "PAPER_AGENT_PORT": "9001",
                },
            ),
            patch.dict(_APP_CONFIG, {"server": {"host": "127.0.0.1", "port": 8001, "advertised_host": "local"}}),
        ):
            self.assertEqual(_get_advertised_host(), "paper.example.test")
            self.assertEqual(_get_listen_host(), "0.0.0.0")
            self.assertEqual(_get_server_port(), 9001)


if __name__ == "__main__":
    unittest.main()
