from typing import Optional
from shapely import LineString, Point


class Trajectory:
    """Class representing a player's trajectory as a LineString of Points."""
    
    def __init__(self, geometry: LineString = None):
        self.geometry: LineString = geometry
        
    def update(self, sub_trajectory: LineString):
        if self.geometry is None:
            self.geometry = sub_trajectory
        elif self.geometry.coords[-1] == sub_trajectory.coords[0]:
            coords = list(self.geometry.coords) + list(sub_trajectory.coords)[1:]
            self.geometry = LineString(coords)
        else:
            coords = list(self.geometry.coords) + list(sub_trajectory.coords)
            self.geometry = LineString(coords)
        
    @property
    def start_point(self) -> Optional[Point]:
        if self.geometry is None:
            return None
        return Point(*self.geometry.coords[0])
    
    @property
    def last_known_point(self) -> Optional[Point]:
        if self.geometry is None:
            return None
        return Point(*self.geometry.coords[-1])

    @property
    def is_empty(self) -> bool:
        return self.geometry is None or len(self.geometry.coords) == 0