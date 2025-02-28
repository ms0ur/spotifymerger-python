# Spotify Merger

Приложение для создания плейлистов Spotify из локальных аудиофайлов.

## Возможности

- Поиск треков в Spotify по метаданным локальных аудиофайлов
- Графический интерфейс для удобного управления
- Автоматическая верификация найденных треков
- Поддержка различных форматов аудио (.mp3, .flac, .wav, .aac, .ogg, .m4a)
- Подробное логирование процесса
- Возможность ручного выбора треков при неточном совпадении

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/spotifymerger.git
cd spotifymerger
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` в корневой директории проекта со следующим содержимым:
```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

## Использование

1. Запустите приложение:
```bash
python -m src
```

2. Выберите директорию с аудиофайлами через графический интерфейс
3. Нажмите "Начать обработку"
4. Следите за прогрессом в интерфейсе
5. При необходимости выбирайте треки вручную из предложенных вариантов

## Структура проекта

```
spotifymerger/
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── file_list.py
│   │       └── progress_bar.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── spotify_client.py
│   │   ├── track_processor.py
│   │   └── file_manager.py
│   └── utils/
│       ├── __init__.py
│       ├── metadata.py
│       └── logger.py
├── requirements.txt
└── README.md
```

## Логи

Логи сохраняются в директории `logs/` в формате:
```
spotify_merger_YYYYMMDD_HHMMSS.log
```

## Лицензия

MIT 