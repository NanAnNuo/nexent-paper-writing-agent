import tempfile
import unittest
from pathlib import Path

from orchestrator.write_jobs import WriteJobProgressContext, WriteJobStore


class WriteJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_job_progress_context_persists_progress_and_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WriteJobStore(Path(tmp) / "write_jobs.json")
            job = store.create(title="Draft", section_count=3)
            store.mark_running(job["job_id"])
            context = WriteJobProgressContext(store, job["job_id"])

            await context.report_progress(1, total=3, message="drafting section 1")
            await context.info("reviewing section 1")
            store.finish(job["job_id"], {"status": "completed", "download_url": "http://paper"})

            snapshot = store.get(job["job_id"])
            self.assertEqual(snapshot["status"], "completed")
            self.assertEqual(snapshot["progress"]["current"], 1)
            self.assertEqual(snapshot["result"]["download_url"], "http://paper")
            self.assertTrue(any("reviewing section 1" in event["message"] for event in snapshot["events"]))

    async def test_section_job_uses_section_kind_and_result_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WriteJobStore(Path(tmp) / "write_jobs.json")
            job = store.create(title="Methods", section_count=1, job_kind="section")

            store.mark_running(job["job_id"])
            store.finish(job["job_id"], {
                "status": "success",
                "section_id": "methods",
                "section_content": "Method text.",
            })

            snapshot = store.get(job["job_id"])
            self.assertTrue(job["job_id"].startswith("section-"))
            self.assertEqual(snapshot["job_kind"], "section")
            self.assertEqual(snapshot["status"], "completed")
            self.assertEqual(snapshot["result_status"], "success")
            self.assertEqual(snapshot["result"]["section_content"], "Method text.")

    async def test_paper_job_persists_input_snapshot_for_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WriteJobStore(Path(tmp) / "write_jobs.json")
            job = store.create(
                title="Draft",
                section_count=2,
                snapshot={"material_ids": ["mat-1"], "outline": {"title": "Draft"}},
            )

            snapshot = store.get(job["job_id"])

            self.assertEqual(snapshot["snapshot"]["material_ids"], ["mat-1"])
            self.assertEqual(snapshot["snapshot"]["outline"]["title"], "Draft")


if __name__ == "__main__":
    unittest.main()
