"""Issue + DiffPatch schema shared by all critics, synthesizer, and refiner.

See SKILL.md for semantics.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Literal, List
import json


Category = Literal["visual", "content", "cognitive", "compliance"]


@dataclass
class DiffPatch:
    file: str
    line_start: int
    line_end: int
    old: str
    new: str


@dataclass
class Issue:
    slide: int
    category: Category
    severity: int
    title: str
    detail: str
    patch: Optional[DiffPatch] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.patch is None:
            d["patch"] = None
        return d


def issues_to_json(issues: List[Issue]) -> str:
    return json.dumps([i.to_dict() for i in issues], ensure_ascii=False, indent=2)


def issues_from_json(payload: str) -> List[Issue]:
    raw = json.loads(payload)
    out: List[Issue] = []
    for r in raw:
        patch = r.get("patch")
        dp = DiffPatch(**patch) if patch else None
        out.append(Issue(
            slide=r["slide"],
            category=r["category"],
            severity=r["severity"],
            title=r["title"],
            detail=r["detail"],
            patch=dp,
        ))
    return out
