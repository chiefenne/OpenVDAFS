#!/usr/bin/env python3
"""
Plot one or more SURF (s,t) CSV loop files exported by OpenVDAFS.

Usage:
  python -m tools.plot_uv_loops exports/FC267_loop1.csv exports/FC267_loop2.csv --title "FC267 loops"
  python tools/plot_uv_loops.py exports/*.csv --save out.png

CSV format expected (from export_face_uv_loops):
  - Header lines start with '#'
  - First non-comment line is 's,t'
  - Subsequent lines: "<s>,<t>" floats (global SURF parameter space)

Each file will be drawn in a different color with its file name as legend label.
"""
from __future__ import annotations

import argparse
import glob
import os
from typing import List, Tuple

import matplotlib.pyplot as plt


def read_st_csv(path: str) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # allow optional header 's,t'
            if line.lower().replace(' ', '') in ('s,t', 's;t'):
                continue
            # split by comma (exported), fallback to whitespace
            if ',' in line:
                parts = line.split(',')
            else:
                parts = line.split()
            if len(parts) < 2:
                continue
            try:
                s = float(parts[0])
                t = float(parts[1])
            except ValueError:
                continue
            pts.append((s, t))
    return pts


def plot_files(files: List[str], title: str | None, save: str | None, show: bool, linewidth: float, legend: bool, dpi: int, equal_aspect: bool, markers: bool, marker_size: float) -> None:
    if not files:
        raise SystemExit("No input files provided")

    # Expand globs manually for predictable behavior
    expanded: List[str] = []
    for f in files:
        expanded.extend(sorted(glob.glob(f)))
    if not expanded:
        raise SystemExit("No files matched the given patterns")

    # Color cycle (fallback if rcParams not available)
    palette = [
        'tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple',
        'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan'
    ]

    plt.figure(figsize=(9, 7), dpi=dpi)
    ax = plt.gca()

    any_plotted = False
    all_x: List[float] = []
    all_y: List[float] = []

    for i, path in enumerate(expanded):
        pts = read_st_csv(path)
        if not pts:
            print(f"[warn] Empty or unreadable CSV: {path}")
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        color = palette[i % len(palette)]
        label = os.path.basename(path)
        if markers:
            ax.plot(xs, ys, color=color, linewidth=linewidth, label=label, marker='o', markersize=marker_size)
        else:
            ax.plot(xs, ys, color=color, linewidth=linewidth, label=label)
        all_x.extend(xs)
        all_y.extend(ys)
        any_plotted = True

    if not any_plotted:
        raise SystemExit("No valid data to plot")

    ax.set_xlabel('s (global)')
    ax.set_ylabel('t (global)')
    if title:
        ax.set_title(title)

    if equal_aspect:
        ax.set_aspect('equal', adjustable='box')

    if legend:
        ax.legend(loc='best', fontsize=9)

    ax.grid(True, linestyle=':', linewidth=0.8, alpha=0.6)

    # Fit bounds with a small margin
    if all_x and all_y:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)
        def margin(lo, hi):
            span = hi - lo
            if span <= 0:
                span = 1.0
            pad = 0.03 * span
            return lo - pad, hi + pad
        ax.set_xlim(*margin(xmin, xmax))
        ax.set_ylim(*margin(ymin, ymax))

    if save:
        out = os.path.abspath(save)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        plt.savefig(out, bbox_inches='tight', dpi=dpi)
        print(f"Saved figure -> {out}")
        if not show:
            plt.close()
            return

    plt.show()


def main(argv: List[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Plot SURF (s,t) CSV loop files with distinct colors")
    ap.add_argument('files', nargs='+', help='CSV files or glob patterns (e.g., exports/FA*_loop*.csv)')
    ap.add_argument('--title', default=None, help='Figure title')
    ap.add_argument('--save', default=None, help='Path to save the figure (e.g., plot.png). If omitted, just shows the window')
    ap.add_argument('--no-show', action='store_true', help="Don't show an interactive window (useful when --save is given)")
    ap.add_argument('--no-legend', action='store_true', help='Disable legend')
    ap.add_argument('--linewidth', type=float, default=1.8, help='Line width for plotted loops')
    ap.add_argument('--dpi', type=int, default=120, help='Figure DPI for saving/showing')
    ap.add_argument('--no-equal', action='store_true', help='Do not force equal aspect ratio')
    ap.add_argument('--markers', action='store_true', help='Draw point markers (dots) at each input point')
    ap.add_argument('--marker-size', type=float, default=2.5, help='Marker size for --markers')

    args = ap.parse_args(argv)

    plot_files(
        files=args.files,
        title=args.title,
        save=args.save,
        show=not args.no_show,
        linewidth=args.linewidth,
        legend=not args.no_legend,
        dpi=args.dpi,
    equal_aspect=not args.no_equal,
    markers=args.markers,
    marker_size=args.marker_size,
    )


if __name__ == '__main__':
    main()
