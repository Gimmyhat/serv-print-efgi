# Настройка кодировки для корректного отображения русских символов
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Сборка и деплой сервиса serv-print-efgi"

# Получаем текущую дату для тега образа
$dateTag = Get-Date -Format "yyyyMMdd-HHmmss"
$imageName = "gimmyhat/serv-print-efgi:$dateTag"

Write-Host "Сборка Docker образа с тегом $imageName"
docker build -t $imageName .

Write-Host "Отправка образа в Docker Hub"
docker push $imageName

Write-Host "Обновление тега образа в deployment.yaml"
$deploymentFile = "k8s/deployment.yaml"
$content = Get-Content $deploymentFile -Raw -Encoding UTF8
$content = $content -replace "image: gimmyhat/serv-print-efgi:.*", "image: $imageName"
$content | Set-Content $deploymentFile -Encoding UTF8

Write-Host "Применение конфигураций Kubernetes"

# Применяем секреты и конфигурации мониторинга
Write-Host "Применение конфигураций мониторинга..."
kubectl apply -f k8s/telegram-secret.yaml
kubectl apply -f k8s/alertmanager-config.yaml
kubectl apply -f k8s/servicemonitor.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/prometheus-rules.yaml

# Применяем основной деплоймент
Write-Host "Применение deployment..."
kubectl apply -f k8s/deployment.yaml

Write-Host "Ожидание развертывания..."
kubectl rollout status deployment/serv-print-efgi

Write-Host "Проверка статуса подов..."
kubectl get pods -l app=serv-print-efgi

Write-Host "Деплой завершен"

# Проверка наличия Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running or not installed" -ForegroundColor Red
    exit 1
}

# Проверка подключения к кластеру
Write-Host "Checking Kubernetes connection..." -ForegroundColor Yellow
kubectl cluster-info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Cannot connect to Kubernetes cluster" -ForegroundColor Red
    exit 1
}

# Также тегаем как latest
docker tag $imageName gimmyhat/serv-print-efgi:latest

# Публикация образов в DockerHub
Write-Host "Pushing Docker images to DockerHub..." -ForegroundColor Green
docker push $imageName
docker push gimmyhat/serv-print-efgi:latest
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error pushing Docker image" -ForegroundColor Red
    exit 1
}

# Проверка наличия namespace
$NAMESPACE = "default"  # Измените на ваш namespace, если используете другой
Write-Host "Checking namespace access..." -ForegroundColor Yellow
kubectl auth can-i create deployments --namespace=$NAMESPACE > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Limited permissions in namespace $NAMESPACE" -ForegroundColor Yellow
}

# Применение манифестов Kubernetes
Write-Host "Applying Kubernetes manifests..." -ForegroundColor Green

# Применяем манифесты с проверкой ошибок
$manifests = @(
    "k8s/deployment.yaml",
    "k8s/service.yaml",
    "k8s/ingress.yaml"
)

foreach ($manifest in $manifests) {
    Write-Host "Applying $manifest..." -ForegroundColor Yellow
    kubectl apply -f $manifest
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error applying $manifest" -ForegroundColor Red
        exit 1
    }
}

# Ожидание готовности подов
Write-Host "Waiting for pods to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=serv-print-efgi --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Timeout waiting for pods" -ForegroundColor Yellow
}

Write-Host "Deployment completed successfully!" -ForegroundColor Green

# Вывод информации о развертывании
Write-Host "`nDeployment status:" -ForegroundColor Cyan
kubectl get deployments -l app=serv-print-efgi

# Проверка подов
Write-Host "`nPod status:" -ForegroundColor Cyan
kubectl get pods -l app=serv-print-efgi

# Информация о сервисе
Write-Host "`nService status:" -ForegroundColor Cyan
kubectl get svc serv-print-efgi

# Информация об Ingress
Write-Host "`nIngress status:" -ForegroundColor Cyan
kubectl get ingress serv-print-efgi-ingress

Write-Host "`nAccess URLs:" -ForegroundColor Green
Write-Host "Service URL (internal): http://serv-print-efgi/generate-pdf"
Write-Host "Check your Ingress controller configuration for external access URL" 