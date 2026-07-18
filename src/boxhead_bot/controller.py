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

    def __init__(self, page: Page) -> None:
        self._page = page
        self._current_direction_keys: frozenset[str] = frozenset()
        self._shooting: bool = False

    def move(self, direction: MoveDirection) -> None:
        target_direction_keys = self._DIRECTION_KEYS[direction]
        to_release = self._current_direction_keys - target_direction_keys
        to_press = target_direction_keys - self._current_direction_keys
        for key in to_release:
            self._page.keyboard.up(key)
        for key in to_press:
            self._page.keyboard.down(key)
        self._current_direction_keys = target_direction_keys

    def shoot(self, fire: bool) -> None:
        if fire == self._shooting:
            return
        if fire:
            self._page.keyboard.down("Space")
        else:
            self._page.keyboard.up("Space")
        self._shooting = fire

    def next_weapon(self) -> None:
        self._page.keyboard.press(".")

    def prev_weapon(self) -> None:
        self._page.keyboard.press(",")

    def select_weapon(self, weapon_number: int) -> None:
        self._page.keyboard.press(str(weapon_number))

    def pause(self) -> None:
        self._page.keyboard.press("p")

    def reset(self) -> None:
        self.move(MoveDirection.STILL)
        self.shoot(False)
