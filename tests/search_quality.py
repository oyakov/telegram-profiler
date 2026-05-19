"""
Search quality evaluation script.

Runs a set of real-world queries against the live API and grades each result
by checking whether the evidence text actually matches the query topic.

Usage:
    python tests/search_quality.py [--url http://localhost:8000]

Output: a table of queries with per-result evidence snippets and a PASS/FAIL
grade based on keyword coverage of the top contacts.
"""

import asyncio
import sys
import re
import argparse
import httpx

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from dataclasses import dataclass, field
from typing import Optional

# ── Test cases ────────────────────────────────────────────────────────────────
# Each case: query, list of "expected concept words" that SHOULD appear in
# evidence for a result to be considered relevant.
# A result is RELEVANT if ≥1 expected word is found in any evidence text.
# A query PASSES if ≥50% of top-3 contacts are relevant.

@dataclass
class SearchCase:
    query: str
    expected_words: list[str]          # words that should appear in evidence
    forbidden_words: list[str] = field(default_factory=list)  # words that hurt relevance
    description: str = ""

CASES: list[SearchCase] = [
    # ── Core topic+location queries (hard cases — location bias test) ─────────
    SearchCase(
        query="недвижимость Белград",
        expected_words=["недвижимость", "квартир", "аренд", "продаж", "риелтор", "комнат", "жильё", "жилье", "rent", "estate", "apartment"],
        description="Real estate in Belgrade — must find agents/buyers, NOT just Belgrade-mentioners",
    ),
    SearchCase(
        query="аренда квартира Белград снять жилье",
        expected_words=["аренд", "квартир", "снять", "жильё", "жилье", "комнат", "rent", "apartment", "flat", "housing"],
        description="Apartment rentals in Belgrade",
    ),
    SearchCase(
        query="ресторан кафе еда Белград",
        expected_words=["ресторан", "кафе", "еда", "кухня", "заведение", "food", "restaurant", "кофе", "обед", "ужин", "бар"],
        description="Restaurant/food in Belgrade — NOT just Belgrade news",
    ),

    # ── Profession queries (should work well) ─────────────────────────────────
    SearchCase(
        query="программист Python разработчик",
        expected_words=["python", "программист", "разработчик", "код", "developer", "backend", "frontend", "django", "flask", "fastapi", "software"],
        description="Python developer",
    ),
    SearchCase(
        query="маркетинг реклама SMM",
        expected_words=["маркетинг", "реклам", "smm", "таргет", "контент", "продвижение", "бренд", "marketing", "ads", "instagram"],
        description="Marketing and advertising specialists",
    ),
    SearchCase(
        query="юрист адвокат право",
        expected_words=["юрист", "адвокат", "право", "закон", "договор", "суд", "юридич", "lawyer", "legal", "attorney"],
        description="Lawyers and legal professionals",
    ),
    SearchCase(
        query="работа вакансия найм HR",
        expected_words=["работ", "вакансия", "найм", "hr", "рекрутер", "резюме", "job", "hire", "recruit", "vacancy"],
        description="Job/HR people",
    ),

    # ── Investment / finance ──────────────────────────────────────────────────
    SearchCase(
        query="инвестиции стартап венчур",
        expected_words=["инвестиц", "стартап", "венчур", "фонд", "раунд", "инвестор", "капитал", "startup", "invest", "fund", "vc"],
        description="Investment/startup people",
    ),

    # ── Single-word queries (stress test — should still return relevant results)
    SearchCase(
        query="криптовалюта",
        expected_words=["крипт", "bitcoin", "btc", "eth", "blockchain", "токен", "coin", "web3", "defi"],
        description="Single word: crypto — semantic expansion test",
    ),
    SearchCase(
        query="медицина врач",
        expected_words=["медицин", "врач", "доктор", "больниц", "клиник", "лечение", "здоровье", "doctor", "medical", "health"],
        description="Medicine / doctors",
    ),

    # ── IT / tech ─────────────────────────────────────────────────────────────
    SearchCase(
        query="IT технологии бизнес автоматизация",
        expected_words=["it", "технолог", "автоматизац", "бизнес", "crm", "erp", "software", "tech", "digital", "систем"],
        description="IT/tech business automation",
    ),
]


# ── HTTP client ───────────────────────────────────────────────────────────────

async def run_search(url: str, query: str, limit: int = 10) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{url}/api/search", json={"query": query, "limit": limit})
        resp.raise_for_status()
        return resp.json()


# ── Grading ───────────────────────────────────────────────────────────────────

def evidence_text(contact: dict) -> str:
    """Concatenate all evidence snippets for a contact."""
    ev = contact.get("evidence") or []
    return " ".join(e.get("text", "") for e in ev).lower()


def is_relevant(contact: dict, case: SearchCase) -> bool:
    """True if any expected word appears in the evidence."""
    text = evidence_text(contact)
    if not text.strip():
        # No evidence — can't confirm relevance
        return False
    return any(w.lower() in text for w in case.expected_words)


def grade_case(contacts: list[dict], case: SearchCase, top_n: int = 3) -> dict:
    top = contacts[:top_n]
    relevant_count = sum(1 for c in top if is_relevant(c, case))
    pass_threshold = max(1, top_n // 2)  # at least 1 of top-3 must be relevant
    return {
        "total": len(top),
        "relevant": relevant_count,
        "passed": relevant_count >= pass_threshold,
    }


# ── Pretty printing ───────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
DIM    = "\033[2m"

def highlight(text: str, words: list[str]) -> str:
    """Wrap matching words in bold-green."""
    for w in words:
        text = re.sub(
            f"({re.escape(w)})",
            f"{GREEN}{BOLD}\\1{RESET}",
            text,
            flags=re.IGNORECASE,
        )
    return text


def print_case_result(case: SearchCase, result: dict, grade: dict):
    contacts = result.get("contacts", [])
    status = f"{GREEN}✓ PASS{RESET}" if grade["passed"] else f"{RED}✗ FAIL{RESET}"
    print(f"\n{'─'*72}")
    print(f"{BOLD}{CYAN}Query:{RESET} {case.query}")
    print(f"{DIM}{case.description}{RESET}")
    print(f"Status: {status}  ({grade['relevant']}/{grade['total']} relevant in top-{grade['total']})")
    print()

    if not contacts:
        print(f"  {RED}No results returned{RESET}")
        return

    for i, c in enumerate(contacts[:5], 1):
        name = f"{c.get('first_name') or ''} {c.get('last_name') or ''}".strip() or "—"
        username = c.get("telegram_username") or c.get("username") or ""
        sim = c.get("similarity", 0)
        stype = c.get("search_type", "?")
        relevant = is_relevant(c, case)
        marker = f"{GREEN}✓{RESET}" if relevant else f"{RED}✗{RESET}"

        bar_len = int(sim * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        sim_color = GREEN if sim >= 0.75 else (YELLOW if sim >= 0.5 else RED)
        sim_str = f"{sim_color}{sim:.0%}{RESET}"

        print(f"  {marker} #{i} {BOLD}{name}{RESET} @{username}  [{bar}] {sim_str}  [{stype}]")

        ev = (c.get("evidence") or [])[:2]
        if ev:
            for e in ev:
                snippet = e.get("text", "")[:120].replace("\n", " ")
                snippet = highlight(snippet, case.expected_words)
                rel_pct = e.get("relevance")
                rel_str = f" {DIM}({rel_pct:.0%}){RESET}" if rel_pct is not None else ""
                print(f"     {DIM}»{RESET} {snippet}{rel_str}")
        else:
            print(f"     {DIM}(no evidence){RESET}")
        print()


def print_summary(results: list[tuple[SearchCase, dict]]):
    passed = sum(1 for _, r in results if r["grade"]["passed"])
    total = len(results)
    pct = passed / total * 100 if total else 0
    color = GREEN if pct >= 75 else (YELLOW if pct >= 50 else RED)
    print(f"\n{'═'*72}")
    print(f"{BOLD}Overall: {color}{passed}/{total} passed ({pct:.0f}%){RESET}")
    print(f"{'═'*72}")
    for case, r in results:
        g = r["grade"]
        icon = f"{GREEN}✓{RESET}" if g["passed"] else f"{RED}✗{RESET}"
        print(f"  {icon} {case.query:<40} {g['relevant']}/{g['total']} relevant")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(base_url: str, cases: Optional[list[int]] = None):
    print(f"{BOLD}Search Quality Evaluation{RESET}")
    print(f"API: {base_url}")
    print(f"Test cases: {len(CASES)}")

    selected = [CASES[i] for i in cases] if cases else CASES
    all_results = []

    for case in selected:
        print(f"\n{DIM}Running: {case.query}...{RESET}", end="", flush=True)
        try:
            result = await run_search(base_url, case.query, limit=10)
            grade = grade_case(result.get("contacts", []), case)
            result["grade"] = grade
            all_results.append((case, result))
            print(f"\r{' '*60}\r", end="")
            print_case_result(case, result, grade)
        except Exception as e:
            print(f"\r{RED}ERROR: {e}{RESET}")
            all_results.append((case, {"contacts": [], "messages": [], "grade": {"total": 0, "relevant": 0, "passed": False}}))

    print_summary(all_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search quality evaluation")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--cases", nargs="*", type=int, help="Run only specific case indices (0-based)")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.cases))
