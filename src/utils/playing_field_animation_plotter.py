import osmnx as ox
import matplotlib.pyplot as plt
from shapely import Point
from models.playing_field import PlayingField

class PlayingFieldAnimationPlotter:
    def __init__(self, field: PlayingField):
        self.field = field
        
        # 1. Enable interactive mode for non-blocking animation
        plt.ion() 

        # 2. Plot the base graph ONCE during init.
        # We save 'fig' and 'ax' to add players to them later.
        self.fig, self.ax = ox.plot_graph(
            self.field.graph, 
            show=False, 
            close=False, 
            edge_color='#999999', 
            node_size=0
        )
        
        # List to keep track of player markers so we can clear them next frame
        self.drawn_elements = []

    def visualize_state(self, duration=1.0):
        """
        Updates the existing plot with new player positions.
        Blocks execution for 'duration' seconds, then proceeds.
        """
        
        # 1. Clean up the PREVIOUS frame's players
        # (If we don't do this, the old dots stay on screen forever)
        for artist in self.drawn_elements:
            artist.remove()
        self.drawn_elements.clear()

        colors = ['red', 'blue', 'green', 'orange', 'purple']

        # 2. Draw the NEW state
        for i, (player_id, traj) in enumerate(self.field.player_trajectories.items()):
            if not traj: 
                continue
            
            color = colors[i % len(colors)]
            
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
                
            # --- PLOTTING ---
            # We capture the returned objects (lines/scatters) to delete them later
            
            # A. Trajectory Line (ax.plot returns a list, so we unwrap with comma)
            line, = self.ax.plot(xs, ys, c=color, label=player_id, linewidth=2, alpha=0.8)
            self.drawn_elements.append(line)

            # B. Start Point
            start_dot = self.ax.scatter(xs[0], ys[0], c=color, s=50, zorder=5, edgecolors='black')
            self.drawn_elements.append(start_dot)

            # C. Current Location
            curr_dot = self.ax.scatter(
                xs[-1], ys[-1], 
                facecolors='none', 
                edgecolors=color, 
                s=80, 
                linewidth=2, 
                zorder=6
            )
            self.drawn_elements.append(curr_dot)
            
        # 3. Refresh the plot window
        # re-drawing only the updated artists is faster, but this is safe
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
        # 4. Block for X seconds, then continue code execution
        plt.pause(duration)

    def close(self):
        """Call this at the end of your program to clean up."""
        plt.ioff()
        plt.show()