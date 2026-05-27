from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class SectionOutline:
    id: str
    title: str
    key_points: list[str] = field(default_factory=list)


@dataclass
class PaperOutline:
    title: str
    sections: list[SectionOutline] = field(default_factory=list)


@dataclass
class PaperReference:
    citation_key: str  # ref0, ref1, ...
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    url: str = ""
    venue: str = ""

    def short_str(self) -> str:
        author_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            author_str += " et al."
        return f"{author_str} ({self.year}). {self.title}. {self.venue}"


@dataclass
class PaperSection:
    section_id: str
    title: str
    content: str
    references_used: list[str] = field(default_factory=list)  # citation_keys


@dataclass
class PaperAST:
    title: str
    sections: list[PaperSection] = field(default_factory=list)
    references: list[PaperReference] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PaperAST":
        sections = [PaperSection(**s) for s in data.get("sections", [])]
        refs = [PaperReference(**r) for r in data.get("references", [])]
        return cls(title=data["title"], sections=sections, references=refs)
