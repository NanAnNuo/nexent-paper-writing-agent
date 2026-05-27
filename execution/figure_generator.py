"""
图表生成器 — Generator_Coder + CodeSandbox + Debug 循环

集成代码生成 -> 沙盒执行 -> 失败 Debug(最多 3 次) -> 降级占位图。
"""

from typing import Optional

from .code_sandbox import CodeSandbox, ExecutionResult
from inference.nexent_client import NexentClient
from orchestrator.circuit_breaker import CircuitBreaker
from core.utils import setup_logging

logger = setup_logging("figure_generator")


def generate_figure(
    context: str,
    code: Optional[str] = None,
    nexent_client: Optional[NexentClient] = None,
    sandbox: Optional[CodeSandbox] = None,
    max_debug_attempts: int = 3,
) -> ExecutionResult:
    """
    完整的图表生成流程：代码生成 -> 执行 -> Debug 循环

    如果 code 为 None，先调用 Generator_Coder 生成代码。
    执行失败后最多重试 max_debug_attempts 次。
    超限后降级为占位图。
    """
    nexent_client = nexent_client or NexentClient()
    sandbox = sandbox or CodeSandbox()
    breaker = CircuitBreaker(name="figure_gen", max_retries=max_debug_attempts)

    # Step 1: 如果没有代码，先生成代码
    if not code:
        logger.info("调用 Generator_Coder 生成绘图代码")
        code = nexent_client.generator_coder(context)
        if not code:
            logger.error("Generator_Coder 返回空代码")
            return _fallback_figure()

    # Step 2: 执行 + Debug 循环
    attempt = 0
    while attempt < max_debug_attempts:
        attempt += 1
        logger.info(f"执行绘图代码 (第 {attempt}/{max_debug_attempts} 次)")

        result = sandbox.execute(code)
        if result.success:
            logger.info(f"图表生成成功 (第 {attempt} 次)")
            return result

        if attempt < max_debug_attempts:
            logger.warning(f"图表执行失败，请求修复 (第 {attempt} 次)")
            breaker.counter.increment(context=result.traceback)
            code = nexent_client.generator_coder(
                context=context,
                traceback=result.traceback,
            )
            if not code:
                logger.error("Generator_Coder 返回空修复代码")
                break
        else:
            logger.warning(f"Debug 循环超限 ({max_debug_attempts} 次)，降级为占位图")

    return _fallback_figure()


def _fallback_figure() -> ExecutionResult:
    """生成占位图"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.text(0.5, 0.5, "Figure Placeholder\n(Debug failed)", ha="center", va="center",
            fontsize=14, transform=ax.transAxes)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    os.makedirs("figures", exist_ok=True)
    path = "figures/fallback_placeholder.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    result = ExecutionResult()
    result.success = True
    result.figure_paths = [path]
    result.output = "Fallback figure generated (debug attempts exhausted)"
    result.error = ""
    result.traceback = ""
    return result


import os  # noqa: E402 (needed for _fallback_figure)
