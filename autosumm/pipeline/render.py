"""
Render summary contents to specified format(s).
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import re
from datetime import datetime

try:
    from client import BaseClient, BatchConfig
except:
    from .client import BaseClient, BatchConfig

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

@dataclass
class HTMLRendererConfig:
    math_renderer: str="mathjax"
    mathjax_url: Optional[str]=None
    katex_url: Optional[str]=None
    include_toc: bool=True
    toc_depth: int=3
    number_sections: bool=False
    standalone: bool=True
    self_contained: bool=False
    css_file: Optional[str]=None
    css_inline: Optional[str]=None
    template_file: Optional[str]=None
    highlight_style: str="pygments"
    html5: bool=True

class AZW3RendererConfig:
    pass

@dataclass
class RendererConfig:
    formats: List[str]=field(default_factory=lambda: ["pdf","md"]) # allowed formats: pdf, html, md, epub, mp3, wav, ogg
    output_dir: str="./output"
    base_filename: Optional[str]=None # If None, auto-generate timestamp-based name
    md: MarkdownRendererConfig=field(default_factory=MarkdownRendererConfig)
    pdf: PDFRendererConfig=field(default_factory=PDFRendererConfig)
    html: HTMLRendererConfig=field(default_factory=HTMLRendererConfig)
    azw3: AZW3RendererConfig=field(default_factory=AZW3RendererConfig)

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

    if config.md.include_pagebreaks:
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
    temp_md_file = md_file

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

    subprocess.run(cmd, check=True, capture_output=True,text=True)

    if temp_md_file and temp_md_file.exists():
        temp_md_file.unlink()

    return RenderResult(
        path=str(pdf_file),
        format="pdf",
        success=True
    )

def render_html(summaries: List[str], category, config: RendererConfig) -> RenderResult:
    md_result = None
    temp_md_file = None

    md_result = render_md(summaries, category, config)
    if not md_result.success:
        return RenderResult(
            path="",
            format="html",
            success=False,
            error=f"Failed to create intermediate markdown: {md_result.error}"
        )
    
    md_file = Path(md_result.path)
    temp_md_file = md_file

    content = md_file.read_text(encoding='utf-8')

    content = re.sub(r'\n{3,}', r'\n\n', content)
    content = content.replace("\\pagebreak","")

    md_file.write_text(content, encoding='utf-8')

    output_path = _ensure_output_dir(config.output_dir)
    base_filename = _generate_base_filename(category, config)
    html_file = output_path / f"{base_filename}.html"

    cmd = [
        "pandoc",
        str(md_file),
        "-f", "gfm",  # GitHub-flavored markdown
        "-t", "html5" if config.html.html5 else "html",
        "-o", str(html_file),
        f"--highlight-style={config.html.highlight_style}"
    ]

    if config.html.standalone:
        cmd.append("--standalone")
    
    if config.html.include_toc:
        cmd.extend(["--toc", f"--toc-depth={config.html.toc_depth}"])

    if config.html.number_sections:
        cmd.append("--number-sections")

    if config.html.math_renderer == "mathjax":
        if config.html.mathjax_url:
            cmd.append(f"--mathjax={config.html.mathjax_url}")
        else:
            cmd.append("--mathjax")
    
    elif config.html.math_renderer == "katex":
        if config.html.katex_url:
            cmd.append(f"--katex={config.html.katex_url}")
        else:
            cmd.append("--katex")

    elif config.html_renderer == "mathml":
        cmd.append("--mathml")
    elif config.html.renderer == "webtex":
        cmd.append("--webtex")

    if config.html.self_contained:
        cmd.append("--self-contained")
    
    if config.html.css_file:
        cmd.extend(["--css", config.html.css_file])
    
    if config.html.css_inline:
        temp_css = output_path / f"temp_{base_filename}.css"
        temp_css.write_text(config.html.css_inline, encoding='utf-8')
        cmd.extend(["--css", str(temp_css)])

    if config.html.template_file:
        cmd.extend(["--template", config.html.template_file])

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Clean up temporary files
    if config.html.css_inline:
        temp_css = output_path / f"temp_{base_filename}.css"
        temp_css.unlink(missing_ok=True)
    if temp_md_file and temp_md_file.exists():
        temp_md_file.unlink()

    return RenderResult(
        path=str(html_file),
        format="html",
        success=True
    )

def render_azw3(summaries: List[str], category, config: RendererConfig) -> RenderResult:
    pass

def render(summaries: List[str], category: str, config: RendererConfig) -> List[RenderResult]:
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

    # move "md" to end of config.formats
    reordered_formats = [f for f in config.formats if f != "md"]
    if "md" in config.formats:
        reordered_formats.append("md")

    for format_name in reordered_formats:
        if format_name == "md":
            result = render_md(summaries, category, config)
        elif format_name == "pdf":
            result = render_pdf(summaries, category, config)
        elif format_name == "html":
            result = render_html(summaries, category, config)
        elif format_name == "azw3":
            result = render_azw3(summaries, category, config)
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
        "## Title: First Paper\n##### Authors: Alice, Bob\n##### Link: arxiv:2301.00001\n\nThis is the first summary.\n$x=x+2$\n$$ x^2=4 $$",
        "## Title: Second Paper\n##### Authors: Charlie, Dave\n##### Link: arxiv:2301.00002\n\nThis is the second summary.\n$x=x+2$\n$$ x^2=4 $$"
    ]
    
    config = RendererConfig(
        formats=["md", "pdf", "html"],
        output_dir="./test_output"
    )
    
    results = render(test_summaries, "cs.AI", config)
    
    for result in results:
        if result.success:
            print(f"✓ {result.format}: {result.path}")
        else:
            print(f"✗ {result.format}: {result.error}")