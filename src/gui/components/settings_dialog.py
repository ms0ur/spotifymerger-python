from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt
from src.core.spotify_client import SpotifyClient

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

class SettingsDialog(QDialog):
    def __init__(self, spotify_client: SpotifyClient, parent=None):
        super().__init__(parent)
        self.spotify_client = spotify_client
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Настройки")
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
        title = QLabel("Настройки Spotify API")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1DB954;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Описание
        description = QLabel(
            "Для работы приложения необходимо указать учетные данные вашего приложения Spotify. "
            "Вы можете получить их, создав приложение на странице "
            "<a href='https://developer.spotify.com/dashboard' style='color: #1DB954;'>Spotify Developer Dashboard</a>."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #B3B3B3;")
        description.setOpenExternalLinks(True)
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
        
        # Client ID
        client_id_label = QLabel("Client ID:")
        main_layout.addWidget(client_id_label)
        
        self.client_id_edit = QLineEdit()
        self.client_id_edit.setPlaceholderText("Введите Client ID")
        if self.spotify_client.client_id:
            self.client_id_edit.setText(self.spotify_client.client_id)
        main_layout.addWidget(self.client_id_edit)
        
        # Client Secret
        client_secret_label = QLabel("Client Secret:")
        main_layout.addWidget(client_secret_label)
        
        self.client_secret_edit = QLineEdit()
        self.client_secret_edit.setPlaceholderText("Введите Client Secret")
        if self.spotify_client.client_secret:
            self.client_secret_edit.setText(self.spotify_client.client_secret)
        main_layout.addWidget(self.client_secret_edit)
        
        # Статусы
        status_layout = QHBoxLayout()
        
        # Статус учетных данных
        self.credentials_status = QLabel(
            "✅ Учетные данные сохранены" if self.spotify_client.client_id and self.spotify_client.client_secret
            else "⚠️ Требуется ввести учетные данные"
        )
        self.credentials_status.setStyleSheet(
            "color: #1DB954;" if self.spotify_client.client_id and self.spotify_client.client_secret
            else "color: #B3B3B3;"
        )
        status_layout.addWidget(self.credentials_status)
        
        # Статус авторизации
        self.auth_status = QLabel(
            "✅ Авторизован" if self.spotify_client.is_authorized()
            else "⚠️ Требуется авторизация"
        )
        self.auth_status.setStyleSheet(
            "color: #1DB954;" if self.spotify_client.is_authorized()
            else "color: #B3B3B3;"
        )
        status_layout.addWidget(self.auth_status)
        
        main_layout.addLayout(status_layout)
        
        layout.addWidget(main_frame)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.save_button = ModernButton("Сохранить")
        self.save_button.clicked.connect(self.save_settings)
        
        self.auth_button = ModernButton("Авторизоваться")
        self.auth_button.setProperty("class", "secondary")
        self.auth_button.clicked.connect(self.start_authorization)
        self.auth_button.setEnabled(bool(self.spotify_client.client_id and self.spotify_client.client_secret))
        
        self.close_button = ModernButton("Закрыть")
        self.close_button.setProperty("class", "secondary")
        self.close_button.clicked.connect(self.accept)
        
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.auth_button)
        buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(buttons_layout)
        
    def save_settings(self):
        client_id = self.client_id_edit.text().strip()
        client_secret = self.client_secret_edit.text().strip()
        
        if not client_id or not client_secret:
            QMessageBox.warning(self, "Ошибка", "Необходимо заполнить оба поля")
            return
        
        success, error = self.spotify_client.save_credentials(client_id, client_secret)
        
        if success:
            self.credentials_status.setText("✅ Учетные данные сохранены")
            self.credentials_status.setStyleSheet("color: #1DB954;")
            self.auth_button.setEnabled(True)
            QMessageBox.information(self, "Успех", "Настройки сохранены успешно")
        else:
            self.credentials_status.setText("⚠️ Ошибка сохранения")
            self.credentials_status.setStyleSheet("color: #ff6b6b;")
            self.auth_button.setEnabled(False)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {error}")
            
    def start_authorization(self):
        try:
            QMessageBox.information(
                self,
                "Авторизация",
                "Сейчас откроется окно браузера для авторизации в Spotify. "
                "Пожалуйста, войдите в свой аккаунт и разрешите доступ приложению."
            )
            self.spotify_client.authorize()
            self.auth_status.setText("✅ Авторизован")
            self.auth_status.setStyleSheet("color: #1DB954;")
            QMessageBox.information(self, "Успех", "Авторизация выполнена успешно")
        except Exception as e:
            self.auth_status.setText("⚠️ Ошибка авторизации")
            self.auth_status.setStyleSheet("color: #ff6b6b;")
            QMessageBox.critical(
                self,
                "Ошибка авторизации",
                f"Не удалось выполнить авторизацию: {str(e)}\n"
                "Проверьте правильность введенных данных и попробуйте снова."
            ) 