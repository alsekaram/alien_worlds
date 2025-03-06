from abc import ABC, abstractmethod


class NonceGenerator(ABC):
    @abstractmethod
    async def get_nonce(self, account: str, last_mine_trx: str, difficulty: int) -> str:
        pass
