#!/bin/bash

# Остановка докера
docker-compose down

# Сборка и запуск
docker-compose build --no-cache
docker-compose up -d