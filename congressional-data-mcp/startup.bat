@echo off
REM Congressional Data MCP Server - Windows Startup Script

echo ======================================
echo Congressional Data MCP Server Startup
echo ======================================

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.template to .env and add your API keys.
    pause
    exit /b 1
)

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Parse command
set COMMAND=%1
if "%COMMAND%"=="" set COMMAND=up

if "%COMMAND%"=="up" (
    echo Building and starting services...
    docker-compose up -d --build
    if %errorlevel% equ 0 (
        echo.
        echo SUCCESS: Congressional Data MCP Server is running!
        echo.
        echo Quick Commands:
        echo   View logs:     startup.bat logs
        echo   Stop services: startup.bat down
        echo   Status:        startup.bat status
        echo.
        echo Service URLs:
        echo   Health Check: http://localhost:8080/health
        echo   Metrics:      http://localhost:8080/metrics
    )
) else if "%COMMAND%"=="down" (
    echo Stopping services...
    docker-compose down
) else if "%COMMAND%"=="logs" (
    docker-compose logs -f congressional-mcp
) else if "%COMMAND%"=="status" (
    docker-compose ps
) else (
    echo Usage: startup.bat [command]
    echo Commands:
    echo   up          - Start services in background
    echo   down        - Stop all services  
    echo   logs        - View logs
    echo   status      - Show service status
)

pause
