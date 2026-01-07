from __future__ import annotations
from typing import Protocol, Optional
from datetime import datetime, timezone

import osmnx as ox
import networkx as nx
from shapely.geometry import LineString, Point

from models.location import Location
from models.playing_field import PlayingField


class MovementStrategy(Protocol):
    def next_move(self, last_location: Location, field: PlayingField, max_moving_speed: float, player_id: str, current_time: datetime = None) -> Optional[Location]:
        pass


class NoopStrategy(MovementStrategy):
    def next_move(self, last_location: Location, field: PlayingField, max_moving_speed: float, player_id: str, current_time: datetime = None) -> Optional[Location]:
        return last_location


class CloseLoopStrategy(MovementStrategy):
    """
    Attempts to close the loop back to the player's start location while
    avoiding intersections with any existing trajectories. It respects the
    `max_moving_speed` by returning a point no further than allowed by the
    time delta from `last_location.timestamp`.
    """

    def __init__(self, min_loop_length: float = 50.0):
        self.min_loop_length = min_loop_length
        self.visited_nodes = set()

    def next_move(self, last_known_location: Location, field: PlayingField, max_moving_speed: float, player_id: str, current_time: datetime = None) -> Optional[Location]:
        now = current_time or datetime.now(timezone.utc)
        elapsed_seconds = (now - last_known_location.timestamp).total_seconds()
        max_distance_meter = max(0.0, max_moving_speed * elapsed_seconds)
        
        
        
        last_known_point_proj = ox.projection.project_geometry(Point(last_known_location.x, last_known_location.y), to_crs=field.graph.graph['crs'])[0]
        snapped_point_proj, u, v, key = self._snap_to_edge(field.graph, last_known_point_proj)
        trajectory = field.get_player_trajectory(player_id)
        new_location: Optional[Location] = None

        closest_node = self._get_closest_node(field.graph, u, v, snapped_point_proj)
        dist_to_closest_node = self._get_dist_to_closest_node_along_the_edge(field, snapped_point_proj, u, v, key, closest_node)
        if dist_to_closest_node > max_distance_meter:
            # Move towards the closest node but only up to max_distance_meter following the edge
            edge_data = field.graph.get_edge_data(u, v, key)
            if 'geometry' in edge_data:
                edge_geom: LineString = edge_data['geometry']
            else:
                u_node = field.graph.nodes[u]
                v_node = field.graph.nodes[v]
                edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])
            # get distance along edge to snapped point in the direction towards closest node
            
            if closest_node == u:
                target_dist = dist_to_closest_node - max_distance_meter
                if target_dist < 0:
                    target_dist = 0.0
            else:
                target_dist = (edge_geom.length - dist_to_closest_node) + max_distance_meter
                if target_dist > edge_geom.length:
                    target_dist = edge_geom.length
            new_point_proj = edge_geom.interpolate(target_dist)
            new_point_geo: Point = ox.projection.project_geometry(new_point_proj, crs=field.graph.graph['crs'], to_latlong=True)[0]
            new_location = Location(x=new_point_geo.x, y=new_point_geo.y)
        else:
            # Can reach the closest node; move there and calculate remaining distance until max_distance_meter is used up
            node_data = field.graph.nodes[closest_node]
            self.visited_nodes.add(closest_node)
            closest_node_point_geo: Point = ox.projection.project_geometry(Point(node_data['x'], node_data['y']), crs=field.graph.graph['crs'], to_latlong=True)[0]
            new_location = Location(x=closest_node_point_geo.x, y=closest_node_point_geo.y)
            remaining_distance = max_distance_meter - dist_to_closest_node
            trajectory_length: float = 0.0
            if trajectory and not trajectory.is_empty:
                for i in range(len(trajectory.geometry.coords)-1) if len(trajectory.geometry.coords) > 1 else 0:
                    p1: Point = ox.projection.project_geometry(Point(trajectory.geometry.coords.xy[0][i], trajectory.geometry.coords.xy[1][i]), to_crs=field.graph.graph['crs'])[0]
                    p2: Point = ox.projection.project_geometry(Point(trajectory.geometry.coords.xy[0][i+1], trajectory.geometry.coords.xy[1][i+1]), to_crs=field.graph.graph['crs'])[0]
                    trajectory_length += p1.distance(p2)

            # Continue moving along network while there is remaining distance and min_loop_length not achieved
            while remaining_distance > 0 and trajectory_length < self.min_loop_length:
                neighbors = list(field.graph.successors(closest_node))
                if not neighbors:
                    break  # No further nodes to move to

                # Find the next edge that does not intersect the trajectory and is not already visited
                next_node = None
                for neighbor in neighbors:
                    edge_data = field.graph.get_edge_data(closest_node, neighbor)
                    if not edge_data:
                        continue
                    if 'geometry' in edge_data:
                        edge_geom = edge_data['geometry']
                    else:
                        u_node = field.graph.nodes[closest_node]
                        v_node = field.graph.nodes[neighbor]
                        edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])
                    # Check if the edge intersects the trajectory
                    if trajectory and not trajectory.is_empty:
                        trajectory_geometry_proj: LineString = ox.projection.project_geometry(trajectory.geometry, to_crs=field.graph.graph['crs'])[0]
                        if trajectory_geometry_proj.intersects(edge_geom):
                            continue  # Skip this edge due to intersection
                    if neighbor in self.visited_nodes:
                        continue

                    next_node = neighbor
                    break

                if not next_node:
                    break  # No valid next node found

                edge_data = field.graph.get_edge_data(closest_node, next_node)
                if 'geometry' in edge_data:
                    edge_geom = edge_data['geometry']
                else:
                    u_node = field.graph.nodes[closest_node]
                    v_node = field.graph.nodes[next_node]
                    edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])

                if edge_geom.length <= remaining_distance:
                    # Move to the end of the edge
                    node_data = field.graph.nodes[next_node]
                    node_point_geo: Point = ox.projection.project_geometry(Point(node_data['x'], node_data['y']), crs=field.graph.graph['crs'], to_latlong=True)[0]
                    new_location = Location(
                    x=node_point_geo.x,
                    y=node_point_geo.y
                    )
                    remaining_distance -= edge_geom.length
                    trajectory_length += edge_geom.length
                    closest_node = next_node
                    self.visited_nodes.add(closest_node)
                    dist_to_closest_node = 0
                else:
                    # Move partway along the edge
                    edge_geom: LineString = self._orient_edge_to_node(edge_geom, Point(v_node['x'], v_node['y']))
                    new_point_proj = edge_geom.interpolate(remaining_distance)
                    new_point_geo: Point = ox.projection.project_geometry(new_point_proj, crs=field.graph.graph['crs'], to_latlong=True)[0]
                    new_location = Location(
                    x=new_point_geo.x,
                    y=new_point_geo.y
                    )
                    remaining_distance = 0
            
            # If min_loop_length achieved, try to close the loop back to start
            if trajectory_length >= self.min_loop_length:
                start_proj: Point
                start_location = trajectory.start_point if trajectory and not trajectory.is_empty else None
                if start_location is None:
                    start_proj = snapped_point_proj
                else:
                    start_proj = ox.projection.project_geometry(Point(start_location.x, start_location.y), to_crs=field.graph.graph['crs'])[0]
                u, v, key = ox.nearest_edges(field.graph, start_proj.x, start_proj.y)
                
                end_node: int
                if trajectory and not trajectory.is_empty:
                    trajectory_geometry_proj: LineString = ox.projection.project_geometry(trajectory.geometry, to_crs=field.graph.graph['crs'])[0]
                    end_node = v if (trajectory_geometry_proj.buffer(10).intersects(Point(field.graph.nodes[u]['x'], field.graph.nodes[u]['y']))) or u in self.visited_nodes else u
                else:
                    end_node = v if u in self.visited_nodes else u

                 # Find shortest path from current closest_node to start location's closest node
                 # and move along it using remaining_distance
                
                try:
                    path = nx.shortest_path(field.graph, closest_node, end_node, weight='length')
                    # Move along path towards start
                    for i in range(len(path) - 1):
                        edge_data = field.graph.get_edge_data(path[i], path[i+1])
                        if 'geometry' in edge_data:
                            edge_geom = edge_data['geometry']
                        else:
                            u_node = field.graph.nodes[path[i]]
                            v_node = field.graph.nodes[path[i+1]]
                            edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])
                        
                        if edge_geom.length <= remaining_distance:
                            remaining_distance -= edge_geom.length
                        else:
                            new_point_proj = edge_geom.interpolate(remaining_distance)
                            new_point_geo: Point = ox.projection.project_geometry(new_point_proj, crs=field.graph.graph['crs'], to_latlong=True)[0]
                            new_location = Location(x=new_point_geo.x, y=new_point_geo.y)
                            break
                except nx.NetworkXNoPath:
                    pass
                
        new_location.timestamp = now
        return new_location
    
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

    def _get_dist_to_closest_node_along_the_edge(self, field, snapped_point_proj, u, v, key, closest_node):
        edge_data = field.graph.get_edge_data(u, v, key)
        if edge_data and 'geometry' in edge_data:
            edge_geom: LineString = edge_data['geometry']
        else:
            u_node = field.graph.nodes[u]
            v_node = field.graph.nodes[v]
            edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])

        # distance along edge from its start to the snapped point
        dist_along_edge = edge_geom.project(snapped_point_proj)
        # distance along the edge from snapped point to the closest node
        if closest_node == u:
            dist_to_closest_node = dist_along_edge
        else:
            dist_to_closest_node = edge_geom.length - dist_along_edge
        return dist_to_closest_node
    
    def _get_closest_node(self, graph: nx.MultiDiGraph, u: int, v: int, point_proj: Point) -> int:
        """
        Given an edge (u, v) and a point, return the node (u or v) that is farthest from the point.
        """
        u_node = graph.nodes[u]
        v_node = graph.nodes[v]
        u_point = Point(u_node['x'], u_node['y'])
        v_point = Point(v_node['x'], v_node['y'])
        
        dist_to_u = point_proj.distance(u_point)
        dist_to_v = point_proj.distance(v_point)
        
        if dist_to_u > dist_to_v:
            return v
        else:
            return u
    
    def _snap_to_edge(self, graph: nx.MultiDiGraph, point_proj: Point) -> tuple[Point, int, int, int]:
        """
        Finds the nearest edge and returns the geometry data.
        Returns: (snapped_lat, snapped_lon, u, v, key)
        """

        # 2. Find nearest edge
        u, v, key = ox.nearest_edges(graph, point_proj.x, point_proj.y)
        
        # 3. Get Edge Geometry
        edge_data = graph.get_edge_data(u, v, key)
        if 'geometry' in edge_data:
            edge_geom: LineString = edge_data['geometry']
        else:
            # Construct straight line if no geometry exists
            u_node = graph.nodes[u]
            v_node = graph.nodes[v]
            edge_geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])

        # 4. Snap point to this line
        dist_along_edge = edge_geom.project(point_proj)
        snapped_point_proj = edge_geom.interpolate(dist_along_edge)
        
        return snapped_point_proj, u, v, key
    