"""paper_search：包装 arxiv_client，返回结构化论文列表。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from core.skills.base import BaseSkill, SkillResult


class PaperSearchInput(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    max_results: int = 10
    recent: bool = False


class PaperSearchSkill(BaseSkill):
    name = "paper_search"
    description = "按关键词搜索 arXiv，返回结构化论文元数据列表"
    input_model = PaperSearchInput

    async def execute(self, data: PaperSearchInput, ctx: dict) -> SkillResult:
        if not data.keywords:
            return SkillResult(ok=False, error_code="BAD_INPUT", error_message="关键词为空")
        import arxiv
        from arxiv_client import PARAMS, ArxivClient

        client = ArxivClient(
            max_results=data.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate if data.recent else arxiv.SortCriterion.Relevance,
        )
        fetch_params = [
            PARAMS.TITLE,
            PARAMS.AUTHORS,
            PARAMS.ABSTRACT,
            PARAMS.PUBLISHED,
            PARAMS.PDF_URL,
        ]
        provider = "arxiv"
        warning = None
        try:
            raw_papers = client.fetch_results(data.keywords, fetch_params)
        except Exception as e:
            warning = f"arXiv 暂时不可用，已切换 OpenAlex: {e}"
            provider = "openalex"
            try:
                papers = self._search_openalex(data.keywords, data.max_results, recent=data.recent)
            except Exception as fallback_error:
                return SkillResult(
                    ok=False,
                    error_code="SEARCH_ERROR",
                    error_message=f"arXiv: {e}; OpenAlex: {fallback_error}",
                )
        else:
            # arxiv_client 使用 PARAMS 枚举作为字典键，并包含 datetime 值。
            # Research 结果需要写入 JSON/数据库，因此在 Skill 边界统一转换为普通 JSON 数据。
            papers = []
            for paper in raw_papers:
                normalized = {}
                for key, value in paper.items():
                    json_key = key.value if isinstance(key, Enum) else str(key)
                    if isinstance(value, (datetime, date)):
                        value = value.isoformat()
                    normalized[json_key] = value
                normalized["provider"] = provider
                normalized["venue"] = normalized.get("journal_ref") or "arXiv 预印本"
                normalized["source_type"] = "preprint"
                papers.append(normalized)

            # arXiv may return no matches without raising an exception. Use the
            # same fallback as for a failed request so Ask can show real results.
            if not papers:
                provider = "openalex"
                warning = "arXiv 未找到匹配论文，已切换 OpenAlex"
                try:
                    papers = self._search_openalex(data.keywords, data.max_results, recent=data.recent)
                except Exception as fallback_error:
                    return SkillResult(
                        ok=False,
                        error_code="SEARCH_ERROR",
                        error_message=f"arXiv 无结果；OpenAlex: {fallback_error}",
                    )

        artifact = {
            "type": "paper_list",
            "title": ", ".join(data.keywords),
            "papers": papers,
            "provider": provider,
        }
        output = {"papers": papers, "provider": provider}
        if warning:
            output["warning"] = warning
        return SkillResult(ok=True, output=output, artifacts=[artifact])

    @staticmethod
    def _search_openalex(keywords: list[str], max_results: int, recent: bool = False) -> list[dict]:
        """arXiv 限流时使用 OpenAlex 的公开论文元数据作为只读备用源。"""
        import requests

        params = {
            "search": " ".join(keywords),
            "per-page": max(1, min(max_results, 20)),
        }
        if recent:
            today = date.today()
            params["filter"] = (
                f"from_publication_date:{(today - timedelta(days=365)).isoformat()},"
                f"to_publication_date:{today.isoformat()}"
            )
            params["sort"] = "publication_date:desc"
        response = requests.get(
            "https://api.openalex.org/works",
            params=params,
            headers={"User-Agent": "ResearchX/1.0"},
            timeout=30,
        )
        response.raise_for_status()

        papers = []
        for work in response.json().get("results", []):
            abstract_index = work.get("abstract_inverted_index") or {}
            positioned_words = [
                (position, word)
                for word, positions in abstract_index.items()
                for position in positions
            ]
            abstract = " ".join(word for _, word in sorted(positioned_words))
            location = work.get("best_oa_location") or work.get("primary_location") or {}
            source = location.get("source") or (work.get("primary_location") or {}).get("source") or {}
            authors = [
                item.get("author", {}).get("display_name", "")
                for item in work.get("authorships", [])
                if item.get("author", {}).get("display_name")
            ]
            papers.append({
                "title": work.get("display_name", ""),
                "authors": authors,
                "summary": abstract,
                "published": work.get("publication_date"),
                "pdf_url": location.get("pdf_url") or location.get("landing_page_url"),
                "doi": work.get("doi"),
                "openalex_id": work.get("id"),
                "provider": "openalex",
                "venue": source.get("display_name") or "来源未注明",
                "source_type": source.get("type") or "unknown",
            })
        if not papers:
            raise RuntimeError("OpenAlex 未返回匹配论文")
        return papers
