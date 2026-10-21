import os
import sqlite3
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

UNIVERSITY_NAME = "РЭУ"
UNIVERSITY_ID = 3
BASE = "https://www.rea.ru"
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "news.db")
REQUEST_TIMEOUT = 10
MAX_PAGES = 30

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
    "Наука": "Наука и инновации",
    "Спорт": "Спорт",
    "Абитуриентам": "Абитуриентам",
    "В мире": "Объявления и события",
    "Образование": "Образование",
    "Студенчество": "Студенческая жизнь",
    "Международная деятельность": "Международная деятельность",
    "Проекты": "Сотрудничество и партнёрство",
    "Университет": "Культура и творчество",
}

MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
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


def parse_ru_date(text):
    text = (text or "").strip()
    if text == "Сегодня":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ru, num in MONTHS.items():
        text = text.replace(ru, num)
    for fmt in ("%d %m %Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse():
    conn, cur = init_db()
    total_new = 0

    try:
        for i in range(1, MAX_PAGES + 1):
            url = (
                "https://www.rea.ru/news?"
                f"tree-content-path=news&page={i}&per-page=12"
            )
            try:
                r = requests.get(url, timeout=REQUEST_TIMEOUT,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"[РЭУ] Ошибка страницы {url}: {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select("a.catalog__item-content")
            if not items:
                break

            page_had_new = False
            for item in items:
                link = urljoin(BASE, item.get("href", "")).split("?")[0]

                if cur.execute("SELECT 1 FROM news WHERE link = ?", (link,)).fetchone():
                    continue

                title_tag = item.select_one(".catalog__item-title")
                title = title_tag.get_text(strip=True) if title_tag else "Без названия"

                date_tag = item.select_one(".catalog__item-date")
                pub_date = parse_ru_date(date_tag.get_text(strip=True) if date_tag else "")

                cat_id = DEFAULT_CATEGORY_ID
                content = None
                try:
                    sub = requests.get(link, timeout=REQUEST_TIMEOUT,
                                       headers={"User-Agent": "Mozilla/5.0"})
                    sub.raise_for_status()
                    sub_soup = BeautifulSoup(sub.text, "html.parser")

                    cat_tag = sub_soup.select_one("li.catalog-detail__tag")
                    if cat_tag:
                        raw = cat_tag.get_text(strip=True)
                        cat_name = CATEGORY_MAP.get(raw, "Без категории")
                        cat_id = CATEGORY_ID[cat_name]

                    text_tag = sub_soup.select_one(".catalog-detail__text")
                    if text_tag:
                        content = text_tag.get_text(" ", strip=True)[:2000]
                except requests.RequestException as e:
                    print(f"[РЭУ] Не удалось открыть {link}: {e}")

                cur.execute(
                    """INSERT OR IGNORE INTO news
                       (title, content, link, published_date, category_id, university_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, content, link, pub_date, cat_id, UNIVERSITY_ID),
                )
                if cur.rowcount == 1:
                    conn.commit()
                    total_new += 1
                    page_had_new = True
                    print(f"[РЭУ] + {title[:60]}")

            if not page_had_new:
                break
    except Exception as e:
        conn.rollback()
        print(f"[РЭУ] Ошибка парсинга: {e}")
    finally:
        conn.close()

    print(f"[РЭУ] Готово. Новых новостей: {total_new}")
    return total_new


if __name__ == "__main__":
    parse()