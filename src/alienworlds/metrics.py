"""
Модуль, содержащий определения метрик Prometheus для мониторинга пулов Alien Worlds.
"""
from prometheus_client import Gauge

# Определяем метрику для значения пула TLM по планете и редкости
POOL_VALUE = Gauge('alien_worlds_pool_value',
                   'Pool value for planet by rarity',
                   ['planet', 'rarity'])

# Определяем метрику для максимального значения пула TLM по редкости
MAX_POOL_VALUE = Gauge('alien_worlds_max_pool_value',
                       'Maximum pool value by rarity',
                       ['planet', 'rarity'])
