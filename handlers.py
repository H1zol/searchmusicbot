"""All bot handlers with real music search."""

import logging
from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile

from music_service import Music, Track
from keyboards import get_main_menu, get_search_results_keyboard

logger = logging.getLogger(__name__)

# Временное хранилище (в реальном боте используйте БД)
search_history = {}

def setup_handlers(router: Router) -> None:
    """Set up all handlers."""
    
    @router.message(CommandStart())
    @router.message(Command("menu"))
    async def menu_handler(message: types.Message):
        await message.answer("🎵 Музыкальный бот - главное меню", reply_markup=get_main_menu())

    @router.message(F.text == "🔍 Поиск")
    async def search_prompt_handler(message: types.Message):
        await message.answer("Введите название песни или исполнителя:")

    @router.message(F.text == "🎵 Топ хиты")
    async def top_hits_handler(message: types.Message):
        try:
            async with Music() as music:
                tracks = await music.get_top_hits()
            
            if not tracks:
                await message.answer("❌ Не удалось загрузить топ хиты")
                return
            
            # Сохраняем в историю
            search_id = len(search_history)
            search_history[search_id] = tracks
            
            await message.answer(
                "🔥 Топ хиты:",
                reply_markup=get_search_results_keyboard(tracks, search_id)
            )
            
        except Exception as e:
            logger.error(f"Error getting top hits: {e}")
            await message.answer("❌ Ошибка при загрузке топ хитов")

    @router.message()
    async def search_handler(message: types.Message):
        if not message.text:
            return
            
        query = message.text.strip()
        if len(query) < 2:
            await message.answer("❌ Слишком короткий запрос")
            return

        try:
            await message.answer(f"🔍 Ищу: {query}...")
            
            async with Music() as music:
                tracks = await music.search(query)
            
            if not tracks:
                await message.answer("❌ Ничего не найдено")
                return
            
            # Сохраняем в историю
            search_id = len(search_history)
            search_history[search_id] = tracks
            
            await message.answer(
                f"🎵 Найдено {len(tracks)} треков по запросу: {query}",
                reply_markup=get_search_results_keyboard(tracks, search_id)
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            await message.answer("❌ Ошибка при поиске")

    @router.callback_query(F.data.startswith("track:"))
    async def track_callback_handler(callback: types.CallbackQuery):
        try:
            data = callback.data.split(":")
            action = data[1]
            search_id = int(data[2])
            
            if search_id not in search_history:
                await callback.answer("❌ Результаты поиска устарели")
                return
            
            tracks = search_history[search_id]
            
            if action == "get":
                track_index = int(data[3])
                track = tracks[track_index]
                
                await callback.answer("⬇️ Скачиваю...")
                await send_track(callback, track)
                
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await callback.answer("❌ Ошибка")

async def send_track(callback: types.CallbackQuery, track: Track):
    """Send track to user."""
    try:
        async with Music() as music:
            audio_bytes = await music.get_audio_bytes(track)
        
        audio_file = BufferedInputFile(audio_bytes, filename=f"{track.name}.mp3")
        
        await callback.message.answer_audio(
            audio_file,
            title=track.title[:64],  # Ограничение Telegram
            performer=track.performer[:64],
            caption=f"🎵 {track.name}"
        )
        
    except Exception as e:
        logger.error(f"Error sending track: {e}")
        await callback.message.answer("❌ Ошибка при загрузке трека")