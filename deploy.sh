#!/bin/bash

# Генерируем тег версии на основе даты и времени
VERSION=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="gimmyhat/serv-print-efgi:$VERSION"

# Сборка Docker образа
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Также тегаем как latest
docker tag $IMAGE_NAME gimmyhat/serv-print-efgi:latest

# Публикация образов в DockerHub
echo "Pushing Docker images to DockerHub..."
docker push $IMAGE_NAME
docker push gimmyhat/serv-print-efgi:latest

# Обновляем тег в манифесте
echo "Updating deployment manifest..."
sed -i "s|image: gimmyhat/serv-print-efgi:.*|image: $IMAGE_NAME|" k8s/deployment.yaml

# Применение манифестов Kubernetes
echo "Applying Kubernetes manifests..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Ожидание готовности подов
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=serv-print-efgi --timeout=300s

echo "Deployment completed successfully!"

# Вывод информации о сервисе
echo "Service information:"
kubectl get svc serv-print-efgi

# Проверка подов
echo "Pod information:"
kubectl get pods -l app=serv-print-efgi

# Получаем IP ноды и выводим URL
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
echo "Access URL: http://${NODE_IP}:31005/generate-pdf" 