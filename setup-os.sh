# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых пакетов
sudo apt install -y git curl wget nano

# Открытие порта 5000
sudo ufw allow 5000