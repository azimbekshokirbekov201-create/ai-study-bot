from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.localization import MAIN_ITEMS, tr


def main_menu(language: str) -> ReplyKeyboardMarkup:
    buttons = [KeyboardButton(text=tr(key, language)) for key in MAIN_ITEMS]
    return ReplyKeyboardMarkup(
        keyboard=[buttons[i : i + 2] for i in range(0, len(buttons), 2)],
        resize_keyboard=True,
        input_field_placeholder="AI Study Bot",
    )


def inline_menu(
    items: list[tuple[str, str]], language: str, back: str | None = "home", columns: int = 1
):
    buttons = [InlineKeyboardButton(text=label, callback_data=data) for label, data in items]
    rows = [buttons[i : i + columns] for i in range(0, len(buttons), columns)]
    if back:
        nav = []
        if back != "home":
            nav.append(InlineKeyboardButton(text=tr("back", language), callback_data=f"nav:{back}"))
        nav.append(InlineKeyboardButton(text=tr("home", language), callback_data="nav:home"))
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def choices(keys: list[str], language: str, prefix: str, back: str = "home", columns: int = 1):
    return inline_menu(
        [(tr(key, language), f"nav:{prefix}{key}") for key in keys], language, back, columns
    )
