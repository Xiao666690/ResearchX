import tiktoken
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '../..', '.env')  # 假设 .env 文件在上一级目录
load_dotenv(dotenv_path=dotenv_path)

# httpx 0.27 (locked by this project) does not understand the socks5h URL
# scheme. Keep HTTP(S)_PROXY available, but ignore this unsupported fallback.
if os.environ.get("ALL_PROXY", "").lower().startswith("socks5h://"):
    os.environ.pop("ALL_PROXY", None)


class LLM:
    def __init__(self):
        self.llms = {}

        # OpenAI (保留兼容)
        if os.getenv("OPENAI_API_KEY"):
            self.llms['openai'] = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_API_BASE") or None,
                default_headers={"x-foo": "true"}
            )

        # DeepSeek
        if not os.getenv("DEEPSEEK_API_KEY"):
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        self.llms['deepseek'] = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base=os.getenv("DEEPSEEK_API_BASE"),
        )

        # Kimi K3 (Moonshot)
        if os.getenv("KIMI_API_KEY"):
            self.llms['kimi'] = ChatOpenAI(
                model=os.getenv("KIMI_MODEL", "kimi-k3"),
                temperature=1,
                openai_api_key=os.getenv("KIMI_API_KEY"),
                openai_api_base=os.getenv("KIMI_API_BASE"),
            )

        # Zhipu AI / GLM（OpenAI-compatible）
        if os.getenv("ZHIPU_API_KEY"):
            self.llms['zhipu'] = ChatOpenAI(
                model=os.getenv("ZHIPU_MODEL", "glm-4-flash"),
                openai_api_key=os.getenv("ZHIPU_API_KEY"),
                openai_api_base=os.getenv(
                    "ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/"
                ),
            )

        self.tokenizer = tiktoken.encoding_for_model('gpt-4o')
        self.chatllm = self.llms['deepseek']

    def get_llm(self, name):
        return self.llms.get(name, self.llms['deepseek'])

    def get_all_llms(self):
        return self.llms

    def count_doc_token(self, text):
        return len(self.tokenizer.encode(text))

    ## 将提示词发送给大模型，获取回复
    def chat_with_llm(self, chat_prompt):
        print(chat_prompt)
        max_retries = 5
        retries = 0
        while retries < max_retries:
            try:
                response = self.chatllm.invoke(chat_prompt)
                return response
            except Exception:
                retries += 1
                if retries == max_retries:
                    print("Max retries reached. Exiting...")
                    return None
                print(f"Retrying... (Attempt {retries})")

    def get_stream_llm(self, model_name='deepseek'):
        """获取用于流式输出的 LLM"""
        if model_name == 'deepseek':
            return ChatOpenAI(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                streaming=True,
                openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
                openai_api_base=os.getenv("DEEPSEEK_API_BASE"),
            )
        elif model_name == 'kimi':
            if not os.getenv("KIMI_API_KEY"):
                return self.get_stream_llm('deepseek')
            return ChatOpenAI(
                model=os.getenv("KIMI_MODEL", "kimi-k3"),
                streaming=True,
                temperature=1,
                openai_api_key=os.getenv("KIMI_API_KEY"),
                openai_api_base=os.getenv("KIMI_API_BASE"),
            )
        elif model_name == 'openai':
            if not os.getenv("OPENAI_API_KEY"):
                return self.get_stream_llm('deepseek')
            return ChatOpenAI(
                model="gpt-4o-mini",
                streaming=True,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_API_BASE") or None,
                default_headers={"x-foo": "true"}
            )
        elif model_name == 'zhipu':
            if not os.getenv("ZHIPU_API_KEY"):
                return self.get_stream_llm('deepseek')
            return ChatOpenAI(
                model=os.getenv("ZHIPU_MODEL", "glm-4-flash"),
                streaming=True,
                openai_api_key=os.getenv("ZHIPU_API_KEY"),
                openai_api_base=os.getenv(
                    "ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4/"
                ),
            )
        else:
            # 默认返回 deepseek
            return self.get_stream_llm('deepseek')
