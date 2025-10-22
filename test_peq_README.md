# PEQ Module Tests

This file contains comprehensive tests for the `iir/filter_peq.py` module, which handles Parametric EQ operations in AUpresetConverter.

## Test File: `test_peq.py`

### Test Classes

#### `TestPEQBuild` - Frequency Response Calculation
Tests the `peq_build()` function that calculates frequency response for a set of filters:

- **Basic Functionality**: Validates numpy array output and finite values
- **Empty PEQ**: Ensures empty filter lists return zero response
- **Single Filter**: Tests isolated filter response at center frequency
- **Weighted Filters**: Verifies filter weight multiplication (0.5x, 2.0x, etc.)
- **Different Frequency Arrays**: Tests various frequency ranges and resolutions

#### `TestPEQPreampGain` - Preamp Gain Calculation
Tests preamp gain calculation functions that prevent digital clipping:

- **Positive Gains**: Verifies negative preamp for boost filters
- **Negative Gains**: Confirms minimal preamp for cut-only filters
- **Mixed Gains**: Tests realistic EQ with both boosts and cuts
- **Conservative vs Standard**: Compares two calculation methods
- **Empty PEQ**: Ensures 0.0 preamp for empty filter lists
- **Consistency**: Validates repeated calculations return same results

#### `TestPEQFormatAPO` - APO Format Output
Tests `peq_format_apo()` function that generates EqualizerAPO-compatible text:

- **Basic Structure**: Validates comment, preamp, and filter lines
- **All Filter Types**: Tests PK, LS, HS, LP, HP, BP, NO formatting
- **Parameter Formatting**: Ensures correct frequency, gain, Q values
- **Filter-Specific Rules**: 
  - Peak/Notch/Bandpass: Include frequency, gain, Q
  - Shelf filters: Include frequency, gain (no Q shown)
  - Pass filters: Include frequency only (no gain/Q shown)
- **Empty PEQ**: Handles edge case with no filters
- **Preamp Integration**: Verifies calculated preamp appears in output

#### `TestPEQPrint` - Debug Output
Tests `peq_print()` function for debugging filter information:

- **Output Content**: Verifies filter details (Type, Freq, Q, Gain)
- **Zero Weight Skipping**: Confirms inactive filters are not printed
- **Empty PEQ**: Ensures no output for empty lists
- **Output Capture**: Uses `io.StringIO` to capture and validate print output

#### `TestPEQIntegration` - End-to-End Testing
Integration tests combining multiple PEQ functions:

- **Build/Format Consistency**: Ensures `peq_build()` and `peq_format_apo()` agree
- **Preamp Consistency**: Validates preamp calculations match APO output
- **Realistic EQ Curves**: Tests with practical filter combinations
- **Different PEQ Lengths**: Validates 0, 1, 3, 10 filter scenarios
- **Response Bounds**: Ensures frequency responses stay within reasonable limits

#### `TestPEQWithoutNumpy` - Dependency-Free Tests
Basic validation that works without numpy:

- **Module Structure**: Validates expected functions exist in source code
- **Math Concepts**: Tests core mathematical concepts used in PEQ
- **Import Validation**: Ensures proper module dependencies

## Key Test Coverage

### Functions Tested
- ✅ `peq_build(freq, peq)` - Frequency response calculation
- ✅ `peq_preamp_gain(peq)` - Standard preamp calculation  
- ✅ `peq_preamp_gain_conservative(peq)` - Conservative preamp calculation
- ✅ `peq_format_apo(comment, peq)` - APO format generation
- ✅ `peq_print(peq)` - Debug output printing

### Filter Types Tested
- ✅ **Peak (PK)**: Parametric boost/cut filters
- ✅ **Low Shelf (LS)**: Bass region shaping
- ✅ **High Shelf (HS)**: Treble region shaping
- ✅ **Low Pass (LP)**: High frequency rolloff
- ✅ **High Pass (HP)**: Low frequency rolloff  
- ✅ **Band Pass (BP)**: Narrow frequency selection
- ✅ **Notch (NO)**: Narrow frequency removal

### Edge Cases Covered
- ✅ Empty PEQ lists
- ✅ Single filter PEQs
- ✅ Zero-weight filters
- ✅ Mixed positive/negative gains
- ✅ Wide frequency ranges (1 Hz to 100 kHz)
- ✅ Extreme parameters (very high Q, very low frequencies)
- ✅ Different filter weights (0.5x, 2.0x scaling)

## Running Tests

### Full Test Suite (requires numpy):
```bash
pip install numpy
python3 test_peq.py
```

### Structure Tests Only (no numpy):
```bash
python3 -c "
from test_peq import TestPEQWithoutNumpy
import unittest
unittest.main(module=None, argv=[''], testLoader=unittest.TestLoader().loadTestsFromTestCase(TestPEQWithoutNumpy), verbosity=2, exit=False)
"
```

### Using unittest framework:
```bash
python3 -m unittest test_peq.TestPEQBuild -v
python3 -m unittest test_peq.TestPEQPreampGain -v  
python3 -m unittest test_peq.TestPEQFormatAPO -v
```

## Test Output

Tests provide detailed feedback including:
- Function parameter validation
- Expected vs actual values for numerical calculations  
- APO format structure validation
- Filter type specific behavior verification
- Integration between different PEQ functions

## Integration with Main Project

These tests ensure the PEQ module correctly:

1. **Calculates Frequency Responses** using proper biquad mathematics
2. **Prevents Digital Clipping** with accurate preamp gain calculation  
3. **Generates APO Output** compatible with EqualizerAPO software
4. **Handles Edge Cases** without crashes or invalid results
5. **Maintains Consistency** between different output formats

This validates that the EQ conversion pipeline produces accurate and reliable parametric EQ processing across all supported formats and filter types.