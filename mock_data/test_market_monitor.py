#!/usr/bin/env python3
import unittest
import os
import json
import logging
from pathlib import Path
from mock_api import Mock10CricAPI

# Disable logging for tests
logging.disable(logging.CRITICAL)

class TestMarketMonitor(unittest.TestCase):
    """
    Test the market monitoring functionality using mock data.
    """
    
    def setUp(self):
        """Set up test environment."""
        self.mock_api = Mock10CricAPI()
        self.event_id = "cf27dbc5-2269-334f-993f-694ded1c64d3"
        self.market_id = "592d8ee0-2fd9-342b-8fd2-30a9e690cfb7"
        self.market_line_id = "a21928ef-8d62-30c0-b2aa-8840a659de0e"
        self.selection_id = "2f41d627-55ab-394b-8b58-8a13c150a72d"
    
    def test_get_upcoming_matches(self):
        """Test retrieval of upcoming matches."""
        matches = self.mock_api.get_upcoming_matches()
        self.assertIsInstance(matches, list)
        self.assertTrue(len(matches) > 0)
        
        # Check that we have the expected fields
        first_match = matches[0]
        expected_fields = ["id", "name", "leagueName", "startEventDate"]
        for field in expected_fields:
            self.assertIn(field, first_match)
    
    def test_get_markets_for_event(self):
        """Test retrieval of markets for an event."""
        markets = self.mock_api.get_markets_for_event(self.event_id)
        self.assertIsNotNone(markets["event_data"])
        
        # Check that we have markets
        expanded_markets = markets["event_data"]["expandedMarkets"]
        self.assertTrue(len(expanded_markets) > 0)
        
        # Check that our target market exists
        market_found = False
        for market in expanded_markets:
            if market["id"] == self.market_id:
                market_found = True
                break
        self.assertTrue(market_found, "Expected market not found")
    
    def test_get_markets_for_invalid_event(self):
        """Test retrieval of markets for an invalid event ID."""
        invalid_event_id = "invalid-event-id"
        markets = self.mock_api.get_markets_for_event(invalid_event_id)
        self.assertIn("error", markets)
        self.assertIsNone(markets["event_data"])
    
    def test_place_bet_attempt(self):
        """Test attempt to place a bet (success rate is 80%)."""
        # We'll run this test multiple times to increase the chance of seeing both outcomes
        for _ in range(5):
            result = self.mock_api.place_bet(
                selection_id=self.selection_id,
                event_id=self.event_id,
                market_id=self.market_id,
                market_line_id=self.market_line_id,
                stake=100,
                odds=2.25
            )
            
            # Either success or error should be valid responses
            if result["status"] == "success":
                self.assertIn("bet_id", result)
                self.assertIn("details", result)
                self.assertEqual(result["details"]["event_id"], self.event_id)
                self.assertEqual(result["details"]["market_id"], self.market_id)
                self.assertEqual(result["details"]["selection_id"], self.selection_id)
                self.assertEqual(result["details"]["stake"], 100)
                self.assertEqual(result["details"]["odds"], 2.25)
                self.assertEqual(result["details"]["potential_return"], 225.0)
            else:
                self.assertEqual(result["status"], "error")
                self.assertIn("error", result)
                self.assertIn("message", result)
    
    def test_get_sanctioned_bets(self):
        """Test retrieval of sanctioned bets configuration."""
        sanctioned_bets = self.mock_api.get_sanctioned_bets()
        self.assertIn("settings", sanctioned_bets)
        self.assertIn("selected_bets", sanctioned_bets)
        
        # Check settings
        settings = sanctioned_bets["settings"]
        self.assertIn("first_overs_range", settings)
        self.assertIn("last_overs_range", settings)
        self.assertIn("stake", settings)
        self.assertIn("active", settings)
        
        # Check selected bets
        selected_bets = sanctioned_bets["selected_bets"]
        self.assertTrue(len(selected_bets) > 0)
        
        # Check a specific selected bet
        first_bet = selected_bets[0]
        expected_fields = ["innings", "over", "team", "selection_name", "odds", 
                          "stake", "market_id", "market_line_id", "selection_id", "market_name"]
        for field in expected_fields:
            self.assertIn(field, first_bet)
    
    def test_get_bet_history(self):
        """Test retrieval of bet history."""
        history = self.mock_api.get_bet_history()
        self.assertIsInstance(history, list)
        self.assertTrue(len(history) > 0)
        
        # Check a specific bet in history
        first_bet = history[0]
        expected_fields = ["bet_id", "event_id", "match_name", "market_id", "market_name", 
                          "selection_id", "selection_name", "odds", "stake", "potential_return", 
                          "timestamp", "status"]
        for field in expected_fields:
            self.assertIn(field, first_bet)

if __name__ == "__main__":
    unittest.main() 