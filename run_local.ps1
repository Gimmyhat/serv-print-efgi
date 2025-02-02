# Остановка и удаление старого контейнера
$containerName = "serv-print-efgi-local"
docker stop $containerName 2>$null
docker rm $containerName 2>$null

# Сборка образа
Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t serv-print-efgi:local .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error building Docker image" -ForegroundColor Red
    exit 1
}

# Запуск с настройками, идентичными Kubernetes
Write-Host "Starting container..." -ForegroundColor Green
docker run --rm `
    --name $containerName `
    -p 8005:8005 `
    --memory=2g `
    --memory-reservation=2g `
    --memory-swap=2g `
    --cpus=2 `
    --ulimit nofile=65535:65535 `
    -e TZ=Europe/Moscow `
    -e PYTHONUNBUFFERED=1 `
    -e TMPDIR=/app/temp `
    -e LIBREOFFICE_PATH=/usr/bin/soffice `
    -e SAL_USE_VCLPLUGIN=svp `
    -v "${PWD}/templates:/app/templates:ro" `
    --health-cmd="curl -f http://localhost:8005/health || exit 1" `
    --health-interval=15s `
    --health-timeout=10s `
    --health-retries=3 `
    --health-start-period=30s `
    serv-print-efgi:local

Write-Host "`nContainer stopped" -ForegroundColor Yellow 