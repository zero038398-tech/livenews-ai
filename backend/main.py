import os
import uuid
import threading
import time
from pathlib import Path
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date as date_type, datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from database import get_db, init_db
from models import News
from services.scraper import NewsScraper
from services.translator import Translator
from config import NEWS_SOURCES

CN_TZ = timezone(timedelta(hours=8))

def cn_today():
    return datetime.now(CN_TZ).date()

app = FastAPI(title="LiveNews AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_and_translate(target_date=None):
    print(f"[{datetime.now()}] Starting news fetch + translate...")
    try:
        scraper = NewsScraper()
        translator = Translator()
        news_items = scraper.scrape_all()
        print(f"Scraped {len(news_items)} AI-related news items")

        if target_date is None:
            target_date = cn_today()

        prepared_items = []
        for idx, item in enumerate(news_items):
            is_chinese = any('\u4e00' <= c <= '\u9fff' for c in item['title'])
            source_type = NEWS_SOURCES.get(item.get('_source_key', ''), {}).get('content_type', 'official')

            if is_chinese:
                title_zh = item['title']
                translated_text = item.get('content', '')
            else:
                title_zh = ''
                translated_text = ''
                try:
                    if item.get('title'):
                        title_zh = translator.translate_title(item['title'])
                        time.sleep(3)
                    if item.get('content'):
                        if source_type in ('community', 'social', 'video'):
                            translated_text = translator.summarize_text(item['content'][:3000])
                        else:
                            translated_text = translator.translate_text(item['content'][:2000])
                        time.sleep(3)
                except Exception as e:
                    print(f"  Translation error for '{item['title'][:30]}...': {e}")

                if not title_zh:
                    title_zh = item['title']
                if not translated_text:
                    translated_text = ''

            prepared_items.append({
                'title': item['title'],
                'title_zh': title_zh,
                'original_text': item['content'],
                'translated_text': translated_text,
                'category': item['category']['category'],
                'category_label': item['category']['label'],
                'category_emoji': item['category']['emoji'],
                'source': item['source'],
                'source_url': item['url'],
                'published_at': item['published'],
                'trust_level': item['trust_level'],
                'ai_warning': '预印本提示：此论文来自ArXiv，未经同行评审' if item['source'] == 'ArXiv CS.AI' else None,
                'news_date': target_date,
            })

            print(f"  Prepared {idx+1}/{len(news_items)}: {item['title'][:40]}...")

        db = next(get_db())
        try:
            existing_urls = set(
                row[0] for row in db.query(News.source_url).filter(News.news_date == target_date).all()
            )
            new_count = 0
            for item in prepared_items:
                if item['source_url'] in existing_urls:
                    continue
                news = News(
                    title=item['title'],
                    title_zh=item['title_zh'],
                    original_text=item['original_text'],
                    translated_text=item['translated_text'],
                    category=item['category'],
                    category_label=item['category_label'],
                    category_emoji=item['category_emoji'],
                    source=item['source'],
                    source_url=item['source_url'],
                    published_at=item['published_at'],
                    trust_level=item['trust_level'],
                    multi_source_verified=False,
                    ai_warning=item['ai_warning'],
                    news_date=item['news_date']
                )
                db.add(news)
                new_count += 1
            db.commit()
            print(f"[{datetime.now()}] Done: saved {new_count} new items for {target_date}")
        finally:
            db.close()
    except Exception as e:
        print(f"Error in fetch_and_translate: {e}")


def translate_untranslated_news():
    print(f"[{datetime.now()}] Starting translation of untranslated news...")
    try:
        db = next(get_db())
        untranslated = db.query(News).filter(
            (News.translated_text == None) | (News.translated_text == '')
        ).limit(30).all()

        if not untranslated:
            print("No untranslated news found")
            db.close()
            return

        translator = Translator()
        count = 0
        for news in untranslated:
            try:
                is_chinese = any('\u4e00' <= c <= '\u9fff' for c in news.title)
                is_community = any(kw in news.source.lower() for kw in ['reddit', 'twitter', 'youtube', 'github', 'trending'])
                if is_chinese:
                    news.title_zh = news.title
                    news.translated_text = news.original_text
                else:
                    if news.title:
                        news.title_zh = translator.translate_title(news.title)
                        time.sleep(3)
                    if news.original_text:
                        if is_community:
                            news.translated_text = translator.summarize_text(news.original_text[:3000])
                        else:
                            news.translated_text = translator.translate_text(news.original_text[:2000])
                        time.sleep(3)
                count += 1
                if count % 5 == 0:
                    db.commit()
                    print(f"  Translated {count}/{len(untranslated)}")
            except Exception as e:
                print(f"  Translation error for '{news.title[:30]}...': {e}")
                continue

        db.commit()
        db.close()
        print(f"[{datetime.now()}] Translation completed: {count} items")
    except Exception as e:
        print(f"Error in translation: {e}")


def background_fetch():
    thread = threading.Thread(target=fetch_and_translate, daemon=True)
    thread.start()


def cleanup_old_news():
    try:
        db = next(get_db())
        cutoff_date = cn_today() - timedelta(days=7)
        deleted = db.query(News).filter(News.news_date < cutoff_date).delete(synchronize_session=False)
        db.commit()
        db.close()
        if deleted > 0:
            print(f"[{datetime.now()}] Cleaned up {deleted} news items older than 7 days")
    except Exception as e:
        print(f"Error cleaning up old news: {e}")


@app.on_event("startup")
def startup_event():
    init_db()

    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_translate, 'interval', hours=2, id='fetch_news')
    scheduler.add_job(translate_untranslated_news, 'interval', hours=1, id='translate_news')
    scheduler.add_job(cleanup_old_news, 'interval', hours=24, id='cleanup_news')
    scheduler.start()
    print("Scheduler started: fetch+translate every 2h, translate remaining every 1h, cleanup every 24h")

    db = next(get_db())
    today = cn_today()
    has_today_news = db.query(News).filter(News.news_date == today).first()
    db.close()

    if not has_today_news:
        background_fetch()


@app.get("/api/news")
def get_news(
    date: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(News)
    today = cn_today()
    query_date = today

    if date:
        try:
            query_date = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(News.news_date == query_date)
        except:
            query = query.filter(News.news_date == today)
    else:
        query = query.filter(News.news_date == today)

    if category and category != 'all':
        query = query.filter(News.category == category)

    news_items = query.order_by(News.published_at.desc()).limit(20).all()

    return {
        "success": True,
        "data": {
            "date": str(query_date),
            "news": [item.to_dict() for item in news_items],
            "categories": [
                {"value": "all", "label": "全部", "emoji": "📋"},
                {"value": "chip", "label": "AI芯片动态", "emoji": "🔴"},
                {"value": "tool", "label": "工具与实战", "emoji": "🟢"},
                {"value": "industry", "label": "行业动态", "emoji": "🔵"},
                {"value": "academic", "label": "学术精选", "emoji": "🟣"}
            ]
        }
    }


@app.post("/api/daily-summary")
def generate_daily_summary(
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    today = cn_today()
    if date:
        try:
            query_date = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            query_date = today
    else:
        query_date = today

    news_items = db.query(News).filter(News.news_date == query_date).all()

    if not news_items:
        return {"success": False, "error": "No news found for this date"}

    category_order = ["chip", "industry", "tool", "academic"]
    category_labels = {
        "chip": "AI芯片动态",
        "industry": "行业动态",
        "tool": "工具与实战",
        "academic": "学术精选"
    }

    grouped = {}
    for item in news_items:
        cat = item.category
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "title_zh": item.title_zh,
            "source": item.source,
            "source_url": item.source_url,
            "category_label": item.category_label
        })

    summary_data = []
    for cat_key in category_order:
        if cat_key in grouped and grouped[cat_key]:
            summary_data.append({
                "category": cat_key,
                "category_label": category_labels.get(cat_key, cat_key),
                "items": grouped[cat_key]
            })

    return {
        "success": True,
        "data": {
            "date": str(query_date),
            "summary_data": summary_data,
            "news_count": len(news_items),
            "generated_at": datetime.now().isoformat()
        }
    }


@app.get("/api/categories")
def get_categories():
    return [
        {"value": "all", "label": "全部", "emoji": "📋"},
        {"value": "chip", "label": "AI芯片动态", "emoji": "🔴"},
        {"value": "tool", "label": "工具与实战", "emoji": "🟢"},
        {"value": "industry", "label": "行业动态", "emoji": "🔵"},
        {"value": "academic", "label": "学术精选", "emoji": "🟣"}
    ]


@app.post("/api/admin/fetch-news")
def trigger_fetch_news():
    background_fetch()
    return {"success": True, "message": "News fetch + translate triggered in background"}


@app.post("/api/admin/translate")
def trigger_translate():
    thread = threading.Thread(target=translate_untranslated_news, daemon=True)
    thread.start()
    return {"success": True, "message": "Translation triggered in background"}


def reset_and_refetch():
    print(f"[{datetime.now()}] Resetting all data and re-fetching...")
    try:
        db = next(get_db())
        # 删除所有数据，更稳妥的方式
        while True:
            batch = db.query(News).limit(100).all()
            if not batch:
                break
            for item in batch:
                    db.delete(item)
            db.commit()
        count = db.query(News).count()  # 确认计数
        db.close()
        print(f"Deleted all old news items (remaining: {count})")
    except Exception as e:
        print(f"Error deleting news: {e}")
    fetch_and_translate()


@app.post("/api/admin/reset")
def trigger_reset():
    thread = threading.Thread(target=reset_and_refetch, daemon=True)
    thread.start()
    return {"success": True, "message": "Reset and re-fetch triggered in background"}


def fill_history_task():
    import time
    from datetime import datetime, timedelta, timezone
    import requests
    import feedparser
    from database import SessionLocal, init_db
    from models import News
    from services.translator import Translator
    from config import CATEGORY_CONFIG, NOISE_KEYWORDS
    
    CN_TZ = timezone(timedelta(hours=8))
    
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
                            'title': title, 'content': summary, 'url': link,
                            'source': 'ArXiv CS.AI', 'published': published, 'trust_level': 'S'
                        })
                    except:
                        pass
        except Exception as e:
            print(f"    ArXiv error: {e}")
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
                        'title': title, 'content': hit.get('story_text', '')[:1000], 'url': url,
                        'source': 'Hacker News', 'published': created, 'trust_level': 'A'
                    })
                    count += 1
        except Exception as e:
            print(f"    HN error: {e}")
        return articles
    
    def fetch_reddit_for_date(target_date, subreddit, limit=5):
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
                        'title': title, 'content': post_data.get('selftext', '')[:1000],
                        'url': f"https://reddit.com{post_data.get('permalink', '')}",
                        'source': f'Reddit {subreddit}', 'published': created, 'trust_level': 'A'
                    })
                    count += 1
        except Exception as e:
            print(f"    Reddit error: {e}")
        return articles
    
    def translate_item(title, content, translator):
        is_chinese = any('\u4e00' <= c <= '\u9fff' for c in title)
        if is_chinese:
            return title, content
        try:
            title_zh = translator.translate_title(title) if title else title
            time.sleep(3)
            text_zh = translator.translate_text(content[:2000]) if content else ''
            time.sleep(3)
            return title_zh or title, text_zh or content
        except:
            return title, content
    
    print("=" * 60)
    print("历史数据补全任务开始")
    print("=" * 60)
    
    init_db()
    translator = Translator()
    today = datetime.now(CN_TZ).date()
    dates_to_fill = [today - timedelta(days=i) for i in range(1, 8)]
    
    for target_date in dates_to_fill:
        print(f"\n处理日期: {target_date}")
        
        db = SessionLocal()
        try:
            existing_count = db.query(News).filter(News.news_date == target_date).count()
            print(f"  当前有 {existing_count} 条")
        finally:
            db.close()
        
        all_articles = []
        all_articles.extend(fetch_arxiv_for_date(target_date, 10))
        time.sleep(2)
        all_articles.extend(fetch_hackernews_for_date(target_date, 10))
        time.sleep(2)
        for sub in ['LocalLLaMA', 'ChatGPT', 'MachineLearning']:
            all_articles.extend(fetch_reddit_for_date(target_date, sub, 5))
            time.sleep(2)
        
        print(f"  抓取到 {len(all_articles)} 篇")
        
        if not all_articles:
            continue
        
        db = SessionLocal()
        try:
            existing_urls = set(row[0] for row in db.query(News.source_url).filter(News.news_date == target_date).all())
            new_count = 0
            for article in all_articles:
                url = article.get('url', '')
                if url in existing_urls:
                    continue
                title_zh, translated_text = translate_item(article.get('title', ''), article.get('content', ''), translator)
                cat_info = classify_category(article.get('title', ''), article.get('content', ''))
                if not cat_info:
                    continue
                news = News(
                    title=article.get('title', ''), title_zh=title_zh,
                    original_text=article.get('content', ''), translated_text=translated_text,
                    category=cat_info['category'], category_label=cat_info['label'], category_emoji=cat_info['emoji'],
                    source=article.get('source', 'Unknown'), source_url=url,
                    published_at=article.get('published', datetime.now(CN_TZ)),
                    trust_level=article.get('trust_level', 'B'),
                    multi_source_verified=False, ai_warning=None, news_date=target_date
                )
                db.add(news)
                new_count += 1
                existing_urls.add(url)
            db.commit()
            total = db.query(News).filter(News.news_date == target_date).count()
            print(f"  新增 {new_count} 条，共 {total} 条")
        finally:
            db.close()
    
    print("\n历史数据补全完成!")


@app.post("/api/admin/fill-history")
def trigger_fill_history():
    thread = threading.Thread(target=fill_history_task, daemon=True)
    thread.start()
    return {"success": True, "message": "历史数据补全任务已在后台启动，请等待..."}


STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.is_dir():
    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
