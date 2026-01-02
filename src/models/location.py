from datetime import datetime, timezone
import osmnx as ox

class Location:
    def __init__(self, y: float, x: float):
        self.y: float = y
        self.x: float = x
        self.timestamp: datetime = datetime.now(timezone.utc)
        
    def from_address(address: str) -> 'Location':
        pos = ox.geocode(address)
        return Location(pos[0], pos[1])

    def __eq__(self, other):
        if not isinstance(other, Location):
            return NotImplemented
        
        return self.y == other.y and self.x == other.x

    def __hash__(self):
        return hash((self.y, self.x))