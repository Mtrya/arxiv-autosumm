"""
Render summary contents to specified format(s).
"""

from typing import List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class RendererConfig:
    formats=List[str] # allowed formats: pdf, html, md, epub, mp3, wav, ogg

@dataclass
class RenderResult:
    path: str
    format: str
    success: bool

def render_md(summaries: List[str]) -> RenderResult:
    output_dir = Path("./tmp")
    filepath = output_dir / "test.md"

    markdown_content = "\n\n".join(summaries)
    filepath.write_text(markdown_content,encoding='utf-8')

    return RenderResult(
        path=filepath,
        format="md",
        success=True
    )

if __name__ == "__main__":
    a = "123456"
    b = "523"
    render_md([a,b])