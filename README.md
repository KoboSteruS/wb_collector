# WB_Collector

FastAPI приложение для работы с Wildberries API.

## 🏗️ Структура проекта

```
WB_Collector/
├── app/
│   ├── api/v1/          # API endpoints версии 1
│   ├── core/            # Конфигурация и логирование
│   ├── models/          # Модели данных
│   ├── schemas/         # Pydantic схемы
│   ├── services/        # Бизнес-логика
│   ├── db/              # Работа с БД
│   ├── middleware/      # Промежуточное ПО
│   └── main.py          # Точка входа
├── requirements.txt
└── run.py               # Скрипт запуска
```

## 🚀 Быстрый старт

```bash
# 1. Создание виртуального окружения
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/MacOS

# 2. Установка зависимостей
pip install -r requirements.txt

# 3. Запуск приложения
python run.py
```

Приложение доступно:
- **API**: http://localhost:8000/api/v1/
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## ⚙️ Конфигурация

Настройки в `app/core/config.py` или через переменные окружения:
- `DEBUG` - режим отладки
- `HOST` - хост сервера
- `PORT` - порт сервера
- `LOG_LEVEL` - уровень логирования

## 📝 Логирование

Логи через `loguru`:
- Консоль с цветным форматированием
- Файл `logs/app.log` с автоматической ротацией

## 📊 Парсинг и аналитика

Система автоматического парсинга SPP:
- Фоновый парсинг по расписанию (1 раз в день)
- Анализ самых частых SPP и dest
- Генерация оптимальных ссылок на товары

Подробнее в [PARSING_GUIDE.md](PARSING_GUIDE.md)

---

**Версия**: 0.1.0

