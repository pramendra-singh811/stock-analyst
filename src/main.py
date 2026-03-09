#!/usr/bin/env python3
"""CLI entry point for the Indian Stock Analyst tool."""

import argparse
import sys
from pathlib import Path

from .analyst import StockAnalyst
from .documents.manager import DocumentManager
from .utils.config import (
    load_config,
    save_config,
    load_project_meta,
    PROJECTS_DIR,
)


def cmd_init(args):
    """Initialize a new stock project."""
    analyst = StockAnalyst(args.ticker, args.company, args.exchange)
    print(f"Project initialized for {args.company} ({args.ticker}) on {args.exchange}")
    print(f"Project directory: {analyst.doc_manager.project_dir}")
    print("\nNext steps:")
    print("  1. Run 'industry' to generate an industry analysis")
    print("  2. Add documents with 'add-doc'")
    print("  3. Run 'bull-case' and 'bear-case'")


def cmd_industry(args):
    """Run the industry analysis (Step 2)."""
    analyst = _load_analyst(args.ticker)
    print(f"Generating industry analysis for: {args.industry}")
    print("This uses extended thinking and may take a minute...\n")
    result = analyst.run_industry_analysis(args.industry)
    print("\n" + result)


def cmd_find_docs(args):
    """Find official document links (Step 3)."""
    analyst = _load_analyst(args.ticker)
    print(f"Searching for official filings for {analyst.company_name}...\n")
    result = analyst.find_documents()
    print("\n" + result)


def cmd_add_doc(args):
    """Add a document to the project."""
    dm = DocumentManager(args.ticker)
    path = dm.add_document(args.file, args.category)
    print(f"Added: {path}")


def cmd_list_docs(args):
    """List all documents in a project."""
    dm = DocumentManager(args.ticker)
    print(dm.get_document_summary())


def cmd_remove_doc(args):
    """Remove a document from the project."""
    dm = DocumentManager(args.ticker)
    if dm.remove_document(args.filename, args.category):
        print(f"Removed: {args.filename}")
    else:
        print(f"Not found: {args.filename}")


def cmd_bull_case(args):
    """Generate the bull case (Step 4a)."""
    analyst = _load_analyst(args.ticker)
    print(f"Generating bull case for {analyst.company_name}...\n")
    result = analyst.run_bull_case()
    print("\n" + result)


def cmd_bear_case(args):
    """Generate the bear case (Step 4b)."""
    analyst = _load_analyst(args.ticker)
    print(f"Generating bear case for {analyst.company_name}...\n")
    result = analyst.run_bear_case()
    print("\n" + result)


def cmd_quarterly(args):
    """Run quarterly analysis (Step 5)."""
    analyst = _load_analyst(args.ticker)
    print(f"Analyzing {args.quarter} for {analyst.company_name}...\n")
    result = analyst.run_quarterly_analysis(args.quarter)
    print("\n" + result)


def cmd_management(args):
    """Run management quality check."""
    analyst = _load_analyst(args.ticker)
    print(f"Checking management quality for {analyst.company_name}...\n")
    result = analyst.run_management_quality()
    print("\n" + result)


def cmd_competition(args):
    """Run competitive position analysis."""
    analyst = _load_analyst(args.ticker)
    print(f"Analyzing competitive position for {analyst.company_name}...\n")
    result = analyst.run_competitive_position()
    print("\n" + result)


def cmd_capalloc(args):
    """Run capital allocation scorecard."""
    analyst = _load_analyst(args.ticker)
    print(f"Scoring capital allocation for {analyst.company_name}...\n")
    result = analyst.run_capital_allocation()
    print("\n" + result)


def cmd_ask(args):
    """Ask a custom question."""
    analyst = _load_analyst(args.ticker)
    question = " ".join(args.question)
    print(f"Asking: {question}\n")
    result = analyst.ask(question)
    print("\n" + result)


def cmd_list_projects(args):
    """List all stock projects."""
    if not PROJECTS_DIR.exists():
        print("No projects found.")
        return
    projects = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    if not projects:
        print("No projects found.")
        return
    print("Stock Projects:")
    for p in sorted(projects):
        meta = load_project_meta(p.name)
        name = meta.get("company_name", "Unknown")
        exchange = meta.get("exchange", "?")
        docs = DocumentManager(p.name).list_documents()
        print(f"  {p.name:12s}  {name:30s}  {exchange:4s}  ({len(docs)} docs)")


def _load_analyst(ticker: str) -> StockAnalyst:
    """Load an analyst from an existing project."""
    meta = load_project_meta(ticker)
    if not meta:
        print(f"Error: No project found for ticker '{ticker}'.")
        print("Run 'init' first to create the project.")
        sys.exit(1)
    return StockAnalyst(
        ticker=meta["ticker"],
        company_name=meta["company_name"],
        exchange=meta.get("exchange", "NSE"),
    )


def main():
    parser = argparse.ArgumentParser(
        prog="stock-analyst",
        description="AI-powered Indian Stock Analyst — Powered by Claude",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p = sub.add_parser("init", help="Initialize a new stock project")
    p.add_argument("ticker", help="Stock ticker (e.g. INFY)")
    p.add_argument("company", help="Full company name (e.g. 'Infosys Limited')")
    p.add_argument("--exchange", default="NSE", choices=["NSE", "BSE"],
                    help="Exchange (default: NSE)")
    p.set_defaults(func=cmd_init)

    # list projects
    p = sub.add_parser("projects", help="List all stock projects")
    p.set_defaults(func=cmd_list_projects)

    # industry analysis
    p = sub.add_parser("industry", help="Generate industry analysis (Step 2)")
    p.add_argument("ticker", help="Stock ticker")
    p.add_argument("industry", help="Industry name (e.g. 'IT Services & Consulting')")
    p.set_defaults(func=cmd_industry)

    # find documents
    p = sub.add_parser("find-docs", help="Find official filing links (Step 3)")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_find_docs)

    # add document
    p = sub.add_parser("add-doc", help="Add a document to a project")
    p.add_argument("ticker", help="Stock ticker")
    p.add_argument("file", help="Path to the document file")
    p.add_argument("--category", default="general",
                    help="Category (e.g. annual_reports, quarterly, transcripts)")
    p.set_defaults(func=cmd_add_doc)

    # list documents
    p = sub.add_parser("list-docs", help="List documents in a project")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_list_docs)

    # remove document
    p = sub.add_parser("remove-doc", help="Remove a document from a project")
    p.add_argument("ticker", help="Stock ticker")
    p.add_argument("filename", help="Document filename to remove")
    p.add_argument("--category", default="general")
    p.set_defaults(func=cmd_remove_doc)

    # bull case
    p = sub.add_parser("bull-case", help="Generate bull case (Step 4a)")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_bull_case)

    # bear case
    p = sub.add_parser("bear-case", help="Generate bear case (Step 4b)")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_bear_case)

    # quarterly
    p = sub.add_parser("quarterly", help="Run quarterly analysis (Step 5)")
    p.add_argument("ticker", help="Stock ticker")
    p.add_argument("quarter", help="Quarter label (e.g. 'Q3 FY25')")
    p.set_defaults(func=cmd_quarterly)

    # management
    p = sub.add_parser("management", help="Management quality check")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_management)

    # competition
    p = sub.add_parser("competition", help="Competitive position analysis")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_competition)

    # capital allocation
    p = sub.add_parser("capalloc", help="Capital allocation scorecard")
    p.add_argument("ticker", help="Stock ticker")
    p.set_defaults(func=cmd_capalloc)

    # ask
    p = sub.add_parser("ask", help="Ask a custom question")
    p.add_argument("ticker", help="Stock ticker")
    p.add_argument("question", nargs="+", help="Your question")
    p.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
