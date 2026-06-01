# Script PowerShell para iniciar Diagnóstico Financiero
# Uso: .\start-server.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando Diagnóstico Financiero" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$ProjectPath = $PSScriptRoot
Write-Host "Carpeta del proyecto: $ProjectPath" -ForegroundColor Yellow

# Cambiar a la carpeta del proyecto
Set-Location $ProjectPath

# Verificar que Python está instalado
$PythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Python detectado: $PythonVersion" -ForegroundColor Green

# Verificar que app_standalone.py existe
if (-not (Test-Path "app_standalone.py")) {
    Write-Host "ERROR: app_standalone.py no encontrado" -ForegroundColor Red
    exit 1
}

# Iniciar servidor
Write-Host "`nIniciando servidor..." -ForegroundColor Yellow
Write-Host "Accesible en: http://localhost:8000" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener el servidor`n" -ForegroundColor Yellow

python app_standalone.py
