import asyncio
import json
import logging
from typing import List

import aiohttp
from aiohttp import ClientSession, TCPConnector


from eosapi import EosApi



from infrastructure.database.db import DB
from src.core.entities.wax_acc import WaxAccount

from config.logger_config import configure_color_logging


log = logging.getLogger(__name__)


class MarketManager:
    headers = {
        "accept": "*/*",
        "accept-language": "en-US;q=0.5,en;q=0.3",
        "referer": "https://play.alienworlds.io/",
        "accept-encoding": "gzip, deflate",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
        "origin": "https://play.alienworlds.io",
        "dnt": "1",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "priority": "u=4",
        "te": "trailers",
    }

    def __init__(self):
        self.rpc_host = "https://wax.eosdac.io"
        self.atomic_api = "https://wax.alienworlds.io"
        # self.atomic_api = "https://wax.api.atomicassets.io"
        self.wax_api = EosApi(
            rpc_host=self.rpc_host,
            proxy=("65.21.182.63", 13001, 300),
            yeomen_proxy=("65.21.182.63", 13001, 300),
        )
        self.current_transaction_assets = None


    def add_account(self, account: WaxAccount) -> None:
        log.debug("add_account: %s", account)
        self.wax_api.import_key(account.wallet, account.key, "active")

    def add_accounts(self, accounts: list[WaxAccount]) -> None:
        for account in accounts:
            self.add_account(account)

    async def make_transaction(self, actions: List[dict], cpu_usage: int = 0) -> dict:
        trx = {"actions": actions}
        pink_action = {
            "account": "res.pink",
            "name": "noop",
            "authorization": [
                {
                    "actor": "res.pink",
                    "permission": "paybw",
                }
            ],
            "data": {},
        }
        trx["actions"].insert(0, pink_action)

        trx = await self.wax_api.make_transaction_async(trx, cpu_usage=0)

        pink_signature = await self.get_pink_sign_a(list(trx.pack()))
        try:
            resp = await self.wax_api.push_transaction_async(
                trx, extra_signatures=pink_signature
            )
            transaction_id = resp.get("transaction_id")
            log.info(f"Transaction success: transaction_id={transaction_id}")
            return resp
        except Exception as e:
            log.error(f"Transaction failed: {str(e)}")
            return {}

    async def get_pink_sign_a(self, encoded_trx: list[int] ):
        post_data = {"transaction": encoded_trx}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://wax-mainnet-signer.api.atomichub.io/v1/sign",
                    data=post_data,
                    proxy=self.wax_api.proxy_service.get_random_proxy(),
                ) as resp:
                    res = await resp.json()
                    print(res)
                    if not res.get("code"):
                        return res.get("data")[0]
                    if (type(res.get("error")) == type(dict())) and (
                        res.get("error").get("code")
                        not in [
                            3080004,
                            3080002,  # 3050003
                        ]
                    ):
                        return res
                        # break
                    await asyncio.sleep(0.21)
        except Exception as e:
            print("ERROR PINK SIGN!!!", e)
            await asyncio.sleep(5)
            # continue

    async def get_sale_by_id(self, sale_id: str):
        connector = TCPConnector(ssl=False)
        async with ClientSession(connector=connector) as session:
            for attempt in range(4):
                url = f"{self.atomic_api}/atomicmarket/v1/sales/{sale_id}"
                try:
                    async with session.get(
                        url,
                        proxy=self.wax_api.proxy_service.get_random_proxy(),
                        headers=self.headers
                    ) as response:
                        if response.status != 200:
                            response.raise_for_status()
                        response_data = await response.json()
                        log.debug(
                            "Sale data: %s", response_data
                        )

                        return response_data
                except Exception as e:
                    print(
                        f"Request to {url} failed with {e}, retrying in {4 * (2 ** attempt)} seconds..."
                    )
                    await asyncio.sleep(4 * (2**attempt))
                    continue
            raise ValueError(f"Failed to connect to all URLs after 4 attempts each")

    async def get_sales_by_template(self, template_id: str, limit: int = 1, page: int = 1, sort: str = "price", order: str = "asc"):
        connector = TCPConnector(ssl=False)
        async with ClientSession(connector=connector) as session:
            for attempt in range(4):
                url = f"{self.atomic_api}/atomicmarket/v2/sales?state=1&template_id={template_id}&page={page}&limit={limit}&order={order}&sort={sort}"
                try:
                    async with session.get(
                        url,
                        proxy=self.wax_api.proxy_service.get_random_proxy(),
                        headers=self.headers
                    ) as response:
                        if response.status != 200:
                            response.raise_for_status()
                        response_data = await response.json()
                        log.debug(
                            "Sales for template %s: %s", template_id, response_data
                        )
                        return response_data
                except Exception as e:
                    print(
                        f"Request to {url} failed with {e}, retrying in {4 * (2 ** attempt)} seconds..."
                    )
                    await asyncio.sleep(4 * (2**attempt))
                    continue

    def prepare_buy_transaction(self, sale_data: dict, buyer: str) -> dict:
        """
        Подготавливает все необходимые данные для транзакции покупки NFT.

        :param sale_data: Данные по продаже (ответ от API).
        :param buyer: Имя аккаунта покупателя.
        :return: Словарь с действиями и метаданными транзакции
        """
        asset_ids = [asset["asset_id"] for asset in sale_data["assets"]]
        self.current_transaction_assets = asset_ids

        return {
            'actions': self.generate_buy_actions(sale_data, buyer),
            'asset_ids': asset_ids,
            'sale_id': int(sale_data["sale_id"])
        }

    def generate_buy_actions(self, sale_data: dict, buyer: str) -> List[dict]:
        """
        Генерирует экшоны для выполнения транзакции на основе данных запроса sale_id.

        :param sale_data: Данные по продаже (ответ от API).
        :param buyer: Имя аккаунта покупателя.
        :return: Список экшенов.
        """
        sale_id = int(sale_data["sale_id"])
        asset_ids = [asset["asset_id"] for asset in sale_data["assets"]]
        listing_price = f"{int(sale_data['listing_price']) / 10 ** sale_data['price']['token_precision']:.8f} {sale_data['price']['token_symbol']}"
        settlement_symbol = f"{sale_data['price']['token_precision']},{sale_data['price']['token_symbol']}"

        actions = [
            {
                "account": sale_data["market_contract"],
                "name": "assertsale",
                "authorization": [
                    {
                        "actor": buyer,
                        "permission": "active"
                    }
                ],
                "data": {
                    "sale_id": sale_id,
                    "asset_ids_to_assert": asset_ids,
                    "listing_price_to_assert": listing_price,
                    "settlement_symbol_to_assert": settlement_symbol
                }
            },
            {
                "account": sale_data["price"]["token_contract"],
                "name": "transfer",
                "authorization": [
                    {
                        "actor": buyer,
                        "permission": "active"
                    }
                ],
                "data": {
                    "from": buyer,
                    "to": sale_data["market_contract"],
                    "quantity": listing_price,
                    "memo": "deposit"
                }
            },
            {
                "account": sale_data["market_contract"],
                "name": "purchasesale",
                "authorization": [
                    {
                        "actor": buyer,
                        "permission": "active"
                    }
                ],
                "data": {
                    "buyer": buyer,
                    "sale_id": sale_id,
                    "intended_delphi_median": 0,
                    "taker_marketplace": ""
                }
            }
        ]

        return actions

    async def send_nft(self, owner: WaxAccount, new_owner: WaxAccount, nfts: list[str]):
        self.add_accounts([owner, new_owner])
        log.debug("send_nft nfts: %s", nfts)
        trx = {"actions": []}
        action = {
            "account": "atomicassets",
            "name": "transfer",
            "authorization": [
                {
                    "actor": owner.wallet,
                    "permission": "active",
                },
            ],
            "data": {
                "from": owner.wallet,
                "to": new_owner.wallet,
                "asset_ids": nfts,
                "memo": "",
            },
        }
        try:
            # a = 1 / 0
            pink_action = {
                "account": "res.pink",
                "name": "noop",
                "authorization": [
                    {
                        "actor": "res.pink",
                        "permission": "paybw",
                    }
                ],
                "data": {},
            }
            trx["actions"].insert(0, pink_action)
            trx["actions"].append(action)
            log.debug("send_nft trx: %s", trx)
            trx = await self.wax_api.make_transaction_async(trx, cpu_usage=0)

            pink_signature = await self.get_pink_sign_a(list(trx.pack()))
            resp = await self.wax_api.push_transaction_async(
                trx, extra_signatures=pink_signature
            )
        except Exception as e:
            trx = {"actions": [action]}

            resp = await self.sponsor_push_trx(
                trx,
                sponsor=await db.get_wcw_by_wallet(settings.cold_sponsor),
            )

        return resp

    async def byu_nft(self, buyer: WaxAccount, sale_id: list[str]):
        self.add_accounts([owner, new_owner])
        log.debug("send_nft nfts: %s", nfts)
        trx = {"actions": []}
        action = {
            "account": "atomicassets",
            "name": "transfer",
            "authorization": [
                {
                    "actor": owner.wallet,
                    "permission": "active",
                },
            ],
            "data": {
                "from": owner.wallet,
                "to": new_owner.wallet,
                "asset_ids": nfts,
                "memo": "",
            },
        }
        try:
            # a = 1 / 0
            pink_action = {
                "account": "res.pink",
                "name": "noop",
                "authorization": [
                    {
                        "actor": "res.pink",
                        "permission": "paybw",
                    }
                ],
                "data": {},
            }
            trx["actions"].insert(0, pink_action)
            trx["actions"].append(action)
            log.debug("send_nft trx: %s", trx)
            trx = await self.wax_api.make_transaction_async(trx, cpu_usage=0)

            pink_signature = await self.get_pink_sign_a(list(trx.pack()))
            resp = await self.wax_api.push_transaction_async(
                trx, extra_signatures=pink_signature
            )
        except Exception as e:
            trx = {"actions": [action]}

            resp = await self.sponsor_push_trx(
                trx,
                sponsor=await db.get_wcw_by_wallet(settings.cold_sponsor),
            )

        return resp



async def main() -> None:
    db = DB.getInstance()
    buyer = await db.get_wcw_by_wallet('masterflomas')
    print(buyer)
    market_manager = MarketManager()
    market_manager.add_account(buyer)
    # sale_info = await market_manager.get_sale_by_id("165926312")
    # log.debug("Get sale info: %s", json.dumps(sale_info, indent=4, ensure_ascii=False))
    # actions = market_manager.generate_buy_actions(sale_info['data'], "masterflomas")
    # log.debug("Actions: %s", json.dumps(actions, indent=4, ensure_ascii=False))
    # trx = await market_manager.make_transaction(actions)
    # log.info("Trx: %s", trx)
    sd_template_id = "19553"
    sd_sales = await market_manager.get_sales_by_template(sd_template_id, limit=1, page=1, sort="price", order="asc")
    for sd_sale in sd_sales["data"]:

        transaction_data = market_manager.prepare_buy_transaction(sd_sale, "masterflomas")
        log.debug("Actions: %s", json.dumps(transaction_data['actions'], indent=4, ensure_ascii=False))
        trx = await market_manager.make_transaction(transaction_data['actions'])
        log.debug("Trx: %s", json.dumps(trx, indent=4, ensure_ascii=False))
        log.info("Bought asset: %s", market_manager.current_transaction_assets)
        for asset in market_manager.current_transaction_assets:
            try:
                query = """
                insert into mining_tools (nft_id, tool_type, owner)
                values (%s, 'Standard Drill', 'masterflomas')
                """
                await db.execute_query(query, params=(asset,))
                log.info("Инструмент успешно добавлен: NFT ID=%s, тип='Standard Drill', владелец='masterflomas'", asset)
            except Exception as e:
                log.error("Ошибка при добавлении инструмента (NFT ID=%s): %s", asset, str(e))


if __name__ == '__main__':
    log = logging.getLogger(__name__)
    configure_color_logging(level=logging.INFO)
    asyncio.run(main())
