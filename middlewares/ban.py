from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from database.db import is_user_banned

class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Creator is completely immune to bans
        if user.id == 1368643174:
            return await handler(event, data)

        # Check if user is banned
        if await is_user_banned(user_id=user.id, username=user.username):
            if isinstance(event, Message):
                await event.answer(
                    "🚫 <b>Доступ заблокирован</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "Ваш аккаунт внесён в чёрный список бара Marie Laveau.\n\n"
                    "Доступ к учебным материалам, тренажёру и функциям бота ограничен администрацией.",
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "🚫 Доступ заблокирован администратором.",
                    show_alert=True
                )
            return

        return await handler(event, data)
