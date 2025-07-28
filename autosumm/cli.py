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
        from .initialize import run_setup_wizard
        
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
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    specified_category: str = typer.Option(
        None,
        "--specify-category",
        "-s"
    )
):
    """
    Run the summarization pipeline.
    """
    try:
        from .main import run_pipeline
        
        config_file = Path(config_path)
        if not config_file.exists():
            typer.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
            raise typer.Exit(1)
            
        typer.echo(f"Starting ArXiv AutoSumm with config: {config_path}")
        if verbose:
            typer.echo("Verbose mode enabled")
            
        run_pipeline(str(config_path), verbose, specified_category)
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
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file to test"
    ),
    skip_api_checks: bool = typer.Option(
        False,
        "--skip-api-checks",
        help="Skip validation of API connectivity (LLMs, Embedders, VLMs, etc.)."
    )
):
    """
    Test API connectivity, model availability and email connectivity.
    """
    try:
        from .validate import ConfigValidator, MainConfig, ValidationResult

        config_file = Path(config_path)
        if not config_file.exists():
            typer.echo(f"Error: Configuration file '{config_path}' not found.", err=True)
            raise typer.Exit(1)
            
        typer.echo(f"Testing configuration: {config_path}")
        typer.echo("=" * 60)
        typer.echo("ArXiv AutoSumm Configuration Validation")
        typer.echo("=" * 60)
        
        # Load config and create validator
        config = MainConfig.from_yaml(config_path).get_pipeline_configs()
        validator = ConfigValidator(config)
        
        # Run validation checks one by one with immediate output
        results = {}
        
        # 1. Config loading
        results["config"] = ValidationResult(
            success=True,
            message="Configuration loaded successfully",
            details={"config_path": config_path}
        )
        _print_validation_result(results["config"])
        
        # 2. External dependencies (quick checks)
        if "pdf" in config["render"].formats or "azw3" in config["render"].formats:
            #typer.echo("Validating Pandoc installation for PDF & AZW3 conversion...")
            results["pandoc"] = validator._validate_pandoc()
            _print_validation_result(results["pandoc"])
            
        if "azw3" in config["render"].formats:
            #typer.echo("Validating Calibre installation for AZW3 conversion...")
            results["calibre"] = validator._validate_calibre()
            _print_validation_result(results["calibre"])
            
        if "pdf" in config["render"].formats:
            #typer.echo("Validating TeXLive (xelatex) installation for PDF conversion...")
            results["texlive"] = validator._validate_texlive()
            _print_validation_result(results["texlive"])
        
        # 3. Email configuration
        if config["deliver"]:
            #typer.echo("Validating SMTP configuration and authentication for email delivering...")
            results["email"] = validator._validate_email()
        else:
            results["email"] = ValidationResult(
                success=True,
                message="Email: Disabled in configuration",
                details={"note": "Email delivery not configured"}
            )
        _print_validation_result(results["email"])

        if not skip_api_checks:
            # 4. Summarizer configuration
            #typer.echo("Validating summarizer API connectivity and model availability...")
            results["summarize"] = validator._validate_summarizer()
            _print_validation_result(results["summarize"])

            # 5. Rater configuration
            if config["rate"].strategy == "hybrid":
                #typer.echo("Validating LLM rater API connectivity and model availability...")
                results["rate_llm"] = validator._validate_raterllm()
                _print_validation_result(results["rate_llm"])
                
                #typer.echo("Validating embedder API connectivity and model availability...")
                results["rate_embed"] = validator._validate_embedder()
                _print_validation_result(results["rate_embed"])
                
            elif config["rate"].strategy == "embedder":
                #typer.echo("Validating embedder API connectivity and model availability...")
                results["rate_embed"] = validator._validate_embedder()
                _print_validation_result(results["rate_embed"])
                
            elif config["rate"].strategy == "llm":
                #typer.echo("Validating LLM rater API connectivity and model availability...")
                results["rate_llm"] = validator._validate_raterllm()
                _print_validation_result(results["rate_llm"])

            # 6. Parser configuration
            if config["parse"].enable_vlm:
                #typer.echo("Validating VLM parser API connectivity and model availability...")
                results["parse_vlm"] = validator._validate_parservlm()
                _print_validation_result(results["parse_vlm"])

        # Summary
        total_checks = len(results)
        passed_checks = sum(1 for r in results.values() if r.success)
        typer.echo(f"\nSummary: {passed_checks}/{total_checks} checks passed")

        if passed_checks == total_checks:
            typer.echo("🎉 All validations passed! Configuration is ready.")
        else:
            typer.echo("⚠️  Some issues found. Please review the errors above.")
        
    except ImportError as e:
        typer.echo(f"Error importing validation: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Validation failed: {e}", err=True)
        raise typer.Exit(1)

def _print_validation_result(result):
    """Print validation result using typer.echo"""
    if result.success:
        typer.echo(f"✅ {result.message}")
        if result.details:
            for key, value in result.details.items():
                if key == "available_models":
                    typer.echo(f"   Available models: {', '.join(value[:5])}{'...' if len(value) > 5 else ''}")
                else:
                    typer.echo(f"   {key}: {value}")
    else:
        typer.echo(f"❌ {result.message}")
        if result.error:
            typer.echo(f"   Error: {result.error}")
    typer.echo()

if __name__ == "__main__":
    app()
    