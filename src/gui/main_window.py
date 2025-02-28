from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QProgressBar, QApplication,
    QMessageBox, QHBoxLayout, QFrame, QDialog, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QShortcut, QKeySequence, QFont, QPalette, QColor
from src.core.spotify_client import SpotifyClient
from src.core.track_processor import TrackProcessor
from src.utils.logger import Logger
from src.gui.components.track_selection_dialog import TrackSelectionDialog
from src.gui.components.backup_dialog import BackupDialog
from src.gui.components.settings_dialog import SettingsDialog
from src.gui.components.import_dialog import ImportDialog
import os

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)
    finished = pyqtSignal()
    queue_updated = pyqtSignal(int)
    playlist_created = pyqtSignal(str)
    
    def __init__(self, directory: str, playlist_name: str, spotify_client=None):
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
            
            # Получаем список аудио файлов
            audio_files = self.track_processor.get_audio_files(self.directory)
            total_files = len(audio_files)
            
            if total_files == 0:
                self.error_occurred.emit("Ошибка", "В выбранной директории нет аудио файлов")
                return
            
            processed_count = 0
            spotify_tracks = []
            
            # Создаем плейлист в Spotify если включен экспорт
            playlist_id = None
            if self.spotify_client:
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
                    # Получаем метаданные файла
                    metadata = self.track_processor.extract_metadata(file_path)
                    if not metadata:
                        self.logger.log_missing(file_path, "Не удалось получить метаданные")
                        continue
                    
                    title, artist, duration = metadata
                    
                    # Если нет названия или исполнителя, пропускаем файл
                    if not title or not artist:
                        self.logger.log_missing(file_path, "Отсутствует название или исполнитель в метаданных")
                        continue
                    
                    # Ищем трек в Spotify
                    if self.spotify_client:
                        search_query = f"{title} {artist}"
                        tracks, error = self.spotify_client.search_track(search_query)
                        
                        if error != "OK":  # Изменено: проверяем, что error не равен "OK"
                            self.logger.log_missing(file_path, f"Ошибка поиска: {error}")
                            continue
                            
                        if not tracks:
                            self.logger.log_missing(file_path, "Трек не найден в Spotify")
                            continue
                            
                        # Проверяем, есть ли точное совпадение по названию и исполнителю
                        exact_match = None
                        for track in tracks:
                            track_title = track['name'].lower()
                            track_artist = track['artists'][0]['name'].lower()
                            
                            if title.lower() == track_title and artist.lower() == track_artist:
                                exact_match = track
                                break
                            
                        if exact_match:
                            # Если есть точное совпадение, используем его
                            track_details = {
                                'playlist': self.playlist_name,
                                'manual_selection': False,
                                'original_title': title,
                                'original_artist': artist
                            }
                            spotify_tracks.append(exact_match['uri'])
                            self.logger.log_track_processed(file_path, exact_match, track_details)
                            
                            # Добавляем трек в плейлист сразу
                            if playlist_id:
                                try:
                                    self.spotify_client.add_tracks_to_playlist(playlist_id, [exact_match['uri']])
                                except Exception as e:
                                    self.error_occurred.emit("Ошибка Spotify", f"Не удалось добавить трек в плейлист: {str(e)}")
                        else:
                            # Если нет точного совпадения, добавляем в очередь для ручного выбора
                            self.manual_queue.append((file_path, (title, artist, duration), tracks))
                            self.queue_updated.emit(len(self.manual_queue))
                            self.logger.log_missing(file_path, "Требуется ручной выбор трека")
                    
                except Exception as e:
                    self.logger.log_missing(file_path, f"Ошибка обработки: {str(e)}")
                
                processed_count += 1
                self.progress_updated.emit(processed_count)
            
            # Сохраняем треки для последующего добавления
            if spotify_tracks:
                self.spotify_tracks_to_add = spotify_tracks
            
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
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 10px;
            }
        """)
        self.setMinimumHeight(20)

class SpotifyMergerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spotify Merger")
        self.setMinimumSize(500, 350)
        
        # Инициализация Spotify клиента
        self.spotify_client = SpotifyClient()
        
        # Основные стили приложения
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                font-family: 'Segoe UI', Arial;
                color: #FFFFFF;
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
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                padding: 5px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid #282828;
                background-color: #121212;
            }
            QCheckBox::indicator:checked {
                background-color: #1DB954;
                border: 2px solid #1DB954;
            }
            QCheckBox::indicator:unchecked:hover {
                border: 2px solid #1DB954;
            }
            QFrame {
                background-color: #181818;
                border-radius: 8px;
            }
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #282828;
                height: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1DB954;
                border-radius: 3px;
            }
        """)
        
        self.selected_directory = None
        self.processing_thread = None
        self.has_unresolved_conflicts = False
        self.playlist_id = None
        self.spotify_tracks = []
        
        self.init_components()
        
    def init_components(self):
        # Создаем центральный виджет и основной layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок приложения
        title_label = QLabel("Spotify Merger")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #1DB954;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Создаем контейнер для двух основных секций
        sections_container = QWidget()
        sections_layout = QHBoxLayout(sections_container)
        sections_layout.setSpacing(20)

        # Секция импорта локального плейлиста
        import_section = QFrame()
        import_section.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        import_section.setStyleSheet("""
            QFrame {
                background-color: #282828;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        import_layout = QVBoxLayout(import_section)

        import_title = QLabel("Импорт локального плейлиста")
        import_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        import_layout.addWidget(import_title)

        import_description = QLabel(
            "Создайте плейлист в Spotify из локальных музыкальных файлов. "
            "Поддерживаются форматы MP3, M4A, WAV и FLAC."
        )
        import_description.setWordWrap(True)
        import_description.setStyleSheet("color: #B3B3B3;")
        import_layout.addWidget(import_description)

        import_button = ModernButton("Начать импорт")
        import_button.clicked.connect(self.show_import_dialog)
        import_layout.addWidget(import_button)

        import_layout.addStretch()

        # Секция бэкапа любимых треков
        backup_section = QFrame()
        backup_section.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        backup_section.setStyleSheet("""
            QFrame {
                background-color: #282828;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        backup_layout = QVBoxLayout(backup_section)

        backup_title = QLabel("Бэкап любимых треков")
        backup_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        backup_layout.addWidget(backup_title)

        backup_description = QLabel(
            "Сохраните ваши любимые треки из Spotify в локальный файл. "
            "Файл можно будет использовать для восстановления плейлиста."
        )
        backup_description.setWordWrap(True)
        backup_description.setStyleSheet("color: #B3B3B3;")
        backup_layout.addWidget(backup_description)

        backup_button = ModernButton("Создать бэкап")
        backup_button.clicked.connect(self.show_backup_dialog)
        backup_layout.addWidget(backup_button)

        backup_layout.addStretch()

        # Добавляем секции в контейнер
        sections_layout.addWidget(import_section)
        sections_layout.addWidget(backup_section)

        main_layout.addWidget(sections_container)

        # Нижняя панель с настройками
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        
        settings_button = ModernButton("Настройки")
        settings_button.setProperty("class", "secondary")
        settings_button.clicked.connect(self.show_settings)
        bottom_layout.addWidget(settings_button)
        
        bottom_layout.addStretch()
        
        main_layout.addWidget(bottom_panel)

        # Добавляем горячие клавиши
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Выберите директорию с музыкой")
        if directory:
            self.selected_directory = directory
            self.directory_label.setText(f"Выбрана директория: {directory}")
            self.start_button.setEnabled(True)
            
    def show_error(self, title, message):
        """Показывает диалоговое окно с ошибкой"""
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle(title)
        error_dialog.setText(message)
        error_dialog.exec()
            
    def start_processing(self):
        if not self.selected_directory:
            self.show_error("Ошибка", "Выберите директорию с музыкой")
            return
            
        if not self.playlist_name_edit.text().strip():
            self.show_error("Ошибка", "Введите название плейлиста")
            return
            
        # Проверяем экспорт в Spotify
        if self.spotify_client.is_authorized():
            # Сбрасываем состояние
            self.has_unresolved_conflicts = False
            self.playlist_id = None
            self.spotify_tracks = []
                
            # Запускаем обработку
            self.processing_thread = ProcessingThread(
                directory=self.selected_directory,
                playlist_name=self.playlist_name_edit.text().strip(),
                spotify_client=self.spotify_client
            )
            
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.status_updated.connect(self.update_status)
            self.processing_thread.error_occurred.connect(self.show_error)
            self.processing_thread.finished.connect(self.processing_finished)
            self.processing_thread.queue_updated.connect(self.update_queue_status)
            self.processing_thread.playlist_created.connect(self.on_playlist_created)
            
            self.start_button.setEnabled(False)
            self.cancel_button.show()
            self.directory_label.setEnabled(False)
            self.playlist_name_edit.setEnabled(False)
            
            self.processing_thread.start()
        else:
            self.show_error("Ошибка", "Необходимо авторизоваться в Spotify")
        
    def cancel_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait()
            self.update_status("Обработка отменена")
            self.reset_ui()
            
    def update_progress(self, current: int):
        """Обновляет прогресс-бар"""
        if not self.progress_bar.isVisible():
            self.progress_bar.show()
        self.progress_bar.setValue(current)

    def update_status(self, status: str):
        """Обновляет статус операции"""
        self.status_label.setText(status)
        if not self.status_label.isVisible():
            self.status_label.show()

    def processing_finished(self):
        """Обработчик завершения операции"""
        self.reset_ui()
        
        if self.processing_thread and self.processing_thread.manual_queue:
            self.has_unresolved_conflicts = True
            self.status_label.setText(f"Требуется разрешить {len(self.processing_thread.manual_queue)} конфликтов")
            QMessageBox.information(
                self,
                "Внимание",
                "Есть треки, требующие ручного выбора. Нажмите 'Разрешить конфликты' для продолжения."
            )
        else:
            self.has_unresolved_conflicts = False
            self.status_label.setText("Обработка завершена")
            QMessageBox.information(self, "Готово", "Обработка файлов завершена успешно!")
            self.status_label.hide()
            self.progress_bar.hide()
            
    def reset_ui(self):
        self.start_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.hide()
        self.directory_label.setEnabled(True)
        self.playlist_name_edit.setEnabled(True)
        
    def update_queue_status(self, queue_size: int):
        """Обновляет состояние кнопки очереди"""
        self.cancel_button.setEnabled(queue_size > 0)
        if queue_size > 0:
            self.cancel_button.setText(f"Отменить ({queue_size})")
        else:
            self.cancel_button.setText("Отменить")
            
    def process_manual_queue(self):
        """Обработка очереди треков, требующих ручного вмешательства"""
        if not self.processing_thread:
            return
            
        queue_size = self.processing_thread.get_manual_queue_size()
        if queue_size == 0:
            self.has_unresolved_conflicts = False
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Все конфликты разрешены")
            return
            
        self.status_label.setText(f"Ручная обработка треков ({queue_size} осталось)")
        
        # Получаем следующий трек для обработки
        next_track = self.processing_thread.get_next_manual_track()
        if next_track:
            file_path, metadata, tracks = next_track
            dialog = TrackSelectionDialog(tracks, metadata, self.spotify_client, self)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                selected_track = dialog.get_selected_track()
                if selected_track:
                    # Добавляем трек в плейлист сразу после выбора
                    try:
                        self.spotify_client.add_tracks_to_playlist(self.playlist_id, [selected_track['uri']])
                        # Создаем словарь с деталями для логирования
                        track_details = {
                            'playlist': self.playlist_name_edit.text().strip(),
                            'manual_selection': True,
                            'original_title': metadata[0],
                            'original_artist': metadata[1]
                        }
                        self.processing_thread.logger.log_track_processed(file_path, selected_track, track_details)
                    except Exception as e:
                        self.show_error("Ошибка Spotify", f"Не удалось добавить трек в плейлист: {str(e)}")
                else:
                    self.processing_thread.logger.log_missing(file_path, "Пропущен пользователем (нет выбранного трека)")
            else:
                self.processing_thread.logger.log_missing(file_path, "Пропущен пользователем")
            
            # Обновляем статус очереди
            remaining = self.processing_thread.get_manual_queue_size()
            self.update_queue_status(remaining)
            
            if remaining > 0:
                self.status_label.setText(f"Требуется разрешить {remaining} конфликтов")
            else:
                self.process_manual_queue()  # Рекурсивно вызываем для завершения обработки

    def on_playlist_created(self, playlist_id: str):
        """Обработчик создания плейлиста"""
        self.playlist_id = playlist_id
        QMessageBox.information(
            self,
            "Успех",
            f"Плейлист успешно создан в Spotify!\nID плейлиста: {playlist_id}"
        )

    def show_backup_dialog(self):
        """Открывает диалог управления бэкапом"""
        if not self.spotify_client or not self.spotify_client.is_authorized():
            self.show_error("Ошибка", "Необходимо авторизоваться в Spotify")
            return
            
        dialog = BackupDialog(self.spotify_client, self)
        dialog.exec()

    def show_import_dialog(self):
        """Открывает диалог импорта локального плейлиста"""
        if not self.spotify_client or not self.spotify_client.is_authorized():
            self.show_error("Ошибка", "Необходимо авторизоваться в Spotify")
            return
            
        dialog = ImportDialog(self.spotify_client, self)
        dialog.exec()

    def show_settings(self):
        """Открывает диалог настроек"""
        dialog = SettingsDialog(self.spotify_client, self)
        dialog.exec() 