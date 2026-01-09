import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString
from shapely.ops import substring

class GraphGeometryFunctions:

    def snap_geo_point_to_proj_point_on_edge(location: Point, graph: nx.MultiDiGraph) -> tuple[Point, int, int, int]:
        """
        Snaps a given location to the nearest edge in the graph.
        Returns the snapped Point in projected coordinates.
        """
        # 1. Project point to graph CRS
        point_proj = ox.projection.project_geometry(location, to_crs=graph.graph['crs'])[0]
        
        snapped_point_proj, u, v, key = GraphGeometryFunctions.snap_proj_point_to_proj_point_on_edge(point_proj, graph)
        
        return snapped_point_proj, u, v, key
        
        
    def snap_proj_point_to_proj_point_on_edge(point_proj: Point, graph: nx.MultiDiGraph) -> tuple[Point, int, int, int]:
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
        
    def create_linestring_from_proj_points_within_edge(start_point: Point, end_point: Point, graph: nx.MultiDiGraph, start_node: int, end_node: int) -> LineString:
        # Same edge, just update the trajectory
        # build LineString from path and make sure to start and end from the exact last and new locations
        coords = []
        coords.append((start_point.x, start_point.y))

        # get geometry from last_known_location to next node
        edge_data = graph.get_edge_data(start_node, end_node)
        if 'geometry' in edge_data[0]:
            edge_geom = edge_data[0]['geometry']
            
            start_dist = edge_geom.project(start_point)
            end_dist = edge_geom.project(end_point)
            line = substring(edge_geom, start_dist, end_dist)
            if isinstance(line, LineString):
                coords.extend(line.coords)
            else:
                pt = line
                coords.append((pt.x, pt.y))
            

        coords.append((end_point.x, end_point.y))
        path_proj = LineString(coords)
        # convert path_proj back to lat/lon
        path_geo: LineString = ox.projection.project_geometry(path_proj, crs=graph.graph['crs'], to_latlong=True)[0]
        return path_geo
    
    def create_linestring_from_proj_points_across_nodes(start_point: Point, start_point_u: int, start_point_v: int, end_point: Point, end_point_u: int, end_point_v: int, graph: nx.MultiDiGraph) -> LineString:
        start_node = GraphGeometryFunctions.get_farthest_node(start_point_u, start_point_v, end_point, graph)
        end_node = GraphGeometryFunctions.get_farthest_node(end_point_u, end_point_v, start_point, graph)
        path = ox.shortest_path(graph,
                                start_node,
                                end_node,
                                weight='length')
        # build LineString from path and make sure to start and end from the exact last and new locations
        coords = []
        coords.append((start_point.x, start_point.y))
        for node in path[1:-1]:
            # get geometry from last_known_location to next node
            edge_data = graph.get_edge_data(path[path.index(node) - 1], node)
            if 'geometry' in edge_data[0]:
                edge_geom: LineString = edge_data[0]['geometry']
                node_point = Point(graph.nodes[path[-1]]['x'], graph.nodes[path[-1]]['y'])
                if node == path[1]:  # First edge
                    edge_geom = GraphGeometryFunctions.orient_edge_to_node(edge_geom, node_pt=node_point)
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
                    edge_geom = GraphGeometryFunctions.orient_edge_away_from_node(edge_geom, node_pt=node_point)
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
                node_data = graph.nodes[node]
                coords.append((node_data['x'].item(), node_data['y'].item()))
        if not (coords and coords[-1] == (end_point.x, end_point.y)):
            coords.append((end_point.x, end_point.y))
        path_proj = LineString(coords)
        # convert path_proj back to lat/lon
        return ox.projection.project_geometry(path_proj, crs=graph.graph['crs'], to_latlong=True)[0]
    
    def get_farthest_node(u: int, v: int, point_proj: Point, graph: nx.MultiDiGraph) -> int:
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
            return u
        else:
            return v
        
    def orient_edge_away_from_node(edge_geom: LineString, node_pt: Point, tol=1e-9) -> LineString:
        # If node is already at the first coordinate, return as-is.
        if Point(edge_geom.coords[0]).distance(node_pt) <= tol:
            return LineString(list(edge_geom.coords)[::-1])
        # If node is at the last coordinate, reverse the coordinates so node becomes start.
        if Point(edge_geom.coords[-1]).distance(node_pt) <= tol:
            return edge_geom
        # Otherwise the node is not exactly on endpoints — you may want to snap first.
        return edge_geom
    
    def orient_edge_to_node(edge_geom: LineString, node_pt: Point, tol=1e-9) -> LineString:
        # If node is already at the first coordinate, return as-is.
        if Point(edge_geom.coords[0]).distance(node_pt) <= tol:
            return edge_geom
        # If node is at the last coordinate, reverse the coordinates so node becomes start.
        if Point(edge_geom.coords[-1]).distance(node_pt) <= tol:
            return LineString(list(edge_geom.coords)[::-1])
        # Otherwise the node is not exactly on endpoints — you may want to snap first.
        return edge_geom