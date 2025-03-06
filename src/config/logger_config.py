from typing import Any
import logging
import colorlog

# Добавляем новый уровень логирования
MINE_LEVEL = 25
logging.addLevelName(MINE_LEVEL, "MINE")


# Добавляем метод для логирования на уровне MINE
def mine(self, message, *args, **kwargs):
    if self.isEnabledFor(MINE_LEVEL):
        # Указываем stacklevel=2, чтобы правильно показывать место вызова лога
        self._log(MINE_LEVEL, message, args, **kwargs, stacklevel=2)


# Объявляем тип для Logger
class CustomLogger(logging.Logger):
    def mine(self, message: object, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(MINE_LEVEL):
            self._log(MINE_LEVEL, message, args, **kwargs, stacklevel=2)


# Регистрируем новый класс логгера
logging.setLoggerClass(CustomLogger)


def configure_color_logging(level=logging.WARNING):
    """
    Настраивает цветное логирование с добавлением кастомного уровня MINE.
    """
    # Создаем цветной форматер с использованием формата
    formatter = colorlog.ColoredFormatter(
        "[%(asctime)s.%(msecs)03d]%(module)5s:%(lineno)-3d%(log_color)s%(levelname)7s%(reset)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
            "MINE": "blue",  # Добавляем цвет для уровня MINE
        },
    )

    # Создаем обработчик для вывода логов в консоль
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Получаем корневой логгер и назначаем ему обработчик
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(level)
