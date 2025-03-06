import asyncio
import logging

from prometheus_client import start_http_server, Gauge

from src.alienworlds.utils.pool_monitor import PoolServer

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







async def main():
    pool_server = PoolServer()
    # Запускаем мониторинг в фоновом режиме
    monitor_task = asyncio.create_task(pool_server.start_monitoring())

    try:
        # Здесь можно выполнять другие асинхронные операции
        while True:
            # Например, проверять максимальные значения каждые 10 секунд
            planet, value = pool_server.get_max_pool_planet("Rare")
            print(f"Максимальный Rare пул: {planet} - {value} TLM")
            await asyncio.sleep(0.5)
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
