from typing import Optional
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, LineString
from shapely.ops import substring

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
        start_location_proj: Point = ox.projection.project_geometry(Point(start_location.x, start_location.y), to_crs=self.graph.graph['crs'])[0]
        snapped_point_proj, u, v, key = self._snap_to_edge(start_location_proj)
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
        last_known_location_proj = ox.projection.project_geometry(Point(last_known_location.x, last_known_location.y), to_crs=self.graph.graph['crs'])[0]
        last_known_location_proj, last_known_location_u, last_known_location_v, last_known_location_edge = self._snap_to_edge(last_known_location_proj)
        
        # # 1. Snap new location to the nearest edge (Default u->v)
        new_location_proj = ox.projection.project_geometry(Point(new_location.x, new_location.y), to_crs=self.graph.graph['crs'])[0]
        new_location_proj, new_location_u, new_location_v, new_location_edge = self._snap_to_edge(new_location_proj)

        trajectory = self.get_player_trajectory(player_id)
        if (last_known_location_u, last_known_location_v) == (new_location_u, new_location_v):
            # Same edge, just update the trajectory
            # build LineString from path and make sure to start and end from the exact last and new locations
            coords = []
            coords.append((last_known_location_proj.x, last_known_location_proj.y))

            # get geometry from last_known_location to next node
            edge_data = self.graph.get_edge_data(last_known_location_u, last_known_location_v)
            if 'geometry' in edge_data[0]:
                edge_geom = edge_data[0]['geometry']
                
                start_dist = edge_geom.project(last_known_location_proj)
                end_dist = edge_geom.project(new_location_proj)
                line = substring(edge_geom, start_dist, end_dist)
                if isinstance(line, LineString):
                    coords.extend(line.coords)
                else:
                    pt = line
                    coords.append((pt.x, pt.y))
                

            coords.append((new_location_proj.x, new_location_proj.y))
            path_proj = LineString(coords)
            # convert path_proj back to lat/lon
            path_geo: LineString = ox.projection.project_geometry(path_proj, crs=self.graph.graph['crs'], to_latlong=True)[0]
            # update trajectory
            trajectory.update(path_geo)

        elif (last_known_location_u, last_known_location_v) != (new_location_u, new_location_v):
            start_node = self._get_farthest_node(last_known_location_u, last_known_location_v, new_location_proj)
            end_node = self._get_farthest_node(new_location_u, new_location_v, last_known_location_proj)
            path = ox.shortest_path(self.graph,
                                    start_node,
                                    end_node,
                                    weight='length')
            # build LineString from path and make sure to start and end from the exact last and new locations
            coords = []
            coords.append((last_known_location_proj.x, last_known_location_proj.y))
            for node in path[1:-1]:
                # get geometry from last_known_location to next node
                edge_data = self.graph.get_edge_data(path[path.index(node) - 1], node)
                if 'geometry' in edge_data[0]:
                    edge_geom: LineString = edge_data[0]['geometry']
                    node_point = Point(self.graph.nodes[path[-1]]['x'], self.graph.nodes[path[-1]]['y'])
                    if node == path[1]:  # First edge
                        edge_geom = self._orient_edge_to_node(edge_geom, node_pt=node_point)
                        start_point = last_known_location_proj
                        start_dist = edge_geom.project(start_point)
                        sub_line = substring(edge_geom, start_dist, edge_geom.length)
                        if isinstance(sub_line, LineString):
                            sub_coords = list(sub_line.coords)
                            # avoid duplicating the start point already in coords
                            if coords and sub_coords and coords[-1] == sub_coords[0]:
                                coords.extend(sub_coords[1:])
                            else:
                                coords.extend(sub_coords)
                        else:
                            # substring may return a Point if start==end
                            pt = sub_line
                            pt_coord = (pt.x, pt.y)
                            if not (coords and coords[-1] == pt_coord):
                                coords.append(pt_coord)

                    elif node == path[-2]:  # Last edge
                        edge_geom = self._orient_edge_away_from_node(edge_geom, node_pt=node_point)
                        end_point = new_location_proj
                        end_dist = edge_geom.project(end_point)
                        sub_line = substring(edge_geom, 0, end_dist)
                        if isinstance(sub_line, LineString):
                            sub_coords = list(sub_line.coords)
                            # avoid duplicating the start point already in coords
                            if coords and sub_coords and coords[-1] == sub_coords[0]:
                                coords.extend(sub_coords[1:])
                            else:
                                coords.extend(sub_coords)
                        else:
                            # substring may return a Point if start==end
                            pt = sub_line
                            pt_coord = (pt.x, pt.y)
                            if not (coords and coords[-1] == pt_coord):
                                coords.append(pt_coord)
                    else:  # Middle edges
                        coords.extend(edge_geom.coords)
                else:
                    node_data = self.graph.nodes[node]
                    coords.append((node_data['x'].item(), node_data['y'].item()))
            if not (coords and coords[-1] == (new_location_proj.x, new_location_proj.y)):
                coords.append((new_location_proj.x, new_location_proj.y))
            path_proj = LineString(coords)
            # convert path_proj back to lat/lon
            path_geo: LineString = ox.projection.project_geometry(path_proj, crs=self.graph.graph['crs'], to_latlong=True)[0]
            # update trajectory
            trajectory.update(path_geo)
        new_location_snapped = ox.projection.project_geometry(new_location_proj, crs=self.graph.graph['crs'], to_latlong=True)[0]
        self._player_last_known_locations[player_id] = Location(new_location_snapped.y, new_location_snapped.x)

    def _orient_edge_to_node(self, edge_geom: LineString, node_pt: Point, tol=1e-9) -> LineString:
        # If node is already at the first coordinate, return as-is.
        if Point(edge_geom.coords[0]).distance(node_pt) <= tol:
            return edge_geom
        # If node is at the last coordinate, reverse the coordinates so node becomes start.
        if Point(edge_geom.coords[-1]).distance(node_pt) <= tol:
            return LineString(list(edge_geom.coords)[::-1])
        # Otherwise the node is not exactly on endpoints — you may want to snap first.
        return edge_geom
    
    def _orient_edge_away_from_node(self, edge_geom: LineString, node_pt: Point, tol=1e-9) -> LineString:
        # If node is already at the first coordinate, return as-is.
        if Point(edge_geom.coords[0]).distance(node_pt) <= tol:
            return LineString(list(edge_geom.coords)[::-1])
        # If node is at the last coordinate, reverse the coordinates so node becomes start.
        if Point(edge_geom.coords[-1]).distance(node_pt) <= tol:
            return edge_geom
        # Otherwise the node is not exactly on endpoints — you may want to snap first.
        return edge_geom
    
    def _get_farthest_node(self, u: int, v: int, point_proj: Point) -> int:
        """
        Given an edge (u, v) and a point, return the node (u or v) that is farthest from the point.
        """
        u_node = self.graph.nodes[u]
        v_node = self.graph.nodes[v]
        u_point = Point(u_node['x'], u_node['y'])
        v_point = Point(v_node['x'], v_node['y'])
        
        dist_to_u = point_proj.distance(u_point)
        dist_to_v = point_proj.distance(v_point)
        
        if dist_to_u > dist_to_v:
            return u
        else:
            return v
        
    def _get_player_last_known_location(self, player_id: str) -> Location | None:
        trajectory = self._player_trajectories.get(player_id, None)
        if trajectory is None or trajectory.is_empty:
            return self.get_player_start_location(player_id)
        last_loc = trajectory.last_known_point
        return last_loc


    def _snap_to_edge(self, point_proj: Point) -> tuple[Point, int, int, int]:
        """
        Finds the nearest edge and returns the geometry data.
        Returns: (snapped_lat, snapped_lon, u, v, key)
        """

        # 2. Find nearest edge
        u, v, key = ox.nearest_edges(self.graph, point_proj.x, point_proj.y)
        
        # 3. Get Edge Geometry
        edge_data = self.graph.get_edge_data(u, v, key)
        if 'geometry' in edge_data:
            edge_geom: LineString = edge_data['geometry']
        else:
            # Construct straight line if no geometry exists
            u_node = self.graph.nodes[u]
            v_node = self.graph.nodes[v]
            edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])

        # 4. Snap point to this line
        dist_along_edge = edge_geom.project(point_proj)
        snapped_point_proj = edge_geom.interpolate(dist_along_edge)
        
        return snapped_point_proj, u, v, key