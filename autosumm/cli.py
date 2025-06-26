import typer
import config

app = typer.Typer(name="autosumm")

@app.command()
def init():
    """
    Initialize ArXiv AutoSumm with setup wizard.
    Call functions in initialize.py
    """

@app.command()
def run():
    """
    Run the summarization pipeline.
    Call functions in main.py
    """

@app.command()
def test_config():
    """
    Test API connectivity, model availability and email connectivity.
    Call functions in validate.py
    """
    