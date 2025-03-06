import asyncio

import psycopg
from psycopg import rows
from psycopg_pool import AsyncConnectionPool
from typing import List
from contextlib import asynccontextmanager
import logging

from dotenv import load_dotenv
from os import getenv

from src.infrastructure.database.queries.sql_queries import select_queries
from infrastructure.security.encryptor import Encryptor

DB_HOST = "HOST"
DB_NAME = "DB_NAME"
DB_USER = "DB_USER"
DB_PASS = "DB_PASSWORD"
DB_PORT = "PORT"
SSL_MODE = "SSL_MODE"
SSL_ROOT = "SSL_ROOT_CERT"
SELECT_PREFIX = "select"
SECRET_KEY = "SECRET"

from src.core.entities.wax_acc import WaxAccount


def load_env_vars():
    # Load environment variables from .env file
    load_dotenv()
    return {
        "sslmode": getenv(SSL_MODE),
        "sslrootcert": getenv(SSL_ROOT),
        "DB_URL": getenv("DB_URL"),
    }


class DB:
    _instance = None
    _semaphore = asyncio.Semaphore(10)  # Limit on the number of parallel requests

    @staticmethod
    def getInstance():
        if DB._instance is None:
            DB._instance = DB()
        return DB._instance

    def __init__(self):
        if DB._instance is not None:
            raise Exception("This class is a Singleton!")
        else:
            DB._instance = self
        self.connection_settings = load_env_vars()
        self.encryptor = Encryptor(getenv(SECRET_KEY))

    async def connect(self):
        return AsyncConnectionPool(
            self.connection_settings["DB_URL"],
            min_size=1,
            max_size=10,
        )

    @asynccontextmanager
    async def _get_cursor(self, row_factory=psycopg.rows.tuple_row):
        async with await self.connect() as pool:  # Use the pool as a context manager
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=row_factory) as cur:
                    yield cur

    async def execute_query_old(self, query: str, params=None, row_factory="tuple"):
        async with self._semaphore:
            row_factory_callable = self.row_factories.get(row_factory)
            async with self._get_cursor(row_factory=row_factory_callable) as cur:
                await cur.execute(query, params or ())
                if self.is_select_query(query):
                    return await cur.fetchall()
                else:
                    return cur.rowcount

    async def execute_query(
        self, query: str, params=None, row_factory="tuple", many=False
    ):
        async with self._semaphore:
            row_factory_callable = self.row_factories.get(row_factory)
            async with self._get_cursor(row_factory=row_factory_callable) as cur:
                if many:
                    await cur.executemany(query, params or ())
                else:
                    await cur.execute(query, params or ())
                if self.is_select_query(query):
                    return await cur.fetchall()
                else:
                    return cur.rowcount

    row_factories = {
        "tuple": rows.tuple_row,
        "dict": rows.dict_row,
        "namedtuple": rows.namedtuple_row,
        "class": rows.class_row,
        "args": rows.args_row,
        "kwargs": rows.kwargs_row,
    }

    def is_select_query(self, query):
        return query.strip().lower().startswith(SELECT_PREFIX)

    def construct_query(self, table, columns, placeholders):
        return f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"

    def construct_data_tuple(self, rows_data):
        columns = rows_data[0].keys()
        placeholders = ", ".join(["%s"] * len(columns))
        values = [tuple(d.values()) for d in rows_data]
        return columns, placeholders, values

    async def insert_rows(self, table, rows_data: list[dict]):
        if not rows_data:
            logging.warning("No data provided to insert.")
            return "No data provided."

        columns, placeholders, values = self.construct_data_tuple(rows_data)
        query = self.construct_query(table, columns, placeholders)

        try:
            async with self._semaphore:
                async with self._get_cursor() as cur:
                    await cur.executemany(query, values)
                    return f"Successfully inserted {len(rows_data)} rows."
        except Exception as e:
            logging.error("Failed to insert rows: %s", str(e))
            return f"Failed to insert rows: {str(e)}"

    async def get_wcw_by_wallet(self, wal: str) -> WaxAccount:
        get_wcw_query = select_queries["get_wcw_accounts_by_wallet"]
        rows = await self.execute_query(get_wcw_query, [wal], row_factory="namedtuple")
        row = rows[0]
        decrypted_row = WaxAccount(
            row.wallet,
            row.email,
            self.encryptor.decrypt(row.token),
            self.encryptor.decrypt(row.key),
        )
        return decrypted_row

    async def get_wcw_by_wallets(self, wals: List[str]) -> List[WaxAccount]:

        get_wcw_query = """
            SELECT wallet, email, token, key
            FROM wcw_accounts
            WHERE wallet = ANY(%s::text[]);
        """
        # Выполнение запроса, передаем список как параметр (без преобразования в кортеж)
        rows = await self.execute_query(get_wcw_query, [wals], row_factory="namedtuple")
        accounts = [
            WaxAccount(
                row.wallet,
                row.email,
                self.encryptor.decrypt(row.token),
                self.encryptor.decrypt(row.key),
            )
            for row in rows
        ]
        return accounts

    async def get_random_wallet_with_key(self) -> WaxAccount:
        get_wcw_query = select_queries["get_random_wallet_with_key"]
        rows = await self.execute_query(get_wcw_query, row_factory="namedtuple")
        row = rows[0]
        decrypted_row = WaxAccount(
            row.wallet,
            row.email,
            self.encryptor.decrypt(row.token),
            self.encryptor.decrypt(row.key),
        )
        return decrypted_row

    async def update_token(self, new_token, wallet):
        encrypted_token = self.encryptor.encrypt(new_token)
        update_query = "UPDATE wcw_accounts SET token = %s WHERE wallet = %s"
        updated_rows_count = await self.execute_query(
            update_query, (encrypted_token, wallet)
        )
        return updated_rows_count

    async def update_key(self, key, wallet):
        encrypted_key = self.encryptor.encrypt(key)
        update_query = "UPDATE wcw_accounts SET key = %s WHERE wallet = %s"
        updated_rows_count = await self.execute_query(
            update_query, (encrypted_key, wallet)
        )
        return updated_rows_count

    async def add_wcw_account(self, account: WaxAccount) -> bool:
        account_dict = account.to_dict()
        account_dict["token"] = (
            self.encryptor.encrypt(account_dict["token"])
            if account_dict.get("token")
            else ""
        )
        account_dict["key"] = self.encryptor.encrypt(account_dict["key"])

        try:
            result = await self.insert_rows("wcw_accounts", [account_dict])
            logging.info("Insert result: %s", result)
            return result.startswith("Successfully inserted")
        except Exception as e:
            logging.error("Failed to add WCW account: %s", str(e))
            return False

    async def add_wcw_accounts(self, accounts: list[WaxAccount]) -> bool:
        accounts_dicts = []
        for account in accounts:
            account_dict = account.to_dict()
            account_dict["token"] = (
                self.encryptor.encrypt(account_dict["token"])
                if account_dict.get("token")
                else ""
            )
            account_dict["key"] = self.encryptor.encrypt(account_dict["key"])
            accounts_dicts.append(account_dict)

        try:
            result = await self.insert_rows("wcw_accounts", accounts_dicts)
            logging.info("Insert result: %s", result)
            return result.startswith("Successfully inserted")
        except Exception as e:
            logging.error("Failed to add WCW accounts: %s", str(e))
            return False

    async def update_registration_status(self, wallet: str, is_registered: bool = True):
        """Update the registration status for a specific wallet in aw_miners table"""
        query = """
            UPDATE aw_miners 
            SET is_registered = %s 
            WHERE wallet = %s
        """
        try:
            await self.execute_query(query, (is_registered, wallet))
            logging.info(f"Updated registration status for {wallet} to {is_registered}")
            return True
        except Exception as e:
            logging.error(f"Failed to update registration status for {wallet}: {e}")
            return False


class FernetKeyRotator:
    def __init__(self, db_instance: DB, old_key: bytes, new_key: bytes):
        self.db = db_instance
        self.old_encryptor = Encryptor(old_key)
        self.new_encryptor = Encryptor(new_key)

    async def rotate_keys(self):
        # Получение всех записей из таблицы wcw_accounts
        rows = await self.db.execute_query(
            "SELECT * FROM wcw_accounts", row_factory="namedtuple"
        )

        updated_rows = []
        for row in rows:
            # Преобразование именованного кортежа в словарь
            row_dict = row._asdict()
            # Обновление полей, которые нужно дешифровать
            row_dict["token"] = self.old_encryptor.decrypt(row.token)
            row_dict["key"] = self.old_encryptor.decrypt(row.key)
            # Создание нового именованного кортежа из обновленного словаря

            # тут в б

            decrypted_row = WaxAccount(**row_dict)
            print(decrypted_row)
            # Шифрование полей
            encrypted_token = None
            if decrypted_row.token:
                encrypted_token = self.new_encryptor.encrypt(decrypted_row.token)
            encrypted_key = None
            if decrypted_row.key:
                encrypted_key = self.new_encryptor.encrypt(decrypted_row.key)
            # Добавление обновленной записи в список
            updated_rows.append((encrypted_token, encrypted_key, decrypted_row.wallet))
        # print(updated_rows)

        with self.db._get_cursor() as cur:
            # Create temporary table and fill it with updated data
            create_temp_table_query = "CREATE TEMP TABLE updated_rows (token text NOT NULL, key text, wallet text)"
            cur.execute(create_temp_table_query)
            insert_query = "INSERT INTO updated_rows (token, key, wallet) VALUES (COALESCE(%s, ''), %s, %s)"
            cur.executemany(insert_query, updated_rows)

            # Update the main table using data from the temporary table
            update_query = """
                UPDATE wcw_accounts
                SET token = updated_rows.token, key = updated_rows.key
                FROM updated_rows
                WHERE wcw_accounts.wallet = updated_rows.wallet
            """
            cur.execute(update_query)

        return "Keys rotation completed."


async def main():
    db = DB.getInstance()
    test_acc = await db.get_random_wallet_with_key()
    logging.info("WAX random account: %s", test_acc)
    # miners = [Miner(account=acc) for acc in wax_accs]
    # tasks = [asyncio.create_task(miner.initial_check()) for miner in miners]
    # done, _ = await asyncio.wait(tasks)
    # for task in done:
    #     await task
    # logging.debug("Ready miners: %s", miners)


if __name__ == "__main__":
    # rotation = FernetKeyRotator(DB.getInstance(), b'old_key', b'new_key')
    # result = rotation.rotate_keys()
    # print(result)
    # connection_settings = load_env_vars()
    # db = DB()
    # test_acc = db.get_wcw_by_wallet("eqeyorejougi")
    # test_acc = db.get_random_wallet_with_key()
    # query = select_queries["get_upgraded_miners_list"]
    # test_acc = db.execute_query(query, [], "namedtuple")
    # test_acc = db.get_wcw_by_wallet("oqedozacifoh")
    # print(
    #     [row.wallet for row in set(test_acc) if row.wallet not in {"ma"}],
    #     len(set(test_acc)),
    # )
    # print(test_acc)
    # test_acc = db.execute_query(query, [], "namedtuple")
    # print([row.wallet for row in test_acc])
    # print("\n".join([row.wallet for row in test_acc]))
    from app import configure_color_logging

    log = logging.getLogger(__name__)
    configure_color_logging(level=logging.INFO)

    asyncio.run(main())
