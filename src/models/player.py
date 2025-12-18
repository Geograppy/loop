from models.playing_field import PlayingField


class Player:
    def __init__(self, id: str, name: str, current_location: tuple[float, float], field: PlayingField):
        self.name = name
        self.id = id
        self.current_location = current_location
        self.field = field