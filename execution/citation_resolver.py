"""
双趟引用解析器

Pass 1: 扫描所有章节，按首次出现顺序注册全局 citation_registry
Pass 2: 使用 registry 替换局部引用为全局编号
"""

import re
from core.utils import setup_logging

logger = setup_logging("citation_resolver")


class CitationResolver:
    """双趟引用解析"""

    def resolve(self, ast: dict) -> dict:
        """
        对 AST 进行双趟引用解析

        Pass 1: 构建全局引用注册表
        Pass 2: 统一替换引用编号
        """
        if not ast.get("sections"):
            logger.warning("AST 中没有章节，跳过引用解析")
            return ast

        # Pass 1: 扫描所有章节，构建全局注册表
        registry = {}  # title_lower -> global ref info
        all_section_refs = []

        for section in ast["sections"]:
            content = section.get("content", "")
            refs_used = section.get("references_used", [])

            # 从正文中提取所有引用 key
            content_refs = re.findall(r'ref\d+', content)
            section_refs = refs_used + content_refs
            local_map = {}

            for ref_key in section_refs:
                ref_key = ref_key.strip()
                if not ref_key:
                    continue

                # 查找对应的引用条目
                ref_entry = self._find_reference(ast, ref_key)
                if ref_entry:
                    title_key = (ref_entry.get("title", "") or "").strip().lower()
                    if title_key and title_key not in registry:
                        registry[title_key] = {
                            **ref_entry,
                            "_global_idx": len(registry),
                        }
                    if title_key:
                        local_map[ref_key] = str(registry[title_key]["_global_idx"] + 1)

            all_section_refs.append(local_map)

        # Pass 2: 替换引用编号
        for si, section in enumerate(ast["sections"]):
            content = section.get("content", "")
            refs_used = section.get("references_used", [])

            if si < len(all_section_refs):
                local_map = all_section_refs[si]
                def replace_marker(match):
                    keys = re.findall(r"ref\d+", match.group(1))
                    resolved = [local_map[key] for key in keys if key in local_map]
                    return f"[{', '.join(resolved)}]" if resolved else match.group(0)

                content = re.sub(
                    r"\[((?:ref\d+\s*(?:,\s*ref\d+\s*)*))\]",
                    replace_marker,
                    content,
                )
                refs_used = [local_map.get(k, k) for k in refs_used]

            section["content"] = content
            section["references_used"] = refs_used

        # 更新 AST 的引用列表
        sorted_refs = sorted(registry.values(), key=lambda x: x["_global_idx"])
        ast["references"] = [
            {k: v for k, v in r.items() if k != "_global_idx"}
            for r in sorted_refs
        ]
        ast["citation_registry"] = registry

        logger.info(f"双趟引用解析完成: {len(registry)} 篇文献, {len(ast['sections'])} 章节")
        return ast

    def _find_reference(self, ast: dict, ref_key: str) -> dict:
        """根据引用 key 查找引用条目"""
        for ref in ast.get("references", []):
            if ref.get("citation_key") == ref_key:
                return ref
            if ref_key in ref.get("citation_key", ""):
                return ref
        return {}
