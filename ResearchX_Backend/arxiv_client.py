import arxiv
from enum import Enum
from typing import List, Dict, Any


class PARAMS(Enum):
    TITLE = "title"
    AUTHORS = "authors"
    ABSTRACT = "summary"
    PUBLISHED = "published"
    PDF_URL = "pdf_url"


class ArxivClient:
    def __init__(
        self,
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
    ):
        self.max_results = max_results
        self.sort_by = sort_by
        # arxiv.Client 默认 page_size=100，即使只需要 2 篇也会向 API 请求
        # max_results=100，容易触发共享出口 IP 的 429。按实际需要分页并启用重试。
        self.client = arxiv.Client(
            page_size=max(1, min(max_results, 100)),
            delay_seconds=3.0,
            # Research Skill 自带备用数据源；避免 429 时阻塞请求一分钟以上。
            num_retries=0,
        )

    def fetch_results(
        self, keywords: List[str], fetch_params: List[PARAMS]
    ) -> List[Dict[str, Any]]:
        query_string = " AND ".join(keywords)
        search = arxiv.Search(
            query=query_string, max_results=self.max_results, sort_by=self.sort_by
        )
        results = []
        for result in self.client.results(search):
            paper_info = {}
            if PARAMS.TITLE in fetch_params:
                paper_info[PARAMS.TITLE] = result.title
            if PARAMS.AUTHORS in fetch_params:
                paper_info[PARAMS.AUTHORS] = [author.name for author in result.authors]
            if PARAMS.ABSTRACT in fetch_params:
                paper_info[PARAMS.ABSTRACT] = result.summary
            if PARAMS.PUBLISHED in fetch_params:
                paper_info[PARAMS.PUBLISHED] = result.published
            if PARAMS.PDF_URL in fetch_params:
                paper_info[PARAMS.PDF_URL] = result.pdf_url
            results.append(paper_info)
        return results


def test():
    keywords = ["quantum computing", "machine learning"]
    fetch_params = [PARAMS.TITLE, PARAMS.PDF_URL, PARAMS.PUBLISHED]

    client = ArxivClient(max_results=10)
    results = client.fetch_results(keywords, fetch_params)

    for paper in results:
        print(f"Title: {paper.get(PARAMS.TITLE, 'N/A')}")
        print(f"Authors: {paper.get(PARAMS.AUTHORS, 'N/A')}")
        print(f"Abstract: {paper.get(PARAMS.ABSTRACT, 'N/A')}")
        print(f"PUBLISHED: {paper.get(PARAMS.PUBLISHED, 'N/A')}")
        print(f"PDF URL: {paper.get(PARAMS.PDF_URL, 'N/A')}")
        print("-" * 80)
