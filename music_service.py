"""Music service for downloading and searching music."""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup, Tag
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Загрузка заголовков
headers_path = Path(__file__).parent / "headers.json"
with open(headers_path, encoding="utf-8") as f:
    DEFAULT_HEADERS = json.load(f)

@dataclass
class ServiceConfig:
    """Configuration for music service."""
    timeout: int = 30
    headers: dict = field(default_factory=lambda: DEFAULT_HEADERS)

@dataclass
class Track:
    """Track data class."""
    index: int
    name: str
    title: str
    performer: str
    audio_url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Track":
        """Create Track from a dictionary."""
        return cls(
            index=int(data["index"]),
            name=data["name"],
            title=data["title"],
            performer=data["performer"],
            audio_url=data["audio_url"],
        )

    @classmethod
    def from_element(cls, element: BeautifulSoup | Tag, index: int) -> "Track":
        """Create Track from BeautifulSoup element."""
        artist_name_element = element.find(class_="playlist-name-artist")
        track_name_element = element.find(class_="playlist-name-title")
        if artist_name_element is None or track_name_element is None:
            raise ValueError("Could not find artist name element")

        performer = artist_name_element.text.strip()
        title = track_name_element.text.strip()
        full_name = f"{performer} - {title}"

        audio_url = element.find(class_="playlist-play")
        if not isinstance(audio_url, Tag):
            raise TypeError("Could not find audio URL element")
        audio_url = audio_url.get("data-url", "")

        return cls(
            index=index,
            name=full_name,
            title=title,
            performer=performer,
            audio_url=str(audio_url),
        )

class MusicServiceError(Exception):
    """Base exception for music service errors."""
    pass

class Music:
    """Service for searching and downloading music."""
    BASE_URL = "vuxo7.com"

    def __init__(self, config: ServiceConfig | None = None) -> None:
        self._config = config or ServiceConfig()
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "Music":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Initialize HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(headers=self._config.headers)

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def search(self, keyword: str) -> list[Track]:
        """Search for music by keyword."""
        if not self._session:
            raise MusicServiceError("Failed to initialize session")

        url = self.build_search_query(keyword)
        logger.info("Searching music with keyword: %s", keyword)
        return await self._parse_tracks(url)

    async def get_top_hits(self) -> list[Track]:
        """Get top tracks."""
        return await self._parse_tracks(f"https://{self.BASE_URL}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def _parse_tracks(self, url: str) -> list[Track]:
        """Parse tracks from the given URL."""
        try:
            if not self._session:
                raise MusicServiceError("Failed to initialize session")

            async with self._session.get(url, timeout=ClientTimeout(total=self._config.timeout)) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), "html.parser")
                playlist = soup.find("ul", class_="playlist")

                if not isinstance(playlist, Tag):
                    raise TypeError("Could not find playlist element")

                tracks = [
                    Track.from_element(track_data, index)
                    for index, track_data in enumerate(playlist.find_all("li"))
                ]

            logger.info("Found %d tracks", len(tracks))
            return tracks

        except (aiohttp.ClientError, TimeoutError) as e:
            raise MusicServiceError(f"Failed to search music: {e}") from e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def get_audio_bytes(self, track: Track) -> bytes:
        """Download music file."""
        max_size = 50 * 1024 * 1024  # 50MB

        if not self._session:
            raise MusicServiceError("Failed to initialize session")

        logger.info("Downloading audio for track: %s", track.name)

        try:
            async with self._session.get(track.audio_url, timeout=ClientTimeout(total=self._config.timeout)) as response:
                response.raise_for_status()
                content_length = response.content_length

                if content_length and content_length > max_size:
                    raise MusicServiceError(f"File too large: {content_length} bytes")

                return await response.read()

        except (aiohttp.ClientError, TimeoutError) as e:
            raise MusicServiceError(f"Failed to download audio") from e

    def build_search_query(self, keyword: str) -> str:
        """Build search query with cleaned keyword."""
        cleaned = re.sub(r"[^\w\s]", "", keyword)
        query = cleaned.strip().lower().replace(" ", "-")

        try:
            subdomain = query.encode("idna").decode("ascii")
        except UnicodeError:
            subdomain = query

        return f"https://{subdomain}.{self.BASE_URL}"