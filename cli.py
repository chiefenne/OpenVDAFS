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
import reader
import index
import query
import plot
import data_print

def main():
    ap = argparse.ArgumentParser(description="OpenVDAFS minimal tools")
    ap.add_argument("file", help="Path to .vda file")
    ap.add_argument("--list", dest="list_type", help="List entity names of a type (e.g., CURVE)")
    ap.add_argument("--plot", dest="plot_name", help='Plot an entity by name (e.g., "CV3")')
    ap.add_argument("--plot-data", dest="plot_data_name", help='Print entity data/parameters to terminal (e.g., "CV3" shows order and coefficients)')
    args = ap.parse_args()

    model = reader.read_vdafs(args.file)
    idx = index.build_index(model)

    if args.list_type:
        names = query.list_names_by_type(idx, args.list_type)
        if not names:
            print("(none)")
        else:
            for nm in names:
                print(nm)

    if args.plot_name:
        plot.plot_entity(model, idx, args.plot_name)

    if args.plot_data_name:
        data_print.print_entity_data(model, idx, args.plot_data_name)

if __name__ == "__main__":
    main()
