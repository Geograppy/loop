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

    def __init__(self, intersection_tolerance: float = 1e-6):
        self.intersection_tolerance = intersection_tolerance

    def next_move(self, last_known_location: Location, field: PlayingField, max_moving_speed: float, player_id: str, current_time: datetime = None) -> Optional[Location]:
        now = current_time or datetime.now(timezone.utc)
        elapsed_seconds = (now - last_known_location.timestamp).total_seconds()
        max_distance_m_per_sec = max(0.0, max_moving_speed * elapsed_seconds)
        
        
        
        if not new_location:
            return None
        
        return new_location

    def next_move_ai_generated(self, last_location: Location, field: PlayingField, max_moving_speed: float, player_id: str, current_time: datetime = None) -> Optional[Location]:
        # time-limited movement
        now = current_time or datetime.now(timezone.utc)
        elapsed = (now - last_location.timestamp).total_seconds()
        max_distance = max(0.0, max_moving_speed * elapsed)

        G = field.graph

        # Try to obtain the player's stored trajectory. Tests may replace
        # `player_trajectories` with a Mock, so fall back to the public
        # getter if direct dict access fails.
        
        try:
            traj = field.get_player_trajectory(player_id)
        except Exception:
            traj = []

        if not traj:
            return None

        start_loc = traj[0]

        # Snap last_location to nearest edge
        last_proj_point = ox.projection.project_geometry(Point(last_location.x, last_location.y), to_crs=G.graph.get('crs'))[0]
        try:
            u, v, key = ox.nearest_edges(G, last_proj_point.x, last_proj_point.y)
        except Exception:
            # fall back to nearest node behavior
            node = ox.distance.nearest_nodes(G, last_proj_point.x, last_proj_point.y)
            u, v, key = node, node, 0

        # Get geometry for the edge (u, v, key)
        edge_data = G.get_edge_data(u, v, key) if G.get_edge_data(u, v, key) is not None else G.get_edge_data(u, v)
        if edge_data and isinstance(edge_data, dict) and list(edge_data.keys()):
            # if multigraph, pick the first
            edge_record = edge_data[list(edge_data.keys())[0]]
        else:
            edge_record = edge_data

        # Be defensive: some tests or graph variants may return unexpected
        # types for edge records (e.g. integers). Only treat edge_record as
        # having geometry if it's a dict with a 'geometry' key.
        if isinstance(edge_record, dict) and edge_record.get('geometry') is not None:
            edge_geom = edge_record['geometry']
        else:
            n1, n2 = G.nodes[u], G.nodes[v]
            edge_geom = LineString([(n1['x'], n1['y']), (n2['x'], n2['y'])])

        # Determine whether last_location lies 'on' this edge or at a node
        proj_on_edge_dist = edge_geom.project(last_proj_point)
        proj_on_edge_pt = edge_geom.interpolate(proj_on_edge_dist)
        dist_to_edge = Point(proj_on_edge_pt.x, proj_on_edge_pt.y).distance(last_proj_point)

        # Build forbidden geometries (projected)
        forbidden_geoms = []
        for t in field.player_trajectories.values():
            if len(t) < 2:
                continue
            line_ll = LineString([(p.lon, p.lat) for p in t])
            proj_line = ox.projection.project_geometry(line_ll, to_crs=G.graph.get('crs'))[0]
            forbidden_geoms.append(proj_line)

        # Derive the set of used (directed) edges for this player from their
        # stored trajectory. We use the midpoint of each consecutive pair of
        # trajectory points to snap to the traversed edge.
        used_edges: set[tuple[int, int]] = set()
        player_traj = field.player_trajectories.get(player_id, [])
        for a, b in zip(player_traj[:-1], player_traj[1:]):
            try:
                pa = ox.projection.project_geometry(Point(a.lon, a.lat), to_crs=G.graph.get('crs'))[0]
                pb = ox.projection.project_geometry(Point(b.lon, b.lat), to_crs=G.graph.get('crs'))[0]
                midx = (pa.x + pb.x) / 2.0
                midy = (pa.y + pb.y) / 2.0
                try:
                    uu, vv, kk = ox.nearest_edges(G, midx, midy)
                except Exception:
                    # fallback to nearest_nodes
                    nn = ox.distance.nearest_nodes(G, midx, midy)
                    uu, vv = nn, nn
                used_edges.add((uu, vv))
            except Exception:
                continue

        # Determine current and target nodes (projected coordinates)
        current_node = ox.distance.nearest_nodes(G, last_proj_point.x, last_proj_point.y)
        start_proj = ox.projection.project_geometry(Point(start_loc.lon, start_loc.lat), to_crs=G.graph.get('crs'))[0]
        target_node = ox.distance.nearest_nodes(G, start_proj.x, start_proj.y)

        # If we're effectively at a node (close to an endpoint), try to pick
        # an outgoing edge we haven't used yet and move along it.
        node_coord = Point(G.nodes[current_node]['x'], G.nodes[current_node]['y'])
        dist_to_node = node_coord.distance(last_proj_point)
        NODE_EPS = 1.0  # meters tolerance to consider 'at' a node

        # Also consider being at a node if the projection is near the ends
        at_start_of_edge = proj_on_edge_dist <= 1e-3
        at_end_of_edge = proj_on_edge_dist >= (edge_geom.length - 1e-3)

        if dist_to_node <= NODE_EPS or at_start_of_edge or at_end_of_edge:
            # iterate outgoing edges and select the first unused one that
            # doesn't immediately intersect forbidden geometries
            for nbr in G.successors(current_node):
                if (current_node, nbr) in used_edges:
                    continue
                # get edge geometry
                ed = G.get_edge_data(current_node, nbr)
                if not ed:
                    continue
                ed_rec = ed[list(ed.keys())[0]]
                geom = ed_rec.get('geometry') if ed_rec.get('geometry') is not None else LineString([(G.nodes[current_node]['x'], G.nodes[current_node]['y']), (G.nodes[nbr]['x'], G.nodes[nbr]['y'])])

                # skip if edge intersects forbidden geometries
                blocked = False
                for forbidden in forbidden_geoms:
                    if geom.intersects(forbidden):
                        blocked = True
                        break
                if blocked:
                    continue

                # move along this edge up to max_distance
                take = min(max_distance, geom.length)
                if take <= 0:
                    continue
                dest = geom.interpolate(take)
                dest_ll = ox.projection.project_geometry(dest, crs=G.graph.get('crs'), to_latlong=True)[0]
                return Location(dest_ll.y, dest_ll.x)

        # Copy graph and remove edges that intersect forbidden geometries (except at target_node)
        working = G.copy()
        target_pt = Point(G.nodes[target_node]['x'], G.nodes[target_node]['y'])

        for u, v, k, data in list(working.edges(keys=True, data=True)):
            geom = data.get('geometry')
            if geom is None:
                n1, n2 = G.nodes[u], G.nodes[v]
                geom = LineString([(n1['x'], n1['y']), (n2['x'], n2['y'])])

            blocked = False
            for forbidden in forbidden_geoms:
                inter = geom.intersection(forbidden)
                if inter.is_empty:
                    continue
                if inter.geom_type == 'Point' and inter.distance(target_pt) <= self.intersection_tolerance:
                    continue
                blocked = True
                break

            if blocked:
                try:
                    working.remove_edge(u, v, key=k)
                except Exception:
                    pass

        # Find shortest path on pruned graph
        try:
            node_path = nx.shortest_path(working, current_node, target_node, weight='length')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        # Walk along the path until we reach max_distance, then return that point
        remaining = max_distance
        Gcrs = G.graph.get('crs')

        last_proj_pt = ox.projection.project_geometry(Point(last_location.x, last_location.y), to_crs=Gcrs)[0]

        for i in range(len(node_path) - 1):
            p1, p2 = node_path[i], node_path[i + 1]
            edge_dict = G.get_edge_data(p1, p2)
            if not edge_dict:
                continue
            edge_data = edge_dict[list(edge_dict.keys())[0]]
            if 'geometry' in edge_data and edge_data['geometry'] is not None:
                coords = list(edge_data['geometry'].coords)
                seg = LineString(coords)
            else:
                n1, n2 = G.nodes[p1], G.nodes[p2]
                seg = LineString([(n1['x'], n1['y']), (n2['x'], n2['y'])])

            # start from the beginning of the segment (if i == 0, start at last_proj_pt along seg)
            if i == 0:
                # project last_proj_pt onto seg
                start_dist = seg.project(last_proj_pt)
            else:
                start_dist = 0.0

            seg_len = seg.length
            if start_dist >= seg_len:
                continue

            available = seg_len - start_dist
            take = min(available, remaining)
            if take <= 0:
                break

            point_on_seg = seg.interpolate(start_dist + take)
            # convert back to lat/lon
            latlon_pt = ox.projection.project_geometry(point_on_seg, crs=Gcrs, to_latlong=True)[0]
            return Location(latlon_pt.y, latlon_pt.x)

        # if we exhausted the path but didn't hit max_distance, return the target end
        end_node = node_path[-1]
        end_n = G.nodes[end_node]
        end_pt = ox.projection.project_geometry(Point(end_n['x'], end_n['y']), crs=Gcrs, to_latlong=True)[0]
        return Location(end_pt.y, end_pt.x)
    
    def _get_nearest_node(self, field: PlayingField, location: Location) -> int:
        """
        Return the nearest graph node id for the provided `Location`.
        """
        point_geom = Point(location.x, location.y)
        point_proj = ox.projection.project_geometry(point_geom, to_crs=field.graph.graph['crs'])[0]
        # osmnx.distance.nearest_nodes expects x, y in graph CRS
        node = ox.distance.nearest_nodes(field.graph, point_proj.x, point_proj.y)
        return node
    
    