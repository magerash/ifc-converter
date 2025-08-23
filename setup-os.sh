#!/bin/bash

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y git curl wget nano ufw

# Настройка firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Перейдите в домашнюю директорию
cd ~

# Клонируйте проект
git clone https://github.com/magerash/ifc-converter.git ifc-converter
cd ifc-converter

# Дайте права на выполнение
chmod +x /deployment/deploy.sh

# Запустите развертывание
./deployment/deploy.sh
