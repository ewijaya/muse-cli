# Muse CLI

A Python CLI tool that interprets abstract philosophical text into art search keywords using Google Gemini, and searches for artwork on Meisterdrucke gallery using Apify.

## Features

- **AI-Powered Interpretation**: Uses Google Gemini (gemini-2.0-flash-exp) to convert philosophical quotes into art search keywords
- **Automated Web Scraping**: Leverages Apify's cheerio-scraper to find artwork on Meisterdrucke.ie
- **Beautiful CLI**: Rich terminal UI with tables, spinners, and clickable links
- **Timeout Protection**: Handles API timeouts gracefully

## Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Apify API token

## Installation

1. Clone this repository:
```bash
git clone https://github.com/ewijaya/muse-cli.git
cd muse-cli
```

2. Install the package:
```bash
pip install -e .
```

This installs `muse` as a global command that you can run from anywhere.

3. Set up environment variables in your `~/.zshrc` or `~/.bashrc`:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export APIFY_TOKEN="your-apify-api-token"
```

4. Reload your shell configuration:
```bash
source ~/.zshrc  # or source ~/.bashrc
```

## Usage

### Search for artwork

```bash
muse search "In the depths of solitude, light finds its way"
```

You can search from any directory! The AI will interpret your philosophical text and find matching artwork.

### Search by painting or artist

```bash
muse search "Starry Night by Van Gogh"
muse search "dreaming girl"
muse search "impressionism monet"
```

### Options

- `--max`, `-m`: Maximum number of artworks to return (default: 10)
- `--timeout`, `-t`: Timeout for AI generation in seconds (default: 30)

```bash
muse search "Beauty is truth, truth beauty" --max 5 --timeout 60
```

### Show version

```bash
muse version
```

## Project Structure

```
muse-cli/
├── pyproject.toml   # Package configuration & entry point
├── interpreter.py   # AI layer - Google Gemini integration
├── curator.py       # Scraper layer - Apify integration
├── main.py          # CLI interface - Typer & Rich UI
├── requirements.txt # Python dependencies
└── README.md        # Documentation
```

## How It Works

1. **Input**: You provide an abstract philosophical quote
2. **Interpretation**: Google Gemini converts it into art-related search keywords
3. **Scraping**: Apify scrapes Meisterdrucke.ie for matching artwork
4. **Display**: Results are shown in a beautiful terminal table with clickable links

## API Keys

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key

### Getting an Apify API Token

1. Visit [Apify Console](https://console.apify.com/)
2. Sign up or log in
3. Go to Settings > Integrations > API tokens
4. Create a new token

## License

MIT
