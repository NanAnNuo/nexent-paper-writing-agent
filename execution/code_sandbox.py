"""
代码沙盒 — 安全执行远端生成的 Python 绘图代码

在本地 venv 环境中通过 subprocess 执行代码，捕获 stdout/stderr。
支持超时控制和输出文件检测。
"""

import os
import sys
import subprocess
import tempfile
import time
import traceback as tb
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.utils import setup_logging

logger = setup_logging("code_sandbox")


@dataclass
class ExecutionResult:
    success: bool = False
    output: str = ""
    error: str = ""
    traceback: str = ""
    figure_paths: list[str] = field(default_factory=list)
    execution_time: float = 0.0


class CodeSandbox:
    """安全的 Python 代码沙盒执行环境"""

    def __init__(self, work_dir: str = "figures", timeout: int = 30):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def execute(self, code: str, filename: str = "temp_figure.py") -> ExecutionResult:
        """
        在沙盒中执行 Python 代码
        """
        result = ExecutionResult()

        # 写入临时文件
        script_path = (self.work_dir / filename).resolve()
        script_path.write_text(code, encoding="utf-8")

        start = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, "MPLBACKEND": "Agg"},
            )
            result.execution_time = time.time() - start
            result.output = proc.stdout.strip()
            result.error = proc.stderr.strip()

            if proc.returncode == 0:
                result.success = True
                result.figure_paths = self._find_generated_figures()
                logger.info(f"代码执行成功 ({result.execution_time:.1f}s), 生成 {len(result.figure_paths)} 个文件")
            else:
                result.traceback = self._format_traceback(proc.stderr)
                logger.warning(
                    "代码执行失败 (returncode=%s): %s",
                    proc.returncode,
                    (result.traceback or result.error or "no stderr")[:500],
                )

        except subprocess.TimeoutExpired:
            result.execution_time = time.time() - start
            result.error = f"执行超时 ({self.timeout}s)"
            result.traceback = f"TimeoutError: 代码执行超过 {self.timeout} 秒限制"
            logger.warning(f"代码执行超时 ({self.timeout}s)")

        except Exception as e:
            result.execution_time = time.time() - start
            result.error = str(e)
            result.traceback = tb.format_exc()
            logger.error(f"沙盒执行异常: {e}")

        # 清理临时脚本
        try:
            script_path.unlink()
        except OSError:
            pass

        return result

    def _find_generated_figures(self) -> list[str]:
        """检测生成的图表文件"""
        figures = []
        for ext in ("*.png", "*.pdf", "*.svg", "*.jpg"):
            figures.extend(str(p) for p in self.work_dir.glob(ext))
        return sorted(figures)

    def _format_traceback(self, stderr: str) -> str:
        """格式化错误回溯"""
        lines = stderr.split("\n")
        # 只保留关键错误信息
        relevant = []
        for line in lines:
            if "Traceback" in line or "Error" in line or "Exception" in line:
                relevant.append(line)
            elif line.strip() and relevant:
                relevant.append(line)
        return "\n".join(relevant[-10:]) if relevant else stderr[:500]
