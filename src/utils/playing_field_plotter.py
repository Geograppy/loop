import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from shapely import Point
from models.playing_field import PlayingField

class PlayingFieldPlotter:
    def __init__(self, field: PlayingField):
        self.field = field

    def visualize_state(self):
        """
        Plots the street graph and overlays player trajectories mapped to the streets.
        Start Point: Solid circle.
        Current Location: Circle with transparent fill (hollow look).
        """
        # 1. Plot the base graph
        fig, ax = ox.plot_graph(
            self.field.graph, 
            show=False, 
            close=False, 
            edge_color='#999999', 
            node_size=0
        )

        # colors cycle for different players
        colors = ['red', 'blue', 'green', 'orange', 'purple']

        for i, (player_id, traj) in enumerate(self.field.player_trajectories.items()):
            if not traj or traj.is_empty: 
                continue
            
            # Pick a consistent color for this player
            color = colors[i % len(colors)]
            
            # 2. Convert Lat/Lon storage to Graph's Meter units
            # Convert Lat/Lon to Graph units
            xs, ys = [], []
            if traj.is_empty:
                pt = self.field.get_player_start_location(player_id)
                pt = ox.projection.project_geometry(
                    Point(pt.x, pt.y), 
                    to_crs=self.field.graph.graph['crs']
                )[0]
                xs.append(pt.x)
                ys.append(pt.y)
            else:
                for loc in traj.geometry.coords:
                    # Note: Ensure project_geometry is efficient if called often
                    pt = ox.projection.project_geometry(
                        Point(*loc), 
                        to_crs=self.field.graph.graph['crs']
                    )[0]
                    xs.append(pt.x)
                    ys.append(pt.y)
                
            # 3. Plot the trajectory line
            ax.plot(xs, ys, c=color, label=player_id, linewidth=2, alpha=0.8)

            # 4. Plot START point (Solid)
            # zorder=5 ensures it sits on top of the street lines
            ax.scatter(xs[0], ys[0], c=color, s=50, zorder=5, edgecolors='black')

            # 5. Plot CURRENT location (Transparent fill / Hollow)
            # facecolors='none' makes the inside transparent
            # edgecolors=color sets the ring color
            ax.scatter(
                xs[-1], ys[-1], 
                facecolors='none', 
                edgecolors=color, 
                s=80,       # Make it slightly larger so it's visible
                linewidth=2, 
                zorder=6    # Ensure it sits on top of everything
            )
            
        # Add legend and show
        ax.legend()
        plt.show()