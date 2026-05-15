import re
from groq import Groq
from config import GROQ_API_KEY

TITLE_SYSTEM_PROMPT = (
    "You are a professional title translator. "
    "Translate the given title to Chinese. "
    "Rules: 1) Translate word-by-word faithfully, do NOT add any content not in the original. "
    "2) Keep the translated title concise, similar length to the original. "
    "3) Do NOT expand, explain, or elaborate. "
    "4) Output ONLY the translated Chinese title, nothing else."
)

TEXT_SYSTEM_PROMPT = (
    "You are a professional translator. "
    "Translate the given text to Chinese. "
    "Rules: 1) Translate faithfully, do NOT add any content not in the original. "
    "2) Do NOT expand, explain, summarize, or elaborate. "
    "3) If the original is short, the translation must also be short. "
    "4) Output ONLY the translated Chinese text, nothing else."
)


class Translator:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def _call_groq(self, system_prompt: str, text: str, max_tokens: int = 1024) -> str:
        if not self.client:
            return text
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
            print(f"Translation error: {e}")
            return text

    def _clean_translation(self, translated: str, original: str) -> str:
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
            return original
        zh_chars = len(re.findall(r'[\u4e00-\u9fff]', translated))
        en_words = len(original.split())
        if en_words > 0 and zh_chars > en_words * 4:
            print(f"  Title hallucination detected: {zh_chars} zh chars for {en_words} en words, using original")
            return original
        if '\n' in translated and len(translated.split('\n')) > 2:
            print(f"  Title hallucination detected: multi-line expansion, using original")
            return original
        if any(marker in translated for marker in ['1.', '2.', '3.', '1)', '2)', '3)', '•', '- ']):
            if en_words < 10:
                print(f"  Title hallucination detected: list markers in short title, using original")
                return original
        return translated

    def _validate_text_translation(self, translated: str, original: str) -> str:
        if not translated or not original:
            return original
        zh_chars = len(re.findall(r'[\u4e00-\u9fff]', translated))
        en_words = len(original.split())
        if en_words > 0 and zh_chars > en_words * 5:
            print(f"  Text hallucination detected: {zh_chars} zh chars for {en_words} en words, using original")
            return original
        return translated

    def translate_title(self, title: str) -> str:
        if not title:
            return title
        translated = self._call_groq(TITLE_SYSTEM_PROMPT, title, max_tokens=256)
        translated = self._clean_translation(translated, title)
        translated = self._validate_title_translation(translated, title)
        return translated

    def translate_text(self, text: str) -> str:
        if not text:
            return text
        translated = self._call_groq(TEXT_SYSTEM_PROMPT, text, max_tokens=2048)
        translated = self._clean_translation(translated, title='')
        translated = self._validate_text_translation(translated, text)
        return translated

    def translate(self, text: str, target_lang: str = 'Chinese') -> str:
        return self.translate_text(text)

    def translate_batch(self, texts: list) -> list:
        return [self.translate_text(text) for text in texts]
