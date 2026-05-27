"""
AST 状态管理器

管理 paper_ast.json 的读写、检查点保存/加载、旧格式迁移。
核心数据结构遵循 v6.0 架构：含 entity_registry、citation_registry、execution_trace。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.utils import save_json, load_json, setup_logging

logger = setup_logging("state_manager")


class PaperProject:
    """单篇论文项目的状态"""

    def __init__(self, title: str = ""):
        self.title = title
        self.sections: list[dict] = []
        self.references: list[dict] = []
        self.entity_registry: dict = {
            "images": [],
            "figures": [],
            "tables": [],
            "equations": [],
        }
        self.materials: list[dict] = []
        self.evidence_registry: dict = {}
        self.citation_registry: dict = {}
        self.execution_trace: list[dict] = []
        self.metadata: dict = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "initialized",
        }

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "sections": self.sections,
            "references": self.references,
            "entity_registry": self.entity_registry,
            "materials": self.materials,
            "evidence_registry": self.evidence_registry,
            "citation_registry": self.citation_registry,
            "execution_trace": self.execution_trace,
            "metadata": {**self.metadata, "updated_at": datetime.now().isoformat()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperProject":
        project = cls(title=data.get("title", ""))
        project.sections = data.get("sections", [])
        project.references = data.get("references", [])
        project.entity_registry = data.get("entity_registry", {
            "images": [], "figures": [], "tables": [], "equations": [],
        })
        project.materials = data.get("materials", [])
        project.evidence_registry = data.get("evidence_registry", {})
        project.citation_registry = data.get("citation_registry", {})
        project.execution_trace = data.get("execution_trace", [])
        project.metadata = data.get("metadata", {})
        return project

    def append_section(self, section: dict):
        self.sections.append(section)
        self.metadata["updated_at"] = datetime.now().isoformat()

    def add_reference(self, ref: dict):
        t = ref.get("title", "").strip().lower()
        if t and not any(r.get("title", "").strip().lower() == t for r in self.references):
            ref["_global_idx"] = len(self.references)
            self.references.append(ref)

    def get_section(self, section_id: str) -> Optional[dict]:
        for s in self.sections:
            if s.get("section_id") == section_id:
                return s
        return None

    def log_trace(self, event: str, detail: str = ""):
        self.execution_trace.append({
            "event": event,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        })


class StateManager:
    """AST 状态的读写管理器"""

    def __init__(self, checkpoint_dir: str = "data/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._project: Optional[PaperProject] = None

    def new_project(self, title: str) -> PaperProject:
        self._project = PaperProject(title=title)
        self._project.metadata["status"] = "outline_generated"
        self.save()
        logger.info(f"新项目已创建: {title}")
        return self._project

    def load_project(self, project_id: str = "final_ast") -> Optional[PaperProject]:
        """从文件加载项目状态。自动兼容旧格式。"""
        path = self.checkpoint_dir / f"{project_id}.json"
        data = load_json(str(path))
        if not data:
            logger.warning(f"检查点不存在: {path}")
            return None

        # 旧格式迁移: 检测缺少的字段
        needs_migration = False
        if "entity_registry" not in data:
            data["entity_registry"] = {"images": [], "figures": [], "tables": [], "equations": []}
            needs_migration = True
        elif "images" not in data["entity_registry"]:
            data["entity_registry"]["images"] = []
            needs_migration = True
        if "evidence_registry" not in data:
            data["evidence_registry"] = {}
            needs_migration = True
        if "materials" not in data:
            data["materials"] = []
            needs_migration = True
        if "citation_registry" not in data:
            data["citation_registry"] = {}
            needs_migration = True
        if "execution_trace" not in data:
            data["execution_trace"] = []
            needs_migration = True
        if "metadata" not in data:
            data["metadata"] = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "status": "migrated",
            }
            needs_migration = True

        self._project = PaperProject.from_dict(data)

        if needs_migration:
            logger.info(f"项目已从旧格式迁移: {path}")
            self.save()

        logger.info(f"项目已加载: {self._project.title} ({len(self._project.sections)} 章节)")
        return self._project

    @property
    def project(self) -> Optional[PaperProject]:
        return self._project

    def save(self, project_id: str = "final_ast"):
        if not self._project:
            logger.warning("没有活跃项目可保存")
            return
        path = self.checkpoint_dir / f"{project_id}.json"
        save_json(self._project.to_dict(), str(path))
        logger.info(f"项目已保存: {path}")

    def save_checkpoint(self, name: str):
        """保存命名检查点（如章节级）"""
        if not self._project:
            return
        path = self.checkpoint_dir / f"{name}.json"
        save_json(self._project.to_dict(), str(path))

    def list_checkpoints(self) -> list[str]:
        return sorted(str(p.name) for p in self.checkpoint_dir.glob("*.json"))
