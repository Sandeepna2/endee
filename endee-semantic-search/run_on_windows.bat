@echo off
echo ==========================================
echo   Endee Semantic Search - Windows Launcher
echo ==========================================
echo.

:: 1. Check for Docker
echo [1/4] Checking Docker status...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Docker is NOT running or not installed.
    echo.
    echo Endee Database requires Docker to run on Windows.
    echo Please install/start Docker Desktop and try again.
    echo.
    pause
    exit /b
)
echo Docker is running.

:: 2. Start Endee Container
echo.
echo [2/4] Starting Endee Database container...
docker-compose up -d endee
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Endee container.
    pause
    exit /b
)
echo Endee container is up.

:: 3. Check Python Dependencies
echo.
echo [3/4] Checking Python dependencies...
python -c "import flask; import sentence_transformers" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r backend/requirements.txt
) else (
    echo Dependencies execution check passed.
)

:: 4. Run Application
echo.
echo [4/4] Starting Search API...
echo.
echo    The application will be available at: http://localhost:5000/api/search
echo    The frontend is located at: %~dp0frontend\index.html
echo.
echo    To ingest data, run: python backend/ingest.py
echo.

cd backend
python app.py
