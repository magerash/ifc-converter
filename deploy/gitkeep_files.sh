#!/bin/bash
# Создание структуры папок и .gitkeep файлов

# Создаем необходимые директории
mkdir -p uploads downloads logs templates

# Создаем .gitkeep файлы для пустых папок
touch uploads/.gitkeep
touch downloads/.gitkeep
touch logs/.gitkeep

echo "Структура папок создана успешно!"