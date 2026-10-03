"""Prepare a bounded academic search from an Ask question and selected sources."""
from __future__ import annotations

import json
import re


_TRANSFER_PATTERNS = (
    r"跨(?:领域|学科|场景|任务|模态)|不同(?:领域|场景|任务)|其他(?:领域|场景|任务)",
    r"(?:迁移|移植|推广|扩展|拓展|复用).{0,40}(?:方向|领域|场景|任务|问题)",
    r"(?:应用|用于|运用|用在|落地到).{0,35}(?:方向|领域|场景|任务|问题)",
    r"(?:论文|方法|模型|机制|思路|idea).{0,45}(?:用于|应用到|迁移到|推广到|扩展到|拓展到|落地到).{0,45}(?:上|中|里|方向|领域|场景|任务)",
    r"(?:如果|假如|能否|怎样|怎么|如何).{0,30}(?:放到|应用到|迁移到|用在).{0,35}(?:领域|方向|场景|任务|上|中|里)",
    r"(?:从|基于).{0,20}(?:论文|方法|思路|idea).{0,35}(?:新方向|新场景|新课题|衍生|发散)",
    r"(?:idea|思路|方法).{0,30}(?:还能|可以).{0,20}(?:用于|用在|落地|应用|迁移)",
    r"(?:机制|方法|模型|算法|idea|思路).{0,30}(?:领域|方向|场景|任务).{0,12}(?:能|可以|怎么|如何).{0,8}(?:用|应用|落地|迁移)",
    r"(?:apply|adapt|transfer|extend|generaliz).{0,60}(?:to|into|across|in).{0,60}(?:domain|field|task|scenario|learning)",
    r"(?:could|can|would).{0,40}(?:idea|method|model|approach).{0,40}(?:work|apply|help).{0,25}(?:in|for).{0,35}(?:domain|field|task|learning)",
)

_LITERATURE_PATTERNS = (
    r"(?:找|搜索|搜集|搜搜|检索|查找|推荐|调研|收集).{0,45}(?:论文|文献|研究|工作|papers?|literature)",
    r"(?:有没有|有哪些|列举|推荐).{0,30}(?:相关|相似|类似|同类|近年|最新|外部|其他).{0,15}(?:论文|文献|研究|工作)",
    r"(?:相关|类似|相近|对标|最新).{0,15}(?:论文|文献|研究|工作).{0,20}(?:有哪些|有没有|推荐|吗|？|\?|找|搜)",
    r"(?:有没有|有哪些).{0,25}(?:类似|相关|同类)(?:方法|工作|研究)",
    r"(?:其他|现有|已有|最新).{0,12}(?:研究|论文|工作).{0,25}(?:对比|比较|相比|相较|差别|区别|异同)",
    r"(?:最新|前沿).{0,12}(?:进展|研究趋势|研究现状)|(?:领域|方向).{0,15}(?:研究现状|最新进展|前沿进展)",
    r"(?:arxiv|openalex|google scholar|semantic scholar).{0,25}(?:搜|找|检索|论文|paper|research)",
    r"(?:find|search|recommend|look for|discover).{0,50}(?:papers?|studies|literature|prior work|related work)",
    r"(?:compare|contrast).{0,40}(?:with|against).{0,25}(?:other|recent|related|existing).{0,25}(?:papers?|studies|work)",
    r"(?:related|recent|prior).{0,15}(?:literature|papers?|studies|work).{0,20}(?:on|about|for|support)",
)

_LOCAL_ONLY_PATTERNS = (
    r"(?:本篇|本文|文中|这篇论文|该论文).{0,25}(?:引用|列出|提到|参考文献|相关工作).{0,20}(?:哪些|什么|论文|文献|研究)?",
    r"(?:这篇论文|论文中|文中|作者).{0,35}(?:多少|几块|几张|用了几|成本|耗时|耗电|gpu|精确数值)",
)


def classify_external_request(question: str) -> str | None:
    """Fast route for explicit discovery requests; leave paper facts to the Judge."""
    query = question.strip()
    if any(re.search(pattern, query, re.IGNORECASE) for pattern in _TRANSFER_PATTERNS):
        return "transfer"
    if any(re.search(pattern, query, re.IGNORECASE) for pattern in _LOCAL_ONLY_PATTERNS):
        return None
    if any(re.search(pattern, query, re.IGNORECASE) for pattern in _LITERATURE_PATTERNS):
        return "literature"
    return None


def is_transfer_request(question: str) -> bool:
    """Explicit requests to carry a paper's idea to another area need discovery."""
    return classify_external_request(question) == "transfer"


def is_broad_paper_recommendation(question: str) -> bool:
    """Recognize requests for recent papers that contain no research topic."""
    if classify_external_request(question) != "literature":
        return False
    remainder = re.sub(
        r"最近|最新|近期|近来|今年|本月|本周|论文|文献|研究|工作|文章|推荐|介绍|"
        r"有没有|有哪些|有无|哪些|什么|一些|几篇|值得|看看|想看|阅读|读|"
        r"帮我|给我|请|相关|领域|方向|的|吗|呢|有|无|好|"
        r"recent|latest|new|papers?|studies|literature|recommend|suggest|any|some|please|me",
        "", question.lower(), flags=re.IGNORECASE,
    )
    return not re.sub(r"[\W\d_]+", "", remainder)


def wants_recent_papers(question: str) -> bool:
    return bool(re.search(r"最新|最近|近期|近年|今年|recent|latest|new|current", question, re.I))


def make_search_keywords(llm, question: str, source_context: str, kind: str = "transfer") -> list[str]:
    """Use the selected paper context to form concise English academic terms."""
    if is_broad_paper_recommendation(question):
        # A recommendation with no field cannot be searched as a Chinese sentence.
        return ["machine learning"]
    focus = (
        "兼顾目标领域与可迁移的方法"
        if kind == "transfer"
        else "突出用户要查找的主题、方法和相关研究，不加入未提及的新领域"
    )
    prompt = f"""你是学术检索词生成器。用户想围绕所选论文提出的问题检索相关研究。
根据用户目标和以下有限的论文片段，生成 1 到 3 个英文关键词短语，{focus}。
只输出 JSON，例如 {{"keywords":["federated learning", "adaptive optimization"]}}。
不要把论文片段当成其他论文的事实；不要生成完整回答。
用户问题：{question[:1000]}
所选论文片段：{source_context[:3500] or '暂无可用片段'}
"""
    try:
        response = llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else str(response)
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
        candidates = json.loads(raw).get("keywords", [])
        keywords = [str(item).strip()[:100] for item in candidates if str(item).strip()]
        if keywords:
            return keywords[:3]
    except Exception:
        pass
    # Do not send a full conversational sentence to arXiv as a keyword.
    known_terms = {
        "联邦学习": "federated learning", "大模型": "large language models",
        "语言模型": "large language models", "检索增强": "retrieval augmented generation",
        "计算机视觉": "computer vision", "医学影像": "medical imaging",
        "推荐系统": "recommender systems", "时间序列": "time series forecasting",
        "机器人": "robotics", "强化学习": "reinforcement learning",
        "人工智能": "artificial intelligence", "机器学习": "machine learning",
    }
    matched = [english for chinese, english in known_terms.items() if chinese in question]
    if matched:
        return list(dict.fromkeys(matched))[:3]
    english_words = re.findall(r"[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z][A-Za-z0-9-]*){0,3}", question)
    if english_words:
        return [english_words[0][:100]]
    return [question.strip()[:160]]


def normalize_papers(papers: list[dict]) -> list[dict]:
    """Send only displayable metadata to the browser; preserve source URLs."""
    result = []
    seen = set()
    for paper in papers:
        title = str(paper.get("title") or "").strip()
        if not title or title.casefold() in seen:
            continue
        seen.add(title.casefold())
        url = str(paper.get("pdf_url") or "").strip()
        if not url.startswith(("https://", "http://")):
            url = ""
        authors = paper.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]
        result.append({
            "title": title,
            "authors": [str(author) for author in authors[:6]],
            "summary": str(paper.get("summary") or "").strip()[:1600],
            "published": str(paper.get("published") or "")[:10],
            "pdf_url": url,
            "doi": str(paper.get("doi") or ""),
            "provider": str(paper.get("provider") or ""),
            "importable": bool(re.match(r"^https://(?:www\.|export\.)?arxiv\.org/pdf/", url, re.I)),
        })
    return result


def make_research_prompt(question: str, source_context: str, papers: list[dict], kind: str = "transfer") -> str:
    catalog = "\n".join(
        f"[{i}] {paper['title']} ({paper['published']}; {paper['provider']})\n"
        f"摘要：{paper['summary'][:700] or '未提供摘要'}"
        for i, paper in enumerate(papers[:6], 1)
    )
    guidance = (
        "请用中文给出 2-3 条具体但审慎的迁移建议：说明可迁移的机制、在目标领域的切入点、需要验证的问题。"
        if kind == "transfer"
        else "请用中文概括检索到的相关研究、它们与用户问题的关联，以及优先阅读哪些论文；不要强行写跨领域迁移建议。"
    )
    return f"""你是 PaperAgent 的学术研究助手。你已执行外部学术搜索。
下列是实际返回的论文标题与摘要，不是你读过的全文。
{guidance}
涉及所选本地论文的具体方法时用提供的 [C#] 引用；没有对应片段时只作条件式建议。
引用外部结果时用 [论文1]、[论文2] 等对应下列列表；不可编造论文、性能、数据集或已经证实的结论。
明确说明这些是基于标题/摘要的初步方向，用户可从下方列表选择 PDF 进一步核查。
用户问题：{question[:1000]}
所选本地论文片段：{source_context[:2500] or '暂无可用片段'}
实际搜索结果：\n{catalog}
"""
