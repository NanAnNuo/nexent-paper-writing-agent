"""Deterministic manuscript checks inspired by reviewer-facing Nature checks."""

from __future__ import annotations

import re
from typing import Iterable


CHANNEL_RE = re.compile(r"(\d+)[-\s]?(?:channel|channels|通道)", re.IGNORECASE)
CLASSIFIER_TERMS = {"lda", "svm", "cnn", "lstm", "eegnet"}
RESULT_SECTION_HINTS = {"result", "experiment", "结果", "实验"}
DISCUSSION_HINTS = {"discussion", "讨论"}
CONCLUSION_HINTS = {"conclusion", "结论"}
OVERCLAIM_TERMS = {"proves", "guarantees", "首次", "完全证明", "必然"}


def audit_manuscript(
    sections: Iterable[dict],
    *,
    evidence_registry: dict | None = None,
    entity_registry: dict | None = None,
) -> dict:
    issues = []
    evidence_registry = evidence_registry or {}
    entity_registry = entity_registry or {}
    result_dataset_ids = set(evidence_registry.get("materials", {}).get("result_dataset_ids", []))
    structured_result_assets = list(entity_registry.get("figures", [])) + list(entity_registry.get("tables", []))
    channel_mentions = {}
    classifier_mentions = {}

    for section in sections or []:
        title = str(section.get("title", ""))
        content = str(section.get("content") or section.get("section_content") or "")
        lowered = content.lower()
        for channel in CHANNEL_RE.findall(content):
            channel_mentions.setdefault(channel, set()).add(title)
        used_classifiers = {term for term in CLASSIFIER_TERMS if term in lowered}
        if used_classifiers:
            classifier_mentions[title] = sorted(used_classifiers)

        if any(hint in title.lower() for hint in RESULT_SECTION_HINTS):
            numeric_claims = bool(re.search(r"\d+(?:\.\d+)?\s*(?:%|ms|s\b|p\s*[<=>])", lowered))
            has_reference = bool(re.search(r"\[(?:ref)?\d+\]", content))
            if numeric_claims and not (has_reference or result_dataset_ids):
                issues.append({
                    "code": "unsupported_numeric_result",
                    "severity": "error",
                    "section": title,
                    "message": "Result metrics appear without a result dataset or citation linkage.",
                })
            if result_dataset_ids and not structured_result_assets and "[Figure:" not in content:
                issues.append({
                    "code": "result_evidence_not_visualized",
                    "severity": "warning",
                    "section": title,
                    "message": "Result datasets exist but the result section has no structured figure or table asset.",
                })
        if any(hint in title.lower() for hint in DISCUSSION_HINTS | CONCLUSION_HINTS):
            if any(term in lowered for term in OVERCLAIM_TERMS):
                issues.append({
                    "code": "overbounded_conclusion",
                    "severity": "warning",
                    "section": title,
                    "message": "Discussion or conclusion language may overstate the supported evidence.",
                })

    if len(channel_mentions) > 1:
        issues.append({
            "code": "eeg_channel_conflict",
            "severity": "error",
            "message": f"Conflicting EEG channel counts: {sorted(channel_mentions)}",
        })
    if len(classifier_mentions) > 1:
        unique_sets = {tuple(values) for values in classifier_mentions.values()}
        if len(unique_sets) > 1:
            issues.append({
                "code": "classifier_scope_conflict",
                "severity": "warning",
                "message": "Classifier mentions change across sections; verify method/result consistency.",
            })
    return {
        "ok": not any(issue["severity"] == "error" for issue in issues),
        "issues": issues,
    }
