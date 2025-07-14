import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(name="autosumm")

@app.command()
def init(
    config_path: Optional[str] = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file to create"
    )
):
    """
    Initialize ArXiv AutoSumm with setup wizard.
    Interactive configuration for the 4 essential items:
    1. LLM Provider & API key
    2. ArXiv Categories
    3. Schedule
    4. Email Configuration
    """
    try:
        from initialize import run_setup_wizard
        
        # Check if config already exists
        config_file = Path(config_path)
        if config_file.exists():
            if not typer.confirm(f"Configuration file '{config_path}' already exists. Overwrite?"):
                typer.echo("Setup cancelled.")
                raise typer.Exit(0)
        
        typer.echo("Starting ArXiv AutoSumm Setup Wizard")
        typer.echo("=" * 50)
        
        run_setup_wizard(config_path)
        
    except ImportError as e:
        typer.echo(f"Error importing setup wizard: {e}", err=True)
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\n\nSetup cancelled by user.")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Setup failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def run(
    config_path: Optional[str] = typer.Option(
        "my_own_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """
    Run the summarization pipeline.
    """
    try:
        from main import run_pipeline
        
        config_file = Path(config_path)
        if not config_file.exists():
            typer.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
            raise typer.Exit(1)
            
        typer.echo(f"Starting ArXiv AutoSumm with config: {config_path}")
        if verbose:
            typer.echo("Verbose mode enabled")
            
        run_pipeline(str(config_path), verbose)
        typer.echo("Pipeline completed successfully!")
        
    except ImportError as e:
        typer.echo(f"Error importing pipeline: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Pipeline failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def test_config(
    config_path: Optional[str] = typer.Option(
        "my_own_config.yaml",
        "--config",
        "-c",
        help="Path to configuration file to test"
    )
):
    """
    Test API connectivity, model availability and email connectivity.
    Call functions in validate.py
    """
    typer.echo("Config testing not yet implemented. Use validate.py directly for now.")

if __name__ == "__main__":
    app()
    