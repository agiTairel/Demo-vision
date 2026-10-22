@echo off
REM Arranca la demo en local. Ejecutar desde "Anaconda Prompt" o con doble clic si Python esta en el PATH.
cd /d "%~dp0"
where python >nul 2>nul || (echo No encuentro Python. Abre "Anaconda Prompt", ve a esta carpeta y ejecuta iniciar_demo.bat & pause & exit /b 1)
if not exist .venv (
  echo Creando entorno virtual...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Instalando dependencias (solo tarda la primera vez)...
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
echo.
echo Abriendo la demo en http://localhost:8501  (Ctrl+C para parar)
python -m streamlit run app.py
pause
