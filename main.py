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