# OpenVDAFS

> **🚧 Work in Progress** - This project is under active development.

A Python library and CLI for reading, parsing, inspecting, and visualizing VDA‑FS (Verband der Automobilindustrie — Flächenschnittstelle) files. VDA‑FS is a legacy CAD/CAM interchange format (primarily used in the 1980s–1990s) for exchanging curve and surface geometry. This project provides parsing, visualization, and a developer-friendly API for working with legacy automotive geometry data.

## Features

### ✅ Current Features

- VDA-FS reader for format versions 1.0 and 2.0
- Entity support:
  - `CURVE` (multi-segment parametric, monomial basis)
  - `POINT`, `PSET`, `MDI` (point data)
  - `SURF` (parametric surfaces; wireframe visualization with adjustable density)
  - `CONS` and `FACE` decoding; FACE p-curves can be visualized in SURF (s,t) space and exported to CSV (no 3D FACE triangulation)
- CLI for listing, plotting, and exporting
- Visualization:
  - Plot a single entity by name (`CURVE`, `POINT`/`PSET`/`MDI`)
  - Plot all: draw all `CONS` (via their referenced `CURVE`s) and `SURF` wireframes in one view
  - Plot a `FACE` in the SURF parameter plane (s,t), including SURF grid, p-curves, and annotations
  - Multiple projections: `xy`, `yz`, `xz`, `iso`
- Inspection: Print detailed entity data (orders, parameters, coefficients)
- Exports:
  - Export two FACEs (and dependencies) to minimal VDA files
  - Export FACE loops as CSV in SURF (s,t); includes a standalone CSV plotter under `tools/`
- Utilities (tools/): standalone polygon triangulation demo (outer + holes) with optional plotting

### 🔄 Planned Features

- Enhanced SURF entity support with evaluation functions
- Export capabilities to other formats
- Interactive visualization tools
- Batch processing utilities
- API documentation

## Installation

### Prerequisites

- Python 3.8+
- matplotlib (only needed for plotting; listing/inspection works without it)

### Setup

```bash
git clone https://github.com/chiefenne/OpenVDAFS.git
cd OpenVDAFS
pip install matplotlib  # optional: required for plotting only
```

## Usage

### Command Line Interface

The CLI provides listing, plotting, and export utilities.

#### Options overview

- `--list TYPE` — list entity names of a given type (e.g., `CURVE`, `SURF`, `CONS`, `FACE`, `POINT`, `PSET`, `MDI`)
- `--list ALL` — grouped listing by entity type; also prints `HEADER: N lines` when present
- `--plot NAME` — plot a single entity by name (`CURVE`, `SURF`, `POINT`/`PSET`/`MDI`)
- `--plot-all` — plot all `CONS` (via referenced curves) and `SURF` wireframes in one figure
- `--projection {xy|yz|xz|iso}` or `-p` — choose 2D projection for plots (default: `xy`)
- `--plot-data NAME` — print detailed, textual entity data to the terminal
- `--export-faces FACE1 FACE2` — export two `FACE`s with their dependencies to separate `.vda` files
- `--out-dir DIR` — output directory for exports (default: `./exports`)
- `--surf-iso-lines N` — number of equally spaced iso-lines per parameter direction for SURF wireframe (default: 3)
- `--surf-line-samples M` — samples along each iso-line for SURF wireframe (default: 5)
- `--plot-face-uv FACE` — plot a FACE in the SURF (s,t) parameter plane
- `--pcurve-samples K` — samples per CONS p-curve segment in (s,t) (default: 50)
- `--no-midlines` — hide local midlines (u=0.5/v=0.5 per patch) in the UV plot
- `--export-face-uv-loops FACE` — export FACE loops as CSV files in SURF (s,t); see section below

#### List entities by type

```bash
python cli.py file.vda --list CURVE
python cli.py file.vda --list SURF
python cli.py file.vda --list ALL   # grouped by type; shows HEADER count if present
```

#### Visualize entities

```bash
# Plot geometric representation
python cli.py file.vda --plot CV3

# Plot points (POINT/PSET/MDI)
python cli.py file.vda --plot PT1

# Plot a SURF as a wireframe
python cli.py file.vda --plot SF1

# Choose projection (-p/--projection): xy, yz, xz, iso
python cli.py file.vda --plot CV3 -p yz
python cli.py file.vda --plot CV3 -p iso

# Plot all CONS (via referenced CURVEs) and SURF wireframes in one view
python cli.py file.vda --plot-all -p xz

# Control SURF wireframe density
python cli.py file.vda --plot SF1 --surf-iso-lines 5 --surf-line-samples 9
```

#### Inspect entity data (text)

```bash
# Print detailed entity information (orders, coefficients, parameters) to the terminal
python cli.py file.vda --plot-data CV3
```

#### Export two FACEs (with dependencies)

```bash
python cli.py file.vda --export-faces FA12 FA27 --out-dir ./exports
```
This writes `./exports/FA12.vda` and `./exports/FA27.vda` containing each `FACE` and referenced geometry.

Tip: Some extra utilities live under the `tools/` package and can be run directly, e.g.:

```bash
# Check surface continuity along patch seams
python -m tools.check_surf_continuity examples/SURF_FLAE0001.vda

# Diagnose SURF evaluation variants (dev/experimental)
python -m tools.diagnose_surf_encoding examples/SURF_FLAE0001.vda
```

#### Plot a FACE in the SURF (s,t) plane

Use the deterministic UV debug plot to see a FACE’s p-curves (CONS) in the SURF’s parameter domain. The SURF’s global parameter box [smin,smax]×[tmin,tmax] is used for axes; p-curves are evaluated in their local [0,1] and mapped affinely into this box. FACE endpoints (curve parameters) are marked; each p-curve segment is annotated with its underlying CURVE parameter interval [t0, t1].

```bash
# Plot FACE FA3 in UV with annotations and SURF grid
python cli.py file.vda --plot-face-uv FA3

# Increase p-curve sampling, hide per-patch midlines
python cli.py file.vda --plot-face-uv FA3 --pcurve-samples 100 --no-midlines
```

#### Export FACE loops as SURF (s,t) CSV

Writes one CSV per loop with header comments and a `s,t` column header. Duplicate points at CONS junctions are skipped, and a closing duplicate is removed when equal to the first point.

```bash
python cli.py file.vda --export-face-uv-loops FA3 --out-dir exports --pcurve-samples 80
# -> exports/FA3_loop1.csv, exports/FA3_loop2.csv, ...
```

CSV format:

```text
# FACE: FA3
# SURF: SF1
# loop: 1
# points: 123
s,t
0.12,0.34
0.125,0.341
...
```

#### Plot exported UV loops (standalone tool)

The helper `tools/plot_uv_loops.py` visualizes one or more SURF (s,t) CSVs with different colors. It supports glob patterns, saving, equal aspect, legends, and optional point markers.

```bash
# Multiple files with a title
python -m tools.plot_uv_loops exports/FA3_loop*.csv --title "FA3 loops"

# Save without showing a window, disable legend, force equal aspect (default)
python tools/plot_uv_loops.py exports/*.csv --save out.png --no-show --no-legend

# Draw dots at each sample point
python -m tools.plot_uv_loops exports/*.csv --markers --marker-size 2.5
```

#### Triangulate polygons (standalone tool)

A small demo tool that triangulates a simple polygon with optional holes. By default it runs built-in demo shapes; you can also provide a JSON file.

Algorithm: ear-clipping style triangulation adapted from D. R. Finley’s public-domain JavaScript sample (see References/Attribution).
Holes are unified into the outer polygon using a shortest valid connector and then triangulated.

Intended use in this project: triangulate one or more CONS loops in the SURF (s,t) plane as exported by “Export FACE loops as SURF (s,t) CSV” (via `--export-face-uv-loops`). You can preview those CSVs with `tools/plot_uv_loops.py`.

```bash
# Run all built-in demos (Ohio with/without hole, 7-shape, 6-shape with hole)
python -m tools.triangulate_polygons

# Run specific demos, with plotting
python -m tools.triangulate_polygons --demo ohio --demo six-hole --plot

# Triangulate from JSON input (structure shown below)
python -m tools.triangulate_polygons --input polygon.json --plot
```

JSON input format:

```json
{
  "outer": [[x, y], [x, y], ...],
  "holes": [
    [[x, y], [x, y], ...],
    [[x, y], [x, y], ...]
  ]
}
```

### Notes and limitations

- May fail if the polygon touches itself, is degenerate, or is traced in the wrong direction.
- Plotting requires matplotlib; omit --plot if you don’t have it installed.



### Example Output

For a CURVE entity, `--plot-data` shows:

```text
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

## File structure

```text
OpenVDAFS/
├── cli.py              # Command-line interface
├── reader.py           # VDA-FS file parser
├── index.py            # Entity indexing
├── query.py            # Entity queries
├── plot.py             # Visualization (single entity, all CONS+SURF wireframes)
├── curve_eval.py       # CURVE decoder and evaluator
├── surf_eval.py        # SURF decoder and sampling helpers
├── face_eval.py        # CONS/FACE helpers (decode CONS; FACE export dependencies)
├── tools/              # Utility scripts and helpers
│   ├── __init__.py
│   ├── data_print.py   # Textual data inspection utilities
│   ├── export_faces.py # Write minimal VDA files containing individual FACEs
│   ├── check_surf_continuity.py
│   ├── diagnose_surf_encoding.py
│   ├── plot_uv_loops.py # Plot SURF (s,t) CSV loop files (markers, legends, save)
│   └── triangulate_polygons.py # Standalone polygon triangulation demo (outer + holes; optional plotting)
└── examples/           # Example VDA-FS files
    ├── CURVE_SP1.vda
    └── SURF_FLAE0001.vda
```

## VDA-FS format support

### Supported Entities

| Entity Type | Read | Parse | Visualize | Data Export |
|-------------|------|-------|-----------|-------------|
| CURVE       | ✅   | ✅    | ✅        | ✅          |
| SURF        | ✅   | ✅    | ✅ (wireframe) | ✅          |
| POINT       | ✅   | ✅    | ✅        | ✅          |
| PSET        | ✅   | ✅    | ✅        | ✅          |
| MDI         | ✅   | ✅    | ✅        | ✅          |
| CONS        | ✅   | ✅    | ✅ (via CURVE in plot-all) | — |
| FACE        | ✅   | ✅    | ✅ (UV p-curves) | ✅ (loops→CSV) |

### Format Versions

- **VDA-FS 1.0**: Full support
- **VDA-FS 2.0**: Full support

## Examples

The `examples/` and `VDA_EXAMPLES/` directories contain sample VDA-FS files for testing:

- `CURVE_SP1.vda`: Multi-segment parametric curve
- `SURF_FLAE0001.vda`: Parametric surface data
- `VDA_EXAMPLES/pipe-joint.vda`, `...`: Larger mixed-entity examples

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

MIT License. See `LICENSE` for details.

## References

- DIN 66301: VDA-FS Format Specification
- VDA (Verband der Automobilindustrie) Standards
- Polygon triangulation algorithm by D. R. Finley (public domain), embedded as JavaScript in the website code: [alienryderflex.com/triangulation](https://alienryderflex.com/triangulation/)

## Status

Current version: 0.1.0-dev

Last updated: September 2025
