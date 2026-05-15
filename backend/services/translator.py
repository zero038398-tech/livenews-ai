import re
import time
from groq import Groq
from config import GROQ_API_KEY

TITLE_SYSTEM_PROMPT = (
    "You are a professional title translator. "
    "Translate the given title to Simplified Chinese (简体中文). "
    "Rules: 1) Translate word-by-word faithfully, do NOT add any content not in the original. "
    "2) Keep the translated title concise, similar length to the original. "
    "3) Do NOT expand, explain, or elaborate. "
    "4) Use Simplified Chinese only, never Traditional Chinese. "
    "5) Output ONLY the translated Chinese title, nothing else."
)

TEXT_SYSTEM_PROMPT = (
    "You are a professional translator. "
    "Translate the given text to Simplified Chinese (简体中文). "
    "Rules: 1) Translate faithfully, do NOT add any content not in the original. "
    "2) Do NOT expand, explain, summarize, or elaborate. "
    "3) If the original is short, the translation must also be short. "
    "4) Use Simplified Chinese only, never Traditional Chinese. "
    "5) Always use third person, never translate to first person (e.g. 'Parloa leverages' -> 'Parloa使用', NOT '我使用'). "
    "6) Output ONLY the translated Chinese text, nothing else."
)

SUMMARY_SYSTEM_PROMPT = (
    "You are a professional AI news summarizer. "
    "Summarize the given text into Simplified Chinese (简体中文) in under 200 characters. "
    "Rules: 1) Extract the core technical point: what problem was solved, what method was used, what was the result. "
    "2) Ignore greetings, jokes, meta-comments, and off-topic content. "
    "3) Use Simplified Chinese only, never Traditional Chinese. "
    "4) Keep it concise and factual, under 200 characters. "
    "5) Output ONLY the summary, nothing else."
)


class Translator:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def _call_groq(self, system_prompt: str, text: str, max_tokens: int = 1024, retries: int = 3) -> str:
        if not self.client:
            return ''
        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.1,
                    max_tokens=max_tokens
                )
                result = response.choices[0].message.content.strip()
                return result
            except Exception as e:
                print(f"  Translation error (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"  Retrying in {wait}s...")
                    time.sleep(wait)
        print(f"  All retries failed for: {text[:50]}...")
        return ''

    def _clean_translation(self, translated: str) -> str:
        if not translated:
            return ''
        translated = re.sub(r'^["\']|["\']$', '', translated.strip())
        prefixes = [
            '翻译：', '翻译:', '标题翻译：', '标题翻译:',
            '中文翻译：', '中文翻译:', '中文：', '中文:',
            'Translation:', 'Chinese:', 'Title:',
        ]
        for prefix in prefixes:
            if translated.startswith(prefix):
                translated = translated[len(prefix):].strip()
        return translated

    def _validate_title_translation(self, translated: str, original: str) -> str:
        if not translated or not original:
            return ''
        zh_chars = len(re.findall(r'[\u4e00-\u9fff]', translated))
        if zh_chars == 0:
            return ''
        en_words = len(original.split())
        if en_words > 0 and zh_chars > en_words * 4:
            print(f"  Title hallucination detected: {zh_chars} zh chars for {en_words} en words")
            return ''
        if '\n' in translated and len(translated.split('\n')) > 2:
            print(f"  Title hallucination detected: multi-line expansion")
            return ''
        list_marker_pattern = re.compile(r'(?:^|\n)\s*(?:[1-9][.)]|[•])\s')
        if en_words < 10 and list_marker_pattern.search(translated):
            print(f"  Title hallucination detected: list markers in short title")
            return ''
        return translated

    def _validate_text_translation(self, translated: str, original: str) -> str:
        if not translated or not original:
            return ''
        zh_chars = len(re.findall(r'[\u4e00-\u9fff]', translated))
        if zh_chars == 0:
            return ''
        en_words = len(original.split())
        if en_words > 0 and zh_chars > en_words * 5:
            print(f"  Text hallucination detected: {zh_chars} zh chars for {en_words} en words")
            return ''
        return translated

    def translate_title(self, title: str) -> str:
        if not title:
            return ''
        translated = self._call_groq(TITLE_SYSTEM_PROMPT, title, max_tokens=256)
        translated = self._clean_translation(translated)
        translated = self._validate_title_translation(translated, title)
        return translated

    def translate_text(self, text: str) -> str:
        if not text:
            return ''
        translated = self._call_groq(TEXT_SYSTEM_PROMPT, text, max_tokens=2048)
        translated = self._clean_translation(translated)
        translated = self._validate_text_translation(translated, text)
        return translated

    def summarize_text(self, text: str) -> str:
        if not text:
            return ''
        summarized = self._call_groq(SUMMARY_SYSTEM_PROMPT, text, max_tokens=512)
        summarized = self._clean_translation(summarized)
        if summarized:
            zh_chars = len(re.findall(r'[\u4e00-\u9fff]', summarized))
            if zh_chars == 0:
                return ''
            if len(summarized) > 400:
                summarized = summarized[:400]
        return summarized
