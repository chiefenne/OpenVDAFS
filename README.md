# OpenVDAFS

> **🚧 Work in Progress** - This project is under active development.

A Python library and CLI tool for reading, parsing, and visualizing VDA-FS (Verband der Automobilindustrie - Flächenschnittstelle) files, which were used in automotive CAD/CAM applications for surface and curve data exchange.

## Features

### ✅ Current Features

- **VDA-FS Format Support**: Read and parse VDA-FS format versions 1.0 and 2.0
- **Entity Parsing**: Full support for:
  - `CURVE` entities (multi-segment parametric curves with monomial basis)
  - `POINT`, `PSET`, `MDI` entities (point data)
  - `SURF` entities (parametric surfaces) - *basic support*
- **CLI Tool**: Command-line interface for file inspection and analysis
- **Data Visualization**: Plot geometric entities using matplotlib
- **Data Inspection**: Print detailed entity data including orders, parameters, and coefficients

### 🔄 Planned Features

- Enhanced SURF entity support with evaluation functions
- Export capabilities to other formats
- Interactive visualization tools
- Batch processing utilities
- API documentation

## Installation

### Prerequisites

- Python 3.7+
- matplotlib (for plotting functionality)

### Setup

```bash
git clone https://github.com/chiefenne/OpenVDAFS.git
cd OpenVDAFS
pip install matplotlib  # For plotting functionality
```

## Usage

### Command Line Interface

The CLI tool provides several commands to work with VDA-FS files:

#### List Entities by Type

```bash
python cli.py file.vda --list CURVE
python cli.py file.vda --list SURF
python cli.py file.vda --list POINT
```

#### Visualize Entities

```bash
# Plot geometric representation
python cli.py file.vda --plot CV3

# Plot points
python cli.py file.vda --plot PT1
```

#### Inspect Entity Data

```bash
# Print detailed entity information (orders, coefficients, parameters)
python cli.py file.vda --plot-data CV3
```

### Example Output

For a CURVE entity, `--plot-data` shows:

```
Entity: SP1
Type: CURVE

=== CURVE DETAILS ===
Number of segments: 4
Global parameters: [0.0, 1.0, 2.0, 2.7, 4.0]

--- Segment 1 ---
Order: 5
Parameter range: [0.0, 1.0]
X coefficients: [0.0, 63.8891754, -51.465271, 77.0936432, -48.5175476]
Y coefficients: [0.0, 6.4475098, 56.9390259, -23.5717163, 3.1851807]
Z coefficients: [30.0, 0.0, -60.0, 40.0, -10.0]

--- Segment 2 ---
Order: 3
Parameter range: [1.0, 2.0]
X coefficients: [41.0, -0.9153137, 41.9153137]
Y coefficients: [43.0, 31.1755676, 1.8244324]
Z coefficients: [0.0, -20.0, 15.0]
...
```

### Python API

```python
import reader
import index
import curve_eval

# Read VDA-FS file
model = reader.read_vdafs('file.vda')

# Build index for fast lookup
idx = index.build_index(model)

# Get a specific entity
entity = idx['by_name']['CV3']

# Decode CURVE entity
if entity['command'] == 'CURVE':
    curve = curve_eval.decode_curve_entity(entity)
    # Access curve data: curve['n'], curve['segments'], etc.
```

## File Structure

```
OpenVDAFS/
├── cli.py              # Command-line interface
├── reader.py           # VDA-FS file parser
├── index.py            # Entity indexing
├── query.py            # Entity queries
├── plot.py             # Visualization tools
├── data_print.py       # Data inspection utilities
├── curve_eval.py       # CURVE entity decoder and evaluator
├── surf_eval.py        # SURF entity decoder
└── examples/           # Example VDA-FS files
    ├── CURVE_SP1.vda
    └── SURF_FLAE0001.vda
```

## VDA-FS Format Support

### Supported Entities

| Entity Type | Read | Parse | Visualize | Data Export |
|-------------|------|-------|-----------|-------------|
| CURVE       | ✅   | ✅    | ✅        | ✅          |
| SURF        | ✅   | ✅    | 🔄        | ✅          |
| POINT       | ✅   | ✅    | ✅        | ✅          |
| PSET        | ✅   | ✅    | ✅        | ✅          |
| MDI         | ✅   | ✅    | ✅        | ✅          |

### Format Versions

- **VDA-FS 1.0**: Full support
- **VDA-FS 2.0**: Full support

## Examples

The `examples/` directory contains sample VDA-FS files for testing:

- `CURVE_SP1.vda`: Multi-segment parametric curve
- `SURF_FLAE0001.vda`: Parametric surface data

## Contributing

This project is under active development. Contributions are welcome!

### Development Setup

1. Clone the repository
2. Make your changes
3. Test with example files
4. Submit a pull request

## Technical Details

### CURVE Entity Structure

- Multi-segment parametric curves using monomial basis
- Each segment can have different polynomial orders
- Global parameter knot vectors define segment boundaries
- Coefficients grouped by coordinate (X, Y, Z)

### SURF Entity Structure

- Parametric surfaces with u,v parameter directions
- Patch-based representation with bicubic or higher-order polynomials
- Coefficient matrices for each coordinate

## License

[License information to be added]

## References

- DIN 66301: VDA-FS Format Specification
- VDA (Verband der Automobilindustrie) Standards

## Status

Current version: 0.1.0-dev

Last updated: August 2025
