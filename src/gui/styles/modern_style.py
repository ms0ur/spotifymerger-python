"""Модуль содержит стили для современного интерфейса приложения"""

MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #ffffff;
    }
    QLabel {
        color: #333333;
        font-family: 'Segoe UI';
    }
"""

TITLE_STYLE = """
    font-size: 32px;
    font-weight: bold;
    color: #1DB954;
    margin: 20px;
    font-family: 'Segoe UI';
"""

BUTTON_STYLE = """
    QPushButton {
        background-color: #1DB954;
        border: none;
        border-radius: 20px;
        color: white;
        padding: 8px 16px;
    }
    QPushButton:hover {
        background-color: #1ed760;
    }
    QPushButton:pressed {
        background-color: #1aa34a;
    }
    QPushButton:disabled {
        background-color: #b3b3b3;
    }
"""

PROGRESS_BAR_STYLE = """
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
"""

CONTAINER_STYLE = "background-color: #f8f8f8; border-radius: 15px;"

DIR_LABEL_STYLE = "font-size: 12px; color: #666666;"

STATUS_LABEL_STYLE = "font-size: 14px; color: #333333;"

DIALOG_STYLE = """
    QDialog {
        background-color: #ffffff;
    }
    QLabel {
        color: #333333;
        font-family: 'Segoe UI';
    }
    QLineEdit {
        padding: 8px;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        background-color: #ffffff;
        font-family: 'Segoe UI';
    }
    QLineEdit:focus {
        border: 2px solid #1DB954;
    }
    QListWidget {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        background-color: #ffffff;
        font-family: 'Segoe UI';
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #f0f0f0;
    }
    QListWidget::item:selected {
        background-color: #1DB954;
        color: white;
    }
""" 