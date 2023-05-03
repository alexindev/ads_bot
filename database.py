import psycopg2
from loguru import logger

from config import PG_BASE, PG_USER, PG_PASS


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
                    task BYTEA,
                    status INTEGER)
                '''
            )
        self._conn.commit()

    def get_cities(self):
        """Получить все города"""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';"
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
