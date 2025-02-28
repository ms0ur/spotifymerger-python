import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import SpotifyMergerWindow

def main():
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем наличие необходимых переменных окружения
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Ошибка: Не найдены SPOTIFY_CLIENT_ID или SPOTIFY_CLIENT_SECRET")
        print("Создайте файл .env с этими переменными")
        sys.exit(1)
    
    # Создаем приложение
    app = QApplication(sys.argv)
    
    # Создаем и показываем главное окно
    window = SpotifyMergerWindow()
    window.show()
    
    # Запускаем главный цикл приложения
    sys.exit(app.exec())

if __name__ == "__main__":
    # Добавляем родительскую директорию в путь импорта
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    main() 