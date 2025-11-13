"""Keyboards for music bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    """Get main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="🎵 Топ хиты")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True
    )

def get_search_results_keyboard(tracks: list, search_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for search results."""
    buttons = []
    
    # Показываем первые 10 треков
    for i, track in enumerate(tracks[:10]):
        buttons.append([
            InlineKeyboardButton(
                text=f"{i+1}. {track.performer} - {track.title}",
                callback_data=f"track:get:{search_id}:{i}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)