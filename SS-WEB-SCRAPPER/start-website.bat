@echo off
echo Starting SS-Crawler Website...
echo.

REM Check if database network exists, create if not
docker network ls | findstr "ss-crawler_default" >nul 2>&1
if errorlevel 1 (
    echo Creating Docker network...
    docker network create ss-crawler_default
)

REM Make sure database is running
echo Checking database...
docker ps | findstr "ss_crawler_db" >nul 2>&1
if errorlevel 1 (
    echo Starting database...
    cd SS-CRAWLER
    docker-compose up -d
    cd ..
    timeout /t 5 /nobreak >nul
)

REM Build and start website
echo Building website container...
docker-compose -f docker-compose-website.yml up --build -d

echo.
echo Website starting...
echo.
echo Once ready, access it at: http://localhost:5000
echo.
echo To stop: docker-compose -f docker-compose-website.yml down
pause
