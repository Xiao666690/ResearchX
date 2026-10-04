import time
import traceback
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import dotenv
dotenv.load_dotenv()
from colorama import Fore, Style
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from langchain_core.embeddings import Embeddings

from core.agent.dataprocessAgent import *
from core.backend.crud.crud_document import (
    get_document_status_equal_zero,
    update_document_content,
    update_document_status,
    reset_stuck_documents,
)
from core.backend.crud.crud_knowledge import update_knowledge_content
from core.backend.db.database import SessionLocal
from core.llm.LLM import *
from core.vectordb.chromadb import *


class ONNXEmbeddings(Embeddings):
    """使用 ChromaDB 内置 ONNX 模型，无需 API key，不依赖 sentence-transformers"""
    def __init__(self):
        cache_dir = os.getenv("CHROMA_ONNX_CACHE_DIR")
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            ONNXMiniLM_L6_V2.DOWNLOAD_PATH = cache_dir
        self._ef = ONNXMiniLM_L6_V2()

    def embed_documents(self, texts):
        return self._ef(texts)

    def embed_query(self, text):
        return self._ef([text])[0]


db = SessionLocal()

def test_add():
    dotenv.load_dotenv()
    llms=LLM()
    chroma_db=AcadeChroma("/data1/wyyzah-work/ResearchX_Backend/res/layer2","/data1/wyyzah-work/ResearchX_Backend/res/layer2",ONNXEmbeddings(),llms.get_llm('openai'))
    dp=DataProcessAgent(llms.get_llm('openai'),chroma_db)
    directory = os.getenv("document_SAVE_DIR")

    dp.batch_add_newdocument(directory,"kid1")

if __name__ == '__main__':
    dotenv.load_dotenv()
    llm=LLM()
    chroma_db=AcadeChroma(os.getenv("CHROMA_LAYER1_DIR"),os.getenv("CHROMA_LAYER2_DIR"),ONNXEmbeddings(),llm)
    dp=DataProcessAgent(llm,chroma_db)
    db = SessionLocal()
    # 启动时清理残留的"处理中"文档，避免进程中断后状态卡在 1 导致永不重试
    reset_stuck_documents(db)
    while True:
        document=get_document_status_equal_zero(db)
        time.sleep(3)
        if document:
            print(Fore.RED,f"开始处理{document.documentName}",Style.RESET_ALL)
            print(type(document))

            print(Fore.BLUE,f"更新状态为 1",Style.RESET_ALL)
            document.documentStatus=1
            update_document_status(db,document)
            try:
                result=dp.add_newpaper(os.getenv("AcadeAgent_DIR")+document.documentPath,document.knowledgeID)
            except Exception as e:
                print(Fore.RED, f"文档处理失败，已回滚为排队状态: {e}", Style.RESET_ALL)
                traceback.print_exc()
                document.documentStatus=0
                update_document_status(db,document)
                time.sleep(10)
                continue
            print(result)
            result["uid"]=document.uid
            print(Fore.YELLOW,f"更新向量,",Style.RESET_ALL)
            print(Fore.YELLOW,f"更新描述标签信息,",Style.RESET_ALL)
            update_document_content(db,result)
            print(Fore.YELLOW,f"更新知识库信息,",Style.RESET_ALL)
            ## 更新知识库状态, 总向量数+N,总文件数＋1
            update_knowledge_content(db,result["documentVector"],1,document.knowledgeID)
            print(Fore.GREEN,f"处理完成更新状态为 2,",Style.RESET_ALL)
