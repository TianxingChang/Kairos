# Web Scraping Module

This module is completely separate from the knowledge graph generation workflow and focuses specifically on discovering, crawling, and organizing learning content from the web.

## Structure

```
scraping/
├── __init__.py
├── README.md
├── clients/           # External service clients (Firecrawl, etc.)
├── config/           # Scraping-specific configuration
│   ├── firecrawl_config.py
│   └── firecrawl_mcp_config.json
├── models/           # Data models for scraped content
│   └── learning_resource.py
└── services/         # Business logic for scraping operations
```

## Usage

### Command Line Interface

```bash
# Interactive mode
python scraping_main.py

# Search for learning resources
python scraping_main.py --topic "machine learning"

# Crawl a specific URL
python -m scraping.scraping_main --url "https://speech.ee.ntu.edu.tw/~hylee/ml/2025-spring.php"
python -m scraping.scraping_main --url "https://speech.ee.ntu.edu.tw/~hylee/mlds/2018-spring.php"
python -m scraping.scraping_main --url "https://googly-mingto.github.io/LA_2022_fall/2022-fall.html"
python -m scraping.scraping_main --url "https://speech.ee.ntu.edu.tw/~hylee/genai/2024-spring.php"
# Natural language command
python scraping_main.py --command "search for python tutorials"
```

### Programmatic Usage

```python
from scraping_main import create_scraping_application

app = create_scraping_application()
await app.search_learning_resources("deep learning")
await app.crawl_url("https://example.com")
```

## Configuration

The scraping module uses environment variables for configuration:

- `FIRECRAWL_API_KEY` - API key for Firecrawl service
- `SCRAPING_MAX_RESULTS` - Maximum search results (default: 3)
- `SCRAPING_DOWNLOAD_DIR` - Download directory (default: downloads)
- `SCRAPING_CONTENT_TYPES` - Content types to extract (default: video,tutorial,discussion)

See `.env.example` for all available configuration options.

## Separation from Knowledge Graph Workflow

This module is intentionally separated from the main knowledge graph generation workflow:

- **Different entry point**: `scraping_main.py` vs `main.py`
- **Separate directory structure**: `scraping/` vs main directories
- **Independent configuration**: Own config files and environment variables
- **Distinct data models**: Learning resources vs knowledge graph nodes/edges
- **Different purpose**: Content discovery vs knowledge structure generation

This separation allows both workflows to evolve independently while maintaining clean boundaries.