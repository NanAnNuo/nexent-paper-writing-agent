import tempfile
import unittest
from pathlib import Path

from execution.render_validator import validate_renderable_ast
from execution.citation_resolver import CitationResolver
from orchestrator.asset_manager import ImageAssetStore
from orchestrator.material_sufficiency import assess_material_sufficiency
from orchestrator.quality_audit import audit_manuscript


class MaterialSufficiencyTests(unittest.TestCase):
    def test_experimental_paper_waits_for_result_evidence(self):
        report = assess_material_sufficiency(
            topic="EEG robotic arm control experiment",
            material_text="The project will collect EEG and build a CSP classifier.",
            references=[{"title": "A real paper"}],
        )

        self.assertEqual(report["status"], "WAITING_REQUIRED_USER_MATERIALS")
        self.assertIn("result_evidence", report["missing_materials"])
        self.assertEqual(report["supported_scope"], "outline_or_scaffold_only")

    def test_experimental_paper_can_write_with_method_results_and_references(self):
        report = assess_material_sufficiency(
            topic="EEG robotic arm control experiment",
            material_text=(
                "Method: 10 subjects used a 14-channel EEG device. "
                "Results: classifier accuracy was measured from uploaded result tables."
            ),
            result_evidence="result_table.csv and confusion_matrix.png",
            references=[{"title": "A real paper"}],
            approved_assets=[{"asset_id": "img-1", "approved": True}],
        )

        self.assertEqual(report["status"], "sufficient")
        self.assertEqual(report["missing_materials"], [])

    def test_prediction_topic_without_dataset_requires_degraded_choice(self):
        report = assess_material_sufficiency(
            topic="基于图神经网络的城市空气质量预测方法研究",
            references=[{"title": "A real paper"}],
        )

        self.assertEqual(report["status"], "WAITING_REQUIRED_USER_MATERIALS")
        self.assertIn("missing_result_dataset", report["missing_materials"])
        self.assertTrue(report["degraded_writing_available"])


class AssetStoreTests(unittest.TestCase):
    def test_only_approved_assets_are_renderable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ImageAssetStore(Path(tmp) / "assets.json")
            store.register_candidates([
                {
                    "asset_id": "img-1",
                    "title": "Robot arm",
                    "section_id": "methods",
                    "purpose": "device_photo",
                    "source_url": "https://example.test/image",
                    "image_url": "https://example.test/image.jpg",
                    "license": "CC BY 4.0",
                    "attribution": "Example Author",
                }
            ])

            self.assertEqual(store.approved_assets(), [])
            approved = store.approve(["img-1"])
            self.assertEqual(len(approved), 1)
            self.assertTrue(approved[0]["approved"])


class RenderValidationTests(unittest.TestCase):
    def test_unresolved_references_and_missing_images_warn_without_blocking_render(self):
        result = validate_renderable_ast({
            "title": "Broken paper",
            "sections": [
                {
                    "section_id": "results",
                    "title": "Results",
                    "content": "Result claim [ref0]\n\n[Figure: missing.png]",
                }
            ],
            "references": [],
        })

        self.assertTrue(result["ok"])
        self.assertTrue(any("unresolved citation" in warning for warning in result["warnings"]))
        self.assertTrue(any("missing figure" in warning for warning in result["warnings"]))

    def test_unapproved_structured_image_warns_without_blocking_render(self):
        result = validate_renderable_ast({
            "title": "Draft",
            "sections": [{"section_id": "intro", "title": "Intro", "content": "Text."}],
            "references": [{"citation_key": "ref0", "title": "Paper"}],
            "entity_registry": {
                "images": [{"asset_id": "img-1", "approved": False, "local_path": "x.png"}]
            },
        })

        self.assertTrue(result["ok"])
        self.assertTrue(any("unapproved image" in warning for warning in result["warnings"]))

    def test_required_planned_image_warns_without_blocking_render(self):
        result = validate_renderable_ast({
            "title": "Draft",
            "sections": [{"section_id": "methods", "title": "Methods", "content": "Text."}],
            "references": [{"citation_key": "ref0", "title": "Paper"}],
            "asset_plan": [{
                "section_id": "methods",
                "asset_type": "searched_image_or_diagram",
                "purpose": "system_or_device_context",
                "required": True,
            }],
            "entity_registry": {"images": []},
        })

        self.assertTrue(result["ok"])
        self.assertTrue(any("required approved image asset missing" in warning for warning in result["warnings"]))

    def test_generated_methods_diagram_satisfies_required_visual(self):
        result = validate_renderable_ast({
            "title": "Draft",
            "sections": [{"section_id": "methods", "title": "Methods", "content": "Text."}],
            "references": [],
            "asset_plan": [{
                "section_id": "methods",
                "asset_type": "searched_image_or_diagram",
                "purpose": "system_or_device_context",
                "required": True,
            }],
            "entity_registry": {
                "images": [],
                "figures": [{
                    "approved": True,
                    "section_id": "methods",
                    "purpose": "system_or_device_context",
                }],
            },
        })

        self.assertFalse(any("required approved image asset missing" in warning for warning in result["warnings"]))

    def test_embedded_source_images_are_not_reported_as_unbound_uploads(self):
        result = validate_renderable_ast({
            "title": "Draft",
            "sections": [{"section_id": "methods", "title": "Methods", "content": "Text."}],
            "references": [],
            "materials": [{
                "material_id": "embedded-1",
                "material_role": "image_asset",
                "parse_status": "parsed",
                "metadata": {"source_kind": "docx_embedded_image"},
            }],
            "entity_registry": {"images": [], "figures": []},
        })

        self.assertFalse(any("unbound uploaded image asset" in warning for warning in result["warnings"]))

    def test_citations_resolve_to_final_numeric_markers(self):
        ast = {
            "sections": [
                {
                    "title": "Intro",
                    "content": "Prior work [ref0].",
                    "references_used": ["ref0"],
                }
            ],
            "references": [{"citation_key": "ref0", "title": "Paper A"}],
        }

        CitationResolver().resolve(ast)

        self.assertIn("[1]", ast["sections"][0]["content"])
        self.assertNotIn("[ref0]", ast["sections"][0]["content"])

    def test_grouped_citations_resolve_to_numeric_markers(self):
        ast = {
            "sections": [{
                "title": "Intro",
                "content": "Prior work [ref0, ref1].",
                "references_used": ["ref0", "ref1"],
            }],
            "references": [
                {"citation_key": "ref0", "title": "Paper A"},
                {"citation_key": "ref1", "title": "Paper B"},
            ],
        }

        CitationResolver().resolve(ast)

        self.assertIn("[1, 2]", ast["sections"][0]["content"])
        self.assertNotIn("[ref", ast["sections"][0]["content"])


class QualityAuditTests(unittest.TestCase):
    def test_detects_cross_section_parameter_conflicts(self):
        audit = audit_manuscript([
            {"title": "Methods", "content": "The system uses a 14-channel EEG device and LDA."},
            {"title": "Results", "content": "Signals were captured by a 64-channel EEG cap with SVM."},
        ])

        self.assertTrue(any(issue["code"] == "eeg_channel_conflict" for issue in audit["issues"]))


if __name__ == "__main__":
    unittest.main()
