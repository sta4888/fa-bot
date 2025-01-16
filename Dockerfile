FROM python:3.9

# Установите рабочую директорию
WORKDIR /app

# Скопируйте requirements.txt и установите зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте все файлы проекта в контейнер
COPY .. .

# Укажите команду для запуска бота
CMD ["python", "bot/bot.py"]