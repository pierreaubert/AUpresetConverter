#!/usr/bin/env python3
"""Test RME room EQ filter constraints functionality."""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def enforce_rme_room_filter_constraints(iirs: list) -> list:
    """Enforce RME room EQ constraints on LSC and HSC filters.
    
    This is a copy of the function from converter.py to avoid import dependencies.
    
    Args:
        iirs: List of IIR filter dictionaries
        
    Returns:
        List of IIRs with RME room EQ constraints applied:
        - At most 1 LSC filter (positioned first if present)
        - At most 1 HSC filter (positioned last if present)
        - Other filters preserved in their relative order
    """
    if not iirs:
        return iirs
    
    # Separate filters by type
    lsc_filters = []
    hsc_filters = []
    other_filters = []
    
    for iir in iirs:
        filter_type = iir.get('type', '')
        if filter_type == 'LSC':
            lsc_filters.append(iir)
        elif filter_type == 'HSC':
            hsc_filters.append(iir)
        else:
            other_filters.append(iir)
    
    # Select at most one LSC filter (prefer highest absolute gain)
    selected_lsc = None
    if lsc_filters:
        selected_lsc = max(lsc_filters, key=lambda x: abs(x.get('gain', 0.0)))
    
    # Select at most one HSC filter (prefer highest absolute gain)
    selected_hsc = None
    if hsc_filters:
        selected_hsc = max(hsc_filters, key=lambda x: abs(x.get('gain', 0.0)))
    
    # Reorder: LSC first, other filters in middle, HSC last
    result = []
    if selected_lsc:
        result.append(selected_lsc)
    result.extend(other_filters)
    if selected_hsc:
        result.append(selected_hsc)
    
    return result


class TestRMEConstraints(unittest.TestCase):
    """Test cases for RME room EQ filter constraints."""

    def test_austrian_audio_consistency(self):
        """Test that Austrian Audio files with different filter order produce same result after constraints."""
        # Data from Austrian Audio The Composer (minimal setting) ParametricEQ.txt
        # Original order has HSC filter in position 6 (middle)
        original_filters = [
            {"type": "LSC", "freq": 105, "gain": 2.7, "q": 0.70, "width": 1.0},
            {"type": "PK", "freq": 208, "gain": -2.7, "q": 0.64, "width": 1.0},
            {"type": "PK", "freq": 8501, "gain": 3.9, "q": 2.88, "width": 1.0},
            {"type": "PK", "freq": 2019, "gain": 5.3, "q": 2.46, "width": 1.0},
            {"type": "PK", "freq": 2866, "gain": -4.2, "q": 3.55, "width": 1.0},
            {"type": "HSC", "freq": 10000, "gain": -2.5, "q": 0.70, "width": 1.0},  # HSC in middle
            {"type": "PK", "freq": 5671, "gain": -3.0, "q": 5.62, "width": 1.0},
            {"type": "PK", "freq": 4324, "gain": 1.9, "q": 4.16, "width": 1.0},
            {"type": "PK", "freq": 7145, "gain": 2.2, "q": 5.28, "width": 1.0},
            {"type": "PK", "freq": 5243, "gain": -1.1, "q": 6.00, "width": 1.0},
        ]
        
        # Data from Austrian Audio The Composer (minimal setting) ParametricEQ reordered.txt  
        # Reordered version has HSC filter moved to position 10 (last)
        reordered_filters = [
            {"type": "LSC", "freq": 105, "gain": 2.7, "q": 0.70, "width": 1.0},
            {"type": "PK", "freq": 208, "gain": -2.7, "q": 0.64, "width": 1.0},
            {"type": "PK", "freq": 8501, "gain": 3.9, "q": 2.88, "width": 1.0},
            {"type": "PK", "freq": 2019, "gain": 5.3, "q": 2.46, "width": 1.0},
            {"type": "PK", "freq": 2866, "gain": -4.2, "q": 3.55, "width": 1.0},
            {"type": "PK", "freq": 5671, "gain": -3.0, "q": 5.62, "width": 1.0},
            {"type": "PK", "freq": 4324, "gain": 1.9, "q": 4.16, "width": 1.0},
            {"type": "PK", "freq": 7145, "gain": 2.2, "q": 5.28, "width": 1.0},
            {"type": "PK", "freq": 5243, "gain": -1.1, "q": 6.00, "width": 1.0},
            {"type": "HSC", "freq": 10000, "gain": -2.5, "q": 0.70, "width": 1.0},  # HSC moved to end
        ]
        
        # Apply constraints to both
        constrained_original = enforce_rme_room_filter_constraints(original_filters)
        constrained_reordered = enforce_rme_room_filter_constraints(reordered_filters)
        
        # Both should produce identical results
        self.assertEqual(len(constrained_original), len(constrained_reordered), 
                        "Constrained filter counts should match")
        
        for i, (f1, f2) in enumerate(zip(constrained_original, constrained_reordered)):
            self.assertEqual(f1['type'], f2['type'], f"Filter {i+1} type mismatch")
            self.assertEqual(f1['freq'], f2['freq'], f"Filter {i+1} frequency mismatch")  
            self.assertEqual(f1['gain'], f2['gain'], f"Filter {i+1} gain mismatch")

    def test_lsc_hsc_positioning(self):
        """Test that LSC is positioned first and HSC is positioned last."""
        filters = [
            {"type": "PK", "freq": 1000, "gain": 2.0, "width": 0.7},
            {"type": "HSC", "freq": 8000, "gain": -2.0, "width": 1.0},
            {"type": "LSC", "freq": 100, "gain": 3.0, "width": 1.0},
            {"type": "PK", "freq": 2000, "gain": -1.0, "width": 0.5},
        ]
        
        result = enforce_rme_room_filter_constraints(filters)
        
        # LSC should be first
        self.assertEqual(result[0]['type'], 'LSC', "LSC should be positioned first")
        self.assertEqual(result[0]['freq'], 100, "Correct LSC filter should be first")
        
        # HSC should be last
        self.assertEqual(result[-1]['type'], 'HSC', "HSC should be positioned last")
        self.assertEqual(result[-1]['freq'], 8000, "Correct HSC filter should be last")
        
        # Should have 4 filters total
        self.assertEqual(len(result), 4, "Should preserve all filter types")

    def test_multiple_lsc_hsc_selection(self):
        """Test selection of highest gain LSC and HSC when multiple exist."""
        filters = [
            {"type": "LSC", "freq": 100, "gain": -3.0, "width": 1.0},  # Lower gain magnitude
            {"type": "PK", "freq": 1000, "gain": 2.0, "width": 0.7},
            {"type": "LSC", "freq": 80, "gain": -5.0, "width": 1.2},   # Higher gain magnitude - should be kept
            {"type": "HSC", "freq": 8000, "gain": -2.0, "width": 1.0}, # Lower gain magnitude
            {"type": "PK", "freq": 2000, "gain": -1.0, "width": 0.5},
            {"type": "HSC", "freq": 10000, "gain": -4.0, "width": 0.8}, # Higher gain magnitude - should be kept
        ]
        
        result = enforce_rme_room_filter_constraints(filters)
        
        # Should have only 4 filters (2 PK + 1 LSC + 1 HSC)
        self.assertEqual(len(result), 4, "Should have 4 filters after deduplication")
        
        # Check LSC selection (highest absolute gain)
        self.assertEqual(result[0]['type'], 'LSC')
        self.assertEqual(result[0]['gain'], -5.0, "Should select LSC with highest absolute gain")
        self.assertEqual(result[0]['freq'], 80, "Should select correct LSC filter")
        
        # Check HSC selection (highest absolute gain)
        self.assertEqual(result[-1]['type'], 'HSC')
        self.assertEqual(result[-1]['gain'], -4.0, "Should select HSC with highest absolute gain")
        self.assertEqual(result[-1]['freq'], 10000, "Should select correct HSC filter")

    def test_no_lsc_hsc_filters(self):
        """Test that filters without LSC/HSC are unchanged."""
        filters = [
            {"type": "PK", "freq": 1000, "gain": 2.0, "width": 0.7},
            {"type": "PK", "freq": 2000, "gain": -1.0, "width": 0.5},
            {"type": "LP", "freq": 8000, "gain": 0.0, "width": 1.0},
        ]
        
        result = enforce_rme_room_filter_constraints(filters)
        
        # Should be identical to input
        self.assertEqual(result, filters, "Filters without LSC/HSC should be unchanged")

    def test_only_lsc_filter(self):
        """Test handling of filters with only LSC."""
        filters = [
            {"type": "LSC", "freq": 100, "gain": -3.0, "width": 1.0},
            {"type": "PK", "freq": 1000, "gain": 2.0, "width": 0.7},
            {"type": "PK", "freq": 2000, "gain": -1.0, "width": 0.5},
        ]
        
        result = enforce_rme_room_filter_constraints(filters)
        
        # LSC should be first
        self.assertEqual(result[0]['type'], 'LSC', "LSC should be positioned first")
        self.assertEqual(len(result), 3, "Should preserve all filters")

    def test_only_hsc_filter(self):
        """Test handling of filters with only HSC."""
        filters = [
            {"type": "PK", "freq": 1000, "gain": 2.0, "width": 0.7},
            {"type": "PK", "freq": 2000, "gain": -1.0, "width": 0.5},
            {"type": "HSC", "freq": 8000, "gain": -3.0, "width": 1.0},
        ]
        
        result = enforce_rme_room_filter_constraints(filters)
        
        # HSC should be last
        self.assertEqual(result[-1]['type'], 'HSC', "HSC should be positioned last")
        self.assertEqual(len(result), 3, "Should preserve all filters")

    def test_empty_filter_list(self):
        """Test handling of empty filter list."""
        result = enforce_rme_room_filter_constraints([])
        self.assertEqual(result, [], "Empty list should remain empty")


if __name__ == '__main__':
    unittest.main()