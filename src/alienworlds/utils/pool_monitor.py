import asyncio
import logging
from dotenv import load_dotenv
import os

from eosapi import EosApi

from src.config.logger_config import configure_color_logging
from src.alienworlds.metrics import POOL_VALUE, MAX_POOL_VALUE

# Загрузка переменных окружения
load_dotenv()

# Константы из переменных окружения
WAX_RPC_HOST = os.getenv('WAX_RPC_HOST')
PROXY_HOST = os.getenv('PROXY_HOST')
PROXY_PORT = int(os.getenv('PROXY_PORT', 0))
PROXY_NUM_WORKERS = int(os.getenv('PROXY_NUM_WORKERS', 1))

# Добавляем настройку задержки через переменную окружения
POOL_MONITOR_DELAY = float(os.getenv('POOL_MONITOR_DELAY', 0.5))  # Как часто обновляем данные (секунды)
DISPLAY_INTERVAL = float(os.getenv('DISPLAY_INTERVAL', 0.5))  # Как часто выводим информацию (секунды)

# Список планет и типов редкости для избежания дублирования
PLANETS = ["magor", "neri", "veles", "eyeke", "naron", "kavian"]
RARITIES = ["Abundant", "Common", "Epic", "Legendary", "Mythical", "Rare"]


log = logging.getLogger(__name__)


class PoolServer:
    """Сервер для мониторинга данных о пулах планет."""

    def __init__(self):
        """Инициализация сервера."""
        self.rpc_host = WAX_RPC_HOST  # Используем константу вместо повторного присваивания
        log.info(f"Инициализация с WAX RPC: {self.rpc_host}")

        # Проверяем настройки прокси
        proxy_config = None
        if PROXY_HOST and PROXY_PORT > 0:
            proxy_config = (PROXY_HOST, PROXY_PORT, PROXY_NUM_WORKERS)
            log.info(f"Используем прокси: {PROXY_HOST}:{PROXY_PORT}")

        try:
            self.wax_api = EosApi(
                rpc_host=self.rpc_host,
                proxy=proxy_config,
                yeomen_proxy=proxy_config,
            )
            log.info("API клиент WAX инициализирован успешно")
        except Exception as e:
            log.error(f"Ошибка инициализации API клиента WAX: {e}")
            raise

        # Инициализируем словарь для всех планет сразу
        self.pools_data = {planet: {} for planet in PLANETS}
        self._running = False  # Флаг для управления циклом мониторинга
        self.data_loaded = False  # Флаг, указывающий, что данные были загружены хотя бы раз

    def _process_pools_data(self, planet_name, response_data):
        """
        Обработка данных пулов.

        Args:
            planet_name (str): Название планеты.
            response_data (dict): Ответ от API с данными о пулах.
        """
        if not response_data.get("rows"):
            log.warning(f"Нет данных о пулах для планеты {planet_name}")
            return

        pools = {}
        for bucket in response_data["rows"][0]["pool_buckets"]:
            pool_name = bucket["key"]
            pool_value = float(bucket["value"].replace(" TLM", ""))
            pools[pool_name] = pool_value

            # Обновляем метрику для каждого пула
            POOL_VALUE.labels(planet=planet_name, rarity=pool_name).set(pool_value)
            log.debug(f"Обновлена метрика для {planet_name} {pool_name}: {pool_value}")

        self.pools_data[planet_name] = pools

        # Обновляем метрики максимальных значений
        for rarity in RARITIES:
            max_planet, max_value = self.get_max_pool_planet(rarity)
            if max_planet and max_value > 0:
                MAX_POOL_VALUE.labels(planet=max_planet, rarity=rarity).set(max_value)
                log.debug(f"Обновлена максимальная метрика для {rarity}: {max_planet} - {max_value}")

    def get_max_pool_planet(self, rarity):
        """
        Получить планету с максимальным текущим значением пула указанной редкости.

        Args:
            rarity (str): Тип редкости ('Abundant', 'Common', 'Epic', 'Legendary', 'Mythical', 'Rare').

        Returns:
            tuple: (планета, значение) или (None, 0) если данных нет.
        """
        max_value = 0
        max_planet = None

        for planet, pools in self.pools_data.items():
            if rarity in pools and pools[rarity] > max_value:
                max_value = pools[rarity]
                max_planet = planet

        return max_planet, max_value

    def get_all_planets_pool(self, rarity):
        """
        Получить значения пула указанной редкости для всех планет.

        Args:
            rarity (str): Тип редкости.

        Returns:
            dict: {планета: значение}.
        """
        return {planet: data.get(rarity, 0) for planet, data in self.pools_data.items()}

    def get_sorted_planets_by_pool(self, rarity):
        """
        Получить отсортированный список планет по убыванию значения указанного пула.

        Args:
            rarity (str): Тип редкости.

        Returns:
            list: [(планета, значение), ...].
        """
        planet_pools = [
            (planet, data.get(rarity, 0)) for planet, data in self.pools_data.items()
        ]
        return sorted(planet_pools, key=lambda x: x[1], reverse=True)

    async def start_monitoring(self, delay_seconds=None):
        """
        Запустить мониторинг пулов планет.

        Args:
            delay_seconds (float, optional): Задержка между обновлениями в секундах.
                По умолчанию используется POOL_MONITOR_DELAY.
        """
        if delay_seconds is None:
            delay_seconds = POOL_MONITOR_DELAY

        self._running = True
        await self.pool_monitor(delay_seconds)

    def stop_monitoring(self):
        """Остановить мониторинг пулов."""
        self._running = False
        log.info("Остановка мониторинга пулов")

    async def pool_monitor(self, delay_seconds=0.5):
        """
        Мониторинг пулов планет.

        Args:
            delay_seconds (float): Задержка между обновлениями в секундах.
        """
        log.info(f"Запуск мониторинга пулов с интервалом {delay_seconds} секунд")

        while self._running:
            try:
                tasks = [self.get_planet_pools_data(planet) for planet in PLANETS]
                await asyncio.gather(*tasks)

                # Проверяем, есть ли данные хотя бы для одной планеты
                has_data = any(bool(pools) for pools in self.pools_data.values())
                if has_data:
                    self.data_loaded = True
                    log.info("Данные по пулам успешно получены")

                    # Логируем максимальные значения для каждого типа редкости
                    for rarity in RARITIES:
                        max_planet, max_value = self.get_max_pool_planet(rarity)
                        if max_planet:
                            log.info(f"MAX {rarity}: {max_planet} - {max_value} TLM")
                else:
                    log.warning("Нет данных ни по одной планете")

            except asyncio.CancelledError:
                log.info("Мониторинг пулов отменен")
                break
            except Exception as e:
                log.error("Ошибка в pool_monitor: %s", e, exc_info=True)

            # Ждем указанное время перед следующей итерацией
            await asyncio.sleep(delay_seconds)

    async def get_planet_pools_data(self, planet_name):
        """
        Получение актуальных данных о пулах для конкретной планеты.

        Args:
            planet_name (str): Название планеты.
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
        except Exception as e:
            log.error("Ошибка при получении данных для планеты %s: %s", planet_name, e)
            # Очищаем данные для этой планеты, чтобы не использовать устаревшие
            self.pools_data[planet_name] = {}


async def main():
    """Основная функция программы."""
    # Настройка логирования
    configure_color_logging(level=logging.INFO)

    pool_server = PoolServer()

    # Запускаем мониторинг в фоновом режиме
    monitor_task = asyncio.create_task(pool_server.start_monitoring())

    try:
        # Здесь можно выполнять другие асинхронные операции
        display_mode = os.getenv('DISPLAY_MODE', 'max').lower()  # 'max' или 'all'
        loading_message_shown = False

        while True:
            # Проверяем, загружены ли данные
            if not pool_server.data_loaded:
                if not loading_message_shown:
                    log.info("Ожидание загрузки данных о пулах...")
                    loading_message_shown = True
                await asyncio.sleep(1)  # Короткая задержка при ожидании загрузки
                continue

            if display_mode == 'max':
                # Выводим только максимальные значения
                log.info("Текущие максимальные пулы:")
                for rarity in RARITIES:
                    planet, value = pool_server.get_max_pool_planet(rarity)
                    if value > 0:  # Проверяем, что значение не нулевое
                        log.info("%s: %s - %.4f TLM", rarity, planet, value)
                    else:
                        log.info("%s: нет данных", rarity)
            else:
                # Выводим все данные по всем планетам
                log.info("Текущие значения пулов по планетам:")
                for rarity in RARITIES:
                    log.info("-" * 50)
                    log.info("Пул %s:", rarity)
                    sorted_planets = pool_server.get_sorted_planets_by_pool(rarity)
                    if not any(value > 0 for _, value in sorted_planets):
                        log.info("  Нет данных")
                        continue
                    for planet, value in sorted_planets:
                        if value > 0:  # Показываем только ненулевые значения
                            log.info("  %s: %.4f TLM", planet, value)

            await asyncio.sleep(DISPLAY_INTERVAL)
    except KeyboardInterrupt:
        # Обработка Ctrl+C для корректного завершения
        print("\nЗавершение работы...")
    except Exception as e:
        log.error("Ошибка в основном цикле: %s", e, exc_info=True)
    finally:
        # Останавливаем мониторинг
        pool_server.stop_monitoring()
        # Отменяем задачу мониторинга
        monitor_task.cancel()
        try:
            await monitor_task  # Ждем завершения
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())