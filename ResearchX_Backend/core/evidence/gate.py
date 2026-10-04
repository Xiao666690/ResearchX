"""Research evidence gate. Keep source identity separate from generated prose."""
from __future__ import annotations

import json
import re

from core.research.schemas import EvidenceSource, EvidenceState, ResearchState


class ResearchEvidenceGate:
    def __init__(self, decision_engine=None):
        self.decision_engine = decision_engine

    @staticmethod
    def required_sources(goal: str) -> int:
        comparative = ("比较", "对比", "综述", "趋势", "主流", "代表性", "compare", "review", "survey")
        return 3 if any(term in goal.lower() for term in comparative) else 1

    @staticmethod
    def _collect(state: ResearchState) -> list[EvidenceSource]:
        sources: list[EvidenceSource] = []
        seen: set[str] = set()

        def add(source_id: str, title: str, excerpt: str, locator: str, source_type: str):
            key = source_id or locator or title
            if not key or key in seen or not excerpt.strip():
                return
            seen.add(key)
            sources.append(EvidenceSource(
                citation_id=f"C{len(sources) + 1}", source_id=key,
                title=title, excerpt=excerpt[:2400], locator=locator,
                source_type=source_type,
            ))

        for observation in state.observations:
            if observation.status != "SUCCESS":
                continue
            output = observation.output
            if observation.skill == "paper_search":
                for paper in output.get("papers", []):
                    if not isinstance(paper, dict):
                        continue
                    title = str(paper.get("title") or "")
                    locator = str(paper.get("doi") or paper.get("pdf_url") or paper.get("openalex_id") or "")
                    add(locator or title, title, str(paper.get("summary") or paper.get("abstract") or ""),
                        locator, "paper_abstract")
            elif observation.skill == "local_retrieval":
                for chunk in output.get("evidence", []):
                    if not isinstance(chunk, dict):
                        continue
                    doc_id = str(chunk.get("document_id") or "")
                    page = chunk.get("page_number") or 0
                    add(str(chunk.get("chunk_id") or f"{doc_id}:{page}"), doc_id,
                        str(chunk.get("text") or ""), f"{doc_id}#page={page}", "local_chunk")
            elif observation.skill == "paper_reader":
                doc_id = str(output.get("document_id") or "")
                page = output.get("page") or 0
                add(f"{doc_id}:{page}", doc_id, str(output.get("text") or ""),
                    f"{doc_id}#page={page}", "local_page")
        return sources

    def evaluate(self, state: ResearchState) -> EvidenceState:
        sources = self._collect(state)
        required = self.required_sources(state.goal)
        result = EvidenceState(required_sources=required, sources=sources,
                               score=min(1.0, len(sources) / required))
        if len(sources) < required:
            result.status = "PARTIAL" if sources else "MISSING_EXTERNAL"
            result.reason = f"可追溯来源 {len(sources)} 个，目标至少需要 {required} 个"
            result.missing_aspects = ["补充独立且相关的来源"]
            return result

        if self.decision_engine is not None:
            evidence_text = "\n\n".join(
                f"[{source.citation_id}] {source.title}: {source.excerpt[:800]}"
                for source in sources[:12]
            )
            decision = self.decision_engine.decide_evidence(state.goal, evidence_text)
            result.score = decision.evidence_score
            result.missing_aspects = decision.missing_aspects
            result.search_keywords = decision.search_keywords
            result.status = {
                "ANSWER": "SUFFICIENT",
                "EXPAND_LOCAL": "PARTIAL",
                "SEARCH_EXTERNAL": "MISSING_EXTERNAL",
                "ABSTAIN": "UNSUPPORTED",
            }[decision.decision]
            result.reason = f"证据决策：{decision.decision}"
            if result.status == "SUFFICIENT" and len(sources) > 1:
                # The Ask evidence decision has no conflict category. Check it
                # before permitting synthesis from potentially incompatible claims.
                prompt = (
                    "判断以下独立论文来源是否对研究目标中的同一个事实给出实质矛盾的结论。"
                    "只输出 JSON：{\"conflict\": true/false, \"reason\": \"...\"}。"
                    "仅因研究方法不同、数据集不同或措辞不同不算冲突。\n"
                    f"目标：{state.goal}\n来源：{evidence_text[:6500]}"
                )
                try:
                    response = self.decision_engine.llm.invoke(prompt)
                    raw = response.content if hasattr(response, "content") else str(response)
                    finding = json.loads(re.sub(r"```(?:json)?|```", "", raw).strip())
                    if finding.get("conflict") is True:
                        result.status = "CONFLICT"
                        result.reason = str(finding.get("reason") or "来源之间存在实质冲突")[:500]
                        result.missing_aspects = ["核对冲突来源并补充独立证据"]
                except (ValueError, TypeError, KeyError):
                    # Keep the original conservative evidence decision when the
                    # supplemental conflict check cannot be parsed.
                    pass
        else:
            result.status = "SUFFICIENT"
            result.reason = "已达到来源数量门槛，等待结论核验"
        return result
