import enum

from playwright.sync_api import Page


class MoveDirection(enum.Enum):
    UP = enum.auto()
    DOWN = enum.auto()
    RIGHT = enum.auto()
    LEFT = enum.auto()
    UP_RIGHT = enum.auto()
    UP_LEFT = enum.auto()
    DOWN_RIGHT = enum.auto()
    DOWN_LEFT = enum.auto()
    STILL = enum.auto()


class InputController:
    _DIRECTION_KEYS: dict[MoveDirection, frozenset[str]] = {
        MoveDirection.UP: frozenset({"ArrowUp"}),
        MoveDirection.DOWN: frozenset({"ArrowDown"}),
        MoveDirection.RIGHT: frozenset({"ArrowRight"}),
        MoveDirection.LEFT: frozenset({"ArrowLeft"}),
        MoveDirection.UP_RIGHT: frozenset({"ArrowUp", "ArrowRight"}),
        MoveDirection.UP_LEFT: frozenset({"ArrowUp", "ArrowLeft"}),
        MoveDirection.DOWN_RIGHT: frozenset({"ArrowDown", "ArrowRight"}),
        MoveDirection.DOWN_LEFT: frozenset({"ArrowDown", "ArrowLeft"}),
        MoveDirection.STILL: frozenset(),
    }

    def __init__(self, page: Page):
        self._page = page
        self._current_keys: frozenset[str] = frozenset()

    def move(self, direction: MoveDirection) -> None:
        target = self._DIRECTION_KEYS[direction]
        to_release = self._current_keys - target
        to_press = target - self._current_keys
        for key in to_release:
            self._page.keyboard.up(key)
        for key in to_press:
            self._page.keyboard.down(key)
        self._current_keys = target
