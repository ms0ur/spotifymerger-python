import os
from typing import List, Dict, Optional, Tuple
from mutagen import File
from PyQt6.QtCore import QObject, pyqtSignal
import re

class TrackProcessor(QObject):
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)
    track_processed = pyqtSignal(dict)  # track info
    error_occurred = pyqtSignal(str, str)  # filename, error message
    
    def __init__(self):
        super().__init__()
        self.valid_extensions = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"}
        
    def get_audio_files(self, directory: str) -> List[str]:
        """Получает список всех аудиофайлов в директории"""
        audio_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1].lower() in self.valid_extensions:
                    audio_files.append(os.path.join(root, file))
        return audio_files
        
    def extract_metadata(self, file_path: str) -> Optional[Tuple[str, str, float]]:
        """Извлекает метаданные из аудиофайла"""
        try:
            audio = File(file_path, easy=True)
            if audio is None:
                return None
                
            title = audio.get("title", [None])[0]
            artist = audio.get("artist", [None])[0]
            
            duration = None
            if hasattr(audio.info, 'length'):
                duration = audio.info.length
                
            if title is not None:
                title = self.clean_metadata(title)
            if artist is not None:
                artist = self.clean_metadata(artist)
                
            return title, artist, duration
            
        except Exception as e:
            self.error_occurred.emit(os.path.basename(file_path), f"Ошибка чтения метаданных: {str(e)}")
            return None
            
    @staticmethod
    def clean_metadata(text: str) -> str:
        """Очищает метаданные от мусора"""
        if not text:
            return text
            
        # Удаляем URL
        text = re.sub(r'https?://\S+', '', text)
        
        # Удаляем текст в скобках с доменными именами
        text = re.sub(r'\[(.*?(?:\.(?:com|ru|net|org|cc|me|io))[^\]]*?)\]', '', text)
        text = re.sub(r'\((.*?(?:\.(?:com|ru|net|org|cc|me|io))[^)]*?)\)', '', text)
        
        # Удаляем фразы типа "downloaded from"
        text = re.sub(r'(?i)downloaded\s+from\s+.*?(?=\s|$)', '', text)
        text = re.sub(r'(?i)from\s+.*?(?:\.(?:com|ru|net|org|cc|me|io)).*?(?=\s|$)', '', text)
        
        # Очищаем от множественных пробелов
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
        
    def verify_track(self, found_track: Dict, original_duration: Optional[float],
                    original_title: Optional[str], original_artist: Optional[str]) -> Tuple[bool, str]:
        """Проверяет соответствие найденного трека оригинальному"""
        if original_duration:
            track_duration = found_track['duration_ms'] / 1000
            if abs(original_duration - track_duration) > 2:
                return False, f"Несовпадение длительности: оригинал {original_duration}с, найдено {track_duration}с"
        
        if original_title and original_artist:
            clean_orig_title = self.clean_metadata(original_title.lower())
            clean_orig_artist = self.clean_metadata(original_artist.lower())
            clean_found_title = self.clean_metadata(found_track['name'].lower())
            clean_found_artist = self.clean_metadata(found_track['artists'][0]['name'].lower())
            
            if not (clean_orig_title in clean_found_title or clean_found_title in clean_orig_title):
                return False, f"Несовпадение названия: '{clean_orig_title}' != '{clean_found_title}'"
                
            if not (clean_orig_artist in clean_found_artist or clean_found_artist in clean_orig_artist):
                return False, f"Несовпадение исполнителя: '{clean_orig_artist}' != '{clean_found_artist}'"
        
        return True, "Трек соответствует" 