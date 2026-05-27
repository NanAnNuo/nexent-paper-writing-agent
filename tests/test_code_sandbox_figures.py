import tempfile
import unittest
from pathlib import Path

from execution.code_sandbox import CodeSandbox


class CodeSandboxFigureTests(unittest.TestCase):
    def test_executes_script_path_from_figure_workdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = CodeSandbox(work_dir=str(Path(tmp) / "figures"), timeout=10)

            result = sandbox.execute(
                "from pathlib import Path\n"
                "Path('ok.png').write_bytes(b'png')\n"
                "print('done')\n"
            )

            self.assertTrue(result.success)
            self.assertIn("done", result.output)
            self.assertTrue(any(path.endswith("ok.png") for path in result.figure_paths))


if __name__ == "__main__":
    unittest.main()
