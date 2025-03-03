import sys
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QProgressBar, QMessageBox,
    QFrame, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QIcon, QWindow
from src.core.spotify_client import SpotifyClient

# Импортируем поддержку уведомлений Windows
NOTIFICATIONS_SUPPORTED = False
if sys.platform == 'win32':
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        NOTIFICATIONS_SUPPORTED = True
        logger.info("Поддержка уведомлений Windows включена")
    except ImportError:
        logger.warning("Поддержка уведомлений Windows недоступна")

# Импортируем поддержку таскбара Windows
TASKBAR_SUPPORTED = False
if sys.platform == 'win32':
    try:
        import win32com.client
        TASKBAR_SUPPORTED = True
        logger.info("Поддержка таскбара Windows включена")
    except ImportError:
        logger.warning("Поддержка таскбара Windows недоступна")

class BackupThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    track_info_updated = pyqtSignal(str)
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
                
            self.status_updated.emit(f"Всего треков для сохранения: {total_tracks}")
            
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
                    track_name = track['name']
                    artist_name = track['artists'][0]['name']
                    
                    logger.debug(f"Обработка трека: {track_name} - {artist_name}")
                    self.track_info_updated.emit(f"{track_name} - {artist_name}")
                    
                    formatted_track = {
                        'name': track_name,
                        'artist': artist_name,
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
            self.status_updated.emit("Сохранение файла бэкапа...")
            self.track_info_updated.emit("Завершение работы...")
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
            self.status_updated.emit(f"Бэкап успешно создан! Сохранено {len(formatted_tracks)} треков")
            self.track_info_updated.emit("Готово!")
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {str(e)}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False

class RestoreThread(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, spotify_client, backup_file):
        super().__init__()
        self.spotify_client = spotify_client
        self.backup_file = backup_file
        self.is_running = False

    def run(self):
        try:
            self.is_running = True
            self.status_updated.emit("Восстановление треков из бэкапа...")
            logger.info("Начинаем процесс восстановления")
            
            restored_count, message = self.spotify_client.restore_from_backup(self.backup_file)
            
            if restored_count > 0:
                self.status_updated.emit(f"Восстановлено {restored_count} треков")
                logger.info(f"Восстановлено {restored_count} треков")
                self.finished.emit()
            else:
                self.error_occurred.emit(message)
                logger.error(f"Ошибка восстановления: {message}")
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении: {str(e)}", exc_info=True)
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
        self.restore_thread = None
        self.taskbar = None
        logger.info("Инициализация диалога бэкапа")
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Управление бэкапом")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: #FFFFFF;
                min-height: 20px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title = QLabel("Управление бэкапом треков")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1DB954;
            padding: 5px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Описание
        description = QLabel(
            "Создайте бэкап ваших любимых треков или восстановите их из существующего бэкапа. "
            "Бэкап сохраняется в JSON файл, который можно использовать для восстановления."
        )
        description.setWordWrap(True)
        description.setStyleSheet("""
            color: #B3B3B3;
            padding: 5px;
            min-height: 40px;
        """)
        layout.addWidget(description)
        
        # Контейнер для прогресса
        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet("""
            QFrame {
                background-color: #282828;
                border-radius: 10px;
                padding: 20px;
                min-height: 150px;
            }
        """)
        progress_layout = QVBoxLayout(self.progress_frame)
        progress_layout.setSpacing(15)
        
        # Добавляем общий статус
        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("""
            color: #B3B3B3;
            font-weight: bold;
            font-size: 14px;
            min-height: 25px;
        """)
        progress_layout.addWidget(self.status_label)
        
        # Добавляем информацию о текущем треке
        self.track_info_label = QLabel("")
        self.track_info_label.setStyleSheet("""
            color: #B3B3B3;
            font-style: italic;
            font-size: 13px;
            min-height: 25px;
            padding: 5px 0;
        """)
        self.track_info_label.setWordWrap(True)
        progress_layout.addWidget(self.track_info_label)
        
        # Добавляем прогресс-бар
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        # Добавляем растягивающийся элемент
        progress_layout.addStretch()
        
        layout.addWidget(self.progress_frame)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.backup_button = ModernButton("Создать бэкап")
        self.backup_button.clicked.connect(self.start_backup)
        buttons_layout.addWidget(self.backup_button)
        
        self.restore_button = ModernButton("Восстановить из бэкапа")
        self.restore_button.setProperty("class", "secondary")
        self.restore_button.clicked.connect(self.start_restore)
        buttons_layout.addWidget(self.restore_button)
        
        self.close_button = ModernButton("Закрыть")
        self.close_button.setProperty("class", "secondary")
        self.close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)
        
    def showEvent(self, event):
        """Инициализация таскбара при показе окна"""
        super().showEvent(event)
        
        if sys.platform == 'win32' and TASKBAR_SUPPORTED:
            try:
                self.taskbar = win32com.client.Dispatch("TaskbarLib.TaskbarList")
                logger.info("Таскбар успешно инициализирован")
            except Exception as e:
                logger.error(f"Ошибка инициализации таскбара: {str(e)}")
                self.taskbar = None

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
        self.backup_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.backup_thread = BackupThread(self.spotify_client, file_name)
        self.backup_thread.progress_updated.connect(self.update_progress)
        self.backup_thread.status_updated.connect(self.update_status)
        self.backup_thread.track_info_updated.connect(self.update_track_info)
        self.backup_thread.error_occurred.connect(self.handle_error)
        self.backup_thread.finished.connect(self.backup_finished)
        
        self.track_info_label.setText("")
        self.backup_thread.start()
        
    def start_restore(self):
        logger.info("Запуск процесса восстановления")
        file_name = QFileDialog.getOpenFileName(
            self,
            "Выбрать файл бэкапа",
            os.path.expanduser("~/Desktop"),
            "JSON файлы (*.json)"
        )[0]
        
        if not file_name:
            logger.info("Пользователь отменил выбор файла")
            return
            
        logger.info(f"Выбран файл для восстановления: {file_name}")
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Восстановление добавит треки из бэкапа в ваши любимые треки. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
            
        self.backup_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        self.restore_thread = RestoreThread(self.spotify_client, file_name)
        self.restore_thread.status_updated.connect(self.status_label.setText)
        self.restore_thread.error_occurred.connect(self.handle_error)
        self.restore_thread.finished.connect(self.restore_finished)
        
        self.restore_thread.start()
        
    def update_progress(self, value: int):
        """Обновляет значение прогресс-бара и таскбара"""
        try:
            self.progress_bar.setValue(value)
            if sys.platform == 'win32' and self.taskbar:
                try:
                    # Получаем HWND окна
                    hwnd = self.winId()
                    if hwnd:
                        # Устанавливаем состояние и значение прогресса
                        self.taskbar.SetProgressState(hwnd, 2)  # 2 = TBPF_NORMAL
                        self.taskbar.SetProgressValue(hwnd, value, 100)
                        logger.debug(f"Обновлен прогресс в таскбаре: {value}%")
                except Exception as e:
                    logger.error(f"Ошибка обновления таскбара: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса: {str(e)}")
        
    def update_status(self, status: str):
        """Обновляет текст статуса"""
        self.status_label.setText(status)
        
    def update_track_info(self, info: str):
        """Обновляет информацию о текущем треке"""
        self.track_info_label.setText(info)
        
    def handle_error(self, error_message: str):
        """Обрабатывает ошибки"""
        logger.error(f"Ошибка: {error_message}")
        self.status_label.setText(f"Ошибка: {error_message}")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        
        # Сбрасываем прогресс в таскбаре при закрытии
        self.reset_taskbar()
        QMessageBox.critical(self, "Ошибка", error_message)
        self.reset_ui()
        
    def backup_finished(self):
        """Обработчик завершения бэкапа"""
        logger.info("Бэкап успешно завершен")
        self.status_label.setText("Бэкап успешно создан!")
        self.status_label.setStyleSheet("color: #1DB954;")
        
        if NOTIFICATIONS_SUPPORTED:
            try:
                toaster.show_toast(
                    "Spotify Merger",
                    "Бэкап успешно создан!",
                    duration=5,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {str(e)}")
            
        QMessageBox.information(self, "Готово", "Бэкап успешно создан!")
        self.reset_ui()
        
    def restore_finished(self):
        """Обработчик завершения восстановления"""
        logger.info("Восстановление успешно завершено")
        
        if NOTIFICATIONS_SUPPORTED:
            try:
                toaster.show_toast(
                    "Spotify Merger",
                    "Треки успешно восстановлены!",
                    duration=5,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {str(e)}")
            
        QMessageBox.information(self, "Готово", "Треки успешно восстановлены!")
        self.accept()
        
    def reset_ui(self):
        """Сбрасывает состояние UI"""
        self.backup_button.setEnabled(True)
        self.restore_button.setEnabled(True)
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Готов к работе")
        self.status_label.setStyleSheet("color: #B3B3B3; font-weight: bold;")
        self.track_info_label.setText("")
        self.track_info_label.setStyleSheet("color: #B3B3B3; font-style: italic;")
        
    def reset_taskbar(self):
        """Сбрасывает прогресс в таскбаре"""
        if sys.platform == 'win32' and self.taskbar:
            try:
                hwnd = self.winId()
                if hwnd:
                    self.taskbar.SetProgressState(hwnd, 0)  # 0 = TBPF_NOPROGRESS
            except Exception as e:
                logger.error(f"Ошибка сброса таскбара: {str(e)}")
        
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        if self.backup_thread and self.backup_thread.is_running:
            logger.info("Отмена процесса бэкапа")
            self.backup_thread.is_running = False
            self.backup_thread.wait()
        if self.restore_thread and self.restore_thread.is_running:
            logger.info("Отмена процесса восстановления")
            self.restore_thread.is_running = False
            self.restore_thread.wait()
            
        # Сбрасываем прогресс в таскбаре при закрытии
        self.reset_taskbar()
        event.accept() 