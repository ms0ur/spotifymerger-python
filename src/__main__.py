import os
import sys
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import SpotifyMergerWindow

def main():
    app = QApplication(sys.argv)
    window = SpotifyMergerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 