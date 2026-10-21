import os
import sqlite3
from datetime import datetime

import requests
from bs4 import BeautifulSoup

UNIVERSITY_NAME = "МИРЭА"
UNIVERSITY_ID = 2
BASE = "https://priem.mirea.ru"
LIST_URL = "https://priem.mirea.ru/news?start=0"
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "news.db")
REQUEST_TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

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

KEYWORD_MAP = {
    "Наука и инновации": ["пиш", "иии", "идеи будущего", "химбиотех", "наук", "исследов"],
    "Образование": ["олимпиад", "конкурс", "лицей", "всош", "мош",
                    "профориентац", "предпрофессиональн", "технокалейдоскоп"],
    "Студенческая жизнь": ["бои", "ученик года", "интеллектуальн", "киберспорт",
                            "кибербиатлон", "достижения", "вектор успеха"],
    "Объявления и события": ["дод", "день открытых дверей", "дни открытых дверей", "анонс"],
    "Абитуриентам": ["приемная комиссия", "приёмная кампания", "абитуриент",
                      "навигатор поступления", "технопарк", "фрязино"],
    "Сотрудничество и партнёрство": ["партнер", "сотрудничество со школами"],
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


def normalize_category(raw):
    if not raw:
        return DEFAULT_CATEGORY_ID
    key = raw.strip().lower()
    for cat_name, words in KEYWORD_MAP.items():
        if any(w in key for w in words):
            return CATEGORY_ID[cat_name]
    return DEFAULT_CATEGORY_ID


def parse():
    conn, cur = init_db()
    total_new = 0

    try:
        first = requests.get(LIST_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        first.raise_for_status()
    except requests.RequestException as e:
        print(f"[МИРЭА] Не удалось получить список: {e}")
        conn.close()
        return 0

    soup = BeautifulSoup(first.text, "html.parser")
    counter = soup.select_one(
        ".com-content-category-blog__counter.counter.float-md-end.pt-3.pe-2"
    )
    try:
        num_of_pages = int(counter.text.split()[-1]) if counter else 1
    except (ValueError, AttributeError):
        num_of_pages = 1

    try:
        for i in range(num_of_pages):
            url = f"https://priem.mirea.ru/news?start={i * 9}"
            try:
                r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"[МИРЭА] Ошибка страницы {url}: {e}")
                continue

            page_soup = BeautifulSoup(r.text, "html.parser")
            for card in page_soup.select(".article-body"):
                cat_block = card.select_one("ul")
                raw_cat = ""
                if cat_block:
                    a = cat_block.select_one("a")
                    raw_cat = a.get_text(strip=True) if a else ""
                cat_id = normalize_category(raw_cat)

                href_tag = card.find("a")
                if not href_tag or not href_tag.get("href"):
                    continue
                link = BASE + href_tag["href"]

                title_tag = card.select_one(".article-header")
                title = title_tag.get_text(strip=True) if title_tag else "Без названия"

                time_tag = card.find("time")
                if time_tag and time_tag.get("datetime"):
                    try:
                        dt = datetime.fromisoformat(time_tag["datetime"])
                        pub_date = dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pub_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    pub_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                intro = card.select_one(".article-introtext")
                content = intro.get_text(" ", strip=True) if intro else None

                cur.execute(
                    """INSERT OR IGNORE INTO news
                       (title, content, link, published_date, category_id, university_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, content, link, pub_date, cat_id, UNIVERSITY_ID),
                )
                if cur.rowcount == 1:
                    conn.commit()
                    total_new += 1
                    print(f"[МИРЭА] + {title[:60]}")
    except Exception as e:
        conn.rollback()
        print(f"[МИРЭА] Ошибка парсинга: {e}")
    finally:
        conn.close()

    print(f"[МИРЭА] Готово. Новых новостей: {total_new}")
    return total_new


if __name__ == "__main__":
    parse()