import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import requests

from orchestrator.asset_manager import ImageAssetStore, PUBLIC_IMAGE_HEADERS, search_planned_commons_candidates


class PlannedImageSearchTests(unittest.TestCase):
    def test_public_image_requests_identify_the_client(self):
        self.assertIn("User-Agent", PUBLIC_IMAGE_HEADERS)
        self.assertIn("paper-agent-v6", PUBLIC_IMAGE_HEADERS["User-Agent"])

    @patch("orchestrator.asset_manager.search_openverse_candidates", return_value=[])
    @patch("orchestrator.asset_manager.search_commons_candidates")
    def test_searches_only_planned_real_image_requirements(self, search, _openverse):
        search.return_value = [{
            "title": "Robot arm",
            "caption": "BCI robotic arm device",
            "image_url": "https://example.test/robot-arm.jpg",
        }]

        candidates = search_planned_commons_candidates(
            "EEG robotic arm control",
            [
                {
                    "section_id": "methods",
                    "asset_type": "searched_image_or_diagram",
                    "purpose": "system_or_device_context",
                    "required": True,
                },
                {
                    "section_id": "results",
                    "asset_type": "data_figure",
                    "purpose": "result_evidence",
                    "required": True,
                },
            ],
            section_titles={"methods": "Methods"},
        )

        self.assertEqual(len(candidates), 1)
        self.assertIn("EEG brain computer interface", candidates[0]["planned_query"])
        self.assertIn("robotic arm", candidates[0]["planned_query"])
        self.assertTrue(candidates[0]["asset_plan_required"])
        search.assert_called_once()

    @patch("orchestrator.asset_manager.search_openverse_candidates", return_value=[])
    @patch("orchestrator.asset_manager.search_commons_candidates")
    def test_rejects_pdf_and_unrelated_search_results(self, search, _openverse):
        search.side_effect = [
            [{"title": "NASA press kit", "image_url": "https://example.test/press-kit.pdf"}],
            [{"title": "Landscape", "image_url": "https://example.test/landscape.jpg"}],
            [],
        ]

        candidates = search_planned_commons_candidates(
            "robotic arm",
            [{
                "section_id": "methods",
                "asset_type": "searched_image_or_diagram",
                "purpose": "system_or_device_context",
            }],
        )

        self.assertEqual(candidates, [])

    @patch("orchestrator.asset_manager.search_openverse_candidates", return_value=[])
    @patch("orchestrator.asset_manager.search_commons_candidates")
    def test_rejects_space_robot_arm_for_rehabilitation_paper(self, search, _openverse):
        search.return_value = [{
            "title": "STS-114 robotic arm for NASA",
            "caption": "Space station robotic arm assistant",
            "image_url": "https://example.test/space-arm.jpg",
        }]

        candidates = search_planned_commons_candidates(
            "EEG robotic arm rehabilitation",
            [{
                "section_id": "introduction",
                "asset_type": "searched_image",
                "purpose": "application_context",
            }],
        )

        self.assertEqual(candidates, [])

    @patch("orchestrator.asset_manager.search_openverse_candidates", return_value=[])
    @patch("orchestrator.asset_manager.search_commons_candidates")
    def test_air_quality_query_accepts_monitoring_station_image(self, search, _openverse):
        search.return_value = [{
            "title": "Urban air quality monitoring station",
            "caption": "Air pollution monitoring sensor station",
            "image_url": "https://example.test/monitoring.jpg",
            "source_url": "https://example.test/source",
            "license": "CC BY",
        }]

        candidates = search_planned_commons_candidates(
            "基于图神经网络的城市空气质量预测方法研究",
            [{"section_id": "intro", "asset_type": "searched_image", "purpose": "application_context"}],
        )

        self.assertEqual(len(candidates), 1)
        self.assertIn("air quality monitoring station", candidates[0]["planned_query"])

    @patch("orchestrator.asset_manager.search_openverse_candidates")
    @patch("orchestrator.asset_manager.search_commons_candidates", side_effect=requests.RequestException("offline"))
    def test_falls_back_to_second_open_source_when_commons_is_unavailable(self, _commons, openverse):
        openverse.return_value = [{
            "title": "Air quality station",
            "caption": "Urban monitoring station",
            "image_url": "https://example.test/air.jpg",
            "source_url": "https://example.test/source",
            "license": "CC BY",
        }]
        candidates = search_planned_commons_candidates(
            "城市空气质量预测",
            [{"section_id": "intro", "asset_type": "searched_image", "purpose": "application_context"}],
        )
        self.assertEqual(len(candidates), 1)

    @patch("orchestrator.asset_manager.search_openverse_candidates")
    @patch("orchestrator.asset_manager.search_commons_candidates")
    def test_retains_second_source_candidate_when_commons_found_a_result(self, commons, openverse):
        commons.return_value = [{
            "title": "Commons station",
            "caption": "Air quality station",
            "image_url": "https://commons.test/station.jpg",
            "license": "CC BY",
            "source": "wikimedia_commons",
        }]
        openverse.return_value = [{
            "title": "Openverse station",
            "caption": "Air quality station",
            "image_url": "https://openverse.test/station.jpg",
            "license": "CC BY",
            "source": "openverse",
        }]
        candidates = search_planned_commons_candidates(
            "城市空气质量预测",
            [{"section_id": "intro", "asset_type": "searched_image", "purpose": "application_context"}],
        )
        self.assertEqual({asset["source"] for asset in candidates}, {"wikimedia_commons", "openverse"})

    @patch("orchestrator.asset_manager.search_openverse_candidates")
    @patch("orchestrator.asset_manager.search_commons_candidates", return_value=[])
    def test_xray_search_includes_luggage_scanner_fallback_for_second_source(self, _commons, openverse):
        def openverse_results(query, **_kwargs):
            if query == "x-ray luggage scanner":
                return [{
                    "title": "X-ray security scanner at a train station",
                    "caption": "Monitor displaying scanned luggage images",
                    "image_url": "https://example.test/xray-scanner.jpg",
                    "source_url": "https://example.test/source",
                    "license": "cc0",
                    "source": "openverse",
                }]
            return []

        openverse.side_effect = openverse_results
        candidates = search_planned_commons_candidates(
            "基于深度学习的X光安检图像违禁品检测算法",
            [{"section_id": "intro", "asset_type": "searched_image", "purpose": "application_context"}],
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["planned_query"], "x-ray luggage scanner")

    @patch("orchestrator.asset_manager.requests.Session.get", side_effect=requests.RequestException("download failure"))
    def test_failed_image_download_records_warning_state_without_aborting_assets(self, _get):
        with tempfile.TemporaryDirectory() as tmp:
            store = ImageAssetStore(Path(tmp) / "assets.json")
            store.register_candidates([{
                "asset_id": "fresh",
                "approved": True,
                "image_url": "https://example.test/image.jpg",
            }])
            assets = store.download_approved(Path(tmp) / "write-new" / "images", asset_ids=["fresh"])
        self.assertIn("download_error", assets[0])

    @patch("orchestrator.asset_manager.requests.Session.get")
    def test_image_download_uses_thumbnail_when_commons_original_is_rate_limited(self, get):
        failed = unittest.mock.Mock()
        failed.raise_for_status.side_effect = requests.HTTPError("429")
        success = unittest.mock.Mock()
        success.raise_for_status.return_value = None
        success.headers = {"content-type": "image/jpeg"}
        success.content = b"preview-image"
        get.side_effect = [failed, success]
        with tempfile.TemporaryDirectory() as tmp:
            store = ImageAssetStore(Path(tmp) / "assets.json")
            store.register_candidates([{
                "asset_id": "commons-preview",
                "approved": True,
                "image_url": "https://upload.wikimedia.test/original.jpg",
                "thumbnail_url": "https://upload.wikimedia.test/thumb.jpg",
            }])
            assets = store.download_approved(Path(tmp) / "write-new" / "images", asset_ids=["commons-preview"])
            saved = Path(assets[0]["local_path"])
            self.assertTrue(saved.exists())
            self.assertEqual(saved.read_bytes(), b"preview-image")
        self.assertEqual(assets[0]["downloaded_url"], "https://upload.wikimedia.test/thumb.jpg")
        self.assertNotIn("download_error", assets[0])


if __name__ == "__main__":
    unittest.main()
