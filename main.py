import importlib.util
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("monitor.log", encoding="utf-8"),
              logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

CONFIG_PATH = "config.json"

def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        log.error("Файл конфигурации %s не найден", path)
        sys.exit(1)
    with open(path, encoding="utf-8") as file:
        conf = json.load(file)
    for key in ("interval_minutes", "news_db", "users_db", "output_file", "parsers_dir"):
        if key not in conf:
            log.error("В config.json нет параметра '%s'", key)
            sys.exit(1)
    return conf


def run_parsers(parsers_dir):
    total = 0
    if not os.path.isdir(parsers_dir):
        log.error("Папка '%s' не найдена", parsers_dir)
        return total
    for fname in sorted(os.listdir(parsers_dir)):
        if not (fname.startswith("parser_") and fname.endswith(".py")):
            continue
        name = fname[:-3]
        path = os.path.join(parsers_dir, fname)
        log.info("Запуск парсера %s", path)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            if hasattr(mod, "parse"):
                res = mod.parse()
                if isinstance(res, int):
                    total += res
            log.info("Парсер %s завершён", fname)
        except Exception as e:
            log.exception("Ошибка в парсере %s: %s", fname, e)
    return total

def build_send_list(conf, since_iso):
    news_db = conf["news_db"]
    users_db = conf["users_db"]
    output_file = conf["output_file"]

    news_conn = sqlite3.connect(news_db)
    users_conn = sqlite3.connect(users_db)

    new_news = news_conn.execute("SELECT id, category_id FROM news WHERE added_at >= ?", (since_iso,)).fetchall()
    log.info("Новых новостей за интервал: %d", len(new_news))

    interests = {}
    rows = users_conn.execute("SELECT user_id, category_id FROM user_categories").fetchall()
    for row in rows:
        user_id = row[0]
        category_id = row[1]

        if user_id not in interests:
            interests[user_id] = []

        interests[user_id].append(category_id)

    users = users_conn.execute("SELECT id FROM users").fetchall()

    lines = []

    for user_row in users:
        user_id = user_row[0]
        user_categories = interests.get(user_id, [])
        matched_ids = []
        for news in new_news:
            news_id = news[0]
            news_category = news[1]

            if news_category in user_categories:
                matched_ids.append(news_id)

        if len(matched_ids) == 0:
            continue

        ids_as_string = ", ".join(str(x) for x in matched_ids)
        line = f"{user_id}: {ids_as_string}"
        lines.append(line)

    with open(output_file, "w", encoding="utf-8") as f:
        text = "\n".join(lines)
        f.write(text)

    news_conn.close()
    users_conn.close()

    log.info("send_list.txt сформирован, строк: %d", len(lines))
    return len(lines)

def main():
    conf = load_config()
    interval = int(conf["interval_minutes"]) * 60
    log.info("Сервис запущен. Интервал: %d мин", conf["interval_minutes"])
    last_run = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        while True:
            log.info("=" * 60)
            log.info("Цикл парсинга, старт: %s", datetime.now().isoformat(timespec="seconds"))
            run_parsers(conf["parsers_dir"])
            build_send_list(conf, last_run)
            last_run = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            log.info("Цикл завершён. Следующий через %d мин", conf["interval_minutes"])
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("Получен Ctrl+C, завершение")
    finally:
        log.info("Сервис остановлен")


if __name__ == "__main__":
    main()