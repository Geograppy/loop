import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

import networkx as nx
from shapely.geometry import LineString, Point

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

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



if __name__ == "__main__":
    unittest.main()
