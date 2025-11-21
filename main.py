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
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from typing import Optional

from interpreter import generate_keywords, explain_artwork, InterpreterError, InterpreterTimeoutError
from curator import search_art, CuratorError
from gallery_apis import search_art_api, GalleryAPIError
from usage_tracker import get_tracker
from search_cache import save_search_results, get_artwork_by_index, CacheError


app = typer.Typer(
    name="muse-cli",
    help="Convert philosophical text into art search keywords and find artwork.",
    add_completion=False
)
console = Console()


@app.command()
def search(
    quote: str = typer.Argument(..., help="The philosophical quote or abstract text to interpret"),
    max_results: int = typer.Option(10, "--max", "-m", help="Maximum number of artworks to return"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout for AI generation in seconds"),
    source: str = typer.Option("meisterdrucke", "--source", "-s", help="Art gallery source: meisterdrucke, met, wikiart")
):
    """
    Search for artwork based on abstract philosophical text.

    The AI will interpret your quote and generate art search keywords,
    then search your chosen art gallery for matching artwork.

    Available sources:
    - meisterdrucke: Meisterdrucke.ie gallery (via Apify scraping)
    - met: Metropolitan Museum of Art (official API, no key needed)
    - wikiart: WikiArt database (official API, no key needed)
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

    # Step 2: Search artwork from chosen source
    artworks = []

    # Validate source
    valid_sources = ["meisterdrucke", "met", "wikiart"]
    if source.lower() not in valid_sources:
        console.print(f"[bold red]✗ Error:[/bold red] Invalid source '{source}'", style="red")
        console.print(f"[yellow]Valid sources: {', '.join(valid_sources)}[/yellow]")
        raise typer.Exit(code=1)

    source = source.lower()

    # Set status message based on source
    source_names = {
        "meisterdrucke": "Meisterdrucke via Apify",
        "met": "Metropolitan Museum of Art",
        "wikiart": "WikiArt"
    }
    status_msg = f"[bold cyan]Searching {source_names[source]}...[/bold cyan]"

    with console.status(status_msg, spinner="dots"):
        try:
            if source == "meisterdrucke":
                # Use Apify scraping
                artworks = search_art(keywords, max_results=max_results)
            else:
                # Use API-based sources
                artworks = search_art_api(source, keywords, max_results=max_results)
        except CuratorError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
            console.print("[yellow]Make sure APIFY_TOKEN is set in your environment[/yellow]")
            raise typer.Exit(code=1)
        except GalleryAPIError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
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
    table.add_column("Link", style="blue", min_width=15)

    # Add rows to table
    for idx, artwork in enumerate(artworks, 1):
        title = artwork.get("title", "Untitled")
        artist = artwork.get("artist", "Unknown")
        image_url = artwork.get("image_url", "")

        # Create clickable hyperlink using Rich's native link support
        link = Text("[View Image]", style=f"link {image_url}")

        table.add_row(
            str(idx),
            title,
            artist,
            link
        )

    console.print(table)
    console.print()
    console.print("[dim]Tip: Right-click on [View Image] links and select 'Copy Link Address'[/dim]")
    console.print("[dim]Tip: Use 'muse explain <number>' to get AI analysis of any artwork[/dim]")

    # Save search results to cache for the explain command
    try:
        save_search_results(quote, keywords, artworks, source)
    except CacheError:
        # Don't fail the search if caching fails
        pass


@app.command()
def explain(
    index: int = typer.Argument(..., help="Index number of artwork from last search (1-based)"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout for AI analysis in seconds")
):
    """
    Explain why a specific artwork matches your philosophical quote.

    Use this after running 'muse search' to get an AI-powered analysis of
    how a specific artwork connects to your original philosophical text.

    Example:
        muse search "the weight of existence"
        muse explain 3  # Analyze artwork #3 from the search results
    """
    # Display header panel
    console.print()
    console.print(Panel.fit(
        "[bold magenta]Muse CLI - Artwork Analysis[/bold magenta]\n"
        "[dim]Understanding the philosophical connection[/dim]",
        border_style="magenta"
    ))
    console.print()

    # Load the artwork from cache
    try:
        cache_data = get_artwork_by_index(index)
    except CacheError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
        console.print("[yellow]Run 'muse search <quote>' first to search for artworks[/yellow]")
        raise typer.Exit(code=1)

    artwork = cache_data["artwork"]
    original_query = cache_data["original_query"]
    keywords = cache_data["keywords"]
    source = cache_data["source"]

    # Display artwork info
    console.print(f"[bold cyan]Analyzing artwork #{index}:[/bold cyan]")
    console.print(f"  [white]Title:[/white] {artwork['title']}")
    console.print(f"  [yellow]Artist:[/yellow] {artwork['artist']}")
    console.print(f"  [dim]Source:[/dim] {source}")
    console.print()
    console.print(f"[bold cyan]Original query:[/bold cyan] [green]\"{original_query}\"[/green]")
    console.print(f"[bold cyan]Keywords used:[/bold cyan] [green]{keywords}[/green]")
    console.print()

    # Analyze the artwork
    explanation = None
    with console.status("[bold cyan]Analyzing artwork with AI vision...[/bold cyan]", spinner="dots"):
        try:
            explanation = explain_artwork(
                artwork["image_url"],
                original_query,
                artwork["title"],
                artwork["artist"],
                timeout=timeout
            )
        except InterpreterTimeoutError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
            console.print("[yellow]Try increasing the timeout with --timeout option[/yellow]")
            raise typer.Exit(code=1)
        except InterpreterError as e:
            console.print(f"[bold red]✗ Error:[/bold red] {str(e)}", style="red")
            console.print("[yellow]Make sure GEMINI_API_KEY is set in your environment[/yellow]")
            raise typer.Exit(code=1)

    # Display the explanation in a panel
    console.print(Panel(
        explanation,
        title="[bold]AI Analysis[/bold]",
        border_style="cyan",
        padding=(1, 2)
    ))
    console.print()
    console.print(f"[dim]Image URL: {artwork['image_url']}[/dim]")
    console.print()


@app.command()
def version():
    """Show version information."""
    console.print("[bold]Muse CLI[/bold] v1.0.0")
    console.print("[dim]A philosophical art search tool[/dim]")


@app.command()
def usage():
    """Show Gemini API usage statistics and free tier limits."""
    console.print()
    console.print(Panel.fit(
        "[bold magenta]Gemini API Usage Tracker[/bold magenta]\n"
        "[dim]Monitor your usage against free tier limits[/dim]",
        border_style="magenta"
    ))
    console.print()

    try:
        tracker = get_tracker()
        stats = tracker.get_usage_stats()

        # Create usage table
        table = Table(
            show_header=True,
            header_style="bold cyan",
            border_style="blue",
            title="[bold]API Usage Statistics[/bold]",
            title_style="bold magenta"
        )

        table.add_column("Metric", style="white", min_width=25)
        table.add_column("Current", style="yellow", min_width=15, justify="right")
        table.add_column("Limit", style="cyan", min_width=15, justify="right")
        table.add_column("Usage %", style="green", min_width=10, justify="right")

        # Today's usage
        daily_req_color = "red" if stats["daily_request_percentage"] >= 100 else "yellow" if stats["daily_request_percentage"] > 80 else "green"
        daily_tok_color = "red" if stats["daily_token_percentage"] >= 100 else "yellow" if stats["daily_token_percentage"] > 80 else "green"

        table.add_row(
            "Today's Requests",
            str(stats["daily_requests"]),
            f"{stats['daily_request_limit']:,}",
            f"[{daily_req_color}]{stats['daily_request_percentage']:.1f}%[/{daily_req_color}]"
        )

        table.add_row(
            "Today's Tokens",
            f"{stats['daily_tokens']:,}",
            f"{stats['daily_token_limit']:,}",
            f"[{daily_tok_color}]{stats['daily_token_percentage']:.1f}%[/{daily_tok_color}]"
        )

        table.add_row("", "", "", "")  # Separator

        # All-time usage
        table.add_row(
            "Total Requests (all-time)",
            str(stats["total_requests"]),
            "∞",
            "-"
        )

        table.add_row(
            "Total Tokens (all-time)",
            f"{stats['total_tokens']:,}",
            "∞",
            "-"
        )

        console.print(table)
        console.print()

        # Free tier limits info
        limits_panel = Panel(
            "[bold cyan]Free Tier Limits:[/bold cyan]\n"
            "• 15 requests per minute\n"
            f"• {stats['daily_request_limit']:,} requests per day\n"
            f"• {stats['daily_token_limit']:,} tokens per day\n\n"
            "[dim]Daily counters reset at midnight UTC[/dim]",
            title="[bold]Gemini 2.0 Flash Experimental[/bold]",
            border_style="blue"
        )
        console.print(limits_panel)
        console.print()

        # Usage details
        details_text = (
            f"[bold]First used:[/bold] {stats['first_use_date']}\n"
            f"[bold]Last reset:[/bold] {stats['last_reset_date']}\n"
            f"[bold]Storage:[/bold] ~/.muse-cli/usage.json"
        )
        console.print(details_text)
        console.print()

        # Warning if approaching limits
        if stats["at_limit"]:
            console.print("[bold red]⚠️  Warning: Daily API limit reached![/bold red]")
            console.print("[yellow]Your usage may be throttled or blocked until midnight UTC.[/yellow]")
            console.print()
        elif stats["approaching_limit"]:
            console.print("[bold yellow]⚠️  Warning: Approaching daily API limits![/bold yellow]")
            console.print("[dim]Consider monitoring your usage to stay within free tier.[/dim]")
            console.print()

        # Tips
        console.print("[dim]Tip: Usage tracking is based on estimates. Actual API usage may vary.[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error loading usage statistics:[/bold red] {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
