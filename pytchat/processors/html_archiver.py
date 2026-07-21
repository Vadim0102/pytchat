import html
import httpx
import os
import re
import time
from base64 import standard_b64encode
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from .chat_processor import ChatProcessor
from .default.processor import DefaultProcessor
from ..exceptions import UnknownConnectionError
import tempfile

PATTERN = re.compile(r"(.*)\(([0-9]+)\)$")

fmt_headers = ['datetime', 'elapsed', 'authorName',
               'message', 'superchat', 'type', 'authorChannel']

# Белый список доверенных доменов для скачивания эмодзи
TRUSTED_DOMAINS = {
    'ggpht.com', 'googleusercontent.com', 'youtube.com',
    'yt3.ggpht.com', 'yt4.ggpht.com', 'android.apis.google.com'
}


def _is_trusted_url(url: str) -> bool:
    """Проверка, что ссылка принадлежит официальным доменам Google/YouTube"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(domain == td or domain.endswith('.' + td) for td in TRUSTED_DOMAINS)
    except Exception:
        return False


class HTMLArchiver(ChatProcessor):
    def __init__(self, save_path, callback=None):
        super().__init__()
        # self.client больше не используется напрямую в потоках для предотвращения гонок
        self.client = httpx.Client(http2=True)
        self.save_path = self._checkpath(save_path)
        self.processor = DefaultProcessor()
        self.emoji_table = {}
        self.callback = callback
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.tmp_fp = tempfile.NamedTemporaryFile(mode="a", encoding="utf-8", delete=False)
        self.tmp_filename = self.tmp_fp.name
        self.counter = 0

    def __del__(self):
        """Гарантированное удаление временного файла при уничтожении объекта в случае сбоя"""
        try:
            if hasattr(self, 'tmp_fp') and self.tmp_fp is not None:
                self.tmp_fp.close()
        except Exception:
            pass
        try:
            if hasattr(self, 'tmp_filename') and os.path.exists(self.tmp_filename):
                os.remove(self.tmp_filename)
        except Exception:
            pass

    def _checkpath(self, filepath):
        """Атомарное резервирование имени файла во избежание состояния гонки (TOCTOU)"""
        splitter = os.path.splitext(os.path.basename(filepath))
        body = splitter[0]
        extention = splitter[1]
        newpath = filepath
        counter = 1
        while True:
            try:
                # Открытие с флагом 'x' гарантирует атомарную ошибку, если файл уже существует
                with open(newpath, mode='x', encoding='utf-8'):
                    pass
                return newpath
            except FileExistsError:
                match = re.search(PATTERN, body)
                if match:
                    counter = int(match[2]) + 1
                    num_with_bracket = f'({str(counter)})'
                    body = f'{match[1]}{num_with_bracket}'
                else:
                    body = f'{body}({str(counter)})'
                newpath = os.path.join(os.path.dirname(filepath), body + extention)

    def _parse_html_line(self, raw_line):
        """Экранирование всех полей, кроме предразобранного и безопасного HTML-сообщения"""
        escaped_cells = []
        for idx, cell in enumerate(raw_line):
            cell_str = str(cell)
            if idx == 3:
                # Поле сообщения уже экранировано внутри _parse_message
                escaped_cells.append(cell_str)
            else:
                escaped_cells.append(html.escape(cell_str))
        return ''.join(('<tr>',
                        ''.join(''.join(('<td>', cell, '</td>')) for cell in escaped_cells),
                        '</tr>\n'))

    def _parse_table_header(self, raw_line):
        return ''.join(('<thead><tr>',
                        ''.join(''.join(('<th>', html.escape(str(cell)), '</th>')) for cell in raw_line),
                        '</tr></thead>\n'))

    def _parse_message(self, message_items: list) -> str:
        """Экранирование текста сообщения и безопасное встраивание эмодзи"""
        res = []
        for item in message_items:
            if isinstance(item, dict):
                # Обработка эмодзи
                emoji_class = self._set_emoji_table(item)
                # Экранируем текст для использования внутри HTML-атрибута title
                escaped_txt = html.escape(item.get('txt', ''), quote=True)
                res.append(f'<span class="{emoji_class}" title="{escaped_txt}"></span>')
            else:
                # Обычный текст сообщения: экранируем полностью
                res.append(html.escape(str(item)))
        return ''.join(res)

    def _encode_img(self, url):
        """Безопасное скачивание изображений с защитой от SSRF, гигантских файлов и гонок в клиенте"""
        if not _is_trusted_url(url):
            raise ValueError(f"Untrusted URL for emoji: {url}")

        err = None
        MAX_SIZE = 1024 * 1024 * 2  # Ограничение размера файла в 2 МБ
        for _ in range(5):
            try:
                # Создаем локальный клиент внутри потока для потокобезопасности
                with httpx.Client(http2=True) as local_client:
                    with local_client.stream("GET", url, timeout=30) as resp:
                        resp.raise_for_status()
                        cl = resp.headers.get("Content-Length")
                        if cl and int(cl) > MAX_SIZE:
                            raise ValueError("Image exceeds maximum allowed size")

                        content = bytearray()
                        for chunk in resp.iter_bytes(chunk_size=8192):
                            content.extend(chunk)
                            if len(content) > MAX_SIZE:
                                raise ValueError("Image exceeds maximum allowed size")
                break
            except (httpx.HTTPError, ValueError) as e:
                err = e
                time.sleep(3)
        else:
            raise UnknownConnectionError(str(err))

        return standard_b64encode(content).decode()
