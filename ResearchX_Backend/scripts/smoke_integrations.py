"""Small live checks for configured model providers and public paper search.

Run from ResearchX_Backend with ``.venv\\Scripts\\python scripts\\smoke_integrations.py``.
Only provider status and result counts are printed; credentials and response bodies stay private.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm.LLM import LLM
from core.skills.paper_search import PaperSearchSkill


def check_models() -> bool:
    client = LLM()
    passed = True
    for name in ("deepseek", "kimi", "zhipu"):
        if name not in client.get_all_llms():
            print(f"model {name}: NOT_CONFIGURED")
            passed = False
            continue
        try:
            reply = client.get_llm(name).invoke("Reply with the single word OK.")
            success = bool(str(reply.content).strip())
            print(f"model {name}: {'OK' if success else 'EMPTY_RESPONSE'}")
            passed &= success
        except Exception as exc:
            code = getattr(exc, "status_code", None)
            print(f"model {name}: FAILED ({type(exc).__name__}, status={code})")
            passed = False
    return passed


async def check_search() -> bool:
    result = await PaperSearchSkill().run(
        {"keywords": ["retrieval augmented generation"], "max_results": 2}
    )
    papers = result.output.get("papers", []) if result.ok else []
    print(
        f"paper_search: {'OK' if papers else 'FAILED'} "
        f"(provider={result.output.get('provider', 'none')}, count={len(papers)}, "
        f"error_code={result.error_code})"
    )
    return bool(papers)


if __name__ == "__main__":
    models_ok = check_models()
    search_ok = asyncio.run(check_search())
    raise SystemExit(0 if models_ok and search_ok else 1)
