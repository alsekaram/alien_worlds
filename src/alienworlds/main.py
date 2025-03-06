# from app.infrastructure.external.nonce import create_nonce_generator, NonceGeneratorType
#
#
# async def main():
#     nonce_generator = create_nonce_generator(NonceGeneratorType.EXTERNAL)
#     nonce = await nonce_generator.get_nonce(
#         "1eja4.c.wam",
#         "c7b5bc6f9fe8a9970f7ccc22c8ef717f0cd75be1e3ee3c360b9ed26ca0586cd1",
#         0,
#     )
#     print(nonce)
#
#
# if __name__ == "__main__":
#     import asyncio
#
#     asyncio.run(main())

import asyncio
import logging
import datetime

from prometheus_client import start_http_server, Gauge


from eosapi import EosApi

from config.logger_config import configure_color_logging


log = logging.getLogger(__name__)


# Определяем метрику
POOL_VALUE = Gauge('alien_worlds_pool_value',
                   'Pool value for planet by rarity',
                   ['planet', 'rarity'])

# PLANET_POOL = Gauge('planet_pool_tlm', 'Planet pool value in TLM', ['planet', 'pool_type'])


MAX_POOL_VALUE = Gauge('alien_worlds_max_pool_value',
                       'Maximum pool value by rarity',
                       ['planet', 'rarity'])




class PoolServer:
    def __init__(self):
        self.rpc_host = "https://wax.alienworlds.io"
        # self.rpc_host = "https://wax.eosdac.io"
        self.wax_api = EosApi(
            rpc_host=self.rpc_host,
            proxy=("65.21.182.63", 13001, 300),
            yeomen_proxy=("65.21.182.63", 13001, 300),
        )
        self.pools_data = {
            "magor": {},
            "neri": {},
            "veles": {},
            "eyeke": {},
            "naron": {},
            "kavian": {},
        }

    def _process_pools_data(self, planet_name, response_data):
        """Обработка данных пулов"""
        if response_data["rows"]:
            pools = {}
            for bucket in response_data["rows"][0]["pool_buckets"]:
                pool_name = bucket["key"]
                pool_value = float(bucket["value"].replace(" TLM", ""))
                pools[pool_name] = pool_value

            self.pools_data[planet_name] = pools

    def get_max_pool_planet(self, rarity):
        """
        Получить планету с максимальным текущим значением пула указанной редкости

        Args:
            rarity (str): Тип редкости ('Abundant', 'Common', 'Epic', 'Legendary', 'Mythical', 'Rare')

        Returns:
            tuple: (планета, значение) или (None, 0) если данных нет
        """
        max_value = 0
        max_planet = None

        for planet, pools in self.pools_data.items():
            if rarity in pools:
                if pools[rarity] > max_value:
                    max_value = pools[rarity]
                    max_planet = planet

        return max_planet, max_value

    def get_all_planets_pool(self, rarity):
        """
        Получить значения пула указанной редкости для всех планет

        Args:
            rarity (str): Тип редкости

        Returns:
            dict: {планета: значение}
        """
        return {planet: data.get(rarity, 0) for planet, data in self.pools_data.items()}

    def get_sorted_planets_by_pool(self, rarity):
        """
        Получить отсортированный список планет по убыванию значения указанного пула

        Args:
            rarity (str): Тип редкости

        Returns:
            list: [(планета, значение), ...]
        """
        planet_pools = [
            (planet, data.get(rarity, 0)) for planet, data in self.pools_data.items()
        ]
        return sorted(planet_pools, key=lambda x: x[1], reverse=True)

    async def pool_monitor(self, delay_seconds=0.15):
        planets = ["magor", "neri", "veles", "eyeke", "naron", "kavian"]

        while True:
            try:
                tasks = [self.get_planet_pools_data(planet) for planet in planets]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Логируем результаты сразу после получения
                # for planet, data in zip(planets, results):
                #     log.debug(f"Получены данные для {planet}: {data}")

                max_values = {}

                # Обработка полученных данных
                for planet, data in zip(planets, results):
                    if isinstance(data, Exception):
                        log.error("Ошибка запроса для планеты %s: %s", planet, data)
                        continue

                    if data and 'rows' in data and data['rows']:
                        for bucket in data['rows'][0].get('pool_buckets', []):
                            rarity = bucket.get('key')
                            value = float(bucket.get('value', '0.0000 TLM').split()[0])
                            # print(
                            #     f"{planet} {rarity}: {value:.4f} TLM")
                            POOL_VALUE.labels(
                                planet=planet,
                                rarity=rarity
                            ).set(value)

                            if rarity not in max_values or value > max_values[rarity]:
                                max_values[rarity] = value

                # log.info(max_values)
                timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:23]
                print(f"[{timestamp_str}] main:158   INFO - {max_values}")
                # for rarity, max_value in max_values.items():
                #     MAX_POOL_VALUE.labels(rarity=rarity).set(max_value)

                await asyncio.sleep(delay_seconds)

            except Exception as e:
                log.error(f"Ошибка в pool_monitor: {e}")
                await asyncio.sleep(delay_seconds)

    async def get_planet_pools_data(self, planet_name):
        """
        Получение актуальных данных о пулах для конкретной планеты

        Args:
            planet_name (str): Название планеты
        """
        payload = {
            "json": True,
            "code": "m.federation",
            "scope": f"{planet_name}.world",
            "table": "pools",
            "key_type": "",
            "index_position": 1,
            "lower_bound": "",
            "upper_bound": "",
            "limit": 1,
        }

        try:
            resp = await self.wax_api.get_table_rows_async(payload)
            log.debug("%s pools: %s", planet_name, resp)
            self._process_pools_data(planet_name, resp)
            return resp
        except Exception as e:
            log.error("Ошибка при получении данных для планеты %s: %s", planet_name, e)


async def main():
    pool_server = PoolServer()
    # Запускаем мониторинг в фоновом режиме
    monitor_task = asyncio.create_task(pool_server.pool_monitor())

    try:
        # Здесь можно выполнять другие асинхронные операции
        while True:
            # Например, проверять максимальные значения каждые 10 секунд
            planet, value = pool_server.get_max_pool_planet("Rare")
            print(f"Максимальный Rare пул: {planet} - {value} TLM")
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        # Обработка Ctrl+C для корректного завершения
        print("\nЗавершение работы...")
    finally:
        # Если используете второй вариант с флагом
        # await pool_server.stop_monitoring()
        monitor_task.cancel()  # Отменяем задачу мониторинга
        try:
            await monitor_task  # Ждем завершения
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    log = logging.getLogger(__name__)
    configure_color_logging(level=logging.INFO)
    start_http_server(8001)

    asyncio.run(main())
