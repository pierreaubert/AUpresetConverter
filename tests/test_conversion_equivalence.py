#!/usr/bin/env python3
"""Test conversion equivalence between different EQ formats

This module tests that different representations of the same EQ curve 
produce identical output when converted to a common format (RME TotalMix room EQ).
"""

import unittest
import os
import sys
import difflib
from xml.etree import ElementTree as ET

# Add parent directory to path to import converter modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from converter import file2iir, iir2rme_totalmix_room
    CONVERTER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import converter modules: {e}")
    CONVERTER_AVAILABLE = False


class TestConversionEquivalence(unittest.TestCase):
    """Test that different EQ formats produce equivalent output when converted
    
    This test class verifies that the two Sennheiser HD 650 preset files:
    - 'Sennheiser HD 650 -- 9 iirs.aupreset' (9 IIR filters)
    - 'Sennheiser HD 650 ParametricEq.aupreset' (10 parametric EQ filters)
    
    Produce the same RME TotalMix room EQ output when converted, confirming
    that both representations describe the same frequency response curve.
    """
    
    def setUp(self):
        """Set up test fixtures with file paths and verify availability"""
        if not CONVERTER_AVAILABLE:
            self.skipTest("Converter module not available")
        
        # Define paths to the preset files (using text versions from examples_rews)
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.preset_9_iirs = os.path.join(
            self.base_dir, 
            "examples_rews", 
            "Sennheiser HD 650 -- 9 iirs.txt"
        )
        self.preset_parametric = os.path.join(
            self.base_dir, 
            "examples_rews", 
            "Sennheiser HD 650 ParametricEq.txt"
        )
        
        # Verify both files exist
        self.assertTrue(
            os.path.exists(self.preset_9_iirs), 
            f"Missing preset file: {self.preset_9_iirs}"
        )
        self.assertTrue(
            os.path.exists(self.preset_parametric), 
            f"Missing preset file: {self.preset_parametric}"
        )
    
    def _parse_xml_structure(self, xml_content):
        """Parse XML content and extract structured data for comparison
        
        Args:
            xml_content (str): XML content as string
            
        Returns:
            dict: Structured representation of the XML for comparison
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Extract structured data from the XML
            structure = {
                'tag': root.tag,
                'children': {}
            }
            
            # Parse Room EQ sections
            for child in root:
                if 'Room EQ' in child.tag:
                    params = {}
                    params_elem = child.find('Params')
                    if params_elem is not None:
                        for val in params_elem.findall('val'):
                            param_name = val.get('e', '')
                            param_value = val.get('v', '')
                            # Clean up the parameter value (remove comma)
                            param_value = param_value.rstrip(',')
                            params[param_name] = param_value
                    structure['children'][child.tag] = params
            
            return structure
        except ET.ParseError as e:
            return {'error': f'XML parsing failed: {e}'}
    
    def _compare_xml_output(self, xml1, xml2):
        """Compare two XML strings and provide detailed difference report
        
        Args:
            xml1 (str): First XML string
            xml2 (str): Second XML string
            
        Returns:
            tuple: (are_equal: bool, difference_report: str)
        """
        # Quick string comparison first
        if xml1 == xml2:
            return True, "XML outputs are identical"
        
        # Parse both XML structures
        struct1 = self._parse_xml_structure(xml1)
        struct2 = self._parse_xml_structure(xml2)
        
        if struct1 == struct2:
            return True, "XML structures are equivalent (minor formatting differences only)"
        
        # Generate detailed difference report
        lines1 = xml1.splitlines()
        lines2 = xml2.splitlines()
        
        diff = list(difflib.unified_diff(
            lines1, lines2, 
            fromfile='9 IIRs preset', 
            tofile='ParametricEq preset',
            lineterm=''
        ))
        
        difference_report = "\n".join([
            "XML structures differ:",
            f"Structure 1: {struct1}",
            f"Structure 2: {struct2}",
            "\nLine-by-line differences:",
            *diff
        ])
        
        return False, difference_report
    
    def test_sennheiser_hd650_conversion_equivalence(self):
        """Test that both HD 650 presets produce identical RME room EQ output
        
        This is the main test that verifies the two different representations 
        of the Sennheiser HD 650 EQ curve produce the same RME TotalMix room EQ
        configuration when converted.
        """
        # Load first preset (9 IIRs)
        success1, iir1 = file2iir(self.preset_9_iirs)
        self.assertTrue(success1, f"Failed to parse {self.preset_9_iirs}")
        self.assertGreater(len(iir1), 0, "9 IIRs preset produced empty filter list")
        
        # Load second preset (ParametricEq)
        success2, iir2 = file2iir(self.preset_parametric)
        self.assertTrue(success2, f"Failed to parse {self.preset_parametric}")
        self.assertGreater(len(iir2), 0, "ParametricEq preset produced empty filter list")
        
        # Convert both to RME TotalMix room EQ format
        success_rme1, rme_xml1 = iir2rme_totalmix_room(iir1, [])  # Mono (left channel only)
        self.assertTrue(success_rme1, "Failed to convert 9 IIRs preset to RME format")
        
        success_rme2, rme_xml2 = iir2rme_totalmix_room(iir2, [])  # Mono (left channel only)
        self.assertTrue(success_rme2, "Failed to convert ParametricEq preset to RME format")
        
        # Compare the outputs using detailed comparison
        are_equal, difference_report = self._compare_xml_output(rme_xml1, rme_xml2)
        
        # Log filter information for debugging
        print(f"\n9 IIRs preset loaded {len(iir1)} filters")
        for i, filt in enumerate(iir1):
            print(f"  Filter {i+1}: {filt}")
        
        print(f"\nParametricEq preset loaded {len(iir2)} filters")
        for i, filt in enumerate(iir2):
            print(f"  Filter {i+1}: {filt}")
        
        if not are_equal:
            print(f"\nXML Differences:\n{difference_report}")
        
        # Main assertion - the converted outputs should be equivalent
        self.assertTrue(
            are_equal, 
            f"RME TotalMix room EQ outputs differ between the two HD 650 presets.\n"
            f"This suggests the presets may not represent the same EQ curve.\n\n"
            f"{difference_report}"
        )
    
    def test_filter_count_information(self):
        """Test to log information about filter counts and types
        
        This test provides debugging information about what filters
        are present in each preset to help understand any differences.
        """
        # Load both presets
        success1, iir1 = file2iir(self.preset_9_iirs)
        success2, iir2 = file2iir(self.preset_parametric)
        
        self.assertTrue(success1 and success2, "Failed to load one or both presets")
        
        # Analyze filter types and parameters
        def analyze_filters(iir_list, name):
            print(f"\n=== {name} ===")
            print(f"Total filters: {len(iir_list)}")
            
            filter_types = {}
            for filt in iir_list:
                filt_type = filt.get('type', 'Unknown')
                if filt_type not in filter_types:
                    filter_types[filt_type] = 0
                filter_types[filt_type] += 1
            
            print("Filter type breakdown:")
            for filt_type, count in sorted(filter_types.items()):
                print(f"  {filt_type}: {count}")
            
            print("Filter details:")
            for i, filt in enumerate(iir_list):
                freq = filt.get('freq', 'N/A')
                gain = filt.get('gain', 'N/A')
                filt_type = filt.get('type', 'N/A')
                q = filt.get('q', 'N/A')
                width = filt.get('width', 'N/A')
                print(f"  {i+1}: {filt_type} @ {freq}Hz, {gain}dB, Q={q}, Width={width}")
        
        analyze_filters(iir1, "9 IIRs Preset")
        analyze_filters(iir2, "ParametricEq Preset")
    
    def test_missing_file_handling(self):
        """Test appropriate error handling for missing preset files"""
        nonexistent_file = os.path.join(self.base_dir, "nonexistent_preset.txt")
        
        # file2iir raises FileNotFoundError for missing files
        with self.assertRaises(FileNotFoundError):
            file2iir(nonexistent_file)
    
    def test_empty_filter_conversion(self):
        """Test RME conversion behavior with empty filter lists"""
        # Test with empty filter list
        success, rme_xml = iir2rme_totalmix_room([], [])
        self.assertTrue(success, "RME conversion should succeed with empty filter list")
        self.assertIn("<Preset>", rme_xml, "RME output should still contain valid XML structure")
        self.assertIn("</Preset>", rme_xml, "RME output should be properly closed")


if __name__ == '__main__':
    # Print environment info
    print(f"Python version: {sys.version}")
    print(f"Converter module available: {CONVERTER_AVAILABLE}")
    print("-" * 60)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)