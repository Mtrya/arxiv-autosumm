import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(name="autosumm")

@app.command()
def init():
    """
    Initialize ArXiv AutoSumm with setup wizard.
    Call functions in initialize.py
    """
    typer.echo("Setup wizard not yet implemented. Please configure manually.")

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
            
        run_pipeline(str(config_path))
        typer.echo("Pipeline completed successfully!")
        
    except ImportError as e:
        typer.echo(f"Error importing pipeline: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Pipeline failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def test_config():
    """
    Test API connectivity, model availability and email connectivity.
    Call functions in validate.py
    """
    typer.echo("Config testing not yet implemented. Use validate.py directly for now.")
    