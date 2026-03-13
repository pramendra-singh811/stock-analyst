"""Core analyst engine — sends prompts to Gemini with document context."""

import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from .documents.manager import DocumentManager
from .prompts.renderer import render_prompt
from .prompts.templates import PromptTemplates
from .utils.config import (
    get_api_key,
    get_project_dir,
    load_project_meta,
    save_project_meta,
)


DEFAULT_MODEL = "gemini-2.0-flash"

# Gemini 2.0 Flash rate limits (free tier: 15 RPM, paid tier: 1000 RPM)
_MAX_RETRIES = 5
_INITIAL_BACKOFF = 5  # seconds
_MAX_BACKOFF = 120  # seconds
_MIN_REQUEST_INTERVAL = 4.0  # seconds between requests (~15 RPM safe margin)


class StockAnalyst:
    """Orchestrates analysis for a single stock."""

    def __init__(self, ticker: str, company_name: str, exchange: str = "NSE"):
        self.ticker = ticker.upper()
        self.company_name = company_name
        self.exchange = exchange.upper()
        self.doc_manager = DocumentManager(self.ticker)
        self.client = genai.Client(api_key=get_api_key())
        self.model = DEFAULT_MODEL
        self._last_request_time = 0.0

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

    def _throttle(self):
        """Enforce minimum interval between API requests to stay within RPM."""
        elapsed = time.time() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            wait = _MIN_REQUEST_INTERVAL - elapsed
            print(f"  Rate-limiting: waiting {wait:.1f}s before next request...")
            time.sleep(wait)
        self._last_request_time = time.time()

    def _call_gemini(
        self,
        user_prompt: str,
        system: str | None = None,
        include_docs: bool = True,
        model: str | None = None,
        thinking: bool = False,
    ) -> str:
        """Send a message to Gemini and return the text response.

        Includes rate-limiting (≤15 RPM) and exponential backoff on 429/5xx.
        """
        sys_prompt = system or self.system_prompt

        # Build content parts: documents first, then the prompt
        parts = []
        if include_docs:
            parts.extend(self.doc_manager.prepare_for_api())
        parts.append(types.Part.from_text(text=user_prompt))

        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.7,
        )

        if thinking:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=4096,
            )

        # Retry with exponential backoff on rate-limit / server errors
        backoff = _INITIAL_BACKOFF
        for attempt in range(1, _MAX_RETRIES + 1):
            self._throttle()
            try:
                response = self.client.models.generate_content(
                    model=model or self.model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=config,
                )

                # Extract text from response
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text_parts.append(part.text)
                return "\n".join(text_parts)

            except ClientError as e:
                if e.code == 429:
                    if attempt == _MAX_RETRIES:
                        print("Rate limit exceeded after all retries. "
                              "Please wait a few minutes or check your quota.")
                        raise
                    print(f"  Rate limited (429). Retrying in {backoff}s "
                          f"(attempt {attempt}/{_MAX_RETRIES})...")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, _MAX_BACKOFF)
                else:
                    raise
            except ServerError:
                if attempt == _MAX_RETRIES:
                    print("Server error after all retries.")
                    raise
                print(f"  Server error. Retrying in {backoff}s "
                      f"(attempt {attempt}/{_MAX_RETRIES})...")
                time.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

    def _save_output(self, name: str, content: str) -> str:
        """Save analysis output to the project's outputs directory."""
        output_dir = get_project_dir(self.ticker) / "outputs"
        output_dir.mkdir(exist_ok=True)
        out_path = output_dir / f"{name}.md"
        out_path.write_text(content)
        return str(out_path)

    # ── Step 2: Industry Analysis ──────────────────────────────────────

    def run_industry_analysis(self, industry_name: str) -> str:
        """Generate an industry overview (Step 2). Uses thinking mode."""
        prompt = render_prompt("INDUSTRY_ANALYSIS", INDUSTRY_NAME=industry_name)
        result = self._call_gemini(
            prompt,
            system="You are an industry analyst writing for long-term equity investors.",
            include_docs=False,
            thinking=True,
        )
        path = self._save_output("industry_analysis", result)

        # Also save as a document for future reference
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
        result = self._call_gemini(
            prompt,
            system="You are a research assistant helping find official Indian company filings.",
            include_docs=False,
            thinking=True,
        )
        path = self._save_output("document_links", result)
        print(f"Document links saved to: {path}")
        return result

    # ── Step 4a: Bull Case ─────────────────────────────────────────────

    def run_bull_case(self) -> str:
        """Generate the Lynch-style bull case (Step 4a)."""
        prompt = render_prompt("BULL_CASE", COMPANY_NAME=self.company_name)
        result = self._call_gemini(prompt)
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
        result = self._call_gemini(prompt)
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
        result = self._call_gemini(prompt)
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
        result = self._call_gemini(prompt)
        path = self._save_output("management_quality", result)
        print(f"Management quality check saved to: {path}")
        return result

    def run_competitive_position(self) -> str:
        """Run the competitive position analysis."""
        prompt = render_prompt(
            "COMPETITIVE_POSITION", COMPANY_NAME=self.company_name
        )
        result = self._call_gemini(prompt)
        path = self._save_output("competitive_position", result)
        print(f"Competitive position saved to: {path}")
        return result

    def run_capital_allocation(self) -> str:
        """Run the capital allocation scorecard."""
        prompt = render_prompt(
            "CAPITAL_ALLOCATION", COMPANY_NAME=self.company_name
        )
        result = self._call_gemini(prompt)
        path = self._save_output("capital_allocation", result)
        print(f"Capital allocation scorecard saved to: {path}")
        return result

    # ── Custom Query ───────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """Ask any custom question with full document context."""
        result = self._call_gemini(question)
        return result
