import logging
from datetime import datetime
from typing import Optional, Dict, List
import os
import json

class Logger:
    _instance = None
    
    def __new__(cls, log_dir: str = "logs"):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_dir: str = "logs"):
        if self._initialized:
            return
            
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Настраиваем логгер
        self.logger = logging.getLogger('SpotifyMerger')
        self.logger.setLevel(logging.INFO)
        
        # Очищаем существующие обработчики
        self.logger.handlers = []
        
        # Создаем форматтер
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Добавляем обработчик для файла
        log_file = os.path.join(log_dir, f"spotify_merger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Добавляем обработчик для консоли
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Создаем файлы для вывода
        self.output_file = os.path.join(log_dir, "output.txt")
        self.missing_file = os.path.join(log_dir, "missing.txt")
        self.output_json = "output.json"
        
        # Инициализируем структуру для хранения треков
        self.playlists: Dict[str, Dict] = {}
        self.tracks_list: List[Dict] = []
        self.processed_track_ids = set()  # Для отслеживания уже добавленных треков
        
        self._initialized = True
        
    def log_track_processed(self, file_path: str, track_info: dict, details: dict = None):
        """Логирует информацию об обработанном треке"""
        # Проверяем, не был ли этот трек уже добавлен
        track_id = track_info['id']
        if track_id in self.processed_track_ids:
            return
            
        # Добавляем ID в множество обработанных
        self.processed_track_ids.add(track_id)
        
        # Логируем в основной лог
        self.logger.info(
            f"Добавлен трек: {track_info['name']} - {track_info['artists'][0]['name']} "
            f"в плейлист {details.get('playlist', 'Unknown')}"
        )
        
        # Добавляем трек в список для JSON
        track_data = {
            "id": track_id,
            "uri": f"spotify:track:{track_id}"
        }
        self.tracks_list.append(track_data)
        
        # Записываем в output.txt
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] Обработан файл: {os.path.basename(file_path)}\n")
                f.write(f"  Оригинал: {details.get('original_title', '')} - {details.get('original_artist', '')}\n")
                f.write(f"  Spotify: {track_info['name']} - {track_info['artists'][0]['name']}\n")
                f.write(f"  ID: {track_info['id']}\n")
                if details.get('manual_selection'):
                    f.write("  (Выбрано вручную)\n")
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Ошибка при записи в output.txt: {e}")
            
    def save_results(self, playlist_id: str = None, playlist_name: str = "My playlist #1"):
        """Сохраняет результаты в JSON формате"""
        try:
            # Формируем структуру данных
            playlist_data = {
                "name": playlist_name,
                "id": playlist_id or "",
                "tracks": self.tracks_list
            }
            
            result = {
                "playlists": {
                    playlist_name: playlist_data
                }
            }
            
            # Сохраняем в JSON файл
            with open(self.output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                
            # Добавляем итоговую информацию в output.txt
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write("\nИтоговая информация:\n")
                f.write(json.dumps(result, indent=2, ensure_ascii=False))
                f.write("\n")
                
            self.logger.info(f"Сохранено {len(self.tracks_list)} треков в {self.output_json}")
                
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении результатов: {e}")
        
    def log_error(self, file_path: str, error: str):
        """Логирует ошибку обработки файла"""
        # Логируем в основной лог
        self.logger.error(f"Ошибка при обработке {file_path}: {error}")
        
        # Записываем в missing.txt
        try:
            with open(self.missing_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {os.path.basename(file_path)}\n")
                f.write(f"  Причина: {error}\n\n")
        except Exception as e:
            self.logger.error(f"Ошибка при записи в missing.txt: {e}")
        
    def log_missing(self, file_path: str, reason: str):
        """Логирует информацию о пропущенном файле"""
        # Логируем в основной лог
        self.logger.warning(f"Пропущен файл {file_path}. Причина: {reason}")
        
        # Записываем в missing.txt
        try:
            with open(self.missing_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {os.path.basename(file_path)}\n")
                f.write(f"  Причина: {reason}\n\n")
        except Exception as e:
            self.logger.error(f"Ошибка при записи в missing.txt: {e}")
        
    def log_info(self, message: str):
        """Логирует информационное сообщение"""
        self.logger.info(message)
        
    def log_warning(self, message: str):
        """Логирует предупреждение"""
        self.logger.warning(message)
        
    def log_debug(self, message: str):
        """Логирует отладочное сообщение"""
        self.logger.debug(message) 