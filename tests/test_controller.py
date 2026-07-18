from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from boxhead_bot.controller import InputController, MoveDirection


@pytest.fixture
def mock_page(mocker: MockerFixture) -> Mock:
    page = mocker.Mock()
    return page


# Move tests


def test_construction_does_not_press_any_keys(mock_page):
    _ = InputController(mock_page)
    mock_page.keyboard.down.assert_not_called()
    mock_page.keyboard.up.assert_not_called()


def test_move_single_direction(mock_page):
    controller = InputController(mock_page)
    controller.move(MoveDirection.UP)
    mock_page.keyboard.up.assert_not_called()
    mock_page.keyboard.down.assert_called_once_with("ArrowUp")


def test_move_diagonal_direction(mock_page):
    controller = InputController(mock_page)
    controller.move(MoveDirection.UP_RIGHT)
    mock_page.keyboard.up.assert_not_called()
    mock_page.keyboard.down.assert_any_call("ArrowUp")
    mock_page.keyboard.down.assert_any_call("ArrowRight")
    assert mock_page.keyboard.down.call_count == 2


def test_move_same_direction_twice_is_idempotent(mock_page):
    controller = InputController(mock_page)
    controller.move(MoveDirection.UP)
    mock_page.keyboard.reset_mock()
    controller.move(MoveDirection.UP)
    mock_page.keyboard.up.assert_not_called()
    mock_page.keyboard.down.assert_not_called()


def test_move_different_direction_swaps_keys(mock_page):
    controller = InputController(mock_page)
    controller.move(MoveDirection.UP)
    mock_page.keyboard.reset_mock()
    controller.move(MoveDirection.DOWN)
    mock_page.keyboard.up.assert_called_once_with("ArrowUp")
    mock_page.keyboard.down.assert_called_once_with("ArrowDown")


def test_move_diagonal_direction_with_shared_key(mock_page):
    controller = InputController(mock_page)
    controller.move(MoveDirection.UP_RIGHT)
    mock_page.keyboard.reset_mock()
    controller.move(MoveDirection.UP_LEFT)
    mock_page.keyboard.up.assert_called_once_with("ArrowRight")
    mock_page.keyboard.down.assert_called_once_with("ArrowLeft")


def test_move_to_still_releases_all_held_keys(mock_page):
    controller = InputController(mock_page)
    controller.move(MoveDirection.UP_RIGHT)
    mock_page.keyboard.reset_mock()
    controller.move(MoveDirection.STILL)
    mock_page.keyboard.up.assert_any_call("ArrowUp")
    mock_page.keyboard.up.assert_any_call("ArrowRight")
    assert mock_page.keyboard.up.call_count == 2
    mock_page.keyboard.down.assert_not_called()


# Shoot tests


def test_shoot_true_presses_space_key(mock_page):
    controller = InputController(mock_page)
    controller.shoot(True)
    mock_page.keyboard.up.assert_not_called()
    mock_page.keyboard.down.assert_called_once_with("Space")


def test_shoot_true_twice_is_idempotent(mock_page):
    controller = InputController(mock_page)
    controller.shoot(True)
    mock_page.keyboard.reset_mock()
    controller.shoot(True)
    mock_page.keyboard.up.assert_not_called()
    mock_page.keyboard.down.assert_not_called()


def test_shoot_false_after_true_releases_space_key(mock_page):
    controller = InputController(mock_page)
    controller.shoot(True)
    mock_page.keyboard.reset_mock()
    controller.shoot(False)
    mock_page.keyboard.up.assert_called_once_with("Space")


def test_shoot_false_when_nothing_held_does_nothing(mock_page):
    controller = InputController(mock_page)
    controller.shoot(False)
    mock_page.keyboard.down.assert_not_called()
    mock_page.keyboard.up.assert_not_called()


# Weapons change tests


def test_next_weapon_presses_dot_key(mock_page):
    controller = InputController(mock_page)
    controller.next_weapon()
    mock_page.keyboard.press.assert_called_once_with(".")


def test_prev_weapon_presses_comma_key(mock_page):
    controller = InputController(mock_page)
    controller.prev_weapon()
    mock_page.keyboard.press.assert_called_once_with(",")


@pytest.mark.parametrize("weapon_number", range(10))
def test_select_weapon_presses_number_key(mock_page, weapon_number):
    controller = InputController(mock_page)
    controller.select_weapon(weapon_number)
    mock_page.keyboard.press.assert_called_once_with(str(weapon_number))


# Pause tests


def test_pause_presses_p_key(mock_page):
    controller = InputController(mock_page)
    controller.pause()
    mock_page.keyboard.press.assert_called_once_with("p")
