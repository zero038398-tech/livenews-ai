import os
import uuid
import threading
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date as date_type, datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from database import get_db, init_db
from models import News
from services.scraper import NewsScraper
from services.translator import Translator

app = FastAPI(title="LiveNews AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_and_save_news():
    print(f"[{datetime.now()}] Starting news fetch...")
    try:
        scraper = NewsScraper()
        news_items = scraper.scrape_all()
        print(f"Scraped {len(news_items)} AI-related news items")
        scraper.save_to_db(news_items, translator=None)
        print(f"[{datetime.now()}] News saved to DB (without translation)")
    except Exception as e:
        print(f"Error fetching news: {e}")


def translate_untranslated_news():
    print(f"[{datetime.now()}] Starting translation...")
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
                if is_chinese:
                    news.title_zh = news.title
                    news.translated_text = news.original_text
                else:
                    if news.title:
                        news.title_zh = translator.translate_title(news.title)
                    if news.original_text:
                        news.translated_text = translator.translate_text(news.original_text[:2000])
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


def fetch_and_translate():
    fetch_and_save_news()
    translate_untranslated_news()


def background_fetch():
    thread = threading.Thread(target=fetch_and_translate, daemon=True)
    thread.start()


@app.on_event("startup")
def startup_event():
    init_db()

    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_save_news, 'interval', hours=2, id='fetch_news')
    scheduler.add_job(translate_untranslated_news, 'interval', hours=1, id='translate_news')
    scheduler.start()
    print("Scheduler started: fetch every 2h, translate every 1h")

    db = next(get_db())
    today = date_type.today()
    has_today_news = db.query(News).filter(News.news_date == today).first()
    db.close()

    if not has_today_news:
        background_fetch()


@app.get("/")
def root():
    return {"message": "LiveNews AI API", "version": "1.0.0"}


@app.get("/api/news")
def get_news(
    date: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(News)
    today = date_type.today()

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
            "date": date or str(today),
            "news": [item.to_dict() for item in news_items],
            "categories": [
                {"value": "all", "label": "全部", "emoji": "📋"},
                {"value": "chip", "label": "AI芯片动态", "emoji": "🔴"},
                {"value": "tool", "label": "工具推荐", "emoji": "🟢"},
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
    today = date_type.today()
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
        "tool": "工具推荐",
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
        {"value": "tool", "label": "工具推荐", "emoji": "🟢"},
        {"value": "industry", "label": "行业动态", "emoji": "🔵"},
        {"value": "academic", "label": "学术精选", "emoji": "🟣"}
    ]


@app.post("/api/admin/fetch-news")
def trigger_fetch_news():
    background_fetch()
    return {"success": True, "message": "News fetch triggered in background"}


@app.post("/api/admin/translate")
def trigger_translate():
    thread = threading.Thread(target=translate_untranslated_news, daemon=True)
    thread.start()
    return {"success": True, "message": "Translation triggered in background"}


def retranslate_all_news():
    print(f"[{datetime.now()}] Starting re-translation of all news...")
    try:
        db = next(get_db())
        all_news = db.query(News).all()

        if not all_news:
            print("No news found to re-translate")
            db.close()
            return

        translator = Translator()
        count = 0
        for news in all_news:
            try:
                is_chinese = any('\u4e00' <= c <= '\u9fff' for c in news.title)
                if is_chinese:
                    news.title_zh = news.title
                    news.translated_text = news.original_text
                else:
                    if news.title:
                        news.title_zh = translator.translate_title(news.title)
                    if news.original_text:
                        news.translated_text = translator.translate_text(news.original_text[:2000])
                count += 1
                if count % 5 == 0:
                    db.commit()
                    print(f"  Re-translated {count}/{len(all_news)}")
            except Exception as e:
                print(f"  Re-translation error for '{news.title[:30]}...': {e}")
                continue

        db.commit()
        db.close()
        print(f"[{datetime.now()}] Re-translation completed: {count} items")
    except Exception as e:
        print(f"Error in re-translation: {e}")


@app.post("/api/admin/retranslate")
def trigger_retranslate():
    thread = threading.Thread(target=retranslate_all_news, daemon=True)
    thread.start()
    return {"success": True, "message": "Re-translation of all news triggered in background"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
