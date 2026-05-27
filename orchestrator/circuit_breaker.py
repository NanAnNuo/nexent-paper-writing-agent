"""
熔断机制 — 重试计数器 + 熔断判断

用于控制 Debug 循环、Discriminator 审查循环的最大尝试次数。
支持序列化，可写入 paper_ast.json 持久化。
"""

import time
from typing import Optional


class RetryCounter:
    """可持久化的重试计数器"""

    def __init__(self, name: str = "", max_retries: int = 3):
        self.name = name
        self.max_retries = max_retries
        self._attempts: list[dict] = []

    @property
    def count(self) -> int:
        return len(self._attempts)

    @property
    def is_blown(self) -> bool:
        return self.count >= self.max_retries

    def increment(self, context: str = "") -> int:
        self._attempts.append({
            "attempt": self.count + 1,
            "timestamp": time.time(),
            "context": context,
        })
        return self.count

    def reset(self):
        self._attempts.clear()

    def last_error(self) -> Optional[str]:
        if not self._attempts:
            return None
        return self._attempts[-1].get("context", "")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "max_retries": self.max_retries,
            "count": self.count,
            "is_blown": self.is_blown,
            "attempts": self._attempts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RetryCounter":
        obj = cls(name=data.get("name", ""), max_retries=data.get("max_retries", 3))
        obj._attempts = data.get("attempts", [])
        return obj


class CircuitBreaker:
    """熔断器 — 当重试计数器熔断时跳过操作"""

    def __init__(self, name: str = "", max_retries: int = 3):
        self.counter = RetryCounter(name=name, max_retries=max_retries)
        self._bypassed = False

    def attempt(self, context: str = "") -> bool:
        """尝试执行操作。返回 True 可执行，False 已熔断需降级"""
        if self._bypassed:
            return True  # 已被手动 bypass
        if self.counter.is_blown:
            return False
        self.counter.increment(context)
        return True

    def bypass(self):
        """手动跳过熔断"""
        self._bypassed = True

    def reset(self):
        self.counter.reset()
        self._bypassed = False

    def to_dict(self) -> dict:
        return {**self.counter.to_dict(), "bypassed": self._bypassed}

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitBreaker":
        obj = cls(
            name=data.get("name", ""),
            max_retries=data.get("max_retries", 3),
        )
        obj._bypassed = data.get("bypassed", False)
        obj.counter = RetryCounter.from_dict(data)
        return obj
