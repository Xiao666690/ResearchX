import json
import os
import fitz
from langchain_community.document_loaders import PyPDFLoader
from rich.progress import Progress

from core.llm import myprompts
from core.utils.util import cal_file_md5, check_and_parse_json, split_text_into_chunks
import time

from core.vectordb.chromadb import AcadeChroma


class DataProcessAgent:
    def __init__(self,llm,chromadb):
        self.llm=llm
        self.chromadb:AcadeChroma=chromadb
        self.sqlitconnect=None

    # 将新的论文增加到layer1和layer2
    def add_newpaper(self,filepath,knowledgeID):
        file_hash = cal_file_md5(filepath)
        doc = fitz.open(filepath)
        chunks = []
        chunksMetadataList = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if text:
                for chunk in split_text_into_chunks(text):
                    chunks.append(chunk)
                    metadata = {
                        'source': filepath,
                        'documentID': file_hash,
                        'knowledge_name': knowledgeID,
                        'page_number': page_num + 1
                    }
                    chunksMetadataList.append(metadata)
        print(chunksMetadataList[0])
        self.chromadb.add_paper_to_layer1(chunks, chunksMetadataList)

        
        # 调用大模型的RAG进行论文摘要,并将摘要存储到layer2
        json_paper = self.summarize_paper(filepath)
        if not isinstance(json_paper, dict):
            # 摘要是增强信息；模型服务暂时不可用时仍应完成正文索引。
            first_page = doc.load_page(0).get_text("text").strip()
            json_paper = {
                "Abstract": first_page[:1200] or "PDF 已完成正文索引。",
                "Primary Classification": "Computer Science",
                "Secondary Classification": "Unclassified",
                "Research Direction Tags": [],
            }
        metadataofpaper={
            "source":filepath,
            "Primary Classification":json_paper["Primary Classification"],# 二级分类
            "Secondary Classification":json_paper["Secondary Classification"], #一级分类
            "documentID":file_hash, #文件的hash
            "knowledgeID":knowledgeID, #所在的知识库
            }
        self.chromadb.add_paper_to_layer2([json.dumps(json_paper, indent=2)], [metadataofpaper])
        return {
            "Primary Classification":json_paper["Primary Classification"],# 二级分类
            "Secondary Classification":json_paper["Secondary Classification"], #一级分类
            "Research Direction Tags":json_paper["Research Direction Tags"], #标签
            "Abstract":json_paper["Abstract"], #摘要
            "documentVector":len(chunksMetadataList) #向量数
        }
        # todo 将摘要存储到数据库中
    def batch_add_newpaper(self, dir,knowledgeID):
        with Progress() as progress:
            task = progress.add_task("[green]Processing files", total=len(os.listdir(dir)))
            for file_name in os.listdir(dir):
                # 进行文件处理操作
                file_path = os.path.join(dir, file_name)       
                progress.update(task, advance=1, description=f"[cyan]processing ... {file_name}")
                # 执行其他操作，例如添加文章
                self.add_newpaper(file_path,knowledgeID)
                # 更新进度条

            print("[bold green]Batch processing completed!")

        # 完成后显示完成信息
        print("[bold green]Batch processing completed!")

    def summarize_paper(self,filename):
        ## 获得retriver
        start_time = time.time()

        fileRetriver = self.chromadb.chroma_db_layer1.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3, 'filter': {'source': filename}},
        )

        ## 检索出论文相关内容
        docs = fileRetriver.batch(["Retrieve detailed information about the document's key contributions, innovative methods, experimental results, thorough analysis, and significant advancements."])
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time} seconds")
        call_prompt = myprompts.SUMMRISE_TEMPLET.format(context=docs[0])
        print(f"Summary prompt length: {len(call_prompt)}")


       # print(len(prompt))
        max_retries = 5
        retries = 0
        while retries < max_retries:
            try:
                response = self.llm.chat_with_llm(call_prompt)
                if check_and_parse_json(response.content)!=None:
                    break
                print("Summary response was not valid JSON")
            except Exception:
                retries += 1
                if retries == max_retries:
                    print("Max retries reached. Exiting...")
                    return None
                print(f"Retrying... (Attempt {retries})")
        return check_and_parse_json(response.content)
    




