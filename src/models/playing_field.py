from typing import Optional
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, LineString

from functions.graph_geometry_functions import GraphGeometryFunctions
from models.location import Location
from models.trajectory import Trajectory

class PlayingField:
    def __init__(self, address: str, radius: int):
        """
        Initialize the playing field with a given address and radius.

        :param address: The address around which to create the playing field.
        :param radius: The radius (in meters) for the playing field.
        """
        self.address: str = address
        self.radius: int = radius
        self.graph: nx.MultiDiGraph = self._create_playing_field()
        self._player_start_locations: dict[str, Location] = {}
        self._player_last_known_locations: dict[str, Location] = {}
        self._player_trajectories: dict[str, Trajectory] = {}
    
    @property
    def player_trajectories(self) -> dict[str, Trajectory]:
        return self._player_trajectories
    
    def _create_playing_field(self) -> nx.MultiDiGraph:
        # Create a graph from the point within the specified radius
        G = ox.graph_from_address(self.address, dist=self.radius, network_type='walk')
        G = ox.project_graph(G)
        return G
    
    def add_player(self, player_id: str, start_location: Location) -> None:

        snapped_point_proj, u, v, key = GraphGeometryFunctions.snap_geo_point_to_proj_point_on_edge(Point(start_location.x, start_location.y), self.graph)
        snapped_point = ox.projection.project_geometry(snapped_point_proj, crs=self.graph.graph['crs'], to_latlong=True)[0]

        self._player_start_locations[player_id] = Location(snapped_point.y, snapped_point.x)
        self._player_last_known_locations[player_id] = Location(snapped_point.y, snapped_point.x)
        self._player_trajectories[player_id] = Trajectory()

    
    def get_player_start_location(self, player_id: str) -> Location | None:
        loc = self._player_start_locations.get(player_id, None)
        if loc:
            return loc
        return None
    
    def get_player_last_known_location(self, player_id: str) -> Location | None:
        loc = self._player_last_known_locations.get(player_id, None)
        if loc:
            return loc
        return None

    def get_player_trajectory(self, player_id: str) -> Optional[Trajectory]:
        return self._player_trajectories.get(player_id, None)

    def update_current_location(self, player_id: str, new_location: Location):
        if player_id not in self._player_trajectories:
            return
        last_known_location = self._get_player_last_known_location(player_id)
        last_known_location_proj, last_known_location_u, last_known_location_v, last_known_location_edge = GraphGeometryFunctions.snap_geo_point_to_proj_point_on_edge(Point(last_known_location.x, last_known_location.y), self.graph)
        
        # # 1. Snap new location to the nearest edge (Default u->v)
        new_location_proj, new_location_u, new_location_v, new_location_edge = GraphGeometryFunctions.snap_geo_point_to_proj_point_on_edge(Point(new_location.x, new_location.y), self.graph)
        trajectory = self.get_player_trajectory(player_id)
        if (last_known_location_u, last_known_location_v) == (new_location_u, new_location_v):
            path_geo: LineString = GraphGeometryFunctions.create_linestring_from_proj_points_within_edge(last_known_location_proj, new_location_proj, self.graph, new_location_u, new_location_v)
            # update trajectory
            trajectory.update(path_geo)

        elif (last_known_location_u, last_known_location_v) != (new_location_u, new_location_v):
            path_geo = GraphGeometryFunctions.create_linestring_from_proj_points_across_nodes(last_known_location_proj, last_known_location_u, last_known_location_v, new_location_proj, new_location_u, new_location_v, self.graph)
            # update trajectory
            trajectory.update(path_geo)
        new_location_snapped = ox.projection.project_geometry(new_location_proj, crs=self.graph.graph['crs'], to_latlong=True)[0]
        self._player_last_known_locations[player_id] = Location(new_location_snapped.y, new_location_snapped.x)

   
    
    

        
    def _get_player_last_known_location(self, player_id: str) -> Location | None:
        trajectory = self._player_trajectories.get(player_id, None)
        if trajectory is None or trajectory.is_empty:
            return self.get_player_start_location(player_id)
        last_loc = trajectory.last_known_point
        return last_loc


    