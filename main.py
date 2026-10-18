# import importlib.util
# import json
# import logging
# import os
# import sqlite3
# import sys
# import time
# from datetime import datetime
#
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.FileHandler("monitor.log", encoding="utf-8"),
#         logging.StreamHandler(sys.stdout),
#     ],
# )
# log = logging.getLogger(__name__)
#
# CONFIG_PATH = "config.json"
#
#
# def load_config(path=CONFIG_PATH):
#     if not os.path.exists(path):
#         log.error("Файл конфигурации %s не найден", path)
#         sys.exit(1)
#     with open(path, "r", encoding="utf-8") as f:
#         try:
#             cfg = json.load(f)
#         except json.JSONDecodeError as e:
#             log.error("Ошибка в config.json: %s", e)
#             sys.exit(1)
#
#     required = ["interval_minutes", "news_db", "users_db",
#                 "output_file", "parsers_dir"]
#     for key in required:
#         if key not in cfg:
#             log.error("В config.json отсутствует параметр '%s'", key)
#             sys.exit(1)
#     return cfg
#
#
# def run_parsers(parsers_dir):
#     """Загружает и запускает parse() из каждого parser_*.py напрямую по пути."""
#     if not os.path.isdir(parsers_dir):
#         log.error("Папка парсеров '%s' не найдена", parsers_dir)
#         return 0
#
#     files = sorted(f for f in os.listdir(parsers_dir)
#                    if f.startswith("parser_") and f.endswith(".py"))
#
#     if not files:
#         log.warning("В папке '%s' нет парсеров", parsers_dir)
#         return 0
#
#     total = 0
#     for fname in files:
#         module_name = fname[:-3]
#         file_path = os.path.join(parsers_dir, fname)
#
#         log.info("Запуск парсера %s", file_path)
#         try:
#             spec = importlib.util.spec_from_file_location(module_name, file_path)
#             module = importlib.util.module_from_spec(spec)
#             sys.modules[module_name] = module
#             spec.loader.exec_module(module)
#
#             if not hasattr(module, "parse"):
#                 log.warning("В %s нет функции parse()", fname)
#                 continue
#
#             result = module.parse()
#             if isinstance(result, int):
#                 total += result
#             log.info("Парсер %s завершён", fname)
#         except Exception as e:
#             log.exception("Ошибка в парсере %s: %s", fname, e)
#
#     return total
#
#
# def build_send_list(cfg, since_iso):
#     """Формирует send_list.txt: какие новости каким пользователям отправить."""
#     news_conn = sqlite3.connect(cfg["news_db"])
#     news_conn.row_factory = sqlite3.Row
#     users_conn = sqlite3.connect(cfg["users_db"])
#     users_conn.row_factory = sqlite3.Row
#
#     new_news = news_conn.execute(
#         """SELECT id, category_id, title
#            FROM news
#            WHERE added_at >= ?
#            ORDER BY id""",
#         (since_iso,),
#     ).fetchall()
#
#     log.info("Новых новостей за интервал: %d", len(new_news))
#
#     rows = users_conn.execute(
#         "SELECT user_id, category_id FROM user_categories"
#     ).fetchall()
#
#     user_interests = {}
#     for r in rows:
#         user_interests.setdefault(r["user_id"], set()).add(r["category_id"])
#
#     users = users_conn.execute("SELECT id, name FROM users").fetchall()
#
#     lines = []
#     for u in users:
#         uid = u["id"]
#         interests = user_interests.get(uid, set())
#         matched = [n["id"] for n in new_news if n["category_id"] in interests]
#         if matched:
#             lines.append(f"{uid}: " + ", ".join(str(x) for x in matched))
#
#     with open(cfg["output_file"], "w", encoding="utf-8") as f:
#         f.write("\n".join(lines))
#
#     news_conn.close()
#     users_conn.close()
#
#     log.info("send_list.txt сформирован, строк: %d", len(lines))
#     return len(lines)
#
#
# def main():
#     cfg = load_config()
#     interval_sec = int(cfg["interval_minutes"]) * 60
#     log.info("Сервис запущен. Интервал: %d мин", cfg["interval_minutes"])
#
#     last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#
#     try:
#         while True:
#             log.info("=" * 60)
#             log.info("Цикл парсинга, старт: %s",
#                      datetime.now().isoformat(timespec="seconds"))
#
#             run_parsers(cfg["parsers_dir"])
#             build_send_list(cfg, last_run)
#
#             last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             log.info("Цикл завершён. Следующий запуск через %d мин",
#                      cfg["interval_minutes"])
#
#             time.sleep(interval_sec)
#     except KeyboardInterrupt:
#         log.info("Получен Ctrl+C, завершение работы")
#     finally:
#         log.info("Сервис остановлен")
#
#
# if __name__ == "__main__":
#     main()




import importlib.util
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime

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
    for key in ("interval_minutes", "news_db", "users_db",
                "output_file", "parsers_dir"):
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


def main():
    cfg = load_config()
    interval = int(cfg["interval_minutes"]) * 60
    log.info("Сервис запущен. Интервал: %d мин", cfg["interval_minutes"])

    last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        while True:
            log.info("=" * 60)
            log.info("Цикл парсинга, старт: %s", datetime.now().isoformat(timespec="seconds"))
            run_parsers(cfg["parsers_dir"])
            last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.info("Цикл завершён. Следующий через %d мин", cfg["interval_minutes"])
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("Получен Ctrl+C, завершение")
    finally:
        log.info("Сервис остановлен")


if __name__ == "__main__":
    main()