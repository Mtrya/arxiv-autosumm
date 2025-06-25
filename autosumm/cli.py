import typer

app = typer.Typer(name="autosumm")

@app.command()
def init():
    """Initialize ArXiv AutoSumm with setup wizard."""

@app.command()
def run():
    """Run the summarization pipeline."""

@app.command()
def test_config():
    """Test API connectivity, model availability and email connectivity."""
    import pipeline as pl