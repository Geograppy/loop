from datetime import datetime, timedelta, timezone
import os
from time import sleep
import osmnx as ox
import sys
import unittest





sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from utils.playing_field_animation_plotter import PlayingFieldAnimationPlotter
from utils.playing_field_plotter import PlayingFieldPlotter
from models.strategy import CloseLoopStrategy
from models.location import Location
from models.playing_field import PlayingField
from models.player import Player

class PlayerTests(unittest.TestCase):
    @property
    def _is_debugging(self) -> bool:
        return False
    
    def test_player_initialization(self):
        address = "Jeugdsquare 5, 3210 Linden"
        location_point = Location.from_address(address)
        field = PlayingField(address, 250)
        player = Player("1", "TestPlayer", location_point, field)
        
        self.assertIsNotNone(player)
        self.assertEqual(player.display_name, "TestPlayer")
        self.assertEqual(player.id, "1")
        self.assertEqual(player.current_location, location_point)
        self.assertEqual(player.field, field)
        self.assertIsNotNone(field.get_player_trajectory(player.id))
        
    def test_player_update_location(self):
        address = "Jeugdsquare 5, 3210 Linden"
        location_point = Location.from_address(address)
        field = PlayingField(address, 250)
        player = Player("1", "TestPlayer", location_point, field)

        new_location = Location.from_address("Jeugdsquare 1, 3210 Linden")
        player.update_current_location(new_location)
        
        self.assertEqual(player.current_location, new_location)
        self.assertIsNotNone(field.get_player_trajectory(player.id))
        
    def test_player_next_move(self):
        timestamp1: datetime = datetime.now(timezone.utc) - timedelta(seconds=10)
        timestamp2: datetime = datetime.now(timezone.utc) - timedelta(seconds=5)
        address = "Knapzak 2, 3210 Linden"
        location1: Location = Location.from_address(address)
        location1.timestamp = timestamp1
        field = PlayingField(address, 1000)
        player = Player("1", "TestPlayer", location1, field, strategy=CloseLoopStrategy(), max_moving_speed=10.0)
        if self._is_debugging:
            plotter = PlayingFieldAnimationPlotter(field)
            plotter.visualize_state()

        should_continue = True
        max_moves = 20
        moves_made = 0
        while should_continue and moves_made < max_moves:
            sleep(0.5)  # Simulate time passing
            moves_made += 1
            should_continue = player.move()
            if self._is_debugging:
                plotter.visualize_state()
        # if should_continue:
        #     should_continue = player.move()
        #     sleep(0.5)  # Simulate time passing
        #     if self._is_debugging:
        #         plotter.visualize_state()
        # if should_continue:
        #     should_continue = player.move()
        #     sleep(0.5)  # Simulate time passing
        #     if self._is_debugging:
        #         plotter.visualize_state()
        # if should_continue:
        #     should_continue = player.move()
        #     sleep(0.5)  # Simulate time passing
        #     if self._is_debugging:
        #         plotter.visualize_state()
        # if should_continue:
        #     should_continue = player.move()
        #     sleep(0.5)  # Simulate time passing
        #     if self._is_debugging:
        #         plotter.visualize_state()
        # if should_continue:
        #     should_continue = player.move()
        #     sleep(0.5)  # Simulate time passing
        #     if self._is_debugging:
        #         plotter.visualize_state()
            
        self.assertIsNotNone(field.get_player_trajectory(player.id))
        if self._is_debugging:
            plotter.close()
