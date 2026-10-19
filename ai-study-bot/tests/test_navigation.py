from aiogram.types import ReplyKeyboardMarkup

from app.keyboards import choices, main_menu
from app.localization import MAIN_ITEMS, menu_key, tr


def test_every_main_menu_button_round_trips_in_both_languages():
    for lang in ("uz", "en"):
        keyboard = main_menu(lang)
        assert isinstance(keyboard, ReplyKeyboardMarkup)
        assert len(keyboard.keyboard) == 5
        assert {menu_key(button.text) for row in keyboard.keyboard for button in row} == set(
            MAIN_ITEMS
        )


def test_inline_navigation_and_callback_size():
    keyboard = choices(["listening", "reading", "grammar"], "uz", "learn:cefr:B2:", "cefr")
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert buttons[-1].callback_data == "nav:home"
    assert buttons[-2].callback_data == "nav:cefr"
    assert all(len(button.callback_data.encode()) <= 64 for button in buttons)
    assert tr("back", "en") == "⬅️ Back"
