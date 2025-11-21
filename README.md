# Muse CLI

<p align="center">
  <img src="assets/muse-banner.jpeg" alt="Muse CLI Banner" width="100%">
</p>

A CLI for semantic search across art museum databases. Transforms natural language queries into structured search terms, then aggregates results from multiple gallery sources.

## What it does

Takes unstructured text input → generates search keywords via LLM → queries multiple gallery sources → returns aggregated results in terminal.

**Gallery sources:**
- **Meisterdrucke** - Web scraping via Apify (requires token)
- **Metropolitan Museum** - REST API, 470K+ artworks, no auth
- **WikiArt** - REST API, 250K+ artworks, no auth

**Other features:**
- Terminal UI via Rich (tables, hyperlinks, progress indicators)
- Token usage tracking (local JSON storage, daily reset)
- Timeout handling for flaky API calls
- Built on free-tier LLM limits: 15 RPM, 1.5K requests/day, 1M tokens/day

## Prerequisites

- Python 3.8+
- LLM API key (currently uses Gemini, free tier sufficient)
- Apify token (optional, only for Meisterdrucke)

## Installation

```bash
git clone https://github.com/ewijaya/muse-cli.git
cd muse-cli
pip install -e .
```

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export GEMINI_API_KEY="your-key-here"
export APIFY_TOKEN="your-token-here"  # optional
```

```bash
source ~/.zshrc
```

## Usage

### Basic search

```bash
muse search "solitude and light"
```

The LLM interprets the input and generates search terms. Default source is Meisterdrucke.

### Specify source

```bash
muse search "impressionism monet" --source met
muse search "starry night" --source wikiart
muse search "van gogh" --source meisterdrucke
```

### Options

```bash
muse search "text" --source <meisterdrucke|met|wikiart> --max 10 --timeout 30
```

- `--source`, `-s` - Gallery source (default: meisterdrucke)
- `--max`, `-m` - Result limit (default: 10)
- `--timeout`, `-t` - LLM timeout in seconds (default: 30)

### Token tracking

```bash
muse usage
```

Shows request count and estimated token consumption against free tier limits. Resets daily at UTC midnight. Note: Token counts are estimates (~1.3 tokens/word).

### Version

```bash
muse version
```

## Architecture

```
muse-cli/
├── main.py          # CLI entry point (Typer framework)
├── interpreter.py   # LLM interface (gemini-2.0-flash-exp)
├── curator.py       # Apify scraper for Meisterdrucke
├── gallery_apis.py  # HTTP clients for Met/WikiArt APIs
├── usage_tracker.py # Token counter with persistent storage
└── pyproject.toml   # Package config, console_scripts entry point
```

## Implementation notes

**LLM choice:** Currently using Gemini 2.0 Flash (experimental) for free-tier access. 1M tokens/day is sufficient for personal use. Alternative models would require hosting infrastructure.

**Gallery selection:** Met and WikiArt have stable REST APIs with no auth barriers. Meisterdrucke requires scraping but has a larger collection of prints.

**Token tracking:** Rough estimation based on word count. Actual consumption may vary. Free-tier APIs don't expose token counts in responses, so we approximate.

**Timeout handling:** LLM inference can be slow or unreliable. Default 30s timeout prevents hanging.

## API keys

**LLM API (Gemini):**
1. [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key (no credit card for free tier)

**Apify (optional):**
1. [Apify Console](https://console.apify.com/)
2. Settings → Integrations → API tokens

**Met/WikiArt:** No keys required.

## License

MIT
