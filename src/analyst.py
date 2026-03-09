"""Core analyst engine — sends prompts to Claude with document context."""

import anthropic

from .documents.manager import DocumentManager
from .prompts.renderer import render_prompt
from .prompts.templates import PromptTemplates
from .utils.config import (
    get_api_key,
    get_project_dir,
    load_project_meta,
    save_project_meta,
)


DEFAULT_MODEL = "claude-opus-4-6"
MAX_TOKENS = 8192


class StockAnalyst:
    """Orchestrates analysis for a single stock."""

    def __init__(self, ticker: str, company_name: str, exchange: str = "NSE"):
        self.ticker = ticker.upper()
        self.company_name = company_name
        self.exchange = exchange.upper()
        self.doc_manager = DocumentManager(self.ticker)
        self.client = anthropic.Anthropic(api_key=get_api_key())
        self.model = DEFAULT_MODEL

        # Persist project metadata
        meta = load_project_meta(self.ticker)
        meta.update(
            {
                "ticker": self.ticker,
                "company_name": self.company_name,
                "exchange": self.exchange,
            }
        )
        save_project_meta(self.ticker, meta)

    @property
    def system_prompt(self) -> str:
        return render_prompt(
            "SYSTEM_INSTRUCTIONS",
            COMPANY_NAME=self.company_name,
            TICKER=self.ticker,
            EXCHANGE=self.exchange,
        )

    def _call_claude(
        self,
        user_prompt: str,
        system: str | None = None,
        include_docs: bool = True,
        model: str | None = None,
        extended_thinking: bool = False,
    ) -> str:
        """Send a message to Claude and return the text response."""
        sys_prompt = system or self.system_prompt

        # Build user content: documents first, then the prompt
        user_content = []
        if include_docs:
            user_content.extend(self.doc_manager.prepare_for_api())
        user_content.append({"type": "text", "text": user_prompt})

        kwargs = {
            "model": model or self.model,
            "max_tokens": MAX_TOKENS,
            "system": sys_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }

        if extended_thinking:
            kwargs["temperature"] = 1  # required for extended thinking
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 4096,
            }

        response = self.client.messages.create(**kwargs)

        # Extract text from response
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _save_output(self, name: str, content: str) -> str:
        """Save analysis output to the project's outputs directory."""
        output_dir = get_project_dir(self.ticker) / "outputs"
        output_dir.mkdir(exist_ok=True)
        out_path = output_dir / f"{name}.md"
        out_path.write_text(content)
        return str(out_path)

    # ── Step 2: Industry Analysis ──────────────────────────────────────

    def run_industry_analysis(self, industry_name: str) -> str:
        """Generate an industry overview (Step 2). Uses extended thinking."""
        prompt = render_prompt("INDUSTRY_ANALYSIS", INDUSTRY_NAME=industry_name)
        result = self._call_claude(
            prompt,
            system="You are an industry analyst writing for long-term equity investors.",
            include_docs=False,
            extended_thinking=True,
        )
        path = self._save_output("industry_analysis", result)

        # Also save as a document for future reference
        from pathlib import Path

        doc_path = self.doc_manager.docs_dir / "industry"
        doc_path.mkdir(exist_ok=True)
        (doc_path / "industry_analysis.md").write_text(result)

        meta = load_project_meta(self.ticker)
        meta["industry_name"] = industry_name
        meta["industry_analysis_done"] = True
        save_project_meta(self.ticker, meta)

        print(f"Industry analysis saved to: {path}")
        return result

    # ── Step 3: Document Finder ────────────────────────────────────────

    def find_documents(self) -> str:
        """Generate links to official filings (Step 3)."""
        prompt = render_prompt(
            "DOCUMENT_FINDER",
            COMPANY_NAME=self.company_name,
            TICKER=self.ticker,
            EXCHANGE=self.exchange,
        )
        result = self._call_claude(
            prompt,
            system="You are a research assistant helping find official Indian company filings.",
            include_docs=False,
            extended_thinking=True,
        )
        path = self._save_output("document_links", result)
        print(f"Document links saved to: {path}")
        return result

    # ── Step 4a: Bull Case ─────────────────────────────────────────────

    def run_bull_case(self) -> str:
        """Generate the Lynch-style bull case (Step 4a)."""
        prompt = render_prompt("BULL_CASE", COMPANY_NAME=self.company_name)
        result = self._call_claude(prompt)
        path = self._save_output("bull_case", result)

        # Save as document for future reference
        doc_path = self.doc_manager.docs_dir / "analysis"
        doc_path.mkdir(exist_ok=True)
        (doc_path / "bull_case.md").write_text(result)

        print(f"Bull case saved to: {path}")
        return result

    # ── Step 4b: Bear Case ─────────────────────────────────────────────

    def run_bear_case(self) -> str:
        """Generate the Munger-style bear case (Step 4b)."""
        prompt = render_prompt("BEAR_CASE", COMPANY_NAME=self.company_name)
        result = self._call_claude(prompt)
        path = self._save_output("bear_case", result)

        doc_path = self.doc_manager.docs_dir / "analysis"
        doc_path.mkdir(exist_ok=True)
        (doc_path / "bear_case.md").write_text(result)

        print(f"Bear case saved to: {path}")
        return result

    # ── Step 5: Quarterly Analysis ─────────────────────────────────────

    def run_quarterly_analysis(self, quarter: str) -> str:
        """Analyze a quarter's earnings (Step 5). e.g. quarter='Q3 FY25'."""
        prompt = render_prompt(
            "QUARTERLY_ANALYSIS",
            COMPANY_NAME=self.company_name,
            QUARTER=quarter,
        )
        result = self._call_claude(prompt)
        safe_name = quarter.replace(" ", "_").lower()
        path = self._save_output(f"quarterly_{safe_name}", result)

        doc_path = self.doc_manager.docs_dir / "analysis"
        doc_path.mkdir(exist_ok=True)
        (doc_path / f"quarterly_{safe_name}.md").write_text(result)

        print(f"Quarterly analysis saved to: {path}")
        return result

    # ── Bonus Prompts ──────────────────────────────────────────────────

    def run_management_quality(self) -> str:
        """Run the management quality check."""
        prompt = PromptTemplates.MANAGEMENT_QUALITY
        result = self._call_claude(prompt)
        path = self._save_output("management_quality", result)
        print(f"Management quality check saved to: {path}")
        return result

    def run_competitive_position(self) -> str:
        """Run the competitive position analysis."""
        prompt = render_prompt(
            "COMPETITIVE_POSITION", COMPANY_NAME=self.company_name
        )
        result = self._call_claude(prompt)
        path = self._save_output("competitive_position", result)
        print(f"Competitive position saved to: {path}")
        return result

    def run_capital_allocation(self) -> str:
        """Run the capital allocation scorecard."""
        prompt = render_prompt(
            "CAPITAL_ALLOCATION", COMPANY_NAME=self.company_name
        )
        result = self._call_claude(prompt)
        path = self._save_output("capital_allocation", result)
        print(f"Capital allocation scorecard saved to: {path}")
        return result

    # ── Custom Query ───────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """Ask any custom question with full document context."""
        result = self._call_claude(question)
        return result
