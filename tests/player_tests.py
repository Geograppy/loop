import os
import osmnx as ox
import sys
import unittest



sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from models.playing_field import PlayingField
from models.player import Player

class PlayerTests(unittest.TestCase):
    
    def test_player_initialization(self):
        address = "Jeugdsquare 5, 3210 Linden"
        location_point = ox.geocode(address)
        field = PlayingField(address, 250)
        player = Player("1", "TestPlayer", location_point, field)
        
        self.assertIsNotNone(player)
        self.assertEqual(player.name, "TestPlayer")
        self.assertEqual(player.id, "1")
        self.assertEqual(player.current_location, location_point)
        self.assertEqual(player.field, field)