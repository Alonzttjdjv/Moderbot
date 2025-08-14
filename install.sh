#!/bin/bash

# Скрипт установки Telegram Chat Moderator Bot
# Для Linux и macOS

echo "🚀 Установка Telegram Chat Moderator Bot..."
echo "=========================================="

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+ и попробуйте снова."
    exit 1
fi

# Проверяем версию Python
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Требуется Python 3.8+, у вас: $python_version"
    exit 1
fi

echo "✅ Python $python_version найден"

# Проверяем наличие pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 не найден. Установите pip и попробуйте снова."
    exit 1
fi

echo "✅ pip3 найден"

# Создаем виртуальное окружение
echo "📦 Создание виртуального окружения..."
python3 -m venv venv

# Активируем виртуальное окружение
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Обновляем pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip

# Устанавливаем зависимости
echo "📚 Установка зависимостей..."
pip install -r requirements.txt

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p data backups logs

# Копируем пример конфигурации
if [ ! -f .env ]; then
    echo "⚙️  Создание файла конфигурации..."
    cp .env.example .env
    echo "⚠️  Отредактируйте файл .env и настройте BOT_TOKEN и ADMIN_IDS"
else
    echo "✅ Файл .env уже существует"
fi

# Делаем скрипты исполняемыми
chmod +x start.py

echo ""
echo "🎉 Установка завершена успешно!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте файл .env и настройте параметры"
echo "2. Получите токен бота у @BotFather"
echo "3. Добавьте ID администраторов в ADMIN_IDS"
echo "4. Запустите бота командой: python start.py"
echo ""
echo "📖 Подробная документация в файле README.md"
echo "🆘 При проблемах проверьте логи в папке logs/"