"""Small read-only PTT2 client helpers built on top of PyPtt."""

from __future__ import annotations

import time

import PyPtt
from PyPtt import command, connect_core, data_type, exceptions, screens


class GuestCapacityError(RuntimeError):
    """PTT2 has temporarily exhausted its anonymous guest slots."""


def make_bot() -> PyPtt.API:
    return PyPtt.API(
        host=PyPtt.HOST.PTT2,
        log_level=PyPtt.LogLevel.INFO,
        screen_timeout=5.0,
        screen_long_timeout=20.0,
        screen_height=100,
    )


def _finish_login_state(bot: PyPtt.API, screen: str, *, registered: bool) -> None:
    if not all(target in screen for target in screens.Target.MainMenu):
        raise exceptions.LoginError()

    if "> (" in screen:
        bot.cursor = data_type.Cursor.NEW
    elif "●(" in screen:
        bot.cursor = data_type.Cursor.OLD
    else:
        raise exceptions.UnknownError()

    screens.Target.InBoardWithCursor = screens.Target.InBoardWithCursor[
        : screens.Target.InBoardWithCursorLen
    ]
    screens.Target.InBoardWithCursor.append(bot.cursor)
    screens.Target.InMailBoxWithCursor = screens.Target.InMailBoxWithCursor[
        : screens.Target.InMailBoxWithCursorLen
    ]
    screens.Target.InMailBoxWithCursor.append(bot.cursor)

    bot.is_registered_user = registered
    bot._is_login = True


def login_guest(bot: PyPtt.API) -> None:
    """Enter PTT2's built-in, read-only guest session.

    PyPtt's registered-account login submits ``account,password``. PTT2's
    guest account instead enters directly after the account name, so it needs
    this small protocol adapter.
    """
    bot.connect_core.connect()
    bot.ptt_id = "guest"
    bot._ptt_pw = ""

    targets = [
        connect_core.TargetUnit(screens.Target.MainMenu, break_detect=True),
        connect_core.TargetUnit(
            "太多 guest",
            break_detect=True,
            exceptions_=GuestCapacityError("PTT2 guest capacity is full"),
        ),
        connect_core.TargetUnit("【看板列表】", response=command.go_main_menu),
        connect_core.TargetUnit("登入太頻繁", response=" "),
        connect_core.TargetUnit("系統過載", break_detect=True),
        connect_core.TargetUnit("任意鍵", response=" "),
        connect_core.TargetUnit("【分類看板】", response=command.go_main_menu),
        connect_core.TargetUnit("熱門話題", response=command.go_main_menu),
    ]
    bot.connect_core.send(
        "guest" + command.enter,
        targets,
        screen_timeout=bot.config.screen_long_timeout,
        refresh=False,
        secret=True,
    )

    queue = bot.connect_core.get_screen_queue()
    screen = queue[-1] if queue else ""
    _finish_login_state(bot, screen, registered=False)


def login_with_retry(
    ptt_id: str,
    password: str,
    *,
    guest_attempts: int = 4,
    guest_retry_seconds: int = 20,
) -> PyPtt.API:
    """Create and log in a bot, retrying only transient guest-capacity errors."""
    is_guest = ptt_id.strip().lower() == "guest"
    attempts = max(1, guest_attempts if is_guest else 1)

    for attempt in range(1, attempts + 1):
        bot = make_bot()
        try:
            if is_guest:
                login_guest(bot)
            else:
                bot.login(
                    ptt_id=ptt_id,
                    ptt_pw=password,
                    kick_other_session=False,
                )
            return bot
        except GuestCapacityError as exc:
            try:
                bot.connect_core.close()
            except Exception:
                pass
            if attempt == attempts:
                raise GuestCapacityError(
                    "PTT2 guest capacity remained full after "
                    f"{attempts} attempts. Add PTT2_ID and PTT2_PASSWORD as "
                    "GitHub Actions secrets, or retry later."
                ) from exc
            time.sleep(guest_retry_seconds * attempt)
        except Exception:
            try:
                bot.connect_core.close()
            except Exception:
                pass
            raise

    raise AssertionError("unreachable")
