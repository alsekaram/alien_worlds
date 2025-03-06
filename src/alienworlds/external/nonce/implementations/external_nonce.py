import asyncio
from contextlib import asynccontextmanager

from ..interfaces import NonceGenerator


class ExternalNonce(NonceGenerator):
    HOST = "localhost"
    PORT = 20083

    @asynccontextmanager
    async def open_connection(self, host, port):
        reader, writer = await asyncio.open_connection(host, port)
        try:
            yield reader, writer
        finally:
            writer.close()
            await writer.wait_closed()

    async def get_nonce(self, account, last_mine_trx, difficulty=0) -> str:

        params = (
            f"last_mine_trx={last_mine_trx}&account={account}&difficulty={difficulty}"
        )
        async with self.open_connection(self.HOST, self.PORT) as (reader, writer):
            writer.write(params.encode("utf-8"))
            await writer.drain()
            data = await reader.read()

        nonce = data.decode("utf-8").strip()
        return nonce
