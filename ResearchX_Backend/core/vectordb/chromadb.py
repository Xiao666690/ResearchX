import logging

from langchain_chroma import Chroma

from core.common.types import EvidenceChunk

logger = logging.getLogger(__name__)


# 提供对向量数据库的操作
class AcadeChroma:
    def __init__(self,persist_directory_layer1,persist_directory_layer2,embedding_model,llm_model):
        self.chroma_db_layer1 = Chroma(persist_directory=persist_directory_layer1, embedding_function=embedding_model)
        self.chroma_db_layer2 = Chroma(persist_directory=persist_directory_layer2, embedding_function=embedding_model)
        self.current_layer1_count=self.chroma_db_layer1._collection.count()
        self.current_layer2_count=self.chroma_db_layer2._collection.count()
        self.retrieval_enhancer = None
    # 增
    def add_paper_to_layer1(self,texts,metadatas):
        # 分批写入：一次性 embedding 整篇论文会让 ONNX 内存瞬间暴涨，
        # Windows 可能直接杀掉 Worker 进程。改为每批 64 个文本块循环写入。
        BATCH = 64
        for i in range(0, len(texts), BATCH):
            self.chroma_db_layer1.add_texts(
                texts[i:i+BATCH],
                metadatas[i:i+BATCH],
            )
        self.current_layer1_count=self.chroma_db_layer1._collection.count()
    
    def add_paper_to_layer2(self,texts,metadatas):
        self.chroma_db_layer2.add_texts(texts, metadatas)
        self.current_layer2_count=self.chroma_db_layer2._collection.count()

    # 查 
    # 全局查询 , 根据问题返回检索出来的文档
    def query_paper_with_score_layer1(self,query_str):
        return self.chroma_db_layer1.similarity_search_with_score(query_str)
    # 根据问题返回检索出来的文档
    def query_paper_with_score_layer2(self,query_str):
        return self.chroma_db_layer2.similarity_search_with_score(query_str)
    
    # 过滤器查询
    def query_paper_with_score_layer1_by_filter(self,query_str,filter):
        fileRetriver=self.chroma_db_layer1.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 12,'filter':filter},
                )
        docs=fileRetriver.batch([query_str])
        return str(docs)
    # 过滤器查询
    def query_paper_with_score_layer2_by_filter(self,query_str,filters):
        pass

    def search_evidence(self, query_str: str, filter: dict | None = None, k: int = 12) -> list[EvidenceChunk]:
        """结构化检索：返回带 documentID/page_number/score 的 EvidenceChunk 列表。

        用于替换旧的 str(docs) 返回，供 Citation、RRF、Grounding 使用。
        """
        if self.retrieval_enhancer is not None:
            try:
                return self.retrieval_enhancer.search(
                    self.chroma_db_layer1, query_str, filter, k
                )
            except Exception:
                logger.exception("BGE hybrid retrieval failed; using the ONNX index")

        docs_scores = self.chroma_db_layer1.similarity_search_with_score(
            query_str, k=k, filter=filter
        )
        chunks: list[EvidenceChunk] = []
        for index, (doc, score) in enumerate(docs_scores):
            m = doc.metadata or {}
            document_id = m.get("documentID") or m.get("document_id") or ""
            page_number = m.get("page_number", 0)
            chunks.append(EvidenceChunk(
                chunk_id=m.get("chunk_id") or str(getattr(doc, "id", "") or f"{document_id}:p{page_number}:{index}"),
                document_id=document_id,
                knowledge_id=m.get("knowledge_name") or m.get("knowledgeID"),
                source=m.get("source", ""),
                page_number=int(page_number or 0),
                text=doc.page_content,
                dense_score=float(score),
            ))
        return chunks

    def get_opening_evidence(self, document_ids: list[str]) -> list[EvidenceChunk]:
        """Return the opening PDF chunks for a paper overview question.

        Generic prompts such as "summarize this paper" are poor embedding
        queries. Reading each selected paper's first page gives the model
        actual title/abstract/introduction text with traceable citations.
        """
        result: list[EvidenceChunk] = []
        per_document = 4 if len(document_ids) == 1 else 2
        for document_id in dict.fromkeys(document_ids):
            stored = self.chroma_db_layer1._collection.get(
                where={"documentID": document_id},
                include=["documents", "metadatas"],
            )
            rows = [
                (index, doc_id, text, metadata or {})
                for index, (doc_id, text, metadata) in enumerate(zip(
                    stored.get("ids") or [],
                    stored.get("documents") or [],
                    stored.get("metadatas") or [],
                ))
                if text
            ]
            rows.sort(key=lambda row: (int(row[3].get("page_number", 0) or 0), row[0]))
            seen_texts: set[str] = set()
            for _, doc_id, text, metadata in rows:
                if text in seen_texts:
                    continue
                seen_texts.add(text)
                result.append(EvidenceChunk(
                    chunk_id=metadata.get("chunk_id") or doc_id,
                    document_id=document_id,
                    knowledge_id=metadata.get("knowledge_name") or metadata.get("knowledgeID"),
                    source=metadata.get("source", ""),
                    page_number=int(metadata.get("page_number", 0) or 0),
                    text=text,
                ))
                if len(seen_texts) >= per_document:
                    break
        return result

    
    # 删除指定 kid下的文档
    # 注意：0xC0000005 这类原生 segfault 无法被 try/except 捕获。因此这里先
    # 用 _collection.count() 探测索引是否可访问——若索引已损坏/不可用，直接跳过
    # 删除，而不是对异常索引执行 get(where) 过滤触发 hnswlib 底层崩溃。
    def delete_paper_from_layer1(self,kid,documentid):
        if self.chroma_db_layer1 is None:
            return
        try:
            # 探测索引可读性，异常则放弃删除（防止原生崩溃）
            try:
                self.chroma_db_layer1._collection.count()
            except Exception:
                logger.warning("delete_paper_from_layer1: layer1 索引不可用，跳过 (kid=%s, doc=%s)", kid, documentid)
                return
            filterDocs=self.chroma_db_layer1.get(where={"$and":[{"knowledge_name":kid},{"documentID":documentid}]},include=["metadatas"])
            ids = (filterDocs or {}).get("ids") or []
            if len(ids)>0:
                self.chroma_db_layer1.delete(ids)
        except Exception as e:
            logger.warning("delete_paper_from_layer1 failed (kid=%s, doc=%s): %s", kid, documentid, e)

    def delete_paper_from_layer2(self,kid,documentid):
        if self.chroma_db_layer2 is None:
            return
        try:
            # 探测索引可读性，异常则放弃删除（防止原生崩溃）
            try:
                self.chroma_db_layer2._collection.count()
            except Exception:
                logger.warning("delete_paper_from_layer2: layer2 索引不可用，跳过 (kid=%s, doc=%s)", kid, documentid)
                return
            filterDocs=self.chroma_db_layer2.get(where={"$and":[{"knowledgeID":kid},{"documentID":documentid}]},include=["metadatas"])
            ids = (filterDocs or {}).get("ids") or []
            if len(ids)>0:
                self.chroma_db_layer2.delete(ids)
        except Exception as e:
            logger.warning("delete_paper_from_layer2 failed (kid=%s, doc=%s): %s", kid, documentid, e)
    # 改
    def alter_paper_from_layer1(self,ids,text):
        pass 
    
    # 状态查询
    def get_layer_vector_count(self):
        return self.current_layer1_count,self.current_layer2_count


