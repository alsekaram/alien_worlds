# Alien Worlds Pool Monitoring

Система мониторинга пулов Alien Worlds с метриками Prometheus, визуализацией в Grafana и обратным прокси Caddy.

## Быстрый старт (локально)

### 1. Подготовка секретов
```bash
# Создать секреты из примеров
mkdir -p secrets
cp secrets-example/grafana_admin_user.txt.example secrets/grafana_admin_user.txt
cp secrets-example/grafana_admin_password.txt.example secrets/grafana_admin_password.txt

# Сгенерировать сильный пароль для Grafana
openssl rand -base64 24 > secrets/grafana_admin_password.txt
chmod 600 secrets/grafana_admin_*.txt
```

### 2. Настройка окружения
```bash
# Создать .env файл для локальной работы
cp env.example .env
# Очистить DOMAIN для локального режима
sed -i '' 's/^DOMAIN=.*/DOMAIN=/' .env
```

**Для локальной работы:**
- Оставьте `DOMAIN` пустым - будет использоваться localhost:8080
- `ACME_EMAIL` можно не менять для локалки

### 3. Запуск
```bash
docker compose up -d
```

### 4. Доступ к сервисам
- **Grafana**: http://localhost:8080 (через Caddy) или http://localhost:3000 (напрямую)
- **Prometheus**: http://localhost:9090
- **Приложение**: http://localhost:8000

### 5. Вход в Grafana
- Логин: `admin`
- Пароль: содержимое файла `secrets/grafana_admin_password.txt`

```bash
# Посмотреть пароль
cat secrets/grafana_admin_password.txt
```

## Деплой в продакшн

### 1. Подготовка сервера
```bash
# Установить Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Открыть порты в firewall (пример для ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
```

### 2. Настройка DNS
Создайте A-запись, указывающую ваш домен на публичный IP сервера:
```
your-domain.com → 1.2.3.4
```

### 3. Клонирование и настройка
```bash
git clone https://github.com/alsekaram/alien_worlds.git
cd alien_worlds

# Создать секреты
mkdir -p secrets
cp secrets-example/grafana_admin_user.txt.example secrets/grafana_admin_user.txt
openssl rand -base64 32 > secrets/grafana_admin_password.txt
chmod 600 secrets/grafana_admin_*.txt
```

### 4. Настройка домена и email
```bash
cp env.example .env
# Отредактировать .env файл
nano .env
```

Заполните переменные:
```env
DOMAIN=your-domain.com
ACME_EMAIL=admin@your-domain.com
```

## Переменные окружения (.env)

### Основные настройки

| Переменная | Описание | Пример | По умолчанию | Обязательно |
|------------|----------|---------|--------------|-------------|
| `DOMAIN` | Домен для доступа к Grafana через HTTPS | `monitoring.company.com` | - | Только для прода |
| `ACME_EMAIL` | Email для Let's Encrypt сертификатов | `admin@company.com` | `admin@example.com` | Только для прода |

### Настройки WAX API

| Переменная | Описание | Пример | По умолчанию |
|------------|----------|---------|--------------|
| `WAX_RPC_HOST` | URL WAX RPC сервера | `https://wax.greymass.com` | `https://wax.greymass.com` |

### Настройки прокси (опционально)

| Переменная | Описание | Пример | По умолчанию |
|------------|----------|---------|--------------|
| `PROXY_HOST` | Хост прокси сервера | `proxy.example.com` | - |
| `PROXY_PORT` | Порт прокси сервера | `8080` | `0` (отключен) |
| `PROXY_NUM_WORKERS` | Количество воркеров прокси | `5` | `1` |

### Настройки мониторинга

| Переменная | Описание | Пример | По умолчанию |
|------------|----------|---------|--------------|
| `POOL_MONITOR_DELAY` | Интервал обновления данных (сек) | `1.0` | `0.5` |
| `DISPLAY_INTERVAL` | Интервал вывода информации (сек) | `2.0` | `0.5` |
| `DISPLAY_MODE` | Режим отображения (`max` или `all`) | `all` | `max` |

### Технические переменные

| Переменная | Описание | Значение |
|------------|----------|----------|
| `PYTHONUNBUFFERED` | Отключение буферизации Python | `1` |
| `PYTHONPATH` | Путь к модулям Python | `/app` |

### Автоматические переменные Grafana
- `GF_SERVER_ROOT_URL` - URL корня Grafana (https://${DOMAIN} в продакшн)
- `GF_SERVER_DOMAIN` - домен Grafana (${DOMAIN} в продакшн)
- `GF_SECURITY_ADMIN_USER__FILE` - путь к файлу с логином админа
- `GF_SECURITY_ADMIN_PASSWORD__FILE` - путь к файлу с паролем админа

### 5. Запуск в продакшн
```bash
docker compose up -d
```

### 6. Проверка
- Откройте https://your-domain.com
- Проверьте валидность SSL сертификата
- Войдите в Grafana с логином `admin` и паролем из `secrets/grafana_admin_password.txt`

## Управление секретами

### Смена пароля Grafana
Если admin пользователь уже создан, изменение файла секрета не изменит пароль автоматически.

**Вариант 1: Через API**
```bash
# Узнать текущий пароль
OLD_PASSWORD=$(cat secrets/grafana_admin_password.txt)

# Сгенерировать новый
openssl rand -base64 32 > secrets/grafana_admin_password.txt
NEW_PASSWORD=$(cat secrets/grafana_admin_password.txt)

# Сменить через API
curl -u admin:$OLD_PASSWORD \
  -X PUT http://localhost:3000/api/user/password \
  -H 'Content-Type: application/json' \
  -d "{\"oldPassword\":\"$OLD_PASSWORD\",\"newPassword\":\"$NEW_PASSWORD\",\"confirmNew\":\"$NEW_PASSWORD\"}"
```

**Вариант 2: Полный сброс** (потеряются настройки Grafana)
```bash
docker compose down
docker volume ls | grep grafana  # найти имя тома
docker volume rm <имя_тома_grafana>
docker compose up -d
```

## Структура проекта

```
alien_worlds/
├── docker-compose.yml          # Основная конфигурация сервисов
├── Dockerfile                  # Образ приложения
├── env.example                # Пример переменных окружения
├── secrets-example/           # Примеры файлов секретов
│   ├── grafana_admin_user.txt.example
│   └── grafana_admin_password.txt.example
├── secrets/                   # Реальные секреты (не в git)
├── caddy/
│   └── Caddyfile             # Конфигурация reverse proxy Caddy
├── grafana/
│   ├── dashboards/           # JSON дашборды
│   └── provisioning/         # Настройки провизионинга
├── prometheus/
│   └── prometheus.yml        # Конфигурация Prometheus
└── src/                      # Исходный код приложения
```

## Мониторинг и логи

### Просмотр логов
```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f grafana
docker compose logs -f caddy
docker compose logs -f prometheus
```

### Статус сервисов
```bash
docker compose ps
```

### Ресурсы контейнеров
```bash
docker stats
```

## Безопасность

### Рекомендации
1. **Смените пароль Grafana** после первого входа
2. **Настройте файрвол** - открывайте только необходимые порты
3. **Регулярно обновляйте** образы контейнеров
4. **Настройте резервное копирование** томов с данными

### Обновление образов
```bash
docker compose pull
docker compose up -d --remove-orphans
```

### Резервное копирование
```bash
# Создать бэкап данных Grafana и Prometheus
docker run --rm -v alien_worlds_grafana_data:/data -v $(pwd):/backup ubuntu tar czf /backup/grafana-backup.tar.gz /data
docker run --rm -v alien_worlds_prometheus_data:/data -v $(pwd):/backup ubuntu tar czf /backup/prometheus-backup.tar.gz /data
```

## Troubleshooting

### Проблемы с SSL
- Убедитесь, что домен указывает на правильный IP
- Проверьте, что порты 80/443 открыты и доступны из интернета
- Посмотрите логи Caddy: `docker compose logs caddy`

### Grafana недоступна
- Проверьте статус контейнера: `docker compose ps grafana`
- Посмотрите логи: `docker compose logs grafana`
- Убедитесь, что файлы секретов существуют и доступны для чтения

### Prometheus не собирает метрики
- Проверьте конфигурацию в `prometheus/prometheus.yml`
- Убедитесь, что приложение экспортирует метрики на `/metrics`
- Посмотрите логи: `docker compose logs prometheus`

## Контакты

Для вопросов и предложений создавайте issues в репозитории.