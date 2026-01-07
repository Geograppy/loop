import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

import networkx as nx
from shapely.geometry import LineString, Point

from models.location import Location
from models.trajectory import Trajectory


class TestTrajectory(unittest.TestCase):
    """Test cases for Trajectory."""

    def test_trajectory_initialization_should_have_none_geometry(self):
        """Trajectory should initialize with a starting location."""
        trajectory = Trajectory()
        self.assertIsNone(trajectory.geometry)
        self.assertIsNone(trajectory.start_point)
        self.assertIsNone(trajectory.last_known_point)

    def test_trajectory_initialization_with_geometry(self):
        """Trajectory should initialize with a starting location."""
        loc1 = Location(51.5, -0.1)
        loc2 = Location(51.5001, -0.1001)
        loc3 = Location(51.5010, -0.1010)
        trajectory = Trajectory(LineString([(loc1.x, loc1.y), (loc2.x, loc2.y), (loc3.x, loc3.y)]))
        self.assertIsNotNone(trajectory.geometry)
        self.assertEqual(trajectory.start_point.x, loc1.x)
        self.assertEqual(trajectory.start_point.y, loc1.y)
        self.assertEqual(trajectory.last_known_point.x, loc3.x)
        self.assertEqual(trajectory.last_known_point.y, loc3.y)

    def test_update_trajectory_with_shared_endpoints(self):
        """Trajectory should update correctly with new locations."""
        loc1 = Location(51.5, -0.1)
        loc2 = Location(51.5001, -0.1001)
        loc3 = Location(51.5010, -0.1010)
        trajectory = Trajectory(LineString([(loc1.x, loc1.y), (loc2.x, loc2.y)]))
        trajectory.update(LineString([(loc2.x, loc2.y), (loc3.x, loc3.y)]))
        self.assertEqual(trajectory.last_known_point.x, loc3.x)
        self.assertEqual(trajectory.last_known_point.y, loc3.y)
        self.assertIsNotNone(trajectory.geometry)
        self.assertEqual(len(trajectory.geometry.coords), 3)
        
    def test_update_trajectory_without_shared_endpoints(self):
        """Trajectory should update correctly with new locations."""
        loc1 = Location(51.5, -0.1)
        loc2 = Location(51.5001, -0.1001)
        loc3 = Location(51.5010, -0.1010)
        loc4 = Location(51.5020, -0.1020)
        trajectory = Trajectory(LineString([(loc1.x, loc1.y), (loc2.x, loc2.y)]))
        trajectory.update(LineString([(loc3.x, loc3.y), (loc4.x, loc4.y)]))
        self.assertEqual(trajectory.last_known_point.x, loc4.x)
        self.assertIsNotNone(trajectory.geometry)
        self.assertEqual(len(trajectory.geometry.coords), 4)