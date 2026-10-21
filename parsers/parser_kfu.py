import os
import sqlite3
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://media.kpfu.ru/news/"
UNIVERSITY_NAME = "КФУ"
UNIVERSITY_ID = 1
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "news.db")
MAX_PAGES = 15
REQUEST_TIMEOUT = 10
SLEEP_BETWEEN = 0.3


ALL_CATEGORIES = {
    1: "Наука и инновации",
    2: "Образование",
    3: "Студенческая жизнь",
    4: "Спорт",
    5: "Культура и творчество",
    6: "Международная деятельность",
    7: "Сотрудничество и партнёрство",
    8: "Объявления и события",
    9: "Абитуриентам",
    10: "Без категории",
}
CATEGORY_ID = {name: cid for cid, name in ALL_CATEGORIES.items()}
DEFAULT_CATEGORY_ID = CATEGORY_ID["Без категории"]

CATEGORY_MAP = {
    "Новости науки": "Наука и инновации",
    "Новости институтов": "Наука и инновации",
    "Новости образования": "Образование",
    "Новости клиники": "Образование",
    "Новости лицеев": "Образование",
    "Студенческая жизнь": "Студенческая жизнь",
    "Международное сотрудничество": "Международная деятельность",
    "Выпускнику": "Сотрудничество и партнёрство",
    "Новости ректора": "Объявления и события",
    "Акции, мероприятия": "Объявления и события",
    "Абитуриенту": "Абитуриентам",
}


def init_db(db_name=DB_NAME):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            link TEXT UNIQUE NOT NULL,
            published_date TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            university_id INTEGER NOT NULL,
            added_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_categories (
            category_id INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS universities (
            university_id INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)

    for cid, name in ALL_CATEGORIES.items():
        cur.execute(
            "INSERT OR IGNORE INTO news_categories (category_id, name) VALUES (?, ?)",
            (cid, name),
        )
    cur.execute(
        "INSERT OR IGNORE INTO universities (university_id, name) VALUES (?, ?)",
        (UNIVERSITY_ID, UNIVERSITY_NAME),
    )
    conn.commit()
    return conn, cur


def normalize_date(raw):
    raw = (raw or "").strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_html(url):
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"[КФУ] Ошибка запроса {url}: {e}")
        return None


def detect_category(html):
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one(".newsCart-cat")
    if not block:
        return DEFAULT_CATEGORY_ID
    text = block.get_text(" ", strip=True)
    for key, cat_name in CATEGORY_MAP.items():
        if key in text:
            return CATEGORY_ID[cat_name]
    return DEFAULT_CATEGORY_ID


def get_next_page(soup):
    btn = soup.select_one(".pager__item.pager__item--next a")
    if not btn:
        return None
    return BASE_URL + btn.get("href", "")


def save_news(cur, title, link, pub_date, cat_id):
    cur.execute(
        """INSERT OR IGNORE INTO news
           (title, link, published_date, category_id, university_id)
           VALUES (?, ?, ?, ?, ?)""",
        (title, link, pub_date, cat_id, UNIVERSITY_ID),
    )
    return cur.rowcount == 1


def parse():
    conn, cur = init_db()
    total_new = 0
    url = BASE_URL
    try:
        for page in range(1, MAX_PAGES + 1):
            html = fetch_html(url)
            if html is None:
                break
            soup = BeautifulSoup(html, "html.parser")
            items = soup.select(".newsItem")
            if not items:
                break

            stop = False
            for block in items:
                link_tag = block.select_one(".boldLink")
                date_tag = block.select_one(".newsItem-date")
                if not link_tag or not date_tag:
                    continue

                link = "https://media.kpfu.ru" + link_tag.get("href", "")
                title = link_tag.get_text(strip=True)
                pub_date = normalize_date(date_tag.get_text(strip=True))

                art_html = fetch_html(link)
                cat_id = detect_category(art_html) if art_html else DEFAULT_CATEGORY_ID

                if save_news(cur, title, link, pub_date, cat_id):
                    conn.commit()
                    total_new += 1
                    print(f"[КФУ] + {title[:60]}")
                    time.sleep(SLEEP_BETWEEN)
                else:
                    stop = True
                    break

            if stop:
                break
            next_url = get_next_page(soup)
            if not next_url:
                break
            url = next_url
    except Exception as e:
        conn.rollback()
        print(f"[КФУ] Ошибка парсинга: {e}")
    finally:
        conn.close()

    print(f"[КФУ] Готово. Новых новостей: {total_new}")
    return total_new


if __name__ == "__main__":
    parse()