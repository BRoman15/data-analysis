"""Создаем users.db и заполняет пользователями."""
import os
import sqlite3

USERS_DB = "users.db"

USERS = [
    (1, "Иван", "ivan@yandex.ru", [1, 2, 8]),
    (2, "Пётр", "petr@yandex.ru", [3, 4, 5]),
    (3, "Анна", "anna@yandex.ru", [6, 7]),
    (4, "Мария", "mariy@yandex.ru", [2, 9, 10]),
    (5, "Сергей", "sergey@yandex.ru", [1, 4, 8, 5]),
]


def main():
    if os.path.exists(USERS_DB):
        os.remove(USERS_DB)

    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE user_categories (
            user_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    for uid, name, email, cats in USERS:
        cur.execute("INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                    (uid, name, email))
        for cid in cats:
            cur.execute(
                "INSERT INTO user_categories (user_id, category_id) VALUES (?, ?)",
                (uid, cid),
            )

    conn.commit()
    conn.close()
    print(f"{USERS_DB} создан, пользователей: {len(USERS)}")


if __name__ == "__main__":
    main()