# Portfolio Website - Django Project

## Описание
Профессиональное портфолио Python Full Stack разработчика.

## Структура проекта
```
portfolio_django/
├── manage.py
├── requirements.txt
├── README.md
├── portfolio_project/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── main/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── templates/
│   └── index.html
└── static/
    ├── css/
    ├── js/
    └── images/
```

## Установка и запуск

### 1. Создание виртуального окружения
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Миграции базы данных
```bash
python manage.py migrate
```

### 4. Запуск сервера разработки
```bash
python manage.py runserver
```

### 5. Открыть в браузере
Перейти по адресу: http://127.0.0.1:8000/

## Запуск через Docker (опционально)
```bash
docker build -t portfolio .
docker run -p 8000:8000 portfolio
```

## Запуск через Gunicorn (production)
```bash
gunicorn portfolio_project.wsgi:application --bind 0.0.0.0:8000
```

## Технологии
- Django 6.0
- Python 3.10+
- HTML5/CSS3
- JavaScript
- SQLite (по умолчанию) / PostgreSQL (для production)
