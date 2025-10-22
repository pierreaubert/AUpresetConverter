# IIR Module Tests

This directory contains comprehensive tests for the `iir` module used in AUpresetConverter.

## Test Files

### `test_iir.py` - Full Test Suite
Comprehensive test suite that covers all aspects of the IIR module including:

- **Biquad Math Functions**: Q/BW conversions (`bw2q`, `q2bw`)
- **Biquad Filter Types**: All 7 filter types (LOWPASS, HIGHPASS, BANDPASS, PEAK, NOTCH, LOWSHELF, HIGHSHELF)
- **Filter Creation**: Parameter validation and coefficient generation
- **Frequency Response**: Single-point and vectorized calculations
- **PEQ Functions**: Building frequency responses, preamp gain calculation, APO format output
- **Edge Cases**: Extreme parameters, error handling

**Requirements**: numpy, iir module
**Usage**: `python3 test_iir.py`

### `test_iir_basic.py` - Basic Tests (No Dependencies)
Lightweight test suite that doesn't require numpy:

- **Math Validation**: Tests core mathematical functions without imports
- **Module Structure**: Validates file structure and expected functions
- **Basic Calculations**: Verifies biquad coefficient math
- **Filter Type Constants**: Tests enumeration values

**Requirements**: None (pure Python)  
**Usage**: `python3 test_iir_basic.py`

### `test_peq.py` - PEQ Module Tests
Comprehensive test suite for the Parametric EQ module (`iir/filter_peq.py`):

- **Frequency Response Building**: Tests `peq_build()` function
- **Preamp Gain Calculation**: Tests standard and conservative methods
- **APO Format Generation**: Tests `peq_format_apo()` output
- **Debug Output**: Tests `peq_print()` function
- **Integration Tests**: End-to-end validation of PEQ pipeline
- **All Filter Types**: PK, LS, HS, LP, HP, BP, NO

**Requirements**: numpy, iir module
**Usage**: `python3 test_peq.py`
**Documentation**: See `test_peq_README.md` for detailed information

## Test Coverage

### Math Functions
- ✅ Q to bandwidth conversion (`q2bw`)
- ✅ Bandwidth to Q conversion (`bw2q`)
- ✅ Round-trip consistency tests
- ✅ Edge cases and boundary conditions

### Biquad Filters
- ✅ All 7 filter types creation
- ✅ Parameter validation
- ✅ Coefficient generation
- ✅ Frequency response calculation
- ✅ Zero Q handling
- ✅ Type-to-string conversion
- ✅ String representation

### PEQ (Parametric EQ) Functions
- ✅ Multi-filter response building
- ✅ Preamp gain calculation (standard and conservative)
- ✅ APO format output generation
- ✅ Empty PEQ handling

### Numpy Integration
- ✅ Vectorized frequency response
- ✅ Consistency between single and vector methods
- ✅ Large array handling

### Edge Cases
- ✅ Very low/high frequencies
- ✅ Extreme Q values
- ✅ Zero and negative gains
- ✅ Invalid filter types
- ✅ NaN/infinity handling

## Running Tests

### With numpy (full tests):
```bash
pip install numpy
python3 test_iir.py
```

### Without numpy (basic tests):
```bash
python3 test_iir_basic.py
```

### Using unittest framework:
```bash
python3 -m unittest test_iir.py -v
python3 -m unittest test_iir_basic.py -v
```

## Test Results Format

Both test files use Python's `unittest` framework and provide detailed output:

- **✓ Pass**: Test passed successfully
- **✗ Fail**: Test failed with assertion error
- **Skip**: Test skipped due to missing dependencies

The tests are designed to be self-contained and provide clear feedback about what functionality is being tested.

## Integration

These tests verify that the IIR module correctly:

1. **Parses EQ data** into internal representations
2. **Processes filters** using proper biquad mathematics  
3. **Generates output** in various formats (AUpreset, APO, etc.)
4. **Handles edge cases** without crashes or invalid results

This ensures the EQ converter produces accurate and reliable results across all supported filter types and formats.