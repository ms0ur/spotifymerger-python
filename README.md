# Spotify Merger

Приложение для создания плейлистов в Spotify из локальных музыкальных файлов.

Created with Cursor IDE

## Возможности

- Создание плейлистов в Spotify из локальных аудио файлов
- Поддержка форматов MP3, M4A, WAV и FLAC
- Умный поиск соответствий в Spotify
- Возможность ручного выбора треков
- Создание бэкапа любимых треков
- Восстановление треков из бэкапа

## Установка

1. Склонируйте репозиторий:
```bash
git clone https://github.com/yourusername/spotifymerger-python.git
cd spotifymerger-python
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите приложение:
```bash
python -m src
```

## Настройка

1. Создайте приложение на [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. В настройках приложения добавьте Redirect URI: `http://localhost:8888/callback`
3. Включите Web API в настройках приложения
4. Скопируйте Client ID и Client Secret
5. Введите их в настройках приложения Spotify Merger

## Использование

1. Запустите приложение
2. Нажмите кнопку настроек и введите Client ID и Client Secret
3. Авторизуйтесь в Spotify
4. Выберите папку с музыкой для создания плейлиста
5. Введите название плейлиста
6. Нажмите "Начать"

## Сборка

Для создания исполняемого файла:

1. Убедитесь, что все зависимости установлены:
```bash
pip install -r requirements.txt
```

2. Соберите приложение одним из способов:

Используя python:
```bash
python -m PyInstaller build_config.spec
```

Или если PyInstaller установлен глобально:
```bash
pyinstaller build_config.spec
```

После успешной сборки исполняемый файл будет находиться в папке `dist`.

## Лицензия

MIT 