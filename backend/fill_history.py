import os
import sys
import time
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, init_db
from models import News
from services.translator import Translator
from config import CATEGORY_CONFIG, NOISE_KEYWORDS

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
CN_TZ = timezone(timedelta(hours=8))

def cn_now():
    return datetime.now(CN_TZ)

def classify_category(title, content=''):
    text = (title + ' ' + content).lower()
    for kw in NOISE_KEYWORDS:
        if kw.lower() in text:
            return None
    
    for cat, config in CATEGORY_CONFIG.items():
        for kw in config.get('strict_keywords', []):
            if kw.lower() in text:
                return {'category': cat, 'label': config['label'], 'emoji': config['emoji']}
    
    for cat, config in CATEGORY_CONFIG.items():
        matches = sum(1 for kw in config['keywords'] if kw.lower() in text)
        if matches >= 2:
            return {'category': cat, 'label': config['label'], 'emoji': config['emoji']}
    
    return {'category': 'industry', 'label': CATEGORY_CONFIG['industry']['label'], 'emoji': CATEGORY_CONFIG['industry']['emoji']}

def fetch_arxiv_for_date(target_date, max_results=10):
    articles = []
    start_date = datetime.combine(target_date, datetime.min.time())
    end_date = start_date + timedelta(days=1)
    
    start_str = start_date.strftime('%Y%m%d%H%M%S')
    end_str = end_date.strftime('%Y%m%d%H%M%S')
    
    url = f'http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending'
    
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                try:
                    published_str = entry.find('atom:published', ns).text
                    published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    
                    item_date = published.astimezone(CN_TZ).date()
                    if item_date != target_date:
                        continue
                    
                    title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
                    summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()[:1000]
                    link = entry.find('atom:id', ns).text
                    
                    articles.append({
                        'title': title,
                        'content': summary,
                        'url': link,
                        'source': 'ArXiv CS.AI',
                        'published': published,
                        'trust_level': 'S'
                    })
                except Exception as e:
                    pass
    except Exception as e:
        print(f"    ArXiv API error: {e}")
    
    return articles

def fetch_hackernews_for_date(target_date, limit=10):
    articles = []
    
    try:
        resp = requests.get('https://hn.algolia.com/api/v1/search?query=AI&tags=story&numericFilters=created_at_i>0&hitsPerPage=50', timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            count = 0
            for hit in data.get('hits', []):
                if count >= limit:
                    break
                
                created_str = hit.get('created_at', '')
                if not created_str:
                    continue
                
                created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                item_date = created.astimezone(CN_TZ).date()
                
                if item_date != target_date:
                    continue
                
                title = hit.get('title', '')
                if not title:
                    continue
                
                url = hit.get('url', '') or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                
                articles.append({
                    'title': title,
                    'content': hit.get('story_text', '')[:1000],
                    'url': url,
                    'source': 'Hacker News',
                    'published': created,
                    'trust_level': 'A'
                })
                count += 1
    except Exception as e:
        print(f"    HackerNews API error: {e}")
    
    return articles

def fetch_reddit_for_date(target_date, subreddit='LocalLLaMA', limit=5):
    articles = []
    
    try:
        url = f'https://www.reddit.com/r/{subreddit}/hot/.json?limit=25'
        headers = {'User-Agent': 'LiveNewsAI/1.0'}
        resp = requests.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            count = 0
            for post in data.get('data', {}).get('children', []):
                if count >= limit:
                    break
                
                post_data = post.get('data', {})
                created_utc = post_data.get('created_utc', 0)
                created = datetime.fromtimestamp(created_utc, tz=CN_TZ)
                item_date = created.date()
                
                if item_date != target_date:
                    continue
                
                title = post_data.get('title', '')
                if not title:
                    continue
                
                articles.append({
                    'title': title,
                    'content': post_data.get('selftext', '')[:1000],
                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'source': f'Reddit {subreddit}',
                    'published': created,
                    'trust_level': 'A'
                })
                count += 1
    except Exception as e:
        print(f"    Reddit API error: {e}")
    
    return articles

def translate_and_prepare(article, translator):
    title = article.get('title', '')
    content = article.get('content', '')
    
    is_chinese = any('\u4e00' <= c <= '\u9fff' for c in title)
    
    if is_chinese:
        title_zh = title
        translated_text = content
    else:
        try:
            if title:
                title_zh = translator.translate_title(title)
                time.sleep(3)
            else:
                title_zh = title
            if content:
                translated_text = translator.translate_text(content[:2000])
                time.sleep(3)
            else:
                translated_text = ''
        except Exception as e:
            print(f"      Translation error: {e}")
            title_zh = title
            translated_text = content
    
    if not title_zh:
        title_zh = title
    if not translated_text:
        translated_text = content
    
    return title_zh, translated_text

def main():
    print("=" * 60)
    print("历史数据补全脚本")
    print("=" * 60)
    
    init_db()
    translator = Translator()
    
    today = datetime.now(CN_TZ).date()
    dates_to_fill = [today - timedelta(days=i) for i in range(1, 8)]
    
    print(f"目标日期: {[str(d) for d in dates_to_fill]}")
    print()
    
    for target_date in dates_to_fill:
        print(f"\n{'='*60}")
        print(f"处理日期: {target_date}")
        print("-" * 60)
        
        db = SessionLocal()
        try:
            existing_count = db.query(News).filter(News.news_date == target_date).count()
            print(f"  当前有 {existing_count} 条新闻")
        finally:
            db.close()
        
        all_articles = []
        
        print("  抓取数据源:")
        
        arxiv_articles = fetch_arxiv_for_date(target_date, max_results=10)
        all_articles.extend(arxiv_articles)
        print(f"    ArXiv: {len(arxiv_articles)} 篇")
        time.sleep(2)
        
        hn_articles = fetch_hackernews_for_date(target_date, limit=10)
        all_articles.extend(hn_articles)
        print(f"    HackerNews: {len(hn_articles)} 篇")
        time.sleep(2)
        
        for sub in ['LocalLLaMA', 'ChatGPT', 'MachineLearning']:
            reddit_articles = fetch_reddit_for_date(target_date, subreddit=sub, limit=5)
            all_articles.extend(reddit_articles)
            print(f"    Reddit {sub}: {len(reddit_articles)} 篇")
            time.sleep(2)
        
        print(f"\n  共抓取 {len(all_articles)} 篇文章")
        
        if not all_articles:
            print("  没有找到新闻")
            continue
        
        db = SessionLocal()
        try:
            existing_urls = set(
                row[0] for row in db.query(News.source_url).filter(News.news_date == target_date).all()
            )
            
            new_count = 0
            for idx, article in enumerate(all_articles):
                url = article.get('url', '')
                if url in existing_urls:
                    continue
                
                print(f"  [{idx+1}/{len(all_articles)}] 翻译: {article.get('title', '')[:40]}...")
                
                title_zh, translated_text = translate_and_prepare(article, translator)
                
                category_info = classify_category(article.get('title', ''), article.get('content', ''))
                if not category_info:
                    continue
                
                published = article.get('published')
                if published is None:
                    published = datetime.now(CN_TZ)
                
                news = News(
                    title=article.get('title', ''),
                    title_zh=title_zh,
                    original_text=article.get('content', ''),
                    translated_text=translated_text,
                    category=category_info['category'],
                    category_label=category_info['label'],
                    category_emoji=category_info['emoji'],
                    source=article.get('source', 'Unknown'),
                    source_url=url,
                    published_at=published,
                    trust_level=article.get('trust_level', 'B'),
                    multi_source_verified=False,
                    ai_warning=None,
                    news_date=target_date
                )
                db.add(news)
                new_count += 1
                existing_urls.add(url)
            
            db.commit()
            total_count = db.query(News).filter(News.news_date == target_date).count()
            print(f"\n  保存了 {new_count} 条新闻，当前日期共 {total_count} 条")
        finally:
            db.close()
        
        print()
    
    print("\n" + "=" * 60)
    print("历史数据补全完成!")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        print("\n各日期新闻数量:")
        for target_date in sorted(dates_to_fill, reverse=True):
            count = db.query(News).filter(News.news_date == target_date).count()
            print(f"  {target_date}: {count} 条")
    finally:
        db.close()

if __name__ == '__main__':
    main()
