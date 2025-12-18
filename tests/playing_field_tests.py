import os
import sys
import unittest


sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from models.playing_field import PlayingField


class PlayingFieldTests(unittest.TestCase):
    
    def test_init_field(self):
        field = PlayingField("Jeugdsquare 5, 3210 Linden", 250)
        
        self.assertIsNotNone(field)