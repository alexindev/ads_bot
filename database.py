import psycopg2
from config import PG_BASE, PG_USER, PG_PASS


class Database:
    def __init__(self):
        self._conn = psycopg2.connect(
            host="localhost",
            database=PG_BASE,
            user=PG_USER,
            password=PG_PASS
        )

    def create_table(self, city):
        with self._conn.cursor() as cur:
            cur.execute(
                '''CREATE TABLE IF NOT EXISTS {} (
                    id SERIAL,
                    task BYTEA,
                    status INTEGER)
                '''.format(city)
            )
        self._conn.commit()



