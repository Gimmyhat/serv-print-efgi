# Сервис генерации PDF из шаблонов DOCX

Сервис для генерации PDF-документов на основе DOCX-шаблонов с использованием LibreOffice для конвертации. 
Поддерживает работу как в локальном Docker-окружении, так и в кластере Kubernetes.

## Особенности

- Генерация PDF из DOCX-шаблонов с использованием LibreOffice
- Поддержка больших файлов и данных
- Оптимизированная работа с памятью
- Единые настройки для локального и Kubernetes окружений
- Расширенное логирование с уникальными идентификаторами запросов
- Автоматическая очистка временных файлов
- Поддержка CORS и сжатия данных
- Prometheus метрики для мониторинга
- Grafana дашборды для визуализации метрик
- Подробная трассировка ошибок с контекстом

## Требования

- Docker
- Python 3.11+
- LibreOffice
- Kubernetes (для production)
- Prometheus и Grafana (для мониторинга)

## Структура проекта

```
.
├── app.py                # Основной код приложения
├── Dockerfile            # Конфигурация Docker образа
├── requirements.txt      # Python зависимости
├── templates/            # Директория с DOCX шаблонами
├── k8s/                 # Конфигурации Kubernetes
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── monitoring/          # Конфигурации мониторинга
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── prometheus-rbac.yaml
│   └── grafana/
│       └── dashboards/
├── docker-compose.monitoring.yml  # Конфигурация для локального мониторинга
├── deploy.ps1           # Скрипт развертывания в Kubernetes
└── run_local.ps1        # Скрипт для локального запуска
```

## Локальный запуск

1. Убедитесь, что Docker установлен и запущен
2. Поместите ваш DOCX шаблон в директорию `templates/` с именем `template.docx`
3. Запустите скрипт:

```powershell
.\run_local.ps1
```

Сервис будет доступен по адресу: http://localhost:8005

## Развертывание в Kubernetes

1. Убедитесь, что у вас есть доступ к кластеру Kubernetes
2. Настройте переменные окружения для доступа к кластеру
3. Запустите скрипт развертывания:

```powershell
.\deploy.ps1
```

## Конфигурация

### Ресурсы контейнера

- Memory: 2GB
- CPU: 2 cores
- Temporary storage: 1GB

### Переменные окружения

- `TZ`: Временная зона (по умолчанию "Europe/Moscow")
- `PYTHONUNBUFFERED`: Отключение буферизации Python (1)
- `TMPDIR`: Директория для временных файлов (/app/temp)
- `LIBREOFFICE_PATH`: Путь к LibreOffice (/usr/bin/soffice)
- `SAL_USE_VCLPLUGIN`: Настройка LibreOffice для работы без GUI (svp)

### Настройки приложения

- Один воркер для предотвращения конфликтов
- Таймаут keep-alive: 300 секунд
- Размер backlog: 2048
- Отключены лимиты на размер запросов
- Включено подробное логирование

## API Endpoints

### POST /generate-pdf

Генерирует PDF документ на основе шаблона и переданных данных.

**Параметры (один из следующих способов):**
- `file`: JSON файл с данными для шаблона (multipart/form-data)
- `data`: JSON строка с данными для шаблона (в query параметре)
- JSON данные в теле запроса (application/json)

**Примеры запросов:**

1. Загрузка файла:
```bash
curl -X POST "http://localhost:8005/generate-pdf" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@data.json"
```

2. Через query параметр:
```bash
curl -X POST "http://localhost:8005/generate-pdf" \
     -H "Content-Type: application/json" \
     -d '{"applicantType":"ORGANIZATION",...}'
```

3. В теле запроса:
```bash
curl -X POST "http://localhost:8005/generate-pdf?data={"applicantType":"ORGANIZATION",...}"
```

При использовании Swagger UI (/docs) вы можете:
1. Загрузить JSON файл через поле "file"
2. Ввести JSON строку в поле "data"
3. Оставить оба поля пустыми и отправить данные в теле запроса

### GET /health

Проверка работоспособности сервиса.

## Мониторинг и логирование

### Логирование

- Уникальные идентификаторы для каждого запроса
- Подробное логирование всех этапов обработки
- Контекстная информация в логах (IP клиента, заголовки, тело запроса)
- Трассировка ошибок с полным стеком
- Форматирование логов в JSON для production окружения

### Prometheus метрики

- `pdf_conversion_errors_total` - количество ошибок конвертации
- `request_processing_duration_seconds` - время обработки запросов
- `temp_files_count` - количество временных файлов
- `memory_usage_bytes` - использование памяти
- `http_requests_total` - общее количество запросов

### Grafana дашборды

- Общее количество обработанных файлов
- Количество ошибок по окружениям
- Среднее время обработки
- Частота запросов
- Использование ресурсов

### Просмотр логов

1. Просмотр всех логов:
   ```bash
   kubectl logs -l app=serv-print-efgi
   ```

2. Фильтрация по ошибкам:
   ```bash
   kubectl logs -l app=serv-print-efgi | grep "error"
   ```

3. Поиск конкретного запроса по ID:
   ```bash
   kubectl logs -l app=serv-print-efgi | grep "pdf_20250202_104410"
   ```

4. Просмотр логов конвертации:
   ```bash
   kubectl logs -l app=serv-print-efgi -f | findstr "convert Converting processing Processing"
   ```

## Устранение неполадок

1. Проверьте логи приложения с фильтрацией по ошибкам:
   ```bash
   kubectl logs -l app=serv-print-efgi | grep "error"
   ```

2. Найдите конкретный запрос по ID:
   ```bash
   kubectl logs -l app=serv-print-efgi | grep "pdf_YYYYMMDD_HHMMSS"
   ```

3. Проверьте метрики в Prometheus:
   ```
   http://localhost:9090/targets
   ```

4. Просмотрите дашборды в Grafana:
   ```
   http://localhost:3000
   ```

## Лицензия

MIT