import sqlite3
import json
import os

USERS = [
    (1, "Иван", "ivan@yandex.ru", [1, 2, 8]),
    (2, "Пётр", "petr@yandex.ru", [3, 4, 5]),
    (3, "Анна", "anna@yandex.ru", [6, 7]),
    (4, "Мария", "mariy@yandex.ru", [2, 9, 10]),
    (5, "Сергей", "sergey@yandex.ru", [1, 4, 8, 5]),]


def main():
    if not os.path.exists("config.json"):
        print("Файл конфигурации не найден")
    with open('config.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    user_db_path = data["users_db"]
    conn = sqlite3.connect(user_db_path)

    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT);""")
    conn.execute("""CREATE TABLE IF NOT EXISTS user_categories (
        user_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE);""")

    for user_id, name, email, cat in USERS:
        conn.execute("INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                    (user_id, name, email))
        for cat_id in cat:
            conn.execute(
                "INSERT INTO user_categories (user_id, category_id) VALUES (?, ?)",
                (user_id, cat_id),
            )
    conn.commit()
    print(f"{data["users_db"]} создан, пользователей: {len(USERS)}")


if __name__ == "__main__":
    main()