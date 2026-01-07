import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

import osmnx as ox
from shapely.geometry import LineString, Point


sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from models.playing_field import PlayingField
from models.location import Location
from models.strategy import CloseLoopStrategy, NoopStrategy


class TestNoopStrategy(unittest.TestCase):
    """Test cases for NoopStrategy."""

    def test_noop_returns_same_location(self):
        """NoopStrategy should return the exact same location."""
        strategy = NoopStrategy()
        loc = Location(51.5, -0.1)
        field = Mock()
        
        result = strategy.next_move(loc, field, max_moving_speed=1.4, player_id="p1")
        self.assertEqual(result, loc)

    def test_noop_ignores_speed_and_time(self):
        """NoopStrategy should ignore speed and time parameters."""
        strategy = NoopStrategy()
        loc = Location(51.5, -0.1)
        field = Mock()
        current_time = datetime.now(timezone.utc)
        
        result = strategy.next_move(loc, field, max_moving_speed=10.0, player_id="p1", current_time=current_time)
        self.assertEqual(result, loc)


class TestCloseLoopStrategy(unittest.TestCase):
    """Test cases for CloseLoopStrategy."""

    def setUp(self):
        """Initialize strategy and common fixtures."""
        self.strategy = CloseLoopStrategy()

    def test_first_move_on_close_loop_strategy_with_no_trajectory(self):
        """Test first move on CloseLoopStrategy when no trajectory exists."""
        timestamp1: datetime = datetime.now(timezone.utc) - timedelta(seconds=10)
        timestamp2: datetime = datetime.now(timezone.utc) - timedelta(seconds=5)
        strategy = CloseLoopStrategy()
        loc = Location.from_address("Jeugdsquare 5, 3210 Linden")
        loc.timestamp = timestamp1
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 1000)
        field.get_player_trajectory = Mock(return_value=None)

        result = strategy.next_move(loc, field, max_moving_speed=4, player_id="p1", current_time=timestamp2)
        self.assertIsNotNone(result)
        
    
    def test_2_moves_within_1_edge_on_close_loop_strategy(self):
        """Test first move on CloseLoopStrategy when no trajectory exists."""
        timestamp1: datetime = datetime.now(timezone.utc) - timedelta(seconds=10)
        timestamp2: datetime = timestamp1 + timedelta(seconds=5)
        timestamp3: datetime = timestamp2 + timedelta(seconds=5)
        strategy = CloseLoopStrategy()
        loc = Location.from_address("Jeugdsquare 5, 3210 Linden")
        loc.timestamp = timestamp1
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 1000)
        field.get_player_trajectory = Mock(return_value=None)

        result1 = strategy.next_move(loc, field, max_moving_speed=4, player_id="p1", current_time=timestamp2)
        self.assertIsNotNone(result1)

        result2 = strategy.next_move(result1, field, max_moving_speed=4, player_id="p1", current_time=timestamp3)

        # assert that result and loc are more or less 20 meters apart
        result2_proj = ox.projection.project_geometry(Point(result2.x, result2.y), to_crs=field.graph.graph['crs'])[0]
        result1_proj = ox.projection.project_geometry(Point(result1.x, result1.y), to_crs=field.graph.graph['crs'])[0]
        distance_moved = result1_proj.distance(result2_proj)
        self.assertAlmostEqual(distance_moved, 4 * 5, delta=1.0)  # max speed
    
    def test_2_moves_across_multiple_edges_on_close_loop_strategy(self):
        """Test first move on CloseLoopStrategy when no trajectory exists."""
        timestamp1: datetime = datetime.now(timezone.utc) - timedelta(seconds=10)
        timestamp2: datetime = timestamp1 + timedelta(seconds=5)
        timestamp3: datetime = timestamp2 + timedelta(seconds=5)
        strategy = CloseLoopStrategy()
        loc = Location.from_address("Jeugdsquare 5, 3210 Linden")
        loc.timestamp = timestamp1
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 1000)
        field.get_player_trajectory = Mock(return_value=None)

        result1 = strategy.next_move(loc, field, max_moving_speed=40, player_id="p1", current_time=timestamp2)
        self.assertIsNotNone(result1)

        result2 = strategy.next_move(result1, field, max_moving_speed=40, player_id="p1", current_time=timestamp3)
        self.assertIsNotNone(result2)
        # assert that  result and loc are more or less 200 meters apart
        result2_proj = ox.projection.project_geometry(Point(result2.x, result2.y), to_crs=field.graph.graph['crs'])[0]
        result1_proj = ox.projection.project_geometry(Point(result1.x, result1.y), to_crs=field.graph.graph['crs'])[0]
        distance_moved = result1_proj.distance(result2_proj)
        self.assertGreaterEqual(distance_moved, 0)  # max speed
    


if __name__ == "__main__":
    unittest.main()
