# Tiny VDAFS CLI: list names by type, plot by entity name.
# Usage:
#   python cli.py <file.vda> --list CURVE
#   python cli.py <file.vda> --plot CV3
#   python cli.py <file.vda> --plot-data CV3
#
# Notes:
# - One chart per invocation (plot shows immediately).
# - --plot shows the geometric curve/points
# - --plot-data prints the raw data to terminal (order, coefficients, etc.)

import sys
import argparse
from textwrap import fill
import reader
import index
import query
from tools import data_print
from tools import export_faces
import os

def main():
    ap = argparse.ArgumentParser(description="OpenVDAFS minimal tools")
    ap.add_argument("file", help="Path to .vda file")
    ap.add_argument("--list", dest="list_type", help="List entity names of a type (e.g., CURVE). Use ALL to list each entity type with its entries")
    ap.add_argument("--plot", dest="plot_name", help='Plot an entity by name (e.g., "CV3")')
    ap.add_argument("--plot-data", dest="plot_data_name", help='Print entity data/parameters to terminal (e.g., "CV3" shows order and coefficients)')
    ap.add_argument("--projection", "-p", dest="projection", choices=["xy", "yz", "xz", "iso"], default="xy",
                    help="2D projection for plotting: xy, yz, xz, or iso (isometric)")
    ap.add_argument("--surf-iso-lines", type=int, default=3,
                    help="Number of equally spaced iso-lines per parameter direction for SURF wireframe (u and v share this value)")
    ap.add_argument("--surf-line-samples", type=int, default=5,
                    help="Number of samples along each iso-line for SURF wireframe (u and v share this value)")
    ap.add_argument("--plot-all", action="store_true", help="Plot all CONS and SURF entities in one view")
    ap.add_argument("--plot-face-uv", dest="plot_face_uv", help='Plot a FACE in (s,t) parameter plane (e.g., "FA3")')
    ap.add_argument("--pcurve-samples", type=int, default=50, help="Samples per CONS segment when plotting p-curves in (s,t)")
    ap.add_argument("--no-midlines", action="store_true", help="Disable drawing local midlines (u=0.5/v=0.5) per patch in (s,t)")
    ap.add_argument("--export-face-uv-loops", dest="export_face_uv_loops", help='Export FACE loops as CSV in SURF (s,t) space; provide a FACE name (e.g., "FA3")')
    ap.add_argument("--export-faces", nargs=2, metavar=('FACE1', 'FACE2'), help="Export two FACEs and their dependencies to separate files")
    ap.add_argument("--out-dir", default="./exports", help="Output directory for exported VDA files")
    args = ap.parse_args()

    model = reader.read_vdafs(args.file)
    idx = index.build_index(model)

    if args.list_type:
        lt = args.list_type.strip().upper()
        if lt == "ALL":
            # Group by entity type and print names per type with basic wrapping
            header = model.get('header')
            if header is not None:
                n_hdr = header.get('n_lines')
                if not n_hdr:
                    n_hdr = len(header.get('lines', []) or [])
                print(f"HEADER: {n_hdr} lines")
            groups = {}
            for e in model.get('entities', []):
                cmd = e.get('command', '')
                nm = e.get('name', '')
                groups.setdefault(cmd, []).append(nm)
            for cmd, names in groups.items():
                print(f"{cmd} ({len(names)}):")
                line = ', '.join(names)
                print('  ' + fill(line, width=100, subsequent_indent='  '))
        else:
            names = query.list_names_by_type(idx, lt)
            if not names:
                print("(none)")
            else:
                # Pretty single-type listing
                print(f"{lt} ({len(names)}):")
                line = ', '.join(names)
                print('  ' + fill(line, width=100, subsequent_indent='  '))

    if args.plot_all:
        import plot
        plot.plot_all(
            model,
            idx,
            projection=args.projection,
            surf_iso_lines=args.surf_iso_lines,
            surf_line_samples=args.surf_line_samples,
        )

    if args.plot_name:
        import plot
        plot.plot_entity(
            model,
            idx,
            args.plot_name,
            projection=args.projection,
            surf_iso_lines=args.surf_iso_lines,
            surf_line_samples=args.surf_line_samples,
        )

    if args.plot_data_name:
        data_print.print_entity_data(model, idx, args.plot_data_name)

    if args.plot_face_uv:
        import plot
        plot.plot_face_uv(
            model,
            idx,
            args.plot_face_uv,
            pcurve_samples=args.pcurve_samples,
            show_local_midlines=not args.no_midlines,
        )

    if args.export_face_uv_loops:
        import plot
        paths = plot.export_face_uv_loops(
            model,
            idx,
            args.export_face_uv_loops,
            out_dir=args.out_dir,
            pcurve_samples=args.pcurve_samples,
        )
        for p in paths:
            print(f"Exported loop CSV -> {p}")

    if args.export_faces:
        f1, f2 = args.export_faces
        out1 = os.path.join(args.out_dir, f1 + '.vda')
        out2 = os.path.join(args.out_dir, f2 + '.vda')
        os.makedirs(args.out_dir, exist_ok=True)
        export_faces.write_face_file(model, idx, f1, out1)
        export_faces.write_face_file(model, idx, f2, out2)
        print(f"Exported {f1} -> {out1}")
        print(f"Exported {f2} -> {out2}")

if __name__ == "__main__":
    main()
