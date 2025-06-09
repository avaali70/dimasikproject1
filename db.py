import aiosqlite
import asyncio

async def init_database(db_path="voice_channels.db"):
    db = Database(db_path)
    await db.init_db()
    return db

class Database:
    def __init__(self, db_path="voice_channels.db"):
        self.db_path = db_path
        self.db = None

    async def init_db(self):
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        # Создание таблицы channels
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        # Создание таблицы users (без session_token для обратной совместимости)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                login TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                avatar_path TEXT
            )
        """)
        # Проверка и добавление столбца session_token
        async with self.db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if 'session_token' not in columns:
                await self.db.execute("ALTER TABLE users ADD COLUMN session_token TEXT")
                print("Added session_token column to users table")  # Для отладки
        await self.db.commit()
        # Инициализация тестовых данных
        async with self.db.execute("SELECT COUNT(*) FROM channels") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                await self.db.execute("INSERT INTO channels (name) VALUES (?)", ("General",))
                await self.db.commit()
        async with self.db.execute("SELECT COUNT(*) FROM users") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                await self.db.execute(
                    "INSERT INTO users (login, password, avatar_path, session_token) VALUES (?, ?, ?, ?)",
                    ("testuser", "testpass", "img/default.png", None)
                )
                await self.db.execute(
                    "INSERT INTO users (login, password, avatar_path, session_token) VALUES (?, ?, ?, ?)",
                    ("avaali", "avaali_pass", "img/avaali.png", None)
                )
                await self.db.commit()
                print("Created test users: testuser/testpass, avaali/avaali_pass")  # Для отладки

    async def add_channel(self, name):
        await self.db.execute("INSERT INTO channels (name) VALUES (?)", (name,))
        await self.db.commit()

    async def get_channels(self):
        async with self.db.execute("SELECT channel_id, name FROM channels") as cursor:
            return [(row["channel_id"], row["name"]) for row in await cursor.fetchall()]

    async def authenticate_user(self, login, password):
        query = "SELECT login, avatar_path, session_token FROM users WHERE login = ?"
        params = (login,)
        if password:
            query += " AND password = ?"
            params = (login, password)
        async with self.db.execute(query, params) as cursor:
            result = await cursor.fetchone()
            print(f"Auth attempt: login={login}, found={result}")  # Для отладки
            return result

    async def verify_token(self, login, session_token):
        async with self.db.execute("SELECT login, avatar_path, session_token FROM users WHERE login = ? AND session_token = ?", (login, session_token)) as cursor:
            result = await cursor.fetchone()
            print(f"Token verification: login={login}, session_token={session_token}, found={result}")  # Для отладки
            if result:
                return {"login": result["login"], "avatar_path": result["avatar_path"], "session_token": result["session_token"]}
            return None

    async def update_token(self, login, session_token):
        await self.db.execute("UPDATE users SET session_token = ? WHERE login = ?", (session_token, login))
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()