# Indian Stock Analyst

AI-powered equity research tool for Indian stocks (NSE/BSE). Powered by Claude.

Every claim is grounded in uploaded documents — no hallucinations. Quote-first sourcing ensures traceability.

## Features

- **Industry Analysis** — One-time sector overview with growth drivers, constraints, and regulatory landscape
- **Document Management** — Upload and organize annual reports, quarterly results, transcripts, and presentations
- **Bull Case (Lynch Pitch)** — Common-sense investment thesis using Peter Lynch's framework
- **Bear Case (Munger Invert)** — Skeptical counter-thesis using Charlie Munger's inversion principle
- **Quarterly Updates** — Structured earnings analysis comparing results to guidance and history
- **Bonus Analysis** — Management quality, competitive position, and capital allocation scorecards
- **Custom Questions** — Ask anything with full document context

## Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/stock-analyst.git
cd stock-analyst
pip install -e .
```

## Configuration

Set your API key via environment variable (recommended):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or copy the example config:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml and add your API key
```

## Quick Start

### Step 1: Initialize a stock project

```bash
stock-analyst init INFY "Infosys Limited" --exchange NSE
```

### Step 2: Generate industry analysis

```bash
stock-analyst industry INFY "IT Services & Consulting"
```

### Step 3: Add company documents

Download annual reports, quarterly results, and transcripts, then add them:

```bash
# Add annual reports
stock-analyst add-doc INFY /path/to/infosys_ar_fy25.pdf --category annual_reports
stock-analyst add-doc INFY /path/to/infosys_ar_fy24.pdf --category annual_reports

# Add quarterly results
stock-analyst add-doc INFY /path/to/infosys_q3_fy25.pdf --category quarterly

# Add earnings transcripts
stock-analyst add-doc INFY /path/to/infosys_concall_q3_fy25.pdf --category transcripts

# Find official filing links (helper)
stock-analyst find-docs INFY

# List all uploaded documents
stock-analyst list-docs INFY
```

### Step 4: Generate bull and bear cases

```bash
stock-analyst bull-case INFY
stock-analyst bear-case INFY
```

### Step 5: Quarterly analysis

Upload the new quarter's filings, then run:

```bash
stock-analyst quarterly INFY "Q3 FY25"
```

### Bonus commands

```bash
stock-analyst management INFY          # Management quality check
stock-analyst competition INFY         # Competitive position map
stock-analyst capalloc INFY            # Capital allocation scorecard
stock-analyst ask INFY "What is the promoter holding trend over the last 3 years?"
```

### List all projects

```bash
stock-analyst projects
```

## Project Structure

```
stock-analyst/
├── src/
│   ├── main.py              # CLI entry point
│   ├── analyst.py            # Core analysis engine (Claude API)
│   ├── prompts/
│   │   ├── templates.py      # All prompt templates
│   │   └── renderer.py       # Template rendering
│   ├── documents/
│   │   └── manager.py        # Document storage & API preparation
│   └── utils/
│       └── config.py         # Configuration & project paths
├── projects/                  # Per-stock data (gitignored)
├── outputs/                   # Generated analyses (gitignored)
├── config.yaml.example        # Example configuration
├── pyproject.toml             # Package configuration
└── requirements.txt           # Dependencies
```

## How It Works

1. **System instructions** enforce quote-first sourcing — every claim must cite an exact quote from uploaded documents
2. **Documents are sent** as content blocks in the Claude API call, giving the model full access to your filings
3. **Outputs are saved** as Markdown files and also stored back as documents, so future analyses can reference past conclusions
4. **Indian market context** is built in — INR figures, SEBI/RBI frameworks, FY conventions, promoter holding tracking

## Supported Document Types

- PDF (`.pdf`) — Annual reports, quarterly results, DRHP
- Word (`.docx`) — Management commentary, notes
- Excel (`.xlsx`) — Financial data
- Text (`.txt`, `.csv`, `.md`, `.json`) — Transcripts, custom notes

## Where to Find Indian Filings

- **BSE India**: [bseindia.com](https://www.bseindia.com/) — Search by company name or scrip code
- **NSE India**: [nseindia.com](https://www.nseindia.com/) — Corporate Filings → Annual Reports / Financial Results
- **Company IR page** — Usually has the cleanest PDFs
- **MCA**: [mca.gov.in](https://www.mca.gov.in/) — Statutory filings

## License

MIT
