from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QProgressBar, QMessageBox,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.core.spotify_client import SpotifyClient

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class BackupThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, spotify_client, output_file):
        super().__init__()
        self.spotify_client = spotify_client
        self.output_file = output_file
        self.is_running = False

    def run(self):
        try:
            self.is_running = True
            self.status_updated.emit("Получение списка любимых треков...")
            logger.info("Начинаем процесс бэкапа")
            
            # Получаем общее количество треков
            total_tracks = self.spotify_client.get_liked_tracks_count()
            logger.info(f"Всего найдено треков: {total_tracks}")
            
            if total_tracks == 0:
                logger.warning("Не найдено сохраненных треков")
                self.error_occurred.emit("У вас нет сохранённых треков")
                return
                
            self.status_updated.emit(f"Сохранение {total_tracks} треков...")
            
            # Получаем треки порциями
            formatted_tracks = []
            processed_count = 0
            
            for tracks_batch in self.spotify_client.get_liked_tracks_batches():
                if not self.is_running:
                    logger.info("Процесс бэкапа был прерван")
                    break
                
                logger.debug(f"Получена новая порция треков: {len(tracks_batch)} шт.")
                
                for track_item in tracks_batch:
                    if not self.is_running:
                        break
                        
                    track = track_item['track']
                    logger.debug(f"Обработка трека: {track['name']} - {track['artists'][0]['name']}")
                    
                    formatted_track = {
                        'name': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'spotify_uri': track['uri'],
                        'duration_ms': track['duration_ms'],
                        'preview_url': track['preview_url']
                    }
                    formatted_tracks.append(formatted_track)
                    
                    processed_count += 1
                    progress = int((processed_count / total_tracks) * 100)
                    logger.debug(f"Прогресс: {progress}% ({processed_count}/{total_tracks})")
                    self.progress_updated.emit(progress)
                    self.status_updated.emit(f"Обработано {processed_count} из {total_tracks} треков")
            
            # Сохраняем в файл
            logger.info("Сохранение результатов в файл")
            with open(self.output_file, 'w', encoding='utf-8') as f:
                backup_data = {
                    'tracks': formatted_tracks,
                    'total': len(formatted_tracks),
                    'version': '1.0',
                    'created_at': datetime.now().isoformat(),
                    'spotify_user': self.spotify_client.get_current_user_id()
                }
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Бэкап успешно создан: {self.output_file}")
            self.status_updated.emit("Бэкап успешно создан!")
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {str(e)}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                border: none;
                border-radius: 16px;
                color: white;
                padding: 5px 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
            }
            QPushButton:disabled {
                background-color: #282828;
                color: #B3B3B3;
            }
            QPushButton[class="warning"] {
                background-color: #ff6b6b;
            }
            QPushButton[class="warning"]:hover {
                background-color: #ff8787;
            }
            QPushButton[class="secondary"] {
                background-color: #535353;
            }
            QPushButton[class="secondary"]:hover {
                background-color: #666666;
            }
        """)

class ModernProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 10px;
                text-align: center;
                background-color: #282828;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 10px;
            }
        """)
        self.setMinimumHeight(20)

class BackupDialog(QDialog):
    def __init__(self, spotify_client: SpotifyClient, parent=None):
        super().__init__(parent)
        self.spotify_client = spotify_client
        self.backup_thread = None
        logger.info("Инициализация диалога бэкапа")
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Бэкап любимых треков")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title = QLabel("Сохранение любимых треков")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1DB954;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Описание
        description = QLabel(
            "Это создаст локальную копию всех ваших любимых треков из Spotify. "
            "Файл можно будет использовать для восстановления плейлиста или импорта в другой аккаунт."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #B3B3B3;")
        layout.addWidget(description)
        
        # Контейнер для прогресса
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: #282828;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        progress_layout = QVBoxLayout(progress_frame)
        
        self.status_label = QLabel("Готов к созданию бэкапа")
        self.status_label.setStyleSheet("color: #B3B3B3;")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = ModernProgressBar()
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_frame)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.start_button = ModernButton("Создать бэкап")
        self.start_button.clicked.connect(self.start_backup)
        
        self.cancel_button = ModernButton("Отмена")
        self.cancel_button.setProperty("class", "secondary")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def start_backup(self):
        logger.info("Запуск процесса бэкапа")
        file_name = QFileDialog.getSaveFileName(
            self,
            "Сохранить бэкап",
            os.path.expanduser("~/Desktop/spotify_favorites_backup.json"),
            "JSON файлы (*.json)"
        )[0]
        
        if not file_name:
            logger.info("Пользователь отменил выбор файла")
            return
            
        logger.info(f"Выбран файл для сохранения: {file_name}")
        self.start_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.backup_thread = BackupThread(self.spotify_client, file_name)
        self.backup_thread.progress_updated.connect(self.progress_bar.setValue)
        self.backup_thread.status_updated.connect(self.status_label.setText)
        self.backup_thread.error_occurred.connect(self.handle_error)
        self.backup_thread.finished.connect(self.backup_finished)
        
        self.backup_thread.start()
        
    def handle_error(self, error_message: str):
        logger.error(f"Ошибка бэкапа: {error_message}")
        QMessageBox.critical(self, "Ошибка", error_message)
        self.reset_ui()
        
    def backup_finished(self):
        logger.info("Бэкап успешно завершен")
        QMessageBox.information(self, "Готово", "Бэкап успешно создан!")
        self.accept()
        
    def reset_ui(self):
        logger.debug("Сброс состояния UI")
        self.start_button.setEnabled(True)
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Готов к созданию бэкапа")
        
    def closeEvent(self, event):
        if self.backup_thread and self.backup_thread.is_running:
            logger.info("Отмена процесса бэкапа")
            self.backup_thread.is_running = False
            self.backup_thread.wait()
        event.accept() 