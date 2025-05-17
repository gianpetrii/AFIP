@echo off
echo Iniciando AFIP Nuestra Parte Extractor...
cd /d "%~dp0"
call win_env\Scripts\activate.bat
python src\main.py
if errorlevel 1 (
    echo Error al iniciar la aplicacion.
    echo Verifique que las dependencias estan instaladas.
    echo Para instalar las dependencias, ejecute: pip install -r requirements.txt
    pause
) else (
    echo Aplicacion cerrada correctamente.
) 