import requests
import time
import base64
import urllib.parse
import webbrowser
import json
import logging
from typing import Optional, Tuple, Dict, Any, List, Generator
import http.server
import socketserver
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import os

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    auth_code = None
    
    def do_GET(self):
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if 'code' in query_components:
            OAuthHandler.auth_code = query_components['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html lang="ru">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Spotify Merger - Авторизация</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background-color: #121212;
                        color: #FFFFFF;
                        margin: 0;
                        padding: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        text-align: center;
                    }
                    .container {
                        background-color: #282828;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        max-width: 400px;
                        width: 90%;
                    }
                    h1 {
                        color: #1DB954;
                        font-size: 24px;
                        margin-bottom: 20px;
                    }
                    .success-icon {
                        font-size: 48px;
                        margin-bottom: 20px;
                        color: #1DB954;
                    }
                    p {
                        color: #B3B3B3;
                        line-height: 1.6;
                        margin-bottom: 20px;
                    }
                    .close-button {
                        background-color: #1DB954;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: background-color 0.3s;
                    }
                    .close-button:hover {
                        background-color: #1ed760;
                    }
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(-20px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                    .fade-in {
                        animation: fadeIn 0.5s ease-out;
                    }
                </style>
            </head>
            <body>
                <div class="container fade-in">
                    <div class="success-icon">✓</div>
                    <h1>Авторизация успешна!</h1>
                    <p>Вы успешно авторизовались в Spotify Merger.<br>Теперь вы можете вернуться в приложение.</p>
                    <button class="close-button" onclick="window.close()">Закрыть окно</button>
                </div>
                <script>
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            error_html = """
            <!DOCTYPE html>
            <html lang="ru">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Spotify Merger - Ошибка</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background-color: #121212;
                        color: #FFFFFF;
                        margin: 0;
                        padding: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        text-align: center;
                    }
                    .container {
                        background-color: #282828;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        max-width: 400px;
                        width: 90%;
                    }
                    h1 {
                        color: #ff6b6b;
                        font-size: 24px;
                        margin-bottom: 20px;
                    }
                    .error-icon {
                        font-size: 48px;
                        margin-bottom: 20px;
                        color: #ff6b6b;
                    }
                    p {
                        color: #B3B3B3;
                        line-height: 1.6;
                        margin-bottom: 20px;
                    }
                    .close-button {
                        background-color: #ff6b6b;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: background-color 0.3s;
                    }
                    .close-button:hover {
                        background-color: #ff8787;
                    }
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(-20px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                    .fade-in {
                        animation: fadeIn 0.5s ease-out;
                    }
                </style>
            </head>
            <body>
                <div class="container fade-in">
                    <div class="error-icon">⚠</div>
                    <h1>Ошибка авторизации</h1>
                    <p>Произошла ошибка при авторизации в Spotify.<br>Пожалуйста, попробуйте снова.</p>
                    <button class="close-button" onclick="window.close()">Закрыть окно</button>
                </div>
                <script>
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))

class SpotifyClient:
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0
        self.user_token = None
        self.user_token_expires_at = 0
        
        logger.info("Инициализация SpotifyClient")
        # Пытаемся загрузить сохраненные учетные данные
        self.load_credentials()
        
        if self.client_id and self.client_secret:
            self.initialize_client()
    
    def load_credentials(self):
        """Загружает сохраненные учетные данные"""
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.spotify_merger')
            credentials_path = os.path.join(config_dir, 'credentials.json')
            
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    data = json.load(f)
                    if not self.client_id:
                        self.client_id = data.get('client_id')
                    if not self.client_secret:
                        self.client_secret = data.get('client_secret')
        except Exception:
            pass
    
    def save_credentials(self, client_id: str, client_secret: str):
        """Сохраняет учетные данные"""
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.spotify_merger')
            os.makedirs(config_dir, exist_ok=True)
            
            credentials_path = os.path.join(config_dir, 'credentials.json')
            
            with open(credentials_path, 'w') as f:
                json.dump({
                    'client_id': client_id,
                    'client_secret': client_secret
                }, f)
                
            self.client_id = client_id
            self.client_secret = client_secret
            return self.initialize_client()
        except Exception as e:
            return False, str(e)
    
    def initialize_client(self):
        """Инициализирует клиент"""
        try:
            # Проверяем валидность учетных данных, получая токен
            token = self.get_token()
            if not token:
                return False, "Не удалось получить токен доступа"
            return True, "OK"
        except Exception as e:
            return False, str(e)
    
    def is_authorized(self):
        """Проверяет, авторизован ли клиент"""
        return bool(self.client_id and self.client_secret and self.get_token())
    
    def get_token(self) -> str:
        """Получает или обновляет токен доступа для поиска"""
        if self.access_token and time.time() < self.token_expires_at - 60:
            return self.access_token
            
        try:
            auth_response = requests.post(
                "https://accounts.spotify.com/api/token",
                data={'grant_type': 'client_credentials'},
                auth=(self.client_id, self.client_secret),
                timeout=10,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if auth_response.status_code != 200:
                raise Exception(f"Ошибка получения токена: {auth_response.text}")
            
            response_data = auth_response.json()
            self.access_token = response_data['access_token']
            self.token_expires_at = time.time() + response_data['expires_in']
            return self.access_token
            
        except Exception as e:
            self.access_token = None
            self.token_expires_at = 0
            raise e
        
    def get_user_token(self) -> str:
        """Получает или обновляет пользовательский токен для создания плейлистов"""
        if self.user_token and time.time() < self.user_token_expires_at - 60:
            return self.user_token
            
        return self._fetch_user_token()
        
    def _start_auth_server(self) -> Tuple[socketserver.TCPServer, Thread]:
        """Запускает локальный сервер для получения кода авторизации"""
        OAuthHandler.auth_code = None
        server = socketserver.TCPServer(('localhost', 8888), OAuthHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return server, server_thread
        
    def _fetch_user_token(self) -> str:
        """Получает пользовательский токен через OAuth"""
        auth_url = "https://accounts.spotify.com/authorize"
        token_url = "https://accounts.spotify.com/api/token"
        redirect_uri = "http://localhost:8888/callback"
        scope = "playlist-modify-public playlist-modify-private user-library-read user-library-modify"
        
        # Запускаем локальный сервер
        server, server_thread = self._start_auth_server()
        
        try:
            # Генерируем URL для авторизации
            auth_params = {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": scope
            }
            
            auth_url_with_params = f"{auth_url}?{urllib.parse.urlencode(auth_params)}"
            
            print("\nДля экспорта плейлиста требуется авторизация в Spotify.")
            print("Сейчас откроется окно браузера. Пожалуйста, войдите в свой аккаунт.")
            webbrowser.open(auth_url_with_params)
            
            # Ждем получения кода авторизации
            while OAuthHandler.auth_code is None:
                time.sleep(1)
            
            auth_code = OAuthHandler.auth_code
            
            # Получаем токен доступа
            auth_header = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            if response.status_code != 200:
                raise Exception(f"Ошибка получения пользовательского токена: {response.text}")
            
            response_data = response.json()
            self.user_token = response_data['access_token']
            self.user_token_expires_at = time.time() + response_data['expires_in']
            return self.user_token
            
        finally:
            # Останавливаем сервер
            server.shutdown()
            server.server_close()
        
    def create_playlist(self, name: str, description: str = "") -> str:
        """Создает новый плейлист в Spotify"""
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        
        # Получаем ID пользователя
        user_response = requests.get(
            "https://api.spotify.com/v1/me",
            headers=headers
        )
        if user_response.status_code != 200:
            raise Exception("Ошибка получения данных пользователя")
            
        user_id = user_response.json()["id"]
        
        # Создаем плейлист
        playlist_data = {
            "name": name,
            "description": description,
            "public": False
        }
        
        playlist_response = requests.post(
            f"https://api.spotify.com/v1/users/{user_id}/playlists",
            headers=headers,
            json=playlist_data
        )
        
        if playlist_response.status_code != 201:
            raise Exception(f"Ошибка создания плейлиста: {playlist_response.text}")
            
        return playlist_response.json()["id"]
        
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> None:
        """Добавляет треки в плейлист"""
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        
        # Добавляем треки порциями по 100 штук
        for i in range(0, len(track_uris), 100):
            chunk = track_uris[i:i + 100]
            response = requests.post(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                headers=headers,
                json={"uris": chunk}
            )
            if response.status_code != 201:
                raise Exception(f"Ошибка добавления треков в плейлист: {response.text}")
                
    def search_track(self, query: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Поиск трека в Spotify"""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "q": query,
            "type": "track",
            "limit": 5,
            "market": "TR"
        }
        
        try:
            response = requests.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            if not results.get("tracks") or not results["tracks"]["items"]:
                return None, "Треки не найдены"
                
            return results["tracks"]["items"], "OK"
            
        except requests.exceptions.RequestException as e:
            return None, f"Ошибка запроса: {str(e)}"
            
    def get_track_by_url(self, url: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Получает информацию о треке по ссылке Spotify"""
        import re
        
        track_id = re.search(r'track/([a-zA-Z0-9]+)', url)
        if not track_id:
            return None, "Неверный формат ссылки"
            
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.get(
                f"https://api.spotify.com/v1/tracks/{track_id.group(1)}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json(), None
            
        except requests.exceptions.RequestException as e:
            return None, f"Ошибка при получении трека: {str(e)}"

    def authorize(self) -> None:
        """Запускает процесс авторизации пользователя"""
        self.get_user_token()

    def get_liked_tracks(self) -> List[Dict]:
        """Получает все любимые треки (устаревший метод)"""
        logger.warning("Использование устаревшего метода get_liked_tracks")
        tracks = []
        for batch in self.get_liked_tracks_batches():
            tracks.extend(batch)
        return tracks

    def get_current_user_id(self) -> str:
        """Получает ID текущего пользователя"""
        logger.debug("Получение ID текущего пользователя")
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.spotify.com/v1/me",
            headers=headers
        )
        if response.status_code != 200:
            logger.error(f"Ошибка получения данных пользователя: {response.text}")
            raise Exception("Ошибка получения данных пользователя")
            
        return response.json()["id"]
            
    def get_liked_tracks_count(self) -> int:
        """Получает общее количество любимых треков"""
        logger.debug("Получение количества любимых треков")
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(
            "https://api.spotify.com/v1/me/tracks",
            headers=headers,
            params={"limit": 1}
        )

        if response.status_code != 200:
            logger.error(f"Ошибка получения количества треков: {response.text}")
            raise Exception(f"Ошибка получения любимых треков: {response.text}")

        return response.json()["total"]

    def get_liked_tracks_batches(self, batch_size: int = 50) -> Generator[List[Dict], None, None]:
        """Получает любимые треки порциями"""
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }

        offset = 0
        total = None

        while True:
            logger.debug(f"Получение порции треков с offset={offset}")
            response = requests.get(
                "https://api.spotify.com/v1/me/tracks",
                headers=headers,
                params={"limit": batch_size, "offset": offset}
            )

            if response.status_code != 200:
                logger.error(f"Ошибка получения треков: {response.text}")
                raise Exception(f"Ошибка получения любимых треков: {response.text}")

            data = response.json()
            if total is None:
                total = data["total"]
                logger.info(f"Всего треков: {total}")

            tracks = data["items"]
            if not tracks:
                break

            logger.debug(f"Получено {len(tracks)} треков")
            yield tracks
            
            offset += batch_size
            if offset >= total:
                break

    def add_to_liked_tracks(self, track_ids: List[str]) -> None:
        """Добавляет треки в любимые"""
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }

        # Добавляем треки порциями по 50 штук
        for i in range(0, len(track_ids), 50):
            chunk = track_ids[i:i + 50]
            response = requests.put(
                "https://api.spotify.com/v1/me/tracks",
                headers=headers,
                json={"ids": chunk}
            )
            if response.status_code not in [200, 201]:
                raise Exception(f"Ошибка добавления треков в любимые: {response.text}")

    def restore_from_backup(self, backup_file: str) -> Tuple[int, str]:
        """Восстанавливает треки из бэкапа в любимые треки
        
        Args:
            backup_file: Путь к файлу бэкапа
            
        Returns:
            Tuple[int, str]: Количество восстановленных треков и сообщение о результате
        """
        try:
            # Читаем файл бэкапа
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
                
            if not isinstance(backup_data, dict) or 'tracks' not in backup_data:
                return 0, "Неверный формат файла бэкапа"
                
            tracks = backup_data['tracks']
            if not tracks:
                return 0, "В бэкапе нет треков"
                
            # Извлекаем ID треков из URI
            track_ids = []
            for track in tracks:
                if 'spotify_uri' in track:
                    track_id = track['spotify_uri'].split(':')[-1]
                    track_ids.append(track_id)
                    
            if not track_ids:
                return 0, "Не найдено действительных ID треков"
                
            # Добавляем треки в любимые
            self.add_to_liked_tracks(track_ids)
            
            return len(track_ids), "Треки успешно восстановлены"
            
        except json.JSONDecodeError:
            return 0, "Ошибка чтения файла бэкапа: неверный формат JSON"
        except Exception as e:
            return 0, f"Ошибка при восстановлении: {str(e)}"

    def check_liked_tracks(self, track_ids: List[str]) -> List[bool]:
        """Проверяет, находятся ли треки в любимых"""
        user_token = self.get_user_token()
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }

        results = []
        # Проверяем треки порциями по 50 штук
        for i in range(0, len(track_ids), 50):
            chunk = track_ids[i:i + 50]
            response = requests.get(
                "https://api.spotify.com/v1/me/tracks/contains",
                headers=headers,
                params={"ids": ",".join(chunk)}
            )
            if response.status_code != 200:
                raise Exception(f"Ошибка проверки любимых треков: {response.text}")
            results.extend(response.json())

        return results 