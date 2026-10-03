
"""Offline English-to-Chinese translation for selected PDF passages."""

from functools import lru_cache
import re


@lru_cache(maxsize=1)
def _english_to_chinese():
    import argostranslate.translate

    languages = {lang.code: lang for lang in argostranslate.translate.get_installed_languages()}
    if "en" not in languages or "zh" not in languages:
        raise RuntimeError("离线英中翻译模型未安装，请运行 scripts/install_offline_translation.py")
    translation = languages["en"].get_translation(languages["zh"])
    if translation is None:
        raise RuntimeError("离线英中翻译模型未安装，请运行 scripts/install_offline_translation.py")
    return translation


class Translator:
    def __init__(self, from_lang="en", to_lang="zh"):
        if (from_lang, to_lang) != ("en", "zh"):
            raise ValueError("目前仅支持离线英文翻译为简体中文")

    def translate(self, text: str) -> str:
        source = re.sub(r"-\s*\r?\n\s*", "", text.replace("\u00ad", ""))
        source = " ".join(source.split())
        if not source:
            return ""
        translation = _english_to_chinese()
        chunks: list[str] = []
        current = ""
        for sentence in re.split(r"(?<=[.!?;])\s+", source):
            if len(current) + len(sentence) + 1 <= 1200:
                current = f"{current} {sentence}".strip()
                continue
            if current:
                chunks.append(current)
                current = ""
            if len(sentence) <= 1200:
                current = sentence
                continue
            words = sentence.split()
            for word in words:
                if len(current) + len(word) + 1 > 1200 and current:
                    chunks.append(current)
                    current = ""
                current = f"{current} {word}".strip()
        if current:
            chunks.append(current)
        return "\n\n".join(translation.translate(chunk) for chunk in chunks)
