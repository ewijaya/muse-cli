#!/usr/bin/env python3
"""
main.py - CLI Interface for Muse CLI
A tool to interpret abstract philosophical text into art search keywords and find artwork.
"""

import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.spinner import Spinner
from rich.live import Live
from typing import Optional

from interpreter import generate_keywords, InterpreterError, InterpreterTimeoutError
from curator import search_art, CuratorError


app = typer.Typer(
    name="muse-cli",
    help="Convert philosophical text into art search keywords and find artwork.",
    add_completion=False
)
console = Console()


def make_hyperlink(url: str, text: str) -> str:
    """
    Create a clickable terminal hyperlink.

    Args:
        url: The URL to link to
        text: The text to display

    Returns:
        Formatted hyperlink string
    """
    return f'\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\'


@app.command()
def search(
    quote: str = typer.Argument(..., help="The philosophical quote or abstract text to interpret"),
    max_results: int = typer.Option(10, "--max", "-m", help="Maximum number of artworks to return"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout for AI generation in seconds")
):
    """
    Search for artwork based on abstract philosophical text.

    The AI will interpret your quote and generate art search keywords,
    then search Meisterdrucke gallery for matching artwork.
    """
    # Display header panel
    console.print()
    console.print(Panel.fit(
        "[bold magenta]Muse CLI[/bold magenta]\n"
        "[dim]Transforming philosophy into art[/dim]",
        border_style="magenta"
    ))
    console.print()

    # Step 1: Generate keywords using Gemma
    keywords = None
    with console.status("[bold cyan]Consulting Gemma...[/bold cyan]", spinner="dots"):
        try:
            keywords = generate_keywords(quote, timeout=timeout)
        except InterpreterTimeoutError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
            console.print("[yellow]Try increasing the timeout with --timeout option[/yellow]")
            raise typer.Exit(code=1)
        except InterpreterError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
            console.print("[yellow]Make sure GEMINI_API_KEY is set in your environment[/yellow]")
            raise typer.Exit(code=1)

    # Display generated keywords
    console.print(f"[bold cyan]Keywords:[/bold cyan] [green]{keywords}[/green]")
    console.print()

    # Step 2: Scrape artwork using Apify
    artworks = []
    with console.status("[bold cyan]Scraping Meisterdrucke via Apify...[/bold cyan]", spinner="dots"):
        try:
            artworks = search_art(keywords, max_results=max_results)
        except CuratorError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
            console.print("[yellow]Make sure APIFY_TOKEN is set in your environment[/yellow]")
            raise typer.Exit(code=1)

    # Step 3: Display results
    if not artworks:
        console.print("[yellow]No artworks found. Try a different quote or keywords.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[bold green]✓ Found {len(artworks)} artwork(s)[/bold green]")
    console.print()

    # Create results table
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        title="[bold]Artwork Results[/bold]",
        title_style="bold magenta"
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Title", style="white", min_width=30)
    table.add_column("Artist", style="yellow", min_width=20)
    table.add_column("Link", style="blue", min_width=10)

    # Add rows to table
    for idx, artwork in enumerate(artworks, 1):
        title = artwork.get("title", "Untitled")
        artist = artwork.get("artist", "Unknown")
        image_url = artwork.get("image_url", "")

        # Create clickable link
        link_text = make_hyperlink(image_url, "View Image")

        table.add_row(
            str(idx),
            title,
            artist,
            link_text
        )

    console.print(table)
    console.print()
    console.print("[dim]Tip: Click on 'View Image' links to open artwork in your browser[/dim]")


@app.command()
def version():
    """Show version information."""
    console.print("[bold]Muse CLI[/bold] v1.0.0")
    console.print("[dim]A philosophical art search tool[/dim]")


if __name__ == "__main__":
    app()
