import networkx as nx
import osmnx as ox
from shapely.geometry import Point, LineString

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