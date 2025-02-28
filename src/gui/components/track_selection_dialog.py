from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QWidget, QFrame, QScrollArea,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QFont
import requests
from io import BytesIO
from src.gui.styles.modern_style import DIALOG_STYLE, BUTTON_STYLE
from functools import lru_cache
import threading

class ImageLoader(QThread):
    image_loaded = pyqtSignal(str, QPixmap)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            response = requests.get(self.url, timeout=5)
            image_data = BytesIO(response.content)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data.getvalue())
            scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_loaded.emit(self.url, scaled_pixmap)
        except Exception as e:
            print(f"Error loading image: {e}")

class TrackItemWidget(QWidget):
    def __init__(self, track, metadata=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Создаем и добавляем лейбл для обложки
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(50, 50)
        self.cover_label.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        layout.addWidget(self.cover_label)
        
        # Загружаем обложку асинхронно
        cover_url = track.get('album', {}).get('images', [{}])[0].get('url')
        if cover_url:
            self.loader = ImageLoader(cover_url)
            self.loader.image_loaded.connect(self._set_image)
            self.loader.start()
        else:
            self.cover_label.setText("No cover")
                
        # Создаем и добавляем информацию о треке
        info_container = QFrame()
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(2)
        
        # Сравниваем и подсвечиваем совпадающие характеристики
        title_style = ""
        artist_style = ""
        duration_style = ""
        
        if metadata:
            orig_title, orig_artist, orig_duration = metadata
            # Проверяем совпадение названия
            if orig_title.lower() in track['name'].lower() or track['name'].lower() in orig_title.lower():
                title_style = "color: #1DB954; font-weight: bold;"
            # Проверяем совпадение исполнителя
            if orig_artist.lower() in track['artists'][0]['name'].lower() or track['artists'][0]['name'].lower() in orig_artist.lower():
                artist_style = "color: #1DB954; font-weight: bold;"
            # Проверяем совпадение длительности (с погрешностью в 2 секунды)
            track_duration = track['duration_ms'] / 1000
            if abs(track_duration - orig_duration) <= 2:
                duration_style = "color: #1DB954; font-weight: bold;"
        
        title_label = QLabel(track['name'])
        title_label.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
        if title_style:
            title_label.setStyleSheet(title_style)
        info_layout.addWidget(title_label)
        
        artist_label = QLabel(track['artists'][0]['name'])
        artist_label.setFont(QFont('Segoe UI', 9))
        if artist_style:
            artist_label.setStyleSheet(artist_style)
        else:
            artist_label.setStyleSheet("color: #666666;")
        info_layout.addWidget(artist_label)
        
        duration = track['duration_ms'] / 1000
        album = track.get('album', {}).get('name', 'Неизвестный альбом')
        details_label = QLabel(f"Длительность: {duration:.1f}с • {album}")
        details_label.setFont(QFont('Segoe UI', 8))
        if duration_style:
            details_label.setStyleSheet(duration_style)
        else:
            details_label.setStyleSheet("color: #999999;")
        info_layout.addWidget(details_label)
        
        layout.addWidget(info_container)
        layout.addStretch()
        
    def _set_image(self, url, pixmap):
        if not self.cover_label:
            return
        self.cover_label.setPixmap(pixmap)

class ModernButton(QPushButton):
    def __init__(self, text, parent=None, color="#1DB954"):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setFont(QFont('Segoe UI', 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        style = BUTTON_STYLE.replace("#1DB954", color)
        self.setStyleSheet(style)

class TrackSelectionDialog(QDialog):
    search_requested = pyqtSignal(str)
    link_submitted = pyqtSignal(str)
    
    def __init__(self, tracks, metadata, spotify_client, parent=None):
        super().__init__(parent)
        self.tracks = tracks
        self.metadata = metadata
        self.spotify_client = spotify_client
        self.selected_track = None
        self.search_mode = False
        
        self.setWindowTitle("Выбор трека")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(DIALOG_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Информация об оригинальном файле
        title, artist, duration = metadata
        info_container = QFrame()
        info_container.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border-radius: 10px;
                padding: 15px;
            }
            QLabel {
                color: #333333;
                font-family: 'Segoe UI';
                padding: 2px;
            }
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(8)
        
        header = QLabel("Оригинальный файл")
        header.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        info_layout.addWidget(header)
        
        info_layout.addWidget(QLabel(f"Название: {title}"))
        info_layout.addWidget(QLabel(f"Исполнитель: {artist}"))
        if duration:
            info_layout.addWidget(QLabel(f"Длительность: {duration:.1f} сек"))
            
        layout.addWidget(info_container)
        
        # Поле поиска (перемещаем выше списка)
        self.search_container = QFrame()
        self.search_container.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border-radius: 10px;
                padding: 10px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                background-color: white;
                color: #333333;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1DB954;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(10, 10, 10, 10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите поисковый запрос")
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_input.setMinimumHeight(40)
        search_layout.addWidget(self.search_input)
        
        self.search_submit_btn = ModernButton("Найти")
        self.search_submit_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_submit_btn)
        
        layout.addWidget(self.search_container)
        self.search_container.hide()
        
        # Список найденных треков в ScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
        """)
        
        tracks_container = QWidget()
        tracks_container.setStyleSheet("background-color: white;")
        tracks_layout = QVBoxLayout(tracks_container)
        tracks_layout.setContentsMargins(0, 0, 0, 0)
        tracks_layout.setSpacing(0)
        
        self.tracks_list = QListWidget()
        self.tracks_list.setSpacing(2)
        self.tracks_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: white;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #f8f8f8;
            }
            QListWidget::item:selected {
                background-color: #e8f5e9;
                color: black;
            }
        """)
        tracks_layout.addWidget(self.tracks_list)
        
        scroll_area.setWidget(tracks_container)
        layout.addWidget(scroll_area)
        
        self.update_tracks_list()
        
        # Поле для Spotify ссылки
        self.link_container = QFrame()
        self.link_container.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border-radius: 10px;
                padding: 10px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                background-color: white;
                color: #333333;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1DB954;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        link_layout = QHBoxLayout(self.link_container)
        link_layout.setContentsMargins(10, 10, 10, 10)
        
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Вставьте ссылку на трек Spotify")
        self.link_input.returnPressed.connect(self.submit_link)
        self.link_input.setMinimumHeight(40)
        link_layout.addWidget(self.link_input)
        
        self.link_submit_btn = ModernButton("Добавить")
        self.link_submit_btn.clicked.connect(self.submit_link)
        link_layout.addWidget(self.link_submit_btn)
        
        layout.addWidget(self.link_container)
        self.link_container.hide()
        
        # Кнопки действий
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.select_btn = ModernButton("Выбрать (Enter)")
        self.select_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.select_btn)
        
        self.search_btn = ModernButton("Поиск (S)", color="#4a90e2")
        self.search_btn.clicked.connect(self.toggle_search)
        buttons_layout.addWidget(self.search_btn)
        
        self.spotify_link_btn = ModernButton("Добавить по ссылке (L)", color="#4a90e2")
        self.spotify_link_btn.clicked.connect(self.add_by_link)
        buttons_layout.addWidget(self.spotify_link_btn)
        
        self.skip_btn = ModernButton("Пропустить (Esc)", color="#ff6b6b")
        self.skip_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.skip_btn)
        
        layout.addLayout(buttons_layout)
        
        # Добавляем горячие клавиши
        QShortcut(QKeySequence(Qt.Key.Key_Return), self, self.accept)
        QShortcut(QKeySequence(Qt.Key.Key_Enter), self, self.accept)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.reject)
        QShortcut(QKeySequence("S"), self, self.toggle_search)
        QShortcut(QKeySequence("L"), self, self.add_by_link)
        
        # Добавляем обработку стрелок
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, lambda: self.navigate_tracks(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, lambda: self.navigate_tracks(1))
        
        # Подключаем обработчики сигналов
        self.search_requested.connect(self._handle_search)
        self.link_submitted.connect(self._handle_link)
        
        # Если треки найдены, выбираем наиболее подходящий
        if tracks:
            self.select_best_match()
            
    def select_best_match(self):
        """Выбирает наиболее подходящий трек"""
        best_score = -1
        best_index = 0
        
        for i in range(self.tracks_list.count()):
            item = self.tracks_list.item(i)
            track = item.data(Qt.ItemDataRole.UserRole)
            score = calculate_track_similarity(track, self.metadata)
            
            if score > best_score:
                best_score = score
                best_index = i
                
        self.tracks_list.setCurrentRow(best_index)
        
    def navigate_tracks(self, direction):
        """Навигация по трекам с помощью стрелок"""
        current_row = self.tracks_list.currentRow()
        new_row = current_row + direction
        
        if 0 <= new_row < self.tracks_list.count():
            self.tracks_list.setCurrentRow(new_row)
            
    def accept(self):
        """Переопределяем метод принятия диалога"""
        selected_track = self.get_selected_track()
        if selected_track:
            self.selected_track = selected_track
            super().accept()
            # Эмитим сигнал о том, что можно открывать следующий диалог
            QTimer.singleShot(100, lambda: self.parent().process_manual_queue() if self.parent() else None)
            
    def update_tracks_list(self):
        self.tracks_list.clear()
        for track in self.tracks:
            item = QListWidgetItem(self.tracks_list)
            track_widget = TrackItemWidget(track, self.metadata)
            item.setSizeHint(track_widget.sizeHint())
            self.tracks_list.addItem(item)
            self.tracks_list.setItemWidget(item, track_widget)
            item.setData(Qt.ItemDataRole.UserRole, track)
            
        # Выбираем наиболее подходящий трек
        if self.tracks:
            self.select_best_match()
        
    def toggle_search(self):
        self.search_mode = not self.search_mode
        self.search_container.setVisible(self.search_mode)
        self.link_container.hide()
        
        if self.search_mode:
            self.search_input.setFocus()
            default_query = f"{self.metadata[0]} {self.metadata[1]}"
            self.search_input.setText(default_query)
            
    def add_by_link(self):
        self.search_container.hide()
        self.link_container.setVisible(not self.link_container.isVisible())
        
        if self.link_container.isVisible():
            self.link_input.setFocus()
            
    def perform_search(self):
        query = self.search_input.text().strip()
        if query:
            self.search_requested.emit(query)
            # Фокусируемся на списке после поиска
            self.tracks_list.setFocus()
            
    def submit_link(self):
        link = self.link_input.text().strip()
        if link:
            self.link_submitted.emit(link)
            
    def get_selected_track(self):
        current_item = self.tracks_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
        
    def _handle_search(self, query):
        """Обработчик поиска треков"""
        tracks, message = self.spotify_client.search_track(query)
        if tracks:
            self.tracks = tracks
            self.update_tracks_list()
        else:
            QMessageBox.warning(self, "Поиск", f"Ничего не найдено: {message}")
            
    def _handle_link(self, link):
        """Обработчик добавления по ссылке"""
        track, error = self.spotify_client.get_track_by_url(link)
        if track:
            self.tracks = [track]
            self.update_tracks_list()
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось получить трек: {error}")

def calculate_track_similarity(track, metadata):
    """Вычисляет схожесть трека с оригинальными метаданными"""
    score = 0
    title, artist, duration = metadata
    
    # Проверяем название
    if title.lower() in track['name'].lower() or track['name'].lower() in title.lower():
        score += 1
    
    # Проверяем исполнителя
    if artist.lower() in track['artists'][0]['name'].lower() or track['artists'][0]['name'].lower() in artist.lower():
        score += 1
    
    # Проверяем длительность
    track_duration = track['duration_ms'] / 1000
    if abs(track_duration - duration) <= 2:
        score += 1
    
    return score 