#!/usr/bin/env python3
"""Comprehensive tests for the iir module"""

import unittest
import math
import sys
import os

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
    from iir.filter_iir import Biquad, bw2q, q2bw
    if NUMPY_AVAILABLE:
        from iir.filter_peq import peq_build, peq_preamp_gain, peq_preamp_gain_conservative, peq_format_apo
    IIR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import iir modules: {e}")
    IIR_AVAILABLE = False


class TestBiquadMath(unittest.TestCase):
    """Test bandwidth/Q conversion functions"""
    
    def setUp(self):
        if not IIR_AVAILABLE:
            self.skipTest("IIR module not available")
    
    def test_q2bw_conversion(self):
        """Test Q to bandwidth conversion"""
        # Test known conversions
        self.assertAlmostEqual(q2bw(1.0), 1.3885, places=3)
        self.assertAlmostEqual(q2bw(0.707), 1.9002, places=3)  # 1/sqrt(2)
        self.assertAlmostEqual(q2bw(2.0), 0.7140, places=3)
    
    def test_bw2q_conversion(self):
        """Test bandwidth to Q conversion"""
        # Test known conversions
        self.assertAlmostEqual(bw2q(1.0), 1.4142, places=3)  # sqrt(2)
        self.assertAlmostEqual(bw2q(0.5), 2.8708, places=3)
        self.assertAlmostEqual(bw2q(2.0), 0.6667, places=3)  # 2/3
    
    def test_q_bw_roundtrip(self):
        """Test that Q->BW->Q conversion is consistent"""
        test_qs = [0.5, 0.707, 1.0, 1.5, 2.0, 5.0, 10.0]
        for q in test_qs:
            with self.subTest(q=q):
                bw = q2bw(q)
                q_back = bw2q(bw)
                self.assertAlmostEqual(q, q_back, places=6)
    
    def test_bw_q_roundtrip(self):
        """Test that BW->Q->BW conversion is consistent"""
        test_bws = [0.1, 0.5, 1.0, 1.5, 2.0, 3.0]
        for bw in test_bws:
            with self.subTest(bw=bw):
                q = bw2q(bw)
                bw_back = q2bw(q)
                self.assertAlmostEqual(bw, bw_back, places=6)


class TestBiquadFilters(unittest.TestCase):
    """Test Biquad filter implementations"""
    
    def setUp(self):
        if not IIR_AVAILABLE:
            self.skipTest("IIR module not available")
        
        # Standard test parameters
        self.freq = 1000.0
        self.srate = 48000
        self.q = 0.707
        self.gain = 3.0
    
    def test_filter_types_exist(self):
        """Test that all filter types are defined"""
        expected_types = [
            Biquad.LOWPASS, Biquad.HIGHPASS, Biquad.BANDPASS,
            Biquad.PEAK, Biquad.NOTCH, Biquad.LOWSHELF, Biquad.HIGHSHELF
        ]
        for filter_type in expected_types:
            with self.subTest(filter_type=filter_type):
                self.assertIsInstance(filter_type, int)
    
    def test_type2name_mapping(self):
        """Test filter type to name mapping"""
        expected_mappings = {
            Biquad.LOWPASS: ["Lowpass", "LP"],
            Biquad.HIGHPASS: ["Highpass", "HP"], 
            Biquad.BANDPASS: ["Bandpath", "BP"],
            Biquad.PEAK: ["Peak", "PK"],
            Biquad.NOTCH: ["Notch", "NO"],
            Biquad.LOWSHELF: ["Lowshelf", "LS"],
            Biquad.HIGHSHELF: ["Highshelf", "HS"]
        }
        
        for filter_type, names in expected_mappings.items():
            with self.subTest(filter_type=filter_type):
                self.assertEqual(Biquad.type2name[filter_type], names)
    
    def test_peak_filter_creation(self):
        """Test peak filter creation"""
        filter_obj = Biquad(Biquad.PEAK, self.freq, self.srate, self.q, self.gain)
        self.assertEqual(filter_obj.typ, Biquad.PEAK)
        self.assertEqual(filter_obj.freq, self.freq)
        self.assertEqual(filter_obj.srate, self.srate)
        self.assertEqual(filter_obj.q, self.q)
        self.assertEqual(filter_obj.db_gain, self.gain)
    
    def test_lowpass_filter_creation(self):
        """Test low pass filter creation"""
        filter_obj = Biquad(Biquad.LOWPASS, self.freq, self.srate, self.q)
        self.assertEqual(filter_obj.typ, Biquad.LOWPASS)
        self.assertEqual(filter_obj.db_gain, 0.0)  # No gain for LP
    
    def test_highpass_filter_creation(self):
        """Test high pass filter creation"""
        filter_obj = Biquad(Biquad.HIGHPASS, self.freq, self.srate, self.q)
        self.assertEqual(filter_obj.typ, Biquad.HIGHPASS)
        self.assertEqual(filter_obj.db_gain, 0.0)  # No gain for HP
    
    def test_lowshelf_filter_creation(self):
        """Test low shelf filter creation"""
        filter_obj = Biquad(Biquad.LOWSHELF, self.freq, self.srate, self.q, self.gain)
        self.assertEqual(filter_obj.typ, Biquad.LOWSHELF)
        self.assertEqual(filter_obj.db_gain, self.gain)
    
    def test_highshelf_filter_creation(self):
        """Test high shelf filter creation"""
        filter_obj = Biquad(Biquad.HIGHSHELF, self.freq, self.srate, self.q, self.gain)
        self.assertEqual(filter_obj.typ, Biquad.HIGHSHELF)
        self.assertEqual(filter_obj.db_gain, self.gain)
    
    def test_bandpass_filter_creation(self):
        """Test band pass filter creation"""
        filter_obj = Biquad(Biquad.BANDPASS, self.freq, self.srate, self.q)
        self.assertEqual(filter_obj.typ, Biquad.BANDPASS)
    
    def test_notch_filter_creation(self):
        """Test notch filter creation"""
        filter_obj = Biquad(Biquad.NOTCH, self.freq, self.srate, self.q)
        self.assertEqual(filter_obj.typ, Biquad.NOTCH)
        self.assertEqual(filter_obj.q, 30.0)  # Notch forces Q to 30
    
    def test_invalid_filter_type(self):
        """Test that invalid filter types raise an error"""
        with self.assertRaises(AssertionError):
            Biquad(999, self.freq, self.srate, self.q)  # Invalid type
    
    def test_zero_q_handling(self):
        """Test that zero Q values are handled correctly"""
        # For bandpass/highpass/lowpass, Q=0 should become 1/sqrt(2)
        filter_obj = Biquad(Biquad.BANDPASS, self.freq, self.srate, 0.0)
        expected_q = 1.0 / math.sqrt(2.0)
        self.assertAlmostEqual(filter_obj.q, expected_q, places=6)
        
        # For shelving filters, Q=0 should become bw2q(0.9)
        shelf_filter = Biquad(Biquad.LOWSHELF, self.freq, self.srate, 0.0, self.gain)
        expected_shelf_q = bw2q(0.9)
        self.assertAlmostEqual(shelf_filter.q, expected_shelf_q, places=6)
    
    def test_coefficients_generation(self):
        """Test that filter coefficients are generated"""
        filter_obj = Biquad(Biquad.PEAK, self.freq, self.srate, self.q, self.gain)
        a1, a2, b0, b1, b2 = filter_obj.constants()
        
        # Coefficients should be real numbers
        for coef in [a1, a2, b0, b1, b2]:
            self.assertIsInstance(coef, (int, float))
            self.assertFalse(math.isnan(coef))
    
    def test_filter_response(self):
        """Test filter frequency response"""
        filter_obj = Biquad(Biquad.PEAK, self.freq, self.srate, self.q, self.gain)
        
        # Test response at filter frequency (should be close to gain)
        response_at_fc = filter_obj.log_result(self.freq)
        self.assertAlmostEqual(response_at_fc, self.gain, places=1)
        
        # Test response at much lower frequency (should be close to 0)
        response_low = filter_obj.log_result(100.0)
        self.assertLess(abs(response_low), 1.0)  # Should be small
        
        # Test response at much higher frequency (should be close to 0)
        response_high = filter_obj.log_result(10000.0)
        self.assertLess(abs(response_high), 1.0)  # Should be small
    
    def test_type2str_method(self):
        """Test type to string conversion"""
        filter_obj = Biquad(Biquad.PEAK, self.freq, self.srate, self.q, self.gain)
        self.assertEqual(filter_obj.type2str(), "PK")
        
        lp_filter = Biquad(Biquad.LOWPASS, self.freq, self.srate, self.q)
        self.assertEqual(lp_filter.type2str(), "LP")
    
    def test_str_representation(self):
        """Test string representation of filter"""
        filter_obj = Biquad(Biquad.PEAK, self.freq, self.srate, self.q, self.gain)
        str_repr = str(filter_obj)
        
        # Should contain key information
        self.assertIn("PK", str_repr)
        self.assertIn("1000", str_repr)  # frequency
        self.assertIn("3.0", str_repr)   # gain


@unittest.skipUnless(NUMPY_AVAILABLE and IIR_AVAILABLE, "Requires numpy and iir modules")
class TestPEQFunctions(unittest.TestCase):
    """Test PEQ (Parametric EQ) functions"""
    
    def setUp(self):
        # Create test PEQ with a few filters
        self.peq = [
            (1.0, Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)),
            (1.0, Biquad(Biquad.LOWSHELF, 100, 48000, 0.7, 2.0)),
            (1.0, Biquad(Biquad.HIGHSHELF, 10000, 48000, 0.7, -2.0))
        ]
        
        # Test frequencies
        self.freq = np.logspace(1, 4, 100)  # 10 Hz to 10 kHz
    
    def test_peq_build(self):
        """Test PEQ frequency response building"""
        response = peq_build(self.freq, self.peq)
        
        # Should return an array
        self.assertIsInstance(response, np.ndarray)
        self.assertEqual(len(response), len(self.freq))
        
        # Response should be finite numbers
        self.assertTrue(np.all(np.isfinite(response)))
    
    def test_peq_build_empty(self):
        """Test PEQ build with empty filter list"""
        empty_peq = []
        response = peq_build(self.freq, empty_peq)
        
        # Should return array of zeros
        np.testing.assert_array_almost_equal(response, np.zeros_like(self.freq))
    
    def test_peq_preamp_gain(self):
        """Test preamp gain calculation"""
        gain = peq_preamp_gain(self.peq)
        
        # Should be a number
        self.assertIsInstance(gain, (int, float))
        self.assertFalse(math.isnan(gain))
        
        # For filters with positive gains, preamp should be negative
        self.assertLessEqual(gain, 0.0)
    
    def test_peq_preamp_gain_empty(self):
        """Test preamp gain with empty PEQ"""
        empty_peq = []
        gain = peq_preamp_gain(empty_peq)
        self.assertEqual(gain, 0.0)
    
    def test_peq_preamp_gain_conservative(self):
        """Test conservative preamp gain calculation"""
        gain = peq_preamp_gain_conservative(self.peq)
        
        # Should be a number
        self.assertIsInstance(gain, (int, float))
        self.assertFalse(math.isnan(gain))
    
    def test_peq_format_apo(self):
        """Test APO format output"""
        comment = "Test EQ"
        apo_text = peq_format_apo(comment, self.peq)
        
        # Should be a string
        self.assertIsInstance(apo_text, str)
        
        # Should contain comment
        self.assertIn(comment, apo_text)
        
        # Should contain preamp line
        self.assertIn("Preamp:", apo_text)
        
        # Should contain filter lines
        self.assertIn("Filter", apo_text)
        
        # Should contain expected filter types
        self.assertIn("PK", apo_text)   # Peak
        self.assertIn("LS", apo_text)   # Low shelf
        self.assertIn("HS", apo_text)   # High shelf
    
    def test_peq_format_apo_different_types(self):
        """Test APO format with different filter types"""
        # Test with lowpass and highpass filters
        lp_hp_peq = [
            (1.0, Biquad(Biquad.LOWPASS, 5000, 48000, 0.7)),
            (1.0, Biquad(Biquad.HIGHPASS, 100, 48000, 0.7)),
        ]
        
        apo_text = peq_format_apo("LP/HP Test", lp_hp_peq)
        
        # Should contain LP and HP
        self.assertIn("LP", apo_text)
        self.assertIn("HP", apo_text)
        
        # LP/HP lines should not contain gain (only Fc)
        lines = apo_text.split('\n')
        lp_lines = [line for line in lines if 'LP' in line]
        hp_lines = [line for line in lines if 'HP' in line]
        
        for line in lp_lines + hp_lines:
            if 'Filter' in line:
                self.assertNotIn('Gain', line)


@unittest.skipUnless(NUMPY_AVAILABLE and IIR_AVAILABLE, "Requires numpy and iir modules")
class TestBiquadNumpyMethods(unittest.TestCase):
    """Test numpy-based methods in Biquad class"""
    
    def test_np_log_result(self):
        """Test numpy-based frequency response calculation"""
        filter_obj = Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)
        
        # Test with numpy array of frequencies
        freqs = np.array([100, 500, 1000, 2000, 5000])
        response = filter_obj.np_log_result(freqs)
        
        # Should return numpy array
        self.assertIsInstance(response, np.ndarray)
        self.assertEqual(len(response), len(freqs))
        
        # Should be finite numbers
        self.assertTrue(np.all(np.isfinite(response)))
        
        # Response at center frequency should be close to gain
        center_response = filter_obj.np_log_result(np.array([1000.0]))
        self.assertAlmostEqual(center_response[0], 3.0, places=1)
    
    def test_np_vs_single_result(self):
        """Test that numpy and single-value results are consistent"""
        filter_obj = Biquad(Biquad.PEAK, 1000, 48000, 1.0, 3.0)
        
        test_freqs = [100, 500, 1000, 2000, 5000]
        
        # Get single results
        single_results = [filter_obj.log_result(f) for f in test_freqs]
        
        # Get numpy results  
        np_results = filter_obj.np_log_result(np.array(test_freqs))
        
        # Should be very close
        for i, (single, numpy_val) in enumerate(zip(single_results, np_results)):
            with self.subTest(freq=test_freqs[i]):
                self.assertAlmostEqual(single, numpy_val, places=6)


class TestFilterEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        if not IIR_AVAILABLE:
            self.skipTest("IIR module not available")
    
    def test_very_low_frequency(self):
        """Test filter with very low frequency"""
        filter_obj = Biquad(Biquad.PEAK, 1.0, 48000, 1.0, 3.0)
        response = filter_obj.log_result(1.0)
        self.assertIsInstance(response, (int, float))
        self.assertFalse(math.isnan(response))
    
    def test_very_high_frequency(self):
        """Test filter with frequency near Nyquist"""
        filter_obj = Biquad(Biquad.PEAK, 20000, 48000, 1.0, 3.0)
        response = filter_obj.log_result(20000)
        self.assertIsInstance(response, (int, float))
        self.assertFalse(math.isnan(response))
    
    def test_very_high_q(self):
        """Test filter with very high Q"""
        filter_obj = Biquad(Biquad.PEAK, 1000, 48000, 100.0, 3.0)
        response = filter_obj.log_result(1000)
        self.assertIsInstance(response, (int, float))
        self.assertFalse(math.isnan(response))
    
    def test_very_low_q(self):
        """Test filter with very low Q"""
        filter_obj = Biquad(Biquad.PEAK, 1000, 48000, 0.1, 3.0)
        response = filter_obj.log_result(1000)
        self.assertIsInstance(response, (int, float))
        self.assertFalse(math.isnan(response))
    
    def test_zero_gain(self):
        """Test filter with zero gain"""
        filter_obj = Biquad(Biquad.PEAK, 1000, 48000, 1.0, 0.0)
        response = filter_obj.log_result(1000)
        self.assertAlmostEqual(response, 0.0, places=2)
    
    def test_negative_gain(self):
        """Test filter with negative gain"""
        filter_obj = Biquad(Biquad.PEAK, 1000, 48000, 1.0, -6.0)
        response = filter_obj.log_result(1000)
        self.assertAlmostEqual(response, -6.0, places=1)


if __name__ == '__main__':
    # Print environment info
    print(f"Python version: {sys.version}")
    print(f"Numpy available: {NUMPY_AVAILABLE}")
    print(f"IIR module available: {IIR_AVAILABLE}")
    print("-" * 50)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)