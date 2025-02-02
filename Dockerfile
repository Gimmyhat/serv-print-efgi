FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN useradd -m -u 1000 appuser

# Создание директорий и настройка прав
RUN mkdir -p /app /app/templates /home/appuser/temp && \
    chown -R appuser:appuser /app /home/appuser && \
    chmod -R 755 /app && \
    chmod 1777 /home/appuser/temp

# Настройка рабочей директории
WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY app.py .
COPY templates/ templates/

# Настройка прав доступа
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod 644 /app/app.py && \
    mkdir -p /home/appuser/.config/libreoffice && \
    chown -R appuser:appuser /home/appuser/.config

# Настройка переменных окружения
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Moscow
ENV TMPDIR=/home/appuser/temp
ENV SAL_USE_VCLPLUGIN=svp
ENV HOME=/home/appuser
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Настройка ulimit для процесса
RUN echo "* soft nofile 65535" >> /etc/security/limits.conf && \
    echo "* hard nofile 65535" >> /etc/security/limits.conf

# Переключение на пользователя appuser
USER appuser

# Запуск приложения с оптимизированными настройками
CMD ["python", "app.py"] 