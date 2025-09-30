import typer
import subprocess
from pathlib import Path
from typing import Optional

app = typer.Typer(name="autosumm")

@app.command()
def tune(
    config_path: Optional[str] = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    category: str = typer.Option(
        None,
        "--category",
        "-s",
        help=""
    )
):
    """
    A placeholder command for prompt tuning entrance
    """
    typer.echo("🔍 Tune feature coming soon!")
    typer.echo(f"   Config: {config_path}")
    if category:
        typer.echo(f"   Category: {category}")

@app.command()
def run(
    config_path: Optional[str] = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    test_mode: bool = typer.Option(False, "--test", "-t", help="Test configuration and dependencies only"),
    specified_category: str = typer.Option(
        None,
        "--specify-category",
        "-s",
        help="Process only specified ArXiv category (single category only)"
    )
):
    """
    Run the ArXiv AutoSumm pipeline.

    Use --test to validate configuration and dependencies without running the full pipeline.
    """
    try:
        from .main import run_pipeline

        config_file = Path(config_path)
        if not config_file.exists():
            typer.echo(f"❌ Error: Configuration file '{config_path}' not found.", err=True)
            typer.echo("   Create a config file from config.basic.yaml or config.advanced.yaml templates")
            raise typer.Exit(1)

        typer.echo(f"🚀 Starting ArXiv AutoSumm with config: {config_file}")
        if verbose:
            typer.echo("📝 Verbose mode enabled")
        if test_mode:
            typer.echo("🧪 Test mode enabled - validating configuration only")
        if specified_category:
            # Validate that only one category is specified
            if ',' in specified_category:
                typer.echo("❌ Error: Only one category can be specified at a time.", err=True)
                typer.echo("   Please specify a single category like: --specify-category cs.AI", err=True)
                raise typer.Exit(1)
            typer.echo(f"🎯 Processing category: {specified_category}")

        if test_mode:
            # Test mode: validate configuration and basic connectivity
            typer.echo("\n🔍 Testing configuration...")
            try:
                from .config import MainConfig
                config = MainConfig.from_yaml(config_file)
                typer.echo("✅ Configuration loaded successfully")

                # Test basic dependencies
                import subprocess

                # Check Python dependencies
                typer.echo("📦 Checking Python dependencies...")
                required_modules = ['arxiv', 'pydantic', 'requests', 'yaml']
                for module in required_modules:
                    try:
                        __import__(module)
                        typer.echo(f"   ✅ {module}")
                    except ImportError:
                        typer.echo(f"   ❌ {module} - missing")

                # Check system dependencies if rendering PDF
                if 'pdf' in config.render.formats:
                    typer.echo("🖨️  Checking system dependencies...")
                    try:
                        result = subprocess.run(['which', 'xelatex'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            typer.echo("   ✅ xelatex (TeXLive)")
                        else:
                            typer.echo("   ❌ xelatex - install TeXLive")
                    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
                        typer.echo(f"   ❌ xelatex - not found: {e}")

                    try:
                        result = subprocess.run(['which', 'pandoc'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            typer.echo("   ✅ pandoc")
                        else:
                            typer.echo("   ❌ pandoc - install pandoc")
                    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
                        typer.echo(f"   ❌ pandoc - not found: {e}")

                typer.echo("\n🎉 Configuration test completed!")
                typer.echo("   Run without --test to execute the full pipeline")

            except Exception as e:
                typer.echo(f"❌ Configuration test failed: {e}", err=True)
                typer.echo(f"   📋 Full error details:", err=True)
                import traceback
                typer.echo(traceback.format_exc(), err=True)
                raise typer.Exit(1)
        else:
            # Normal execution
            run_pipeline(str(config_file), verbose, specified_category)
            typer.echo("✅ Pipeline completed successfully!")

    except ImportError as e:
        typer.echo(f"❌ Error importing pipeline: {e}", err=True)
        typer.echo(f"   📋 Full error details:", err=True)
        import traceback
        typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Pipeline failed: {e}", err=True)
        typer.echo(f"   📋 Full error details:", err=True)
        import traceback
        typer.echo(traceback.format_exc(), err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()