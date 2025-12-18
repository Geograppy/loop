import osmnx as ox
import networkx as nx


class PlayingField:
    def __init__(self, address: str, radius: int):
        """
        Initialize the playing field with a given address and radius.

        :param address: The address around which to create the playing field.
        :param radius: The radius (in meters) for the playing field.
        """
        self.address = address
        self.radius = radius
        self.graph = self._create_playing_field()
        
    def _create_playing_field(self) -> nx.MultiDiGraph:
        """
        Create a playing field graph using OSM data.

        :return: A NetworkX MultiDiGraph representing the playing field.
        """
        
        # Create a graph from the point within the specified radius
        G = ox.graph_from_address(self.address, dist=self.radius, network_type='walk')
        
        return G