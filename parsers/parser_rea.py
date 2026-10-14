# import requests as rq
# from bs4 import BeautifulSoup
# from datetime import datetime
# import time
# import db_functions as db
# import pandas as pd
# from urllib.parse import urljoin, urlparse
#
# def timer(func):
#     def wrapper(*args, **kwargs):
#         start = time.time()
#         result = func(*args, **kwargs)
#         end = time.time()
#         print(f'Программа заняла: {end - start} секунд; {(end - start) / 60:.2f} минут')
#         print("=" * 100)
#         return result
#
#     return wrapper
#
# categories = {
#     "Наука": 'Наука',
#     "Спорт": "Спорт",
#     "Абитуриентам": "Абитуриентам",
#     "В мире": "Объявления",
#     "Образование": "Образование",
#     "Студенчество": "Студенчество",
#     "Международная деятельность": "Международная деятельность",
#     "Проекты": "Сотрудничество",
#     "Университет": "Культура"
# }
#
# con, cursor = db.connect()
#
# urls = []
#
# for i in range(1, 200): # всех новостей 516 страниц
#     page = f"https://www.rea.ru/news?tree-content-path=news&page={i}&per-page=12"
#     urls.append(page)
#
#
# @timer
# def parse(con, cur):
#     print("=" * 100)
#
#     print('Начинаем парсинг новостей категории')
#     print("=" * 100)
#     # dc = pd.read_sql("SELECT * FRON news_categories", con=con)
#
#     data = {
#         "title": [],
#         "publication_date": [],
#         "link": [],
#         "added_at": [],
#         "category": [],
#         "university": [],
#         "content": []
#     }
#
#     for url in urls:
#         response = rq.get(url, timeout=10)
#         html = response.text
#
#         soup = BeautifulSoup(html, 'html.parser')
#
#         if response.status_code == 200:
#             items = soup.select('a.catalog__item-content')
#
#             for item in items:
#                 title = item.select_one('.catalog__item-title')
#                 date = item.select_one('.catalog__item-date')
#                 link = urljoin("https://www.rea.ru", item.get("href"))
#                 link = link.split("?")[0]
#
#                 response_sub = rq.get(link, timeout=10)
#                 html_sub = response_sub.text
#                 soup_sub = BeautifulSoup(html_sub, 'html.parser')
#
#                 if response_sub.status_code == 200:
#                     category_tag = soup_sub.select_one("li.catalog-detail__tag")
#
#                     content_tag = soup_sub.select_one(".catalog-detail__text")
#
#                     if content_tag:
#                         short_content = content_tag.get_text(" ", strip=True)
#                     else:
#                         short_content = "no text"
#
#                     data["content"].append(short_content)
#
#                     if category_tag:
#                         category = category_tag.get_text(strip=True)
#
#                         if category in categories:
#                             category_name = categories[category]
#
#                             cat = cur.execute(
#                                 "SELECT category_id FROM news_categories WHERE name = ?",
#                                 (category_name,)
#                             ).fetchone()[0]
#
#                             data["category"].append(cat)
#                         else:
#                             cat = cur.execute("SELECT category_id FROM news_categories WHERE name = ?", ("unknown",)).fetchone()[0]
#                             data["category"].append(cat)
#                     else:
#                         cat = cur.execute("SELECT category_id FROM news_categories WHERE name = ?", ("unknown",)).fetchone()[0]
#                         data["category"].append(cat)
#
#                 date_text = date.get_text(strip=True)
#
#                 if date_text == "Сегодня":
#                     date_text = datetime.now().strftime("%d %m %Y")
#
#                 data["title"].append(title.get_text(strip=True))
#                 data["publication_date"].append(date_text)
#                 data["link"].append(link)
#                 data["added_at"].append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
#
#                 uni = cur.execute(
#                     "SELECT university_id FROM universities WHERE name = ?",
#                     ("РЭУ",)
#                 ).fetchone()[0]
#
#                 data["university"].append(uni)
#         # else:
#         #     print(response.status_code)
#
#     df = pd.DataFrame(data)
#
#     months = {
#         'января': '01',
#         'февраля': '02',
#         'марта': '03',
#         'апреля': '04',
#         'мая': '05',
#         'июня': '06',
#         'июля': '07',
#         'августа': '08',
#         'сентября': '09',
#         'октября': '10',
#         'ноября': '11',
#         'декабря': '12'
#     }
#
#     df['publication_date'] = df['publication_date'].replace(months, regex=True)
#     df['publication_date'] = pd.to_datetime(
#         df['publication_date'],
#         format='%d %m %Y'
#     )
#     df["category"] = df["category"].astype('int')
#
#     before = len(df)
#
#     df = df.drop_duplicates(subset=["link"])
#
#     after = len(df)
#
#     print(f"Удалено дубликатов: {before - after}")
#
#     df.to_sql(name='news', con=con, if_exists='append', index=False)
#
#     print('=' * 100)
#     print(f'Парсинг закончился, в базу данных сохранено {len(df)} новостей!')
#
#
# @timer
# def check_news(con):
#     print("Проверяем наличие новых новостей...")
#
#     df_cat = pd.read_sql("SELECT * FROM news_categories", con=con)
#     df_uni = pd.read_sql("SELECT * FROM universities", con=con)
#
#     url = "https://www.rea.ru/news?tree-content-path=news&search=&date_from=&date_to=&sub%5B0%5D=57407&page=1&per-page=12"
#
#     response = rq.get(url, timeout=10)
#
#     if response.status_code != 200:
#         print(f"Ошибка: {response.status_code}")
#         return
#
#     soup = BeautifulSoup(response.text, "html.parser")
#
#     item = soup.select_one("a.catalog__item-content")
#
#     if not item:
#         print("Новости не найдены")
#         return
#
#     title = item.select_one(".catalog__item-title")
#     date = item.select_one(".catalog__item-date")
#     link = urljoin("https://www.rea.ru", item.get("href"))
#     link = link.split("?")[0]
#
#     title_text = title.get_text(strip=True)
#
#     print(f"Последняя новость на сайте: {title_text}")
#
#     result = db.get_last_news(cursor)
#
#     if result is None:
#         print("База данных пустая")
#         return
#
#     last_title = result[0]
#
#     if title_text == last_title:
#         print("Новых новостей нет")
#         return
#
#     print("Обнаружена новая новость!")
#
#     news_response = rq.get(link, timeout=10)
#     soup_sub = BeautifulSoup(news_response.text, "html.parser")
#
#     category_tag = soup_sub.select_one("li.catalog-detail__tag")
#
#     if category_tag:
#         category = category_tag.get_text(strip=True)
#
#         if category in categories:
#             category_name = categories[category]
#             category = df_cat.loc[
#                 df_cat["name"] == category_name,
#                 "category_id"
#             ].iloc[0]
#         else:
#             category = df_cat.loc[
#                 df_cat["name"] == "unknown",
#                 "category_id"
#             ].iloc[0]
#
#     else:
#         category = df_cat.loc[
#             df_cat["name"] == "unknown",
#             "category_id"
#         ].iloc[0]
#
#     content_tag = soup_sub.select_one(".catalog-detail__text")
#
#     if content_tag:
#         content = content_tag.get_text(" ", strip=True)
#     else:
#         content = "no text"
#
#     university = df_uni.loc[df_uni["name"] == "РЭУ", "university_id"].iloc[0]
#
#     if date == "Сегодня":
#         date = datetime.now().strftime("%d %m %Y")
#
#     db.insert_news(con, cursor, title, date, link, category, university, content)
#
#
# if __name__ == "__main__":
#     print("Создаем таблицу новостей...")
#     db.table_news(con, cursor)
#     print(f"Таблица новостей создана\n{"=" * 100}")
#
#     db.table_categories(con, cursor)
#     print("=" * 100)
#     db.table_university(con, cursor)
#     print("=" * 100)
#
#     result = db.get_last_news(cursor)
#
#     if result is None:
#         print("База данных пустая. Запускаем первоначальный парсинг...")
#         parse(con, cursor)
#
#     else:
#         print("База данных уже содержит новости")
#
#     check_news(con)




# parsers/parser_rea.py
"""Парсер новостей РЭУ им. Плеханова (rea.ru/news). Автор: <ФИО>."""
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