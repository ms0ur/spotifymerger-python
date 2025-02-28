from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QProgressBar, QMessageBox,
    QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from src.core.spotify_client import SpotifyClient
from src.core.track_processor import TrackProcessor
from src.utils.logger import Logger
from src.gui.components.track_selection_dialog import TrackSelectionDialog
import os

class ImportThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)
    finished = pyqtSignal()
    queue_updated = pyqtSignal(int)
    playlist_created = pyqtSignal(str)
    
    def __init__(self, directory: str, playlist_name: str, spotify_client):
        super().__init__()
        self.directory = directory
        self.playlist_name = playlist_name
        self.spotify_client = spotify_client
        self.is_running = False
        self.manual_queue = []
        self.track_processor = TrackProcessor()
        self.logger = Logger()
        
    def run(self):
        try:
            self.is_running = True
            self.status_updated.emit("Сканирование директории...")
            
            audio_files = self.track_processor.get_audio_files(self.directory)
            total_files = len(audio_files)
            
            if total_files == 0:
                self.error_occurred.emit("Ошибка", "В выбранной директории нет аудио файлов")
                return
            
            processed_count = 0
            spotify_tracks = []
            
            # Создаем плейлист в Spotify
            self.status_updated.emit("Создание плейлиста в Spotify...")
            try:
                playlist_id = self.spotify_client.create_playlist(
                    self.playlist_name,
                    description="Создано с помощью Spotify Merger"
                )
                self.playlist_created.emit(playlist_id)
            except Exception as e:
                self.error_occurred.emit("Ошибка Spotify", f"Не удалось создать плейлист: {str(e)}")
                return
            
            # Обрабатываем каждый файл
            for file_path in audio_files:
                if not self.is_running:
                    break
                
                self.status_updated.emit(f"Обработка: {os.path.basename(file_path)}")
                
                try:
                    metadata = self.track_processor.extract_metadata(file_path)
                    if not metadata:
                        self.logger.log_missing(file_path, "Не удалось получить метаданные")
                        continue
                    
                    title, artist, duration = metadata
                    
                    if not title or not artist:
                        self.logger.log_missing(file_path, "Отсутствует название или исполнитель в метаданных")
                        continue
                    
                    search_query = f"{title} {artist}"
                    tracks, error = self.spotify_client.search_track(search_query)
                    
                    if error != "OK":
                        self.logger.log_missing(file_path, f"Ошибка поиска: {error}")
                        continue
                        
                    if not tracks:
                        self.logger.log_missing(file_path, "Трек не найден в Spotify")
                        continue
                        
                    # Проверяем точное совпадение
                    exact_match = None
                    for track in tracks:
                        track_title = track['name'].lower()
                        track_artist = track['artists'][0]['name'].lower()
                        
                        if title.lower() == track_title and artist.lower() == track_artist:
                            exact_match = track
                            break
                        
                    if exact_match:
                        track_details = {
                            'playlist': self.playlist_name,
                            'manual_selection': False,
                            'original_title': title,
                            'original_artist': artist
                        }
                        spotify_tracks.append(exact_match['uri'])
                        self.logger.log_track_processed(file_path, exact_match, track_details)
                        
                        try:
                            self.spotify_client.add_tracks_to_playlist(playlist_id, [exact_match['uri']])
                        except Exception as e:
                            self.error_occurred.emit("Ошибка Spotify", f"Не удалось добавить трек в плейлист: {str(e)}")
                    else:
                        self.manual_queue.append((file_path, (title, artist, duration), tracks))
                        self.queue_updated.emit(len(self.manual_queue))
                        self.logger.log_missing(file_path, "Требуется ручной выбор трека")
                    
                except Exception as e:
                    self.logger.log_missing(file_path, f"Ошибка обработки: {str(e)}")
                
                processed_count += 1
                self.progress_updated.emit(int((processed_count / total_files) * 100))
            
            self.status_updated.emit("Обработка завершена")
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit("Ошибка", f"Произошла ошибка при обработке: {str(e)}")
        finally:
            self.is_running = False
            
    def get_manual_queue_size(self):
        return len(self.manual_queue)
        
    def get_next_manual_track(self):
        if self.manual_queue:
            track = self.manual_queue.pop(0)
            self.queue_updated.emit(len(self.manual_queue))
            return track
        return None

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

class ImportDialog(QDialog):
    def __init__(self, spotify_client: SpotifyClient, parent=None):
        super().__init__(parent)
        self.spotify_client = spotify_client
        self.import_thread = None
        self.selected_directory = None
        self.playlist_id = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Импорт локального плейлиста")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #282828;
                border-radius: 4px;
                background-color: #282828;
                color: #FFFFFF;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #1DB954;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title = QLabel("Импорт локальной музыки")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1DB954;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Описание
        description = QLabel(
            "Выберите папку с музыкальными файлами для создания плейлиста в Spotify. "
            "Поддерживаются форматы MP3, M4A, WAV и FLAC."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #B3B3B3;")
        layout.addWidget(description)
        
        # Основной контейнер
        main_frame = QFrame()
        main_frame.setStyleSheet("""
            QFrame {
                background-color: #282828;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        main_layout = QVBoxLayout(main_frame)
        
        # Выбор директории
        self.directory_label = QLabel("Выберите директорию:")
        main_layout.addWidget(self.directory_label)
        
        directory_button = ModernButton("Выбрать папку")
        directory_button.clicked.connect(self.select_directory)
        main_layout.addWidget(directory_button)
        
        # Название плейлиста
        self.playlist_name_edit = QLineEdit()
        self.playlist_name_edit.setPlaceholderText("Название плейлиста")
        main_layout.addWidget(self.playlist_name_edit)
        
        # Прогресс
        self.status_label = QLabel("Готов к импорту")
        self.status_label.setStyleSheet("color: #B3B3B3;")
        main_layout.addWidget(self.status_label)
        
        self.progress_bar = ModernProgressBar()
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        layout.addWidget(main_frame)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.start_button = ModernButton("Начать импорт")
        self.start_button.clicked.connect(self.start_import)
        self.start_button.setEnabled(False)
        
        self.cancel_button = ModernButton("Отмена")
        self.cancel_button.setProperty("class", "secondary")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите директорию с музыкой")
        if directory:
            self.selected_directory = directory
            self.directory_label.setText(f"Выбрана директория: {directory}")
            self.start_button.setEnabled(True)
            
    def start_import(self):
        if not self.selected_directory:
            self.show_error("Ошибка", "Выберите директорию с музыкой")
            return
            
        if not self.playlist_name_edit.text().strip():
            self.show_error("Ошибка", "Введите название плейлиста")
            return
            
        self.start_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.import_thread = ImportThread(
            self.selected_directory,
            self.playlist_name_edit.text().strip(),
            self.spotify_client
        )
        
        self.import_thread.progress_updated.connect(self.progress_bar.setValue)
        self.import_thread.status_updated.connect(self.status_label.setText)
        self.import_thread.error_occurred.connect(self.handle_error)
        self.import_thread.finished.connect(self.import_finished)
        self.import_thread.queue_updated.connect(self.handle_queue_update)
        self.import_thread.playlist_created.connect(self.handle_playlist_created)
        
        self.import_thread.start()
        
    def handle_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)
        self.reset_ui()
        
    def import_finished(self):
        if self.import_thread and self.import_thread.get_manual_queue_size() > 0:
            self.process_manual_queue()
        else:
            QMessageBox.information(self, "Готово", "Импорт успешно завершен!")
            self.accept()
        
    def reset_ui(self):
        self.start_button.setEnabled(True)
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Готов к импорту")
        
    def handle_queue_update(self, queue_size: int):
        if queue_size > 0:
            self.status_label.setText(f"Требуется разрешить {queue_size} конфликтов")
            
    def handle_playlist_created(self, playlist_id: str):
        self.playlist_id = playlist_id
        
    def process_manual_queue(self):
        if not self.import_thread:
            return
            
        next_track = self.import_thread.get_next_manual_track()
        if next_track:
            file_path, metadata, tracks = next_track
            dialog = TrackSelectionDialog(tracks, metadata, self.spotify_client, self)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                selected_track = dialog.get_selected_track()
                if selected_track:
                    try:
                        self.spotify_client.add_tracks_to_playlist(self.playlist_id, [selected_track['uri']])
                        track_details = {
                            'playlist': self.playlist_name_edit.text().strip(),
                            'manual_selection': True,
                            'original_title': metadata[0],
                            'original_artist': metadata[1]
                        }
                        self.import_thread.logger.log_track_processed(file_path, selected_track, track_details)
                    except Exception as e:
                        self.show_error("Ошибка Spotify", f"Не удалось добавить трек в плейлист: {str(e)}")
                else:
                    self.import_thread.logger.log_missing(file_path, "Пропущен пользователем (нет выбранного трека)")
            else:
                self.import_thread.logger.log_missing(file_path, "Пропущен пользователем")
            
            remaining = self.import_thread.get_manual_queue_size()
            if remaining > 0:
                self.process_manual_queue()
            else:
                QMessageBox.information(self, "Готово", "Импорт успешно завершен!")
                self.accept()
        
    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)
        
    def closeEvent(self, event):
        if self.import_thread and self.import_thread.is_running:
            self.import_thread.is_running = False
            self.import_thread.wait()
        event.accept() 