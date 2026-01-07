from typing import Optional
from models.location import Location
from models.strategy import MovementStrategy, NoopStrategy
from models.playing_field import PlayingField

class Player:
    def __init__(self, id: str, display_name: str, current_location: Location, field: PlayingField, *, max_moving_speed: float = 1.4, strategy: MovementStrategy | None = None):
        """
        :param id: player identifier
        :param display_name: human-friendly name
        :param current_location: initial `Location` (has lat/lon/timestamp)
        :param field: the `PlayingField` instance this player will be on
        :param max_moving_speed: maximum movement speed in meters/second (defaults to 1.4 m/s)
        :param strategy: an object implementing `MovementStrategy`. If None,
                         `NoopStrategy` is used.
        """
        self._name: str = display_name
        self.id: str = id
        self._locations: list[Location] = [current_location]
        self._field: PlayingField = field
        # movement constraints
        self.max_moving_speed: float = max_moving_speed
        # strategy that decides the next move
        self._strategy: MovementStrategy = strategy or NoopStrategy()
        field.add_player(self.id, current_location)

    @property
    def current_location(self) -> Location:
        return self._locations[-1]

    @property
    def field(self) -> PlayingField:
        return self._field

    @property
    def display_name(self) -> str:
        return self._name

    def update_current_location(self, new_location: Location):
        self._locations.append(new_location)
        self._field.update_current_location(self.id, new_location)

    def move(self) -> bool:
        """
        Ask the strategy for the next movement. The strategy is passed the
        last known `Location`, the `PlayingField`, the player's
        `max_moving_speed` (meters/second), and the `player_id` so it can
        reason about other players' trajectories.

        The strategy must return a `Location` representing the next point
        the player will try to move to (it should respect the max speed
        considering the `timestamp` on the `Location`), or `None` to
        indicate no movement.
        """

        last_location = self.current_location
        moved_to_new_location = self._strategy.next_move(last_location, self._field, self.max_moving_speed, self.id)

        if moved_to_new_location:
            self.update_current_location(moved_to_new_location)
            return True
        return False