#!/bin/bash

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y git curl wget nano ufw
# Скачиваем и устанавливаем ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
# Установка зависимостей
pip install flask authlib requests python-dotenv

# Настройка firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Настройка authtoken.Необходимо скопировать farwarding путь для Google Cloud Console
# Загрузка переменных из .env файла
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Проверка наличия токена
if [ -z "$NGROK_AUTH_TOKEN" ]; then
    echo "Ошибка: NGROK_AUTH_TOKEN не найден в .env файле"
    exit 1
fi
ngrok config add-authtoken "$NGROK_AUTH_TOKEN"

# Перейдите в домашнюю директорию
cd ~

# Клонируйте проект
#git clone https://github.com/magerash/ifc-converter.git ifc-converter
#cd ifc-converter
git clone https://github.com/magerash/improovements1.git ifc-converter2
cd ifc-converter2
cp .env.example .env
nano .env

# Дайте права на выполнение
chmod +x deploy.sh

# Запустите развертывание
./deploy.sh

# Автоматическая настройка и запуск
python3 setup_oauth_dev.py


