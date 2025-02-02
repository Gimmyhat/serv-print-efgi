# Set UTF8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Create directories
Write-Host "Creating directories..."
New-Item -ItemType Directory -Force -Path "monitoring/prometheus"
New-Item -ItemType Directory -Force -Path "monitoring/grafana/provisioning/dashboards"

# Start monitoring
Write-Host "Starting monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d

Write-Host ""
Write-Host "Monitoring started successfully!"
Write-Host "Grafana: http://localhost:3000"
Write-Host "Prometheus: http://localhost:9090"
Write-Host ""
Write-Host "Grafana login credentials:"
Write-Host "Username: admin"
Write-Host "Password: admin" 