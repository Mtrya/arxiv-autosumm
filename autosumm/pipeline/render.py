"""
Render summary contents to specified format(s).
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import re
import os
from datetime import datetime

@dataclass
class MarkdownRendererConfig:
    include_pagebreaks: bool=True

@dataclass
class PDFRendererConfig:
    pdf_engine: str="xelatex" # install xelatex: ```sudo apt install texlive-xetex``` for ubuntu
    highlight_style: str="pygments"
    font_size: str="14pt"
    document_class: str="extarticle"
    margin: str="0.8in"
    colorlinks: bool=True
    link_color: str="RoyalBlue"
    line_stretch: float=1.15
    pandoc_input_format: str="markdown+raw_tex+yaml_metadata_block"
    pandoc_from_format: str="gfm"
    additional_pandoc_args: List[str]=field(default_factory=list)

@dataclass
class RendererConfig:
    formats: List[str]=field(default_factory=lambda: ["pdf","md"]) # allowed formats: pdf, html, md, epub, mp3, wav, ogg
    output_dir: str="./output"
    base_filename: Optional[str]=None # If None, auto-generate timestamp-based name
    markdown: MarkdownRendererConfig=field(default_factory=MarkdownRendererConfig)
    pdf: PDFRendererConfig=field(default_factory=PDFRendererConfig)

@dataclass
class RenderResult:
    path: str
    format: str
    success: bool
    error: Optional[str]=None

def _generate_base_filename(category: str, config: RendererConfig) -> str:
    """Generate base filename"""
    now = datetime.now()
    iso_calender = now.isocalendar()
    current_year = iso_calender.year
    current_week_number = iso_calender.week

    category_clean = category.replace('.','')

    if config.base_filename:
        return f"config.base_filename{current_year-2000:02d}{current_week_number:02d}"

    return f"summary_{category_clean}_{current_year-2000:02d}{current_week_number:02d}"

def _ensure_output_dir(output_dir: str) -> Path:
    """Ensure output directory exists and return Path object"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path

def render_md(summaries: List[str], category: str, config: RendererConfig) -> RenderResult:
    output_path = _ensure_output_dir(config.output_dir)
    base_filename = _generate_base_filename(category, config)
    md_file = output_path / f"{base_filename}.md"

    if config.markdown.include_pagebreaks:
        separator = "\n\n\\pagebreak\n\n"
        content = separator.join(summaries)
    else:
        content = "\n\n".join(summaries)
    
    content = re.sub(r'\n{3,}', r'\n\n', content)

    md_file.write_text(content, encoding='utf-8')

    return RenderResult(
        path=str(md_file),
        format="md",
        success=True
    )


def render_pdf(summaries: List[str], category, config: RendererConfig) -> RenderResult:
    md_result = None
    temp_md_file = None

    md_result = render_md(summaries, category, config)
    if not md_result.success:
        return RenderResult(
            path="",
            format="pdf",
            success=False,
            error=f"Failed to create intermediate markdown: {md_result.error}"
        )
    
    md_file = Path(md_result.path)

    if "md" not in config.formats:
        temp_md_file = md_file # if markdown is not wanted, remember to clean it up later

    content = md_file.read_text(encoding='utf-8')

    content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
    content = re.sub(r'\n{3,}', r'\n\n', content)

    md_file.write_text(content, encoding='utf-8')

    output_path = _ensure_output_dir(config.output_dir)
    base_filename = _generate_base_filename(category, config)
    pdf_file = output_path / f"{base_filename}.pdf"

    cmd = [
        "pandoc",
        str(md_file),
        "-f", config.pdf.pandoc_from_format,
        "-t", "pdf",
        f"--pdf-engine={config.pdf.pdf_engine}",
        "-o", str(pdf_file),
        f"--highlight-style={config.pdf.highlight_style}",
        "--variable", f"classoption={config.pdf.font_size}",
        "--variable", f"documentclass={config.pdf.document_class}",
        "--variable", f"geometry:margin={config.pdf.margin}",
        "--variable", f"linestretch={config.pdf.line_stretch}",
        "--from", config.pdf.pandoc_input_format
    ]

    if config.pdf.colorlinks:
        cmd.extend([
            "--variable", "colorlinks=true",
            "--variable", f"linkcolor={config.pdf.link_color}"
        ])

    cmd.extend(config.pdf.additional_pandoc_args)

    subprocess.run(cmd, check=True, capture_output=True,text=True)

    if temp_md_file and temp_md_file.exists():
        temp_md_file.unlink()

    return RenderResult(
        path=str(pdf_file),
        format="pdf",
        success=True
    )



def render_html(summaries: List[str], config: RendererConfig) -> RenderResult:
    pass

def render_epub(summaries: List[str], config: RendererConfig) -> RenderResult:
    pass

def render_mp3(summaries: List[str], config: RendererConfig) -> RenderResult:
    pass

def render_wav(summaries: List[str], config: RendererConfig) -> RenderResult:
    pass

def render_ogg(summaries: List[str], config: RendererConfig) -> RenderResult:
    pass

def render(summaries: List[str],category: str, config: RendererConfig) -> List[RenderResult]:
    """Main entry point - delegates to format-specific renderers"""
    results = []

    if not summaries:
        error_result = RenderResult(
            path="",
            format="all",
            success=False,
            error="No summaries provided"
        )
        return [error_result]

    for format_name in config.formats:
        if format_name == "md":
            result = render_md(summaries, category, config)
        elif format_name == "pdf":
            result = render_pdf(summaries, category, config)
        elif format_name == "html":
            result = render_html(summaries, category, config)
        elif format_name == "epub":
            result = render_epub(summaries, category, config)
        elif format_name == "mp3":
            result = render_mp3(summaries, category, config)
        elif format_name == "wav":
            result = render_wav(summaries, category, config)
        elif format_name == "ogg":
            result = render_ogg(summaries, category, config)
        else:
            result = RenderResult(
                path="",
                format=format_name,
                success=False,
                error=f"Unsupported format: {format_name}"
            )
        results.append(result)
    
    return results

if __name__ == "__main__":
    test_summaries = [
        "## Title: First Paper\n##### Authors: Alice, Bob\n##### Link: arxiv:2301.00001\n\nThis is the first summary.",
        "## Title: Second Paper\n##### Authors: Charlie, Dave\n##### Link: arxiv:2301.00002\n\nThis is the second summary."
    ]
    
    config = RendererConfig(
        formats=["md", "pdf"],
        output_dir="./test_output"
    )
    
    results = render(test_summaries, "cs.AI", config)
    
    for result in results:
        if result.success:
            print(f"✓ {result.format}: {result.path}")
        else:
            print(f"✗ {result.format}: {result.error}")