@echo off
REM Script para ejecutar tests con coverage en Windows

echo Ejecutando tests con coverage...
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

echo.
echo Reporte de coverage generado en htmlcov\index.html
echo Abre htmlcov\index.html en tu navegador para ver el reporte detallado

