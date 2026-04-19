#!/bin/bash
set -e

echo "Starting SS-Crawler Website..."
echo ""

# Check if database network exists, create if not
if ! docker network ls | grep -q "ss-crawler_default"; then
    echo "Creating Docker network..."
    docker network create ss-crawler_default
fi

# Make sure database is running
echo "Checking database..."
if ! docker ps | grep -q "ss_crawler_db"; then
    echo "Starting database..."
    cd SS-CRAWLER
    docker-compose up -d
    cd ..
    sleep 5
fi

# Build and start website
echo "Building website container..."
docker-compose -f docker-compose-website.yml up --build -d

echo ""
echo "Website starting..."
echo ""
echo "Once ready, access it at: http://localhost:5000"
echo ""
echo "To stop: docker-compose -f docker-compose-website.yml down"
