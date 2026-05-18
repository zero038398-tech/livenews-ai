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


def fetch_and_translate():
    print(f"[{datetime.now()}] Starting news fetch + translate...")
    try:
        scraper = NewsScraper()
        translator = Translator()
        news_items = scraper.scrape_all()
        print(f"Scraped {len(news_items)} AI-related news items")

        today = cn_today()

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
            })

            print(f"  Prepared {idx+1}/{len(news_items)}: {item['title'][:40]}...")

        db = next(get_db())
        try:
            existing_urls = set(
                row[0] for row in db.query(News.source_url).filter(News.news_date == today).all()
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
                    news_date=today
                )
                db.add(news)
                new_count += 1
            db.commit()
            print(f"[{datetime.now()}] Done: saved {new_count} new items (skipped {len(prepared_items) - new_count} duplicates)")
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


@app.on_event("startup")
def startup_event():
    init_db()

    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_translate, 'interval', hours=2, id='fetch_news')
    scheduler.add_job(translate_untranslated_news, 'interval', hours=1, id='translate_news')
    scheduler.start()
    print("Scheduler started: fetch+translate every 2h, translate remaining every 1h")

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
        count = db.query(News).delete()
        db.commit()
        db.close()
        print(f"Deleted {count} old news items")
    except Exception as e:
        print(f"Error deleting news: {e}")
    fetch_and_translate()


@app.post("/api/admin/reset")
def trigger_reset():
    thread = threading.Thread(target=reset_and_refetch, daemon=True)
    thread.start()
    return {"success": True, "message": "Reset and re-fetch triggered in background"}


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
