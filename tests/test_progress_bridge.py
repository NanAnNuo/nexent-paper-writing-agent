import time
import unittest

from main import _run_with_heartbeat


class FakeContext:
    def __init__(self):
        self.progress = []
        self.logs = []

    async def report_progress(self, progress, total=None, message=None):
        self.progress.append((progress, total, message))

    async def info(self, message):
        self.logs.append(message)


class ProgressBridgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocking_work_reports_heartbeat_before_return(self):
        ctx = FakeContext()

        result = await _run_with_heartbeat(
            lambda: (time.sleep(0.06), "done")[1],
            ctx=ctx,
            progress=1,
            total=3,
            message="drafting",
            heartbeat_seconds=0.01,
        )

        self.assertEqual(result, "done")
        self.assertGreaterEqual(len(ctx.progress), 2)
        self.assertEqual(ctx.progress[0][:2], (1, 3))
        self.assertTrue(any("drafting" in message for message in ctx.logs))


if __name__ == "__main__":
    unittest.main()
