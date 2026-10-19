from aiogram import Dispatcher, Router

from app.handlers import admin, navigation, payments, quizzes, tutor
from app.middlewares.transaction import TransactionMiddleware

ALLOWED_UPDATES = ["message", "callback_query", "pre_checkout_query"]


def create_dispatcher(runtime):
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.update.outer_middleware(TransactionMiddleware(runtime))
    # Specific commands and financial updates take precedence over general text.
    for module in (admin, payments, quizzes, tutor, navigation):
        # Fresh router instances permit multiple application/test lifecycles in
        # one interpreter without mutating module-level router parent pointers.
        source = module.router
        router = Router(name=source.name)
        for name, observer in source.observers.items():
            router.observers[name].handlers = observer.handlers.copy()
        dispatcher.include_router(router)
    return dispatcher
