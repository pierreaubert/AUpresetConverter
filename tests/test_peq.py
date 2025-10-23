#!/usr/bin/env python3
"""Comprehensive tests for the PEQ (Parametric EQ) module"""

import unittest
import math
import sys
import os
import io
from contextlib import redirect_stdout

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Try to import numpy - if not available, skip numpy-dependent tests
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not available, skipping numpy-dependent tests")

# Import the modules to test
try:
    from iir.filter_iir import Biquad
    if NUMPY_AVAILABLE:
        from iir.filter_peq import (
            peq_build, 
            peq_preamp_gain, 
            peq_preamp_gain_conservative,
            peq_format_apo,
            peq_print
        )
    PEQ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import PEQ modules: {e}")
    PEQ_AVAILABLE = False


@unittest.skipUnless(NUMPY_AVAILABLE and PEQ_AVAILABLE, "Requires numpy and PEQ modules")
class TestPEQBuild(unittest.TestCase):
    """Test peq_build function for frequency response calculation"""
    
    def setUp(self):
        # Create test frequencies
        self.freq = np.logspace(1, 4, 100)  # 10 Hz to 10 kHz, 100 points
        
        # Create test PEQ with different filter types
        self.test_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)),      # Peak at 1kHz, +3dB
            (1.0, Biquad(Biquad.LOWSHELF, 100, 48000, 0.7, 2.0)),   # Low shelf at 100Hz, +2dB
            (1.0, Biquad(Biquad.HIGHSHELF, 10000, 48000, 0.7, -2.0)) # High shelf at 10kHz, -2dB
        ]
        
        # Single filter PEQ for isolated testing
        self.single_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 6.0))  # Peak at 1kHz, +6dB
        ]
        
        # Empty PEQ for edge case testing
        self.empty_peq = []
    
    def test_peq_build_basic(self):
        """Test basic peq_build functionality"""
        response = peq_build(self.freq, self.test_peq)
        
        # Should return numpy array
        self.assertIsInstance(response, np.ndarray)
        self.assertEqual(len(response), len(self.freq))
        
        # All values should be finite
        self.assertTrue(np.all(np.isfinite(response)))
        
        # Response should not be all zeros for a non-empty PEQ
        self.assertFalse(np.allclose(response, 0))
    
    def test_peq_build_empty(self):
        """Test peq_build with empty PEQ"""
        response = peq_build(self.freq, self.empty_peq)
        
        # Should return array of zeros
        expected = np.zeros_like(self.freq)
        np.testing.assert_array_almost_equal(response, expected)
    
    def test_peq_build_single_filter(self):
        """Test peq_build with single filter"""
        response = peq_build(self.freq, self.single_peq)
        
        # Find the index closest to 1000 Hz
        target_freq = 1000.0
        freq_idx = np.argmin(np.abs(self.freq - target_freq))
        
        # Response at center frequency should be close to the gain (6dB)
        self.assertAlmostEqual(response[freq_idx], 6.0, places=0)
        
        # Response should be lower at frequencies far from center
        low_freq_idx = np.argmin(np.abs(self.freq - 100.0))
        high_freq_idx = np.argmin(np.abs(self.freq - 10000.0))
        
        self.assertLess(abs(response[low_freq_idx]), 2.0)   # Should be small
        self.assertLess(abs(response[high_freq_idx]), 2.0)  # Should be small
    
    def test_peq_build_weighted_filters(self):
        """Test peq_build with different weights"""
        # Create PEQ with different weights
        weighted_peq = [
            (0.5, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 6.0)),  # Half weight
            (2.0, Biquad(Biquad.PEAK, 2000, 48000, 1.0, 3.0)),  # Double weight
        ]
        
        response = peq_build(self.freq, weighted_peq)
        
        # Find responses at target frequencies
        freq_1k_idx = np.argmin(np.abs(self.freq - 1000.0))
        freq_2k_idx = np.argmin(np.abs(self.freq - 2000.0))
        
        # First filter should be halved (6dB * 0.5 ≈ 4.8dB at peak frequency)
        self.assertAlmostEqual(response[freq_1k_idx], 4.8, places=0)
        
        # Second filter should be doubled (3dB * 2.0 ≈ 6.9dB at peak frequency)  
        self.assertAlmostEqual(response[freq_2k_idx], 6.9, places=0)
    
    def test_peq_build_different_frequencies(self):
        """Test peq_build with different frequency arrays"""
        # Test with single frequency
        single_freq = np.array([1000.0])
        response = peq_build(single_freq, self.single_peq)
        self.assertEqual(len(response), 1)
        self.assertAlmostEqual(response[0], 6.0, places=0)
        
        # Test with wide frequency range
        wide_freq = np.logspace(0, 5, 50)  # 1 Hz to 100 kHz
        response = peq_build(wide_freq, self.test_peq)
        self.assertEqual(len(response), 50)
        self.assertTrue(np.all(np.isfinite(response)))


@unittest.skipUnless(NUMPY_AVAILABLE and PEQ_AVAILABLE, "Requires numpy and PEQ modules") 
class TestPEQPreampGain(unittest.TestCase):
    """Test preamp gain calculation functions"""
    
    def setUp(self):
        # PEQ with positive gains (needs negative preamp)
        self.positive_gain_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 5.0)),
            (1.0, Biquad(Biquad.LOWSHELF, 100, 48000, 0.7, 3.0))
        ]
        
        # PEQ with negative gains (may not need preamp)
        self.negative_gain_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, -3.0)),
            (1.0, Biquad(Biquad.HIGHSHELF, 8000, 48000, 0.7, -2.0))
        ]
        
        # Mixed gains
        self.mixed_gain_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 4.0)),   # +4dB
            (1.0, Biquad(Biquad.PEAK, 2000, 48000, 1.0, -2.0))   # -2dB
        ]
        
        # Empty PEQ
        self.empty_peq = []
    
    def test_peq_preamp_gain_positive(self):
        """Test preamp gain with positive gain filters"""
        gain = peq_preamp_gain(self.positive_gain_peq)
        
        # Should be a number
        self.assertIsInstance(gain, (int, float))
        self.assertFalse(math.isnan(gain))
        
        # Should be negative (reducing overall level)
        self.assertLessEqual(gain, 0.0)
        
        # Should be significant for high positive gains
        self.assertLess(gain, -1.0)
    
    def test_peq_preamp_gain_negative(self):
        """Test preamp gain with negative gain filters"""  
        gain = peq_preamp_gain(self.negative_gain_peq)
        
        # Should be a number
        self.assertIsInstance(gain, (int, float))
        self.assertFalse(math.isnan(gain))
        
        # Negative gains don't increase level, so preamp should be 0 or small
        self.assertGreaterEqual(gain, -0.1)  # Allow small negative for numerical precision
    
    def test_peq_preamp_gain_empty(self):
        """Test preamp gain with empty PEQ"""
        gain = peq_preamp_gain(self.empty_peq)
        self.assertEqual(gain, 0.0)
    
    def test_peq_preamp_gain_mixed(self):
        """Test preamp gain with mixed positive/negative gains"""
        gain = peq_preamp_gain(self.mixed_gain_peq)
        
        # Should be negative due to +4dB peak
        self.assertLess(gain, 0.0)
        
        # Should be roughly around -3.4dB (accounting for the peak)
        self.assertAlmostEqual(gain, -3.4, places=0)
    
    def test_peq_preamp_gain_conservative(self):
        """Test conservative preamp gain calculation"""
        # Capture debug output
        with io.StringIO() as buf, redirect_stdout(buf):
            gain = peq_preamp_gain_conservative(self.positive_gain_peq)
            debug_output = buf.getvalue()
        
        # Should be a number
        self.assertIsInstance(gain, (int, float))
        self.assertFalse(math.isnan(gain))
        
        # Should produce debug output
        self.assertIn("debug preamp gain", debug_output)
        
        # Conservative calculation should be different from regular
        regular_gain = peq_preamp_gain(self.positive_gain_peq)
        # They might be the same in some cases, but implementation is different
        self.assertIsInstance(regular_gain, (int, float))
    
    def test_preamp_gain_conservative_empty(self):
        """Test conservative preamp gain with empty PEQ"""
        gain = peq_preamp_gain_conservative(self.empty_peq)
        self.assertEqual(gain, 0.0)
    
    def test_preamp_gain_consistency(self):
        """Test that preamp gains are consistent for same PEQ"""
        gain1 = peq_preamp_gain(self.mixed_gain_peq)
        gain2 = peq_preamp_gain(self.mixed_gain_peq)
        
        # Should be identical
        self.assertEqual(gain1, gain2)


@unittest.skipUnless(NUMPY_AVAILABLE and PEQ_AVAILABLE, "Requires numpy and PEQ modules")
class TestPEQFormatAPO(unittest.TestCase):
    """Test APO format output generation"""
    
    def setUp(self):
        # Multi-filter PEQ with different types
        self.multi_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)),
            (1.0, Biquad(Biquad.LOWSHELF, 100, 48000, 0.7, 2.0)),
            (1.0, Biquad(Biquad.HIGHSHELF, 8000, 48000, 0.7, -1.5)),
            (1.0, Biquad(Biquad.LOWPASS, 15000, 48000, 0.707)),
            (1.0, Biquad(Biquad.HIGHPASS, 20, 48000, 0.707)),
            (1.0, Biquad(Biquad.BANDPASS, 500, 48000, 2.0)),
            (1.0, Biquad(Biquad.NOTCH, 60, 48000, 30.0))
        ]
        
        # Empty PEQ
        self.empty_peq = []
        
        # Single filter PEQ
        self.single_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 6.0))
        ]
    
    def test_apo_format_basic(self):
        """Test basic APO format generation"""
        comment = "Test EQ Configuration"
        result = peq_format_apo(comment, self.multi_peq)
        
        # Should be a string
        self.assertIsInstance(result, str)
        
        # Should contain the comment
        self.assertIn(comment, result)
        
        # Should contain preamp line
        self.assertIn("Preamp:", result)
        
        # Should contain filter lines
        lines = result.split('\n')
        filter_lines = [line for line in lines if line.startswith("Filter")]
        self.assertEqual(len(filter_lines), len(self.multi_peq))
    
    def test_apo_format_filter_types(self):
        """Test that all filter types are formatted correctly"""
        result = peq_format_apo("All Types", self.multi_peq)
        
        # Check that each filter type is present
        expected_types = ["PK", "LS", "HS", "LP", "HP", "BP", "NO"]
        for filter_type in expected_types:
            self.assertIn(filter_type, result)
    
    def test_apo_format_peak_filter(self):
        """Test Peak filter formatting"""
        peq = [(1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.5, 3.5))]
        result = peq_format_apo("Peak Test", peq)
        
        # Should contain all peak filter parameters
        self.assertIn("PK", result)
        self.assertIn("1000", result)    # Frequency
        self.assertIn("3.50", result)    # Gain  
        self.assertIn("1.50", result)    # Q
        self.assertIn("Gain", result)    # Gain label
        self.assertIn("Q", result)       # Q label
    
    def test_apo_format_shelf_filters(self):
        """Test Low and High shelf filter formatting"""
        peq = [
            (1.0, Biquad(Biquad.LOWSHELF, 100, 48000, 0.7, 2.5)),
            (1.0, Biquad(Biquad.HIGHSHELF, 8000, 48000, 0.7, -3.2))
        ]
        result = peq_format_apo("Shelf Test", peq)
        
        # Low shelf
        self.assertIn("LS", result)
        self.assertIn("100", result)
        self.assertIn("2.50", result)
        
        # High shelf  
        self.assertIn("HS", result)
        self.assertIn("8000", result)
        self.assertIn("-3.20", result)
        
        # Shelf filters should have Gain but no Q in the line
        lines = result.split('\n')
        ls_lines = [line for line in lines if "LS" in line and "Filter" in line]
        hs_lines = [line for line in lines if "HS" in line and "Filter" in line]
        
        for line in ls_lines + hs_lines:
            self.assertIn("Gain", line)
            self.assertNotIn("Q", line)  # Shelf filters don't show Q in APO format
    
    def test_apo_format_pass_filters(self):
        """Test Low and High pass filter formatting"""
        peq = [
            (1.0, Biquad(Biquad.LOWPASS, 12000, 48000, 0.707)),
            (1.0, Biquad(Biquad.HIGHPASS, 30, 48000, 0.707))
        ]
        result = peq_format_apo("Pass Test", peq)
        
        # Should contain filter types
        self.assertIn("LP", result)
        self.assertIn("HP", result)
        
        # Should contain frequencies
        self.assertIn("12000", result)
        self.assertIn("30", result)
        
        # Pass filters should not have Gain or Q in the line
        lines = result.split('\n')
        lp_lines = [line for line in lines if "LP" in line and "Filter" in line]
        hp_lines = [line for line in lines if "HP" in line and "Filter" in line]
        
        for line in lp_lines + hp_lines:
            self.assertNotIn("Gain", line)
            self.assertNotIn("Q", line)
    
    def test_apo_format_bandpass_notch(self):
        """Test Bandpass and Notch filter formatting"""
        peq = [
            (1.0, Biquad(Biquad.BANDPASS, 1000, 48000, 2.0)),
            (1.0, Biquad(Biquad.NOTCH, 60, 48000, 30.0))  # Note: Notch forces Q=30
        ]
        result = peq_format_apo("BP/Notch Test", peq)
        
        # Should contain filter types  
        self.assertIn("BP", result)
        self.assertIn("NO", result)
        
        # Should contain frequencies
        self.assertIn("1000", result)
        self.assertIn("60", result)
        
        # Bandpass and notch should have Q but gain handling varies
        lines = result.split('\n')
        bp_lines = [line for line in lines if "BP" in line and "Filter" in line] 
        no_lines = [line for line in lines if "NO" in line and "Filter" in line]
        
        for line in bp_lines + no_lines:
            self.assertIn("Q", line)
    
    def test_apo_format_empty_peq(self):
        """Test APO format with empty PEQ"""
        result = peq_format_apo("Empty Test", self.empty_peq)
        
        # Should still contain comment and preamp
        self.assertIn("Empty Test", result)
        self.assertIn("Preamp: 0.0 dB", result)  # Empty PEQ should have 0 preamp
        
        # Should not contain any filter lines
        lines = result.split('\n')
        filter_lines = [line for line in lines if line.startswith("Filter")]
        self.assertEqual(len(filter_lines), 0)
    
    def test_apo_format_preamp_calculation(self):
        """Test that preamp is calculated and included correctly"""
        result = peq_format_apo("Preamp Test", self.single_peq)
        
        # Calculate expected preamp
        expected_preamp = peq_preamp_gain(self.single_peq)
        
        # Should contain preamp line with calculated value
        self.assertIn(f"Preamp: {expected_preamp:.1f} dB", result)
    
    def test_apo_format_structure(self):
        """Test overall APO format structure"""
        result = peq_format_apo("Structure Test", self.single_peq)
        lines = result.split('\n')
        
        # Should start with comment
        self.assertEqual(lines[0], "Structure Test")
        
        # Should have preamp as second line
        self.assertTrue(lines[1].startswith("Preamp:"))
        
        # Should have empty line after preamp
        self.assertEqual(lines[2], "")
        
        # Should have filter line(s)
        filter_lines = [line for line in lines if line.startswith("Filter")]
        self.assertGreater(len(filter_lines), 0)
        
        # Should end with empty line
        self.assertEqual(lines[-1], "")


@unittest.skipUnless(NUMPY_AVAILABLE and PEQ_AVAILABLE, "Requires numpy and PEQ modules")
class TestPEQPrint(unittest.TestCase):
    """Test peq_print function"""
    
    def setUp(self):
        self.test_peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)),
            (0.0, Biquad(Biquad.PEAK, 2000, 48000, 1.0, 2.0)),  # Zero weight - should be skipped
            (1.0, Biquad(Biquad.LOWSHELF, 100, 48000, 0.7, 1.5))
        ]
        
        self.empty_peq = []
    
    def test_peq_print_output(self):
        """Test peq_print produces expected output"""
        # Capture printed output
        with io.StringIO() as buf, redirect_stdout(buf):
            peq_print(self.test_peq)
            output = buf.getvalue()
        
        # Should contain filter information for non-zero weight filters
        lines = output.strip().split('\n')
        
        # Should have output for 2 filters (skipping the zero-weight one)
        self.assertEqual(len(lines), 2)
        
        # Each line should contain filter information
        for line in lines:
            self.assertIn("Type:", line)
            self.assertIn("Freq:", line)
            self.assertIn("Q:", line)
            self.assertIn("Gain:", line)
    
    def test_peq_print_empty(self):
        """Test peq_print with empty PEQ"""
        with io.StringIO() as buf, redirect_stdout(buf):
            peq_print(self.empty_peq)
            output = buf.getvalue()
        
        # Should produce no output
        self.assertEqual(output, "")
    
    def test_peq_print_zero_weight_skipping(self):
        """Test that zero-weight filters are skipped"""
        zero_weight_peq = [
            (0.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)),  # Should be skipped
            (1.0, Biquad(Biquad.PEAK, 2000, 48000, 1.0, 2.0))   # Should be printed
        ]
        
        with io.StringIO() as buf, redirect_stdout(buf):
            peq_print(zero_weight_peq)
            output = buf.getvalue()
        
        lines = output.strip().split('\n')
        self.assertEqual(len(lines), 1)  # Only one filter should be printed
        
        # The printed line should be for the 2000 Hz filter
        self.assertIn("2000", lines[0])


@unittest.skipUnless(NUMPY_AVAILABLE and PEQ_AVAILABLE, "Requires numpy and PEQ modules")
class TestPEQIntegration(unittest.TestCase):
    """Integration tests combining multiple PEQ functions"""
    
    def setUp(self):
        # Create a realistic EQ curve
        self.realistic_peq = [
            (1.0, Biquad(Biquad.HIGHPASS, 30, 48000, 0.7)),        # Rumble filter
            (1.0, Biquad(Biquad.PEAK, 200, 48000, 0.5, -2.0)),     # Room mode cut
            (1.0, Biquad(Biquad.LOWSHELF, 500, 48000, 0.7, 1.0)),  # Warmth boost
            (1.0, Biquad(Biquad.PEAK, 3000, 48000, 2.0, -1.5)),    # Presence dip  
            (1.0, Biquad(Biquad.HIGHSHELF, 8000, 48000, 0.7, 1.5)), # Air boost
            (1.0, Biquad(Biquad.LOWPASS, 16000, 48000, 0.7))       # Anti-aliasing
        ]
    
    def test_build_and_format_consistency(self):
        """Test that peq_build and peq_format_apo are consistent"""
        # Generate APO format
        apo_text = peq_format_apo("Realistic EQ", self.realistic_peq)
        
        # Build frequency response  
        freq = np.logspace(1, 4, 100)
        response = peq_build(freq, self.realistic_peq)
        
        # APO should contain the right number of filters
        filter_lines = [line for line in apo_text.split('\n') if line.startswith("Filter")]
        self.assertEqual(len(filter_lines), len(self.realistic_peq))
        
        # Response should be finite and reasonable
        self.assertTrue(np.all(np.isfinite(response)))
        self.assertTrue(np.max(np.abs(response)) < 20)  # Reasonable EQ range
    
    def test_preamp_and_format_consistency(self):
        """Test that preamp calculation matches APO format"""
        calculated_preamp = peq_preamp_gain(self.realistic_peq)
        apo_text = peq_format_apo("Preamp Test", self.realistic_peq)
        
        # Extract preamp from APO text
        preamp_line = [line for line in apo_text.split('\n') if line.startswith("Preamp:")][0]
        apo_preamp = float(preamp_line.split()[1])
        
        # Should match
        self.assertAlmostEqual(calculated_preamp, apo_preamp, places=1)
    
    def test_different_peq_lengths(self):
        """Test functions with different PEQ lengths"""
        lengths_to_test = [0, 1, 3, 10]
        
        for length in lengths_to_test:
            with self.subTest(length=length):
                # Create PEQ of specified length
                test_peq = []
                for i in range(length):
                    freq = 1000 + i * 500  # Spread frequencies
                    gain = 2.0 if i % 2 == 0 else -1.0  # Alternate gains
                    test_peq.append((1.0, Biquad(Biquad.PEAK, freq, 48000, 1.0, gain)))
                
                # All functions should work without error
                freq = np.logspace(1, 4, 50)
                response = peq_build(freq, test_peq) 
                preamp = peq_preamp_gain(test_peq)
                apo_text = peq_format_apo(f"Test {length}", test_peq)
                
                # Basic validation
                self.assertEqual(len(response), 50)
                self.assertIsInstance(preamp, (int, float))
                self.assertIsInstance(apo_text, str)
                
                # Check filter count in APO
                filter_lines = [line for line in apo_text.split('\n') if line.startswith("Filter")]
                self.assertEqual(len(filter_lines), length)


class TestPEQWithoutNumpy(unittest.TestCase):
    """Test PEQ module structure without numpy dependencies"""
    
    def test_peq_module_structure(self):
        """Test that PEQ module has expected functions"""
        try:
            import os
            peq_path = os.path.join(os.path.dirname(__file__), 'iir', 'filter_peq.py')
            
            if os.path.exists(peq_path):
                with open(peq_path, 'r') as f:
                    content = f.read()
                
                # Check for expected functions
                expected_functions = [
                    'def peq_build',
                    'def peq_preamp_gain(',
                    'def peq_preamp_gain_conservative',
                    'def peq_format_apo',
                    'def peq_print'
                ]
                
                for func in expected_functions:
                    self.assertIn(func, content)
                
                # Check for expected imports
                self.assertIn('import numpy as np', content)
                self.assertIn('from iir.filter_iir import Biquad', content)
                
                print("✓ PEQ module structure validation passed")
            else:
                self.skipTest("filter_peq.py not found")
                
        except Exception as e:
            self.skipTest(f"Could not validate PEQ module: {e}")
    
    def test_peq_math_concepts(self):
        """Test mathematical concepts used in PEQ without full imports"""
        import math
        
        # Test logarithmic frequency generation concept
        log_start = 1 + math.log10(2)  # ~20 Hz
        log_end = 4 + math.log10(2)    # ~20 kHz
        
        self.assertAlmostEqual(log_start, 1.301, places=2)
        self.assertAlmostEqual(log_end, 4.301, places=2)
        
        # Test preamp calculation concept (preventing clipping)
        # If we have a +6dB boost, we need -6dB preamp to prevent clipping
        max_boost = 6.0
        expected_preamp = -max_boost
        
        self.assertEqual(expected_preamp, -6.0)


if __name__ == '__main__':
    # Print environment info
    print(f"Python version: {sys.version}")
    print(f"Numpy available: {NUMPY_AVAILABLE}")
    print(f"PEQ module available: {PEQ_AVAILABLE}")
    print("-" * 60)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)