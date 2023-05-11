import psycopg2
from loguru import logger
from ads_bot.config import PG_BASE, PG_USER, PG_PASS


class Database:
    def __init__(self):
        self._conn = psycopg2.connect(
            host="localhost",
            database=PG_BASE,
            user=PG_USER,
            password=PG_PASS
        )

    def create_table(self, city: str) -> None:
        """Создать новый город"""
        with self._conn.cursor() as cur:
            cur.execute(
                f'''CREATE TABLE IF NOT EXISTS "{city}" (
                    id SERIAL,
                    image VARCHAR(100),
                    text VARCHAR(50),
                    status INTEGER)
                '''
            )
        self._conn.commit()

    def create_user_table(self):
        """Таблица работников"""
        with self._conn.cursor() as cur:
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(20) PRIMARY KEY,
                    city VARCHAR(50),
                    job_id VARCHAR(10),
                    status INTEGER
                )'''
            )
        self._conn.commit()

    def get_user_data(self, user_id):
        """Информация о работнике"""
        with self._conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM users WHERE user_id=%s', (user_id,)
            )
            return cur.fetchone()

    def set_user_info(self, user_id, city, job_id, status):
        """Записать данные рабоника"""
        with self._conn.cursor() as cur:
            cur.execute(
                'INSERT INTO users (user_id, city, job_id, status) VALUES (%s, %s, %s, %s)',
                (user_id, city, job_id, status))
            self._conn.commit()

    def delete_user_data(self, user_id: str):
        """Удалить данные пользователя"""
        with self._conn.cursor() as cur:
            cur.execute(
                'DELETE FROM users WHERE user_id=%s', (user_id,))
            self._conn.commit()

    def update_user_status(self, user_id: str, status: int):
        """Обновить статус пользователя"""
        with self._conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET status=%s WHERE user_id=%s', (status, user_id,))
            self._conn.commit()

    def update_status_all_user(self):
        """Обновить статус у всех пользователей"""
        with self._conn.cursor() as cur:
            cur.execute(
                'UPDATE users SET status=1')
            self._conn.commit()

    def rollback(self):
        """Откатить транзакцию"""
        self._conn.rollback()

    def get_cities(self):
        """Получить все города"""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename NOT LIKE 'users';"
            )
            return cur.fetchall()

    def get_city(self, city: str):
        """Получить один город"""
        with self._conn.cursor() as cur:
            cur.execute('SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)',
                        (city,))
            return cur.fetchone()[0]

    def delete_city(self, city: str) -> bool:
        """Удалить город"""
        with self._conn.cursor() as cur:
            try:
                cur.execute(f'DROP TABLE "{city}"')
                self._conn.commit()
                return True
            except Exception as e:
                logger.error(e)
                return False

    def new_job(self, city, image, text, status):
        """Добавить новую работу"""
        with self._conn.cursor() as cur:
            cur.execute(
                f'INSERT INTO "{city}" (image, text, status) VALUES (%s, %s, %s)',
                (image, text, status,))
            self._conn.commit()

    def get_job(self, city, text):
        """Получить запись c идентификатором"""
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT * FROM "{city}" WHERE text=%s', (text,))
            return cur.fetchone()

    def get_all_jobs(self, city):
        """Получить все маршруты из текущего города"""
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT text FROM "{city}"')
            return cur.fetchall()

    def get_photo(self, city, text):
        """Получить фото маршрута"""
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT image FROM "{city}" WHERE text=%s', (text,))
            return cur.fetchone()

    def delete_job(self, city, text):
        """Удалить задание"""
        with self._conn.cursor() as cur:
            cur.execute(f'DELETE FROM "{city}" WHERE text=%s', (text,))
            self._conn.commit()

    def get_job_photo_id(self, city, status):
        """Получить маршрут для работника"""
        with self._conn.cursor() as cur:
            cur.execute(f'SELECT image, text FROM "{city}" WHERE status=%s', (status,))
            return cur.fetchone()

    def update_job_status(self, city, text, status):
        """Обновить статус маршрута"""
        with self._conn.cursor() as cur:
            cur.execute(
                f'UPDATE "{city}" SET status=%s WHERE text=%s', (status, text,)
            )
            self._conn.commit()

    def update_status(self, city, status):
        """Обновить статус для всех маршрутов"""
        with self._conn.cursor() as cur:
            cur.execute(
                f'UPDATE "{city}" SET status=%s', (status,)
            )
            self._conn.commit()
