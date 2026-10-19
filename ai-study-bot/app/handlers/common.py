from aiogram.types import Message


async def send_text(message: Message, text: str, reply_markup=None):
    """Telegram messages are bounded; all text is sent without HTML/Markdown parsing."""
    for start in range(0, max(1, len(text)), 3900):
        await message.answer(
            text[start : start + 3900],
            reply_markup=reply_markup if start + 3900 >= len(text) else None,
            parse_mode=None,
        )
