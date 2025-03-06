import asyncio
import logging

from prometheus_client import start_http_server

from src.alienworlds.metrics import POOL_VALUE, MAX_POOL_VALUE  # Импортируем из отдельного модуля
from src.alienworlds.utils.pool_monitor import PoolServer
from src.config.logger_config import configure_color_logging


log = logging.getLogger(__name__)


async def main():
    log.info("Запуск мониторинга пулов Alien Worlds")

    # Запускаем HTTP сервер для метрик Prometheus
    log.info("Запуск сервера метрик Prometheus на порту 8000")
    start_http_server(8000)

    pool_server = PoolServer()
    # Запускаем мониторинг в фоновом режиме
    monitor_task = asyncio.create_task(pool_server.start_monitoring())

    try:
        # Здесь можно выполнять другие асинхронные операции
        while True:
            # Например, проверять максимальные значения каждые 10 секунд
            for rarity in ["Abundant", "Common", "Rare", "Epic", "Legendary", "Mythical"]:
                planet, value = pool_server.get_max_pool_planet(rarity)
                if planet and value > 0:
                    log.info(f"Максимальный {rarity} пул: {planet} - {value} TLM")
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        # Обработка Ctrl+C для корректного завершения
        log.info("\nЗавершение работы...")
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

    # НЕ запускаем start_http_server здесь, чтобы избежать его запуска дважды
    # start_http_server перенесён в функцию main()

    asyncio.run(main())