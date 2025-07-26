"""
Setup wizard for ArXiv AutoSumm configuration.

This module provides an interactive CLI wizard to help users configure
ArXiv AutoSumm without needing to understand all the technical details.
Focuses on the 4 essential items only, with basic validation.
"""

import typer
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import ValidationError
import yaml
import re

from config import MainConfig, arxiv_categories, recognized_providers, validate_api_config

def get_interactive_input(prompt: str, default: Optional[str] = None, 
                         validation_func=None, password: bool = False) -> str:
    """Get interactive input with optional validation."""
    while True:
        if password:
            import getpass as gp
            value = gp.getpass(f"{prompt} {'(default: hidden)' if default else ''}: ")
            if not value and default:
                return default
        else:
            value = typer.prompt(prompt, default=default)
        
        if validation_func and value:
            try:
                validation_func(value)
                return value
            except Exception as e:
                typer.echo(f"❌ {e}")
                continue
        
        return value


def validate_email(email: str) -> None:
    """Validate email address format."""
    if '@' not in email or not re.match(r"[^@]+@[^@]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

def select_categories_interactively() -> List[str]:
    """Interactive category selection."""
    typer.echo("\n📚 Select ArXiv Categories")
    typer.echo("=" * 60)
    
    # Common categories for quick selection
    common_categories = {
        "cs.AI": "Artificial Intelligence",
        "cs.LG": "Machine Learning", 
        "cs.CL": "Computation and Language (NLP)",
        "cs.CV": "Computer Vision",
        "cs.RO": "Robotics",
        "cs.SY": "Systems and Control",
        "math.OC": "Optimization and Control",
        "math.ST": "Statistics Theory",
        "stat.ML": "Machine Learning (Statistics)",
        "astro-ph.EP": "Earth and Planetary Astrophysics",
        "gr-qc": "General Relativity and Quantum Cosmology",
        "physics.comp-ph": "Computational Physics",
        "physics.space-ph": "Space Physics",
        "q-bio.QM": "Quantitative Methods (Biology)"
    }
    
    typer.echo("Common categories:")
    category_list = list(common_categories.keys())
    for i, (cat, desc) in enumerate(common_categories.items(), 1):
        typer.echo(f"{i}. {cat} - {desc}")
    
    typer.echo("\nEnter category numbers (comma-separated), or 'all' for all categories")
    typer.echo("Or enter custom category codes directly (comma-separated):")
    
    selection = typer.prompt("Your selection")
    
    if selection.lower() == 'all':
        return list(common_categories.keys())
    
    try:
        # Try to parse as numbers
        numbers = [int(n.strip()) for n in selection.split(',')]
        selected = [category_list[n-1] for n in numbers if 1 <= n <= len(category_list)]
        if selected:
            return selected
    except (ValueError, IndexError):
        pass
    
    # Try to parse as category codes
    categories = [c.strip() for c in selection.split(',')]
    valid_categories = []
    for cat in categories:
        if cat in arxiv_categories:
            valid_categories.append(cat)
        else:
            typer.echo(f"⚠️  Skipping invalid category: {cat}")
    
    return valid_categories


def configure_llm_providers() -> Dict[str, any]:
    """Configure LLM providers for summarization and rating."""
    typer.echo("\n🤖 Configure LLM Provider")
    typer.echo("=" * 60)
    
    # Provider selection
    providers = list(recognized_providers.keys())
    typer.echo("Default providers:")
    for i, provider in enumerate(providers, 1):
        typer.echo(f"{i}. {provider}")
    
    provider_idx = typer.prompt("Select provider number (enter 0 to choose custom provider)", type=int)
    if 1 <= provider_idx <= len(providers):
        provider = providers[provider_idx - 1]
    else:
        provider = typer.prompt("Enter custom provider name (Optional)")
    
    base_url = recognized_providers.get(provider, "")
    if not base_url:
        base_url = typer.prompt("Enter API base URL")
    
    # API key (not needed for local providers)
    is_local = provider == "ollama" or "localhost" in base_url
    api_key = None
    if not is_local:
        api_key = get_interactive_input("Enter API key directly or use env:VARIABLE_NAME (e.g., 'sk-123456' or 'env:OPENAI_API_KEY')", password=False)
    
    # Model selection for summarization
    model = typer.prompt("Enter model name for summarization", default=get_default_model(provider))
    
    # Rater LLM configuration
    typer.echo("\n📊 Configure Rater LLM (for initial paper filtering)")
    typer.echo("This can be a cheaper/faster model to reduce costs when processing many papers.")
    
    use_separate_rater = typer.confirm("Use a separate model for rating?", default=True)
    
    rater_provider = provider
    rater_base_url = base_url
    rater_api_key = api_key
    rater_model = model
    
    if use_separate_rater:
        typer.echo("\nConfigure rater LLM:")
        same_as_summarizer = typer.confirm("Use same provider as summarizer?", default=True)
        
        if not same_as_summarizer:
            # Provider selection for rater
            typer.echo("Available providers:")
            for i, provider in enumerate(providers, 1):
                typer.echo(f"{i}. {provider}")
            
            rater_provider_idx = typer.prompt("Select rater provider number (enter 0 to chooses custom provider)", type=int)
            if 1 <= rater_provider_idx <= len(providers):
                rater_provider = providers[rater_provider_idx - 1]
            else:
                rater_provider = typer.prompt("Enter custom rater provider name (Optional)")
            
            rater_base_url = recognized_providers.get(rater_provider, "")
            if not rater_base_url:
                rater_base_url = typer.prompt("Enter rater API base URL")
            
            rater_is_local = rater_provider == "ollama" or "localhost" in rater_base_url
            rater_api_key = None
            if not rater_is_local:
                rater_api_key = get_interactive_input("Enter rater API key directly or use env:VARIABLE_NAME (e.g., 'sk-123456' or 'env:OPENAI_API_KEY')", password=False)
        
        # Model selection for rater
        rater_model = typer.prompt(
            "Enter model name for rating", 
            default=get_cheaper_model(rater_provider)
        )
    
    # Basic validation only - no connectivity test
    try:
        provider, base_url, api_key = validate_api_config(provider, base_url, api_key)
        if use_separate_rater:
            rater_provider, rater_base_url, rater_api_key = validate_api_config(
                rater_provider, rater_base_url, rater_api_key
            )
        typer.echo("✅ Basic configuration validation passed")
    except Exception as e:
        typer.echo(f"❌ Configuration validation failed: {e}")
        if not typer.confirm("Continue anyway?"):
            raise typer.Exit(1)
    
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "rater_provider": rater_provider,
        "rater_base_url": rater_base_url,
        "rater_api_key": rater_api_key,
        "rater_model": rater_model,
        "use_separate_rater": use_separate_rater
    }


def get_default_model(provider: str) -> str:
    """Get default model for provider."""
    defaults = {
        "openai": "gpt-4o",
        "deepseek": "deepseek-reasoner",
        "siliconflow": "deepseek-ai/DeepSeek-R1",
        "dashscope": "qwen-plus",
        "ollama": "qwen3:32b",
        "moonshot": "kimi-k2-0711-preview",
        "minimax": "MiniMax-M1",
        "modelscope": "Qwen/Qwen3-235B-A22B-Thinking-2507"
    }
    return defaults.get(provider, "deepseek-reasoner")


def get_cheaper_model(provider: str) -> str:
    """Get cheaper/faster model for provider (used for rating)."""
    cheaper_defaults = {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "siliconflow": "THUDM/glm-4-9b-chat",
        "dashscope": "qwen-turbo",
        "ollama": "llama3.1:8b",
        "moonshot": "kimi-latest",
        "minimax": "MiniMax-Text-01",
        "modelscope": "Qwen/Qwen2.5-7B-Instruct"
    }
    return cheaper_defaults.get(provider, "deepseek-chat")


def configure_categories() -> Dict[str, any]:
    """Configure categories and log sent."""
    categories = select_categories_interactively()
    typer.echo(f"Selected categories: {', '.join(categories)}")
    
    return {
        "categories": categories, 
    }


def configure_email() -> Dict[str, any]:
    """Configure email settings."""
    typer.echo("\n📧 Configure Email Delivery")
    typer.echo("=" * 60)
    
    # Common SMTP providers
    providers = {
        "gmail": {"server": "smtp.gmail.com", "port": 465},
        "outlook": {"server": "smtp-mail.outlook.com", "port": 587},
        "yahoo": {"server": "smtp.mail.yahoo.com", "port": 465},
        "qq": {"server": "smtp.qq.com", "port": 465},
        "163": {"server": "smtp.163.com", "port": 465}
    }
    
    typer.echo("Email providers:")
    for i, provider in enumerate(providers.keys(), 1):
        typer.echo(f"{i}. {provider.title()}")
    
    provider_choice = typer.prompt("Select provider (Enter 0 to choose custom provider)", type=int, default=1)
    
    if 1 <= provider_choice <= len(providers):
        provider = list(providers.keys())[provider_choice - 1]
        smtp_config = providers[provider]
        smtp_server = smtp_config["server"]
        port = smtp_config["port"]
    else:
        smtp_server = typer.prompt("SMTP server")
        port = typer.prompt("Port", type=int, default=465)
    
    sender = get_interactive_input("Enter sender email. This is YOUR email address that will send the summaries", validation_func=validate_email)
    recipient = get_interactive_input("Enter recipient email. This is where you want to RECEIVE the summaries", default=sender, 
                                    validation_func=validate_email)
    password = get_interactive_input("Enter SMTP password directly or use env:VARIABLE_NAME (e.g., 'qwerty' or 'env:SMTP_PASSWORD')", password=False)
    
    # Basic validation only - no connectivity test
    typer.echo("ℹ️  Basic email configuration accepted")
    typer.echo("   Run 'python autosumm/cli.py test-config' to test dependencies and API & email connectivity")
    typer.echo("=" * 60)
    
    return {
        "smtp_server": smtp_server,
        "port": port,
        "sender": sender,
        "recipient": recipient,
        "password": password
    }


def create_config_from_wizard(config_path: str) -> MainConfig:
    """Create configuration through interactive wizard."""
    typer.echo("🚀 ArXiv AutoSumm Setup Wizard")
    typer.echo("=" * 50)
    typer.echo("This wizard will help you configure the essential settings.")
    typer.echo("You can always modify the configuration file later.")
    typer.echo("Run 'python autosumm/cli.py test_config' to test connectivity after setup.")
    typer.echo()
    
    # Step 1: LLM Configuration
    llm_config = configure_llm_providers()
    
    # Step 2: Schedule and Categories
    category_config = configure_categories()
    
    # Step 3: Email Configuration
    email_config = configure_email()
    
    # Step 4: Create configuration with sensible defaults
    config_data = {
        "run": {
            "categories": category_config["categories"],
            "send_log": False,
            "log_dir": "./logs"
        },
        "fetch": {
            "days": 8,
            "max_results": 1000,
            "max_retries": 10
        },
        "summarize": {
            "provider": llm_config["provider"],
            "api_key": llm_config["api_key"],
            "base_url": llm_config["base_url"],
            "model": llm_config["model"],
            "system_prompt": 'file:./prompts/summ_lm/system.md',
            "user_prompt_template": 'file:./prompts/summ_lm/user.md',
            "completion_options": {"temperature": 0.6}
        },
        "rate": {
            "strategy": "llm",
            "top_k": 200, # arbitrary for llm rating
            "max_selected": 10,
            "embedder": None,  # Skip embedder for simplicity - use LLM only
            "llm": {
                "provider": llm_config["rater_provider"],
                "api_key": llm_config["rater_api_key"],
                "base_url": llm_config["rater_base_url"],
                "model": llm_config["rater_model"],
                "system_prompt": 'file:./prompts/rate_lm/system.md',
                "user_prompt_template": 'file:./prompts/rate_lm/user.md',
                "completion_options": {"temperature": 0.2, "max_tokens": 1024}
            }
        },
        "parse": {
            "enable_vlm": False,
            "tmp_dir": "./tmp"
        },
        "render": {
            "formats": ["pdf", "md"],
            "output_dir": "./output",
            "base_filename": None
        },
        "deliver": email_config,
        "cache": {
            "dir": "~/.cache/arxiv-autosumm",
            "ttl_days": 16
        },
        "batch": {
            "tmp_dir": "./tmp",
            "max_wait_hours": 24,
            "poll_interval_seconds": 30,
            "fallback_on_error": True
        }
    }
    
    # Step 5: Write the raw config data with 'file:' and 'env:' references to the YAML file
    try:
        with open(config_path,'w',encoding='utf-8') as f:
            for i, (key,value) in enumerate(config_data.items()):
                if i > 0:
                    f.write('\n')
                yaml.dump(
                    {key:value},
                    f,
                    sort_keys=False,
                    indent=2,
                    default_flow_style=False,
                    allow_unicode=True
                )
    except Exception as e:
        typer.echo(f"\n❌ Failed to write initial configuration to {config_path}: {e}")
        raise typer.exit(1)
    

    # Step 6: Validate the configuration by loading it from the YAML file
    try:
        typer.echo()
        typer.echo("Running basic configuration validation...")
        config = MainConfig.from_yaml(config_path) # use .from_yaml instead of MainConfig(**config_data) makes sure the config.yaml file keeps 'file:' references instead of long, long string
        typer.echo("\n✅ Basic onfiguration validation passed")
        return config
    except ValidationError as e:
        typer.echo("\n❌ Basic configuration validation failed. Please review the errors below:")
        typer.echo("=" * 60)
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            typer.echo(f"  - Field `{field}`: {message}")
        typer.echo("=" * 60)
        typer.echo("Please run the setup wizard again to correct the configuration.")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"\n❌ Basic configuration validation failed: {e}")
        raise typer.Exit(1)


def run_setup_wizard(config_path: str = "config.yaml") -> None:
    """Run the complete setup wizard."""
    try:
        config = create_config_from_wizard(config_path)
        
        typer.echo("\n✅ Setup completed successfully!")
        typer.echo(f"Configuration saved to: {config_path}")
        typer.echo("\nNext steps:")
        typer.echo(f"1. Review the configuration: {config_path}")
        typer.echo("2. Test connectivity: python autosumm/cli.py test_config")
        typer.echo("3. Run pipeline: python autosumm/main.py")
        typer.echo("4. Or use: python autosumm/cli.py run")
        
    except Exception as e:
        typer.echo(f"\n❌ Setup failed: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    config = MainConfig.from_yaml("config.yaml")