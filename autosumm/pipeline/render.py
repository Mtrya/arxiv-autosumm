"""
Render summary contents to specified format(s).
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import re
import logging
from datetime import datetime
from pymarkdown.api import PyMarkdownApi, PyMarkdownApiException

try:
    from client import BaseClient, BatchConfig
except:
    from .client import BaseClient, BatchConfig

logger = logging.getLogger(__name__)

@dataclass
class MarkdownRendererConfig:
    include_pagebreaks: bool=True

@dataclass
class PDFRendererConfig:
    pdf_engine: str="xelatex" # install xelatex: ```sudo apt install texlive-xetex``` for ubuntu
    highlight_style: str="pygments"
    font_size: str="14pt"
    document_class: str="extarticle"
    margin: str="1.0in"
    colorlinks: bool=True
    link_color: str="RoyalBlue"
    line_stretch: float=1.10
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

@dataclass
class AZW3RendererConfig:
    calibre_path: Optional[str] = "/usr/bin/calibre"  # Path to ebook-convert executable
    author: str = "ArXiv AutoSumm"
    title: Optional[str] = None
    language: str = "en"
    description: Optional[str] = None
    cover_image: Optional[str] = None

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
        return f"{config.base}_filename{current_year-2000:02d}{current_week_number:02d}"

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

    try:
        api = PyMarkdownApi()
        fixed_summaries = []
        for summary in summaries:
            fix_result = api.fix_string(summary)
            fixed_summaries.append(fix_result.fixed_file)
    except PyMarkdownApiException as e:
        logger.warning(f"PyMarkdownApi failed, falling back to raw markdown: {e}")
        fixed_summaries = summaries


    if config.md.include_pagebreaks:
        separator = "\n\n\\pagebreak\n\n"
        content = separator.join(fixed_summaries)
    else:
        content = "\n\n".join(fixed_summaries)

    md_file.write_text(content, encoding='utf-8')

    return RenderResult(
        path=str(md_file),
        format="md",
        success=True
    )

def render_pdf(summaries: List[str], category, config: RendererConfig) -> RenderResult:
    output_path = _ensure_output_dir(config.output_dir)
    base_filename = _generate_base_filename(category, config)
    pdf_file = output_path / f"{base_filename}.pdf"
    
    # Test each summary individually first
    valid_summaries = []
    error_messages = []
    
    for i, summary in enumerate(summaries):
        try:
            # Test render this single summary
            test_config = RendererConfig(
                formats=["md"],
                output_dir=str(output_path),
                base_filename=f"_test_{i}",
                md=config.md,
                pdf=config.pdf,
                html=config.html
            )
            
            test_md = render_md([summary], category, test_config)
            if test_md.success:
                # Test PDF conversion for this single summary
                test_pdf_file = output_path / f"_test_{i}.pdf"
                test_md_file = Path(test_md.path)
                
                content = test_md_file.read_text(encoding='utf-8')
                content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
                content = re.sub(r'\n{3,}', r'\n\n', content)
                test_md_file.write_text(content, encoding='utf-8')
                
                cmd = [
                    "pandoc",
                    str(test_md_file),
                    "-f", config.pdf.pandoc_from_format,
                    "-t", "pdf",
                    f"--pdf-engine={config.pdf.pdf_engine}",
                    "-o", str(test_pdf_file),
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
                
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                
                # Clean up test files
                test_pdf_file.unlink(missing_ok=True)
                test_md_file.unlink(missing_ok=True)
                
                valid_summaries.append(summary)
            else:
                error_messages.append(f"Summary {i+1}: {test_md.error}")
                
        except Exception as e:
            error_messages.append(f"Summary {i+1}: {str(e)}")
    
    if not valid_summaries:
        return RenderResult(
            path="",
            format="pdf",
            success=False,
            error="All summaries failed validation: " + "; ".join(error_messages)
        )
    
    # Render all valid summaries together
    try:
        md_result = render_md(valid_summaries, category, config)
        if not md_result.success:
            return RenderResult(
                path="",
                format="pdf",
                success=False,
                error=f"Failed to create intermediate markdown: {md_result.error}"
            )
        
        md_file = Path(md_result.path)
        content = md_file.read_text(encoding='utf-8')
        content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
        content = re.sub(r'\n{3,}', r'\n\n', content)
        md_file.write_text(content, encoding='utf-8')

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

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if md_result.path and Path(md_result.path).exists():
            Path(md_result.path).unlink(missing_ok=True)

        return RenderResult(
            path=str(pdf_file),
            format="pdf",
            success=True,
            error=None if not error_messages else f"Skipped {len(error_messages)} summaries: " + "; ".join(error_messages[:3])
        )
        
    except Exception as e:
        return RenderResult(
            path="",
            format="pdf",
            success=False,
            error=str(e)
        )

def render_html(summaries: List[str], category, config: RendererConfig) -> RenderResult:
    output_path = _ensure_output_dir(config.output_dir)
    base_filename = _generate_base_filename(category, config)
    html_file = output_path / f"{base_filename}.html"
    
    # Test each summary individually first
    valid_summaries = []
    error_messages = []
    
    for i, summary in enumerate(summaries):
        try:
            # Test render this single summary
            test_config = RendererConfig(
                formats=["md"],
                output_dir=str(output_path),
                base_filename=f"_test_{i}",
                md=config.md,
                pdf=config.pdf,
                html=config.html
            )
            
            test_md = render_md([summary], category, test_config)
            if test_md.success:
                # Test HTML conversion for this single summary
                test_html_file = output_path / f"_test_{i}.html"
                test_md_file = Path(test_md.path)
                
                content = test_md_file.read_text(encoding='utf-8')
                content = re.sub(r'\n{3,}', r'\n\n', content)
                content = content.replace("\\pagebreak","")
                test_md_file.write_text(content, encoding='utf-8')
                
                cmd = [
                    "pandoc",
                    str(test_md_file),
                    "-f", "gfm",
                    "-t", "html5" if config.html.html5 else "html",
                    "-o", str(test_html_file),
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

                if config.html.self_contained:
                    cmd.append("--self-contained")
                
                if config.html.css_file:
                    cmd.extend(["--css", config.html.css_file])

                subprocess.run(cmd, check=True, capture_output=True, text=True)
                
                # Clean up test files
                test_html_file.unlink(missing_ok=True)
                test_md_file.unlink(missing_ok=True)
                
                valid_summaries.append(summary)
            else:
                error_messages.append(f"Summary {i+1}: {test_md.error}")
                
        except Exception as e:
            error_messages.append(f"Summary {i+1}: {str(e)}")
    
    if not valid_summaries:
        return RenderResult(
            path="",
            format="html",
            success=False,
            error="All summaries failed validation: " + "; ".join(error_messages)
        )
    
    # Render all valid summaries together
    try:
        md_result = render_md(valid_summaries, category, config)
        if not md_result.success:
            return RenderResult(
                path="",
                format="html",
                success=False,
                error=f"Failed to create intermediate markdown: {md_result.error}"
            )
        
        md_file = Path(md_result.path)
        content = md_file.read_text(encoding='utf-8')
        content = re.sub(r'\n{3,}', r'\n\n', content)
        content = content.replace("\\pagebreak","")
        md_file.write_text(content, encoding='utf-8')

        cmd = [
            "pandoc",
            str(md_file),
            "-f", "gfm",
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

        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Clean up temporary files
        if config.html.css_inline:
            temp_css = output_path / f"temp_{base_filename}.css"
            temp_css.unlink(missing_ok=True)
        if md_result.path and Path(md_result.path).exists():
            Path(md_result.path).unlink(missing_ok=True)

        return RenderResult(
            path=str(html_file),
            format="html",
            success=True,
            error=None if not error_messages else f"Skipped {len(error_messages)} summaries: " + "; ".join(error_messages[:3])
        )
        
    except Exception as e:
        return RenderResult(
            path="",
            format="html",
            success=False,
            error=str(e)
        )

def render_azw3(summaries: List[str], category, config: RendererConfig) -> RenderResult:
    output_path = _ensure_output_dir(config.output_dir)
    base_filename = _generate_base_filename(category, config)
    azw3_file = output_path / f"{base_filename}.azw3"
    epub_file = output_path / f"{base_filename}.epub"
    
    # Test each summary individually first
    valid_summaries = []
    error_messages = []
    
    for i, summary in enumerate(summaries):
        try:
            # Test render this single summary as ePub first
            test_config = RendererConfig(
                formats=["md"],
                output_dir=str(output_path),
                base_filename=f"_test_{i}",
                md=config.md,
                pdf=config.pdf,
                html=config.html,
                azw3=config.azw3
            )
            
            test_md = render_md([summary], category, test_config)
            if test_md.success:
                # Test ePub conversion for this single summary
                test_epub_file = output_path / f"_test_{i}.epub"
                test_md_file = Path(test_md.path)
                
                content = test_md_file.read_text(encoding='utf-8')
                content = re.sub(r'\n{3,}', r'\n\n', content)
                content = content.replace("\\pagebreak","")
                test_md_file.write_text(content, encoding='utf-8')
                
                cmd = [
                    "pandoc",
                    str(test_md_file),
                    "-f", "gfm",
                    "-t", "epub",
                    "-o", str(test_epub_file),
                    f"--highlight-style={config.html.highlight_style}",
                    "--metadata", f"title={config.azw3.title or f'ArXiv Summaries - {category}'}",
                    "--metadata", f"author={config.azw3.author}",
                    "--metadata", f"lang={config.azw3.language}",
                ]
                
                if config.azw3.description:
                    cmd.extend(["--metadata", f"description={config.azw3.description}"])
                
                if config.azw3.cover_image and Path(config.azw3.cover_image).exists():
                    cmd.extend(["--epub-cover-image", config.azw3.cover_image])
                
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                
                # Test AZW3 conversion using calibre
                test_azw3_file = output_path / f"_test_{i}.azw3"
                
                calibre_path = config.azw3.calibre_path or "ebook-convert"
                calibre_cmd = [
                    calibre_path,
                    str(test_epub_file),
                    str(test_azw3_file),
                    "--title", config.azw3.title or f'ArXiv Summaries - {category}',
                    "--authors", config.azw3.author,
                    "--language", config.azw3.language
                ]
                
                if config.azw3.description:
                    calibre_cmd.extend(["--description", config.azw3.description])
                
                if config.azw3.cover_image and Path(config.azw3.cover_image).exists():
                    calibre_cmd.extend(["--cover", config.azw3.cover_image])
                
                subprocess.run(calibre_cmd, check=True, capture_output=True, text=True)
                
                # Clean up test files
                test_epub_file.unlink(missing_ok=True)
                test_azw3_file.unlink(missing_ok=True)
                test_md_file.unlink(missing_ok=True)
                
                valid_summaries.append(summary)
            else:
                error_messages.append(f"Summary {i+1}: {test_md.error}")
                
        except Exception as e:
            error_messages.append(f"Summary {i+1}: {str(e)}")
    
    if not valid_summaries:
        return RenderResult(
            path="",
            format="azw3",
            success=False,
            error="All summaries failed validation: " + "; ".join(error_messages)
        )
    
    # Render all valid summaries together
    try:
        md_result = render_md(valid_summaries, category, config)
        if not md_result.success:
            return RenderResult(
                path="",
                format="azw3",
                success=False,
                error=f"Failed to create intermediate markdown: {md_result.error}"
            )
        
        md_file = Path(md_result.path)
        content = md_file.read_text(encoding='utf-8')
        content = re.sub(r'\n{3,}', r'\n\n', content)
        content = content.replace("\\pagebreak","")
        md_file.write_text(content, encoding='utf-8')

        # First create ePub
        cmd = [
            "pandoc",
            str(md_file),
            "-f", "gfm",
            "-t", "epub",
            "-o", str(epub_file),
            f"--highlight-style={config.html.highlight_style}",
            "--metadata", f"title={config.azw3.title or f'ArXiv Summaries - {category}'}",
            "--metadata", f"author={config.azw3.author}",
            "--metadata", f"lang={config.azw3.language}",
        ]

        if config.azw3.description:
            cmd.extend(["--metadata", f"description={config.azw3.description}"])
        
        if config.azw3.cover_image and Path(config.azw3.cover_image).exists():
            cmd.extend(["--epub-cover-image", config.azw3.cover_image])

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Convert ePub to AZW3 using calibre's ebook-convert
        try:
            calibre_path = config.azw3.calibre_path or "ebook-convert"
            calibre_cmd = [
                calibre_path,
                str(epub_file),
                str(azw3_file),
                "--title", config.azw3.title or f'ArXiv Summaries - {category}',
                "--authors", config.azw3.author,
                "--language", config.azw3.language
            ]
            
            if config.azw3.description:
                calibre_cmd.extend(["--description", config.azw3.description])
            
            if config.azw3.cover_image and Path(config.azw3.cover_image).exists():
                calibre_cmd.extend(["--cover", config.azw3.cover_image])
            
            subprocess.run(calibre_cmd, check=True, capture_output=True, text=True)
            
            # Clean up ePub file after successful conversion
            if azw3_file.exists():
                epub_file.unlink(missing_ok=True)
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to ePub if calibre is not available
            return RenderResult(
                path=str(epub_file),
                format="epub",
                success=True,
                error="calibre not available, created ePub instead of AZW3. Install calibre: sudo apt install calibre"
            )

        # Clean up temporary markdown
        if md_result.path and Path(md_result.path).exists():
            Path(md_result.path).unlink(missing_ok=True)

        return RenderResult(
            path=str(azw3_file),
            format="azw3",
            success=True,
            error=None if not error_messages else f"Skipped {len(error_messages)} summaries: " + "; ".join(error_messages[:3])
        )
        
    except Exception as e:
        return RenderResult(
            path="",
            format="azw3",
            success=False,
            error=str(e)
        )

def render(summaries: List[str], category: str, config: RendererConfig) -> List[RenderResult]:
    """Main entry point - delegates to format-specific renderers"""
    results = []
    logger.info(f"Starting rendering for {len(summaries)} summaries in formats: {config.formats}")

    if not summaries:
        logger.warning("No summaries provided for rendering")
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
        logger.debug(f"Rendering format: {format_name}")
        if format_name == "md":
            result = render_md(summaries, category, config)
        elif format_name == "pdf":
            result = render_pdf(summaries, category, config)
        elif format_name == "html":
            result = render_html(summaries, category, config)
        elif format_name == "azw3":
            result = render_azw3(summaries, category, config)
        else:
            logger.error(f"Unsupported format requested: {format_name}")
            result = RenderResult(
                path="",
                format=format_name,
                success=False,
                error=f"Unsupported format: {format_name}"
            )
        results.append(result)
    
    successful = sum(1 for r in results if r.success)
    logger.info(f"Rendering completed: {successful}/{len(results)} formats successful")
    
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