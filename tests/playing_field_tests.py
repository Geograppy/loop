import os
import osmnx as ox
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from models.playing_field import PlayingField
from models.player import Player  # Import here to avoid circular import issues
from models.location import Location
from utils.playing_field_animation_plotter import PlayingFieldAnimationPlotter



class PlayingFieldTests(unittest.TestCase):
    @property
    def _is_debugging(self) -> bool:
        return True
    
    def test_init_field(self):
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 250)
        
        self.assertIsNotNone(field)
        
    def test_add_player(self):
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 250)
        
        start_loc = Location.from_address("Jeugdsquare 1, 3210 Linden")
        player = Player("1", "TestPlayer", start_loc, field)
        
        # 2. Action
        field.add_player(player.id, player.current_location)
        trajectory = field.get_player_trajectory(player.id)
        
        # 3. Assertions        
        # A. Check trajectory is initialized
        self.assertIsNotNone(trajectory)
        
        self.assertTrue(trajectory.is_empty)
        
        start_loc = field.get_player_start_location(player.id)
        # B. Check that the location was snapped (i.e., changed)
        self.assertNotEqual(start_loc, player.current_location, 
                            "The location should have been snapped to the nearest edge")

        # C. Verify Proximity (Sanity Check)
        # Check that the point didn't jump to a different city.
        # 0.002 degrees is roughly ~200 meters.
        self.assertAlmostEqual(start_loc.y, player.current_location.y, delta=0.002)
        self.assertAlmostEqual(start_loc.x, player.current_location.x, delta=0.002)

    def test_update_player_location_with_one_player(self):
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 1000)

        if self._is_debugging:
            plotter = PlayingFieldAnimationPlotter(field)
            plotter.visualize_state()
        
        start_loc: Location = Location.from_address("Jeugdsquare 1, 3210 Linden")
        player_id = "1"
        
        # 2. Action
        field.add_player(player_id, start_loc)

        if self._is_debugging:
            plotter.visualize_state()
        new_loc: Location = Location.from_address("Eikenstraat 60, 3210 Linden")
        field.update_current_location(player_id, new_loc)
        if self._is_debugging:
            plotter.visualize_state()
        trajectory = field.get_player_trajectory(player_id)

        # 3. Assertions        
        # A. Check trajectory is initialized
        self.assertIsNotNone(trajectory)
        snapped_loc = trajectory.last_known_point
        
        # B. Check that the location was snapped (i.e., changed)
        self.assertNotEqual(snapped_loc, new_loc, 
                            "The location should have been snapped to the nearest edge")

        # C. Verify Proximity (Sanity Check)
        # Check that the point didn't jump to a different city.
        # 0.002 degrees is roughly ~200 meters.
        self.assertAlmostEqual(snapped_loc.x, new_loc.x, delta=0.002)
        self.assertAlmostEqual(snapped_loc.y, new_loc.y, delta=0.002)
        if self._is_debugging:
            plotter.close()
    
    
    def test_update_player_location_with_multiple_players(self):
        address1 = "Patrijsdreef 9, 3210 Linden"
        address2 = "Jeugdsquare 1, 3210 Linden"
        field = PlayingField(address1, 1000)
        if self._is_debugging:
            plotter = PlayingFieldAnimationPlotter(field)
            plotter.visualize_state()
        location1 = Location.from_address(address1)
        location2 = Location.from_address(address2)
        player1 = Player("1", "TestPlayer", location1, field)
        player2 = Player("2", "TestPlayer2", location2, field)
        field.add_player(player1.id, player1.current_location)
        if self._is_debugging:
            plotter.visualize_state()
        field.add_player(player2.id, player2.current_location)
        if self._is_debugging:
            plotter.visualize_state()

        new_location1 = Location.from_address("Hazenpad 5, 3210 Linden")
        new_location2 = Location.from_address("Eikenstraat 60, 3210 Linden")
        field.update_current_location(player1.id, new_location1)
        if self._is_debugging:
            plotter.visualize_state()
        field.update_current_location(player2.id, new_location2)
        if self._is_debugging:
            plotter.visualize_state()
        
        trajectory1 = field.get_player_trajectory(player1.id)
        trajectory2 = field.get_player_trajectory(player2.id)
        

        # 3. Assertions        
        # A. Check trajectory is initialized
        self.assertIsNotNone(trajectory1)
        snapped_loc1 = trajectory1.last_known_point
        self.assertIsNotNone(trajectory2)
        snapped_loc2 = trajectory2.last_known_point
        
        # B. Check that the location was snapped (i.e., changed)
        self.assertNotEqual(snapped_loc1, new_location1, 
                            "The location1 should have been snapped to the nearest edge")
        self.assertNotEqual(snapped_loc2, new_location2, 
                            "The location2 should have been snapped to the nearest edge")

        # C. Verify Proximity (Sanity Check)
        # Check that the point didn't jump to a different city.
        # 0.002 degrees is roughly ~200 meters.
        self.assertAlmostEqual(snapped_loc1.x, new_location1.x, delta=0.002)
        self.assertAlmostEqual(snapped_loc1.y, new_location1.y, delta=0.002)
        self.assertAlmostEqual(snapped_loc2.x, new_location2.x, delta=0.002)
        self.assertAlmostEqual(snapped_loc2.y, new_location2.y, delta=0.002)

        if self._is_debugging:
            plotter.close()
