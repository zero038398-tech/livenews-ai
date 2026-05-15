import requests
import feedparser
import re
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import List, Dict
from config import NEWS_SOURCES, CATEGORY_CONFIG, NOISE_KEYWORDS, MAX_DAILY_NEWS
from models import News
from database import SessionLocal

AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'machine learning', 'deep learning',
    'neural network', 'llm', 'large language model', 'gpt', 'chatgpt',
    'claude', 'gemini', 'transformer', 'diffusion', 'generative',
    'nlp', 'computer vision', 'reinforcement learning', 'agi',
    '人工智能', '大模型', '深度学习', '机器学习', '神经网络',
    'openai', 'anthropic', 'deepmind', 'nvidia', 'chip', 'gpu',
    'copilot', 'robot', 'autonomous', 'chatbot', 'embedding',
    'fine-tun', 'rag', 'mcp', 'agent', 'model', 'inference',
    'training', 'accelerator', 'semiconductor', 'tsmc', 'datacenter',
    '推理', '训练', '算力', '芯片', '开源', '智能',
]

CHIP_COMPANY_KEYWORDS = [
    'chip', 'gpu', 'nvidia', 'amd', 'intel', 'tsmc', 'semiconductor',
    'accelerator', 'tpu', 'npu', 'inference', 'training', 'datacenter',
    'wafer', 'fab', 'compute', 'hardware', 'silicon', 'memory', 'hbm',
    '芯片', 'GPU', '算力', '推理', '训练', '数据中心', '硬件',
    'cerebras', 'groq', 'samba', 'tenstorrent', 'blackwell', 'gaudi',
    'mi300', 'mi400', 'colossus', 'quantum', 'edge ai',
]


class NewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _is_ai_related(self, text: str) -> bool:
        text_lower = text.lower()
        return any(self._keyword_match(text_lower, kw) for kw in AI_KEYWORDS)

    def _is_noise(self, text: str) -> bool:
        text_lower = text.lower()
        return any(self._keyword_match(text_lower, kw) for kw in NOISE_KEYWORDS)

    def _compute_relevance_score(self, item: Dict, source_key: str) -> float:
        score = 0.0
        source = NEWS_SOURCES.get(source_key, {})
        score += source.get('priority', 5) * 2

        text = (item.get('title', '') + ' ' + item.get('content', '')).lower()

        for kw in CHIP_COMPANY_KEYWORDS:
            if self._keyword_match(text, kw):
                score += 5

        cat_info = item.get('category', {})
        if cat_info.get('category') == 'chip':
            score += 4
        elif cat_info.get('category') == 'tool':
            score += 3
        elif cat_info.get('category') == 'academic':
            score += 2

        if source.get('trust_level') == 'S':
            score += 3

        if item.get('url') and 'arxiv' in item.get('url', ''):
            score += 1

        return score

    def scrape_rss(self, source_key: str) -> List[Dict]:
        source = NEWS_SOURCES.get(source_key)
        if not source or source['type'] != 'rss':
            return []

        try:
            resp = self.session.get(source['url'], timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            items = []

            for entry in feed.entries[:20]:
                title = self._clean_text(entry.get('title', ''))
                content = self._clean_text(entry.get('summary', entry.get('description', '')))
                url = entry.get('link', '')

                if not title or not content:
                    continue

                if self._is_noise(title + ' ' + content):
                    continue

                if not self._is_ai_related(title + ' ' + content):
                    continue

                cat_info = self._categorize(title + ' ' + content)

                item = {
                    'title': title,
                    'content': content[:3000],
                    'url': url,
                    'published': self._parse_date(entry.get('published', '')),
                    'source': source['name'],
                    'category': cat_info,
                    'trust_level': source['trust_level']
                }
                items.append(item)

            return items
        except Exception as e:
            print(f"Error scraping {source_key}: {e}")
            return []

    def scrape_arxiv(self) -> List[Dict]:
        source = NEWS_SOURCES.get('arxiv')
        if not source:
            return []

        try:
            resp = self.session.get(source['url'], timeout=20)
            resp.raise_for_status()

            root = ET.fromstring(resp.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            items = []

            for entry in root.findall('atom:entry', ns)[:15]:
                title_el = entry.find('atom:title', ns)
                summary_el = entry.find('atom:summary', ns)
                link_el = entry.find('atom:id', ns)
                published_el = entry.find('atom:published', ns)

                title = self._clean_text(title_el.text if title_el is not None else '')
                content = self._clean_text(summary_el.text if summary_el is not None else '')
                url = link_el.text.strip() if link_el is not None else ''

                if not title:
                    continue

                cat_info = self._categorize(title + ' ' + content)

                item = {
                    'title': title,
                    'content': content[:3000],
                    'url': url,
                    'published': self._parse_date(published_el.text if published_el is not None else ''),
                    'source': source['name'],
                    'category': cat_info,
                    'trust_level': source['trust_level']
                }
                items.append(item)

            return items
        except Exception as e:
            print(f"Error scraping arxiv: {e}")
            return []

    def scrape_all(self) -> List[Dict]:
        all_news = []
        seen_urls = set()

        for source_key in NEWS_SOURCES.keys():
            if source_key == 'arxiv':
                items = self.scrape_arxiv()
            else:
                items = self.scrape_rss(source_key)

            for item in items:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    item['_source_key'] = source_key
                    item['_score'] = self._compute_relevance_score(item, source_key)
                    all_news.append(item)

        all_news.sort(key=lambda x: x.get('_score', 0), reverse=True)

        selected = all_news[:MAX_DAILY_NEWS]

        for item in selected:
            item.pop('_source_key', None)
            item.pop('_score', None)

        print(f"Scraped {len(all_news)} AI news, selected top {len(selected)} by relevance")
        return selected

    def _clean_text(self, text: str) -> str:
        if not text:
            return ''
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()[:5000]

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now()
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                return datetime.now()

    def _keyword_match(self, text_lower: str, keyword: str) -> bool:
        kw_lower = keyword.lower()
        idx = text_lower.find(kw_lower)
        if idx == -1:
            return False
        if len(kw_lower) <= 2:
            return True
        before_ok = idx == 0 or not text_lower[idx - 1].isalpha()
        after_idx = idx + len(kw_lower)
        after_ok = after_idx >= len(text_lower) or not text_lower[after_idx].isalpha()
        if before_ok and after_ok:
            return True
        if before_ok and after_idx < len(text_lower) and text_lower[after_idx] in '._-':
            return True
        return False

    def _categorize(self, text: str) -> Dict:
        text_lower = text.lower()

        for cat_key, config in CATEGORY_CONFIG.items():
            strict_kws = config.get('strict_keywords', [])
            for keyword in strict_kws:
                if self._keyword_match(text_lower, keyword):
                    return {
                        'category': cat_key,
                        'label': config['label'],
                        'emoji': config['emoji']
                    }

        for cat_key, config in CATEGORY_CONFIG.items():
            for keyword in config['keywords']:
                if self._keyword_match(text_lower, keyword):
                    return {
                        'category': cat_key,
                        'label': config['label'],
                        'emoji': config['emoji']
                    }

        return {
            'category': 'industry',
            'label': CATEGORY_CONFIG['industry']['label'],
            'emoji': CATEGORY_CONFIG['industry']['emoji']
        }

    def save_to_db(self, news_items: List[Dict], translator=None):
        db = SessionLocal()
        try:
            today = date.today()
            saved_count = 0

            for item in news_items:
                existing = db.query(News).filter(
                    News.source_url == item['url'],
                    News.news_date == today
                ).first()

                if existing:
                    continue

                title_zh = item['title']
                translated_text = ''

                if translator and item.get('content'):
                    try:
                        title_zh = translator.translate_title(item['title'])
                        translated_text = translator.translate_text(item['content'][:2000])
                    except Exception as e:
                        print(f"Translation error for '{item['title'][:30]}...': {e}")

                is_chinese_source = any(c > '\u4e00' for c in item['title'])
                if is_chinese_source:
                    title_zh = item['title']
                    translated_text = item.get('content', '')

                news = News(
                    title=item['title'],
                    title_zh=title_zh,
                    original_text=item['content'],
                    translated_text=translated_text,
                    category=item['category']['category'],
                    category_label=item['category']['label'],
                    category_emoji=item['category']['emoji'],
                    source=item['source'],
                    source_url=item['url'],
                    published_at=item['published'],
                    trust_level=item['trust_level'],
                    multi_source_verified=False,
                    ai_warning='预印本提示：此论文来自ArXiv，未经同行评审' if item['source'] == 'ArXiv CS.AI' else None,
                    news_date=today
                )
                db.add(news)
                saved_count += 1

            db.commit()
            print(f"Saved {saved_count} new news items (skipped {len(news_items) - saved_count} duplicates)")
        except Exception as e:
            db.rollback()
            print(f"Error saving to DB: {e}")
        finally:
            db.close()
