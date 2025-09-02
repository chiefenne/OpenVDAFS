#!/usr/bin/env python3
"""
Standalone polygon triangulation demo (with optional hole support), ported from D. R. Finley's JS sample.

- Default runs built-in demo polygons (Ohio with/without hole, "7" shape without hole, "6" shape with hole).
- Optionally read a polygon (and holes) from JSON: {
    "outer": [[x,y], ...],
    "holes": [ [[x,y],...], ... ]     # optional
  }
- Optionally plot the triangulation using matplotlib.

Attribution:
- Based on JavaScript code by D. R. Finley (public domain).
- The code sample is embedded in the following web site:
  https://alienryderflex.com/triangulation/
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

try:
    import matplotlib.pyplot as plt
    _HAVE_MPL = True
except Exception:
    _HAVE_MPL = False

FAIL_MESSAGE = (
    "Triangulation failed: perhaps the polygon touches itself, or is traced in the wrong direction."
)

Point = Tuple[float, float]
Triangle = Tuple[Point, Point, Point]


# --- Geometry helpers (ported closely from the JS) ---

def line_segments_intersect(Ax: float, Ay: float, Bx: float, By: float,
                             Cx: float, Cy: float, Dx: float, Dy: float) -> bool:
    """Returns True if segment AB intersects segment CD.

    Port of JS version which translates and rotates so AB aligns with +X axis.
    """
    # No intersection if any of the four points are identical.
    if ((Ax == Bx and Ay == By) or (Ax == Cx and Ay == Cy) or (Ax == Dx and Ay == Dy)
            or (Bx == Cx and By == Cy) or (Bx == Dx and By == Dy) or (Cx == Dx and Cy == Dy)):
        return False

    # Translate so that A is origin
    Bx_r, By_r = Bx - Ax, By - Ay
    Cx_r, Cy_r = Cx - Ax, Cy - Ay
    Dx_r, Dy_r = Dx - Ax, Dy - Ay

    # Discover length of AB
    distAB = math.hypot(Bx_r, By_r)
    if distAB == 0.0:
        return False

    # Rotate so that B is on +X axis
    cos_ = Bx_r / distAB
    sin_ = By_r / distAB

    newX = Cx_r * cos_ + Cy_r * sin_
    Cy_r = Cy_r * cos_ - Cx_r * sin_
    Cx_r = newX

    newX = Dx_r * cos_ + Dy_r * sin_
    Dy_r = Dy_r * cos_ - Dx_r * sin_
    Dx_r = newX

    # No intersection if CD doesn't cross line AB
    if (Cy_r < 0.0 and Dy_r < 0.0) or (Cy_r >= 0.0 and Dy_r >= 0.0):
        return False

    # Position of intersection along AB
    ABpos = Dx_r + (Cx_r - Dx_r) * Dy_r / (Dy_r - Cy_r)

    # Intersection only if inside segment AB
    return ABpos > 0.0 and ABpos < distAB


def point_inside_triangle(Ax: float, Ay: float,
                          Bx: float, By: float,
                          Cx: float, Cy: float,
                          x: float, y: float) -> bool:
    """Return True if point (x,y) is inside triangle ABC.

    Port of the JS method that uses a point-in-polygon style toggle across the three edges.
    """
    inside = False

    if ((x != Ax or y != Ay) and (x != Bx or y != By) and (x != Cx or y != Cy)):
        if ((Ay < y and By >= y) or (By < y and Ay >= y)) and (Ax + (y - Ay) / (By - Ay) * (Bx - Ax) < x):
            inside = not inside
        if ((By < y and Cy >= y) or (Cy < y and By >= y)) and (Bx + (y - By) / (Cy - By) * (Cx - Bx) < x):
            inside = not inside
        if ((Cy < y and Ay >= y) or (Ay < y and Cy >= y)) and (Cx + (y - Cy) / (Ay - Cy) * (Ax - Cx) < x):
            inside = not inside

    return inside


# --- Unify polygon with one hole via shortest valid connector ---

def unify_outer_and_hole(outer: List[Point], hole: List[Point]) -> Optional[List[Point]]:
    corners = len(outer)
    if corners < 3 or len(hole) < 3:
        return None

    min_i = -1
    h_min_i = -1
    min_dist2 = float('inf')

    def seg_intersects_connector(i_outer: int, j_hole: int) -> bool:
        Ax, Ay = outer[i_outer]
        Cx, Cy = hole[j_hole]
        # Check against all edges of the outer polygon
        for k in range(corners):
            l = (k + 1) % corners
            Bx, By = outer[i_outer]  # same as A-> sanity not used
            Xk, Yk = outer[k]
            Xl, Yl = outer[l]
            if line_segments_intersect(Ax, Ay, Cx, Cy, Xk, Yk, Xl, Yl):
                return True
        # Check against all edges of the hole polygon
        hN = len(hole)
        for k in range(hN):
            l = (k + 1) % hN
            Xk, Yk = hole[k]
            Xl, Yl = hole[l]
            if line_segments_intersect(Ax, Ay, Cx, Cy, Xk, Yk, Xl, Yl):
                return True
        return False

    for i in range(corners):
        for j in range(len(hole)):
            dx = outer[i][0] - hole[j][0]
            dy = outer[i][1] - hole[j][1]
            dist2 = dx * dx + dy * dy
            if dist2 < min_dist2:
                # Ensure connector doesn't intersect any side of either polygon
                # (The intersection test ignores identical endpoints, matching the JS behavior.)
                if not seg_intersects_connector(i, j):
                    min_dist2 = dist2
                    min_i = i
                    h_min_i = j

    if min_i < 0:
        return None

    # Build unified polygon U by walking from outer[min_i] around, then add connector and reversed hole
    u: List[Point] = []
    # Outer forward from min_i, inclusive, wrapping once
    for i in range(corners + 1):
        u.append(outer[(min_i + i) % corners])
    # Hole reversed starting at h_min_i, inclusive, wrapping once
    hN = len(hole)
    for i in range(hN + 1):
        u.append(hole[(h_min_i + hN - i) % hN])
    return u


# --- Triangulation (ear clipping style as in the JS) ---

def triangulate_simple_polygon(poly: List[Point]) -> Optional[List[Triangle]]:
    """Triangulate a simple (hole-free) polygon using the JS approach.

    Returns list of triangles or None on failure.
    """
    if len(poly) < 3:
        return []

    X = [p[0] for p in poly]
    Y = [p[1] for p in poly]
    corners = len(poly)
    triangles: List[Triangle] = []

    safety = 0
    while corners >= 3 and safety < 10000:
        safety += 1
        i = 0
        progressed = False
        while i < corners and corners >= 3:
            j = (i + 1) % corners
            k = (j + 1) % corners
            # Verify triangle is inside, not outside (ported condition)
            if (X[i] != X[j] or Y[i] != Y[j]) and ( (Y[k] - Y[i]) * (X[j] - X[i]) >= (X[k] - X[i]) * (Y[j] - Y[i]) ):
                # Verify the interior does not contain any other corner
                l = 0
                while l < corners:
                    if point_inside_triangle(X[i], Y[i], X[j], Y[j], X[k], Y[k], X[l], Y[l]):
                        break
                    l += 1
                if l == corners:
                    # Usable triangle found
                    tri = ((X[i], Y[i]), (X[j], Y[j]), (X[k], Y[k]))
                    triangles.append(tri)
                    # Remove vertex j (ear clipping)
                    corners -= 1
                    for l2 in range(j, corners):
                        X[l2] = X[l2 + 1]
                        Y[l2] = Y[l2 + 1]
                    X.pop() ; Y.pop()
                    progressed = True
                    # Restart scan from beginning to mimic JS pacing
                    break
            i += 1
        if not progressed:
            # Could not find a valid ear this pass -> failure
            return None

    return triangles


def triangulate(outer: List[Point], holes: Optional[List[List[Point]]] = None) -> Optional[List[Triangle]]:
    holes = holes or []
    # Unify holes one by one (simple generalization of the single-hole JS sample)
    poly = list(outer)
    for h in holes:
        u = unify_outer_and_hole(poly, h)
        if u is None:
            return None
        poly = u
    return triangulate_simple_polygon(poly)


# --- Demo data (ported from test.js) ---

def demo_polygons() -> dict:
    # Ohio-shaped polygon
    polyOH = [(135,460),(20,385),(35,35),(175,35),(270,80),(350,75),(390,40),(485,0),
              (480,190),(440,325),(360,380),(340,435),(315,415),(290,490),(260,500),(215,455)]
    # "O"-shaped hole
    holeO = [(185,200),(235,200),(260,225),(260,305),(235,330),(185,330),(160,305),(160,225)]

    # "7"-shaped polygon
    poly7 = [(100,25),(400,25),(400,107.5),(250,475),(145,475),(295,107.5),(100,107.5)]

    # "6"-shaped polygon and hole
    poly6 = [(250,25),(340,25),(235,190),(261,183),(304,186),(345,202),(383,240),(407,306),(402,373),
             (367,430),(315,463),(250,475),(182,463),(123,420),(95,357),(99,282),(128,214)]
    hole6 = [(256,402),(209,389),(182,361),(173,320),(184,280),(208,255),(238,244),(275,245),
             (308,264),(330,299),(332,336),(317,373),(290,393)]

    return {
        'ohio': (polyOH, []),
        'ohio-hole': (polyOH, [holeO]),
        'seven': (poly7, []),
        'six-hole': (poly6, [hole6]),
    }


# --- Plotting ---

def plot_triangulation(outer: List[Point], holes: List[List[Point]], tris: List[Triangle], title: str = "") -> None:
    if not _HAVE_MPL:
        print("matplotlib not available; skipping plot")
        return
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6,6))
    # Draw triangles
    for (a,b,c) in tris:
        xs = [a[0], b[0], c[0], a[0]]
        ys = [a[1], b[1], c[1], a[1]]
        ax.fill(xs, ys, color='tab:red', alpha=0.25)
        ax.plot(xs, ys, color='tab:red', linewidth=1.0)
    # Draw outer
    xs = [p[0] for p in outer] + [outer[0][0]]
    ys = [p[1] for p in outer] + [outer[0][1]]
    ax.plot(xs, ys, color='black', linewidth=2.0)
    # Draw holes
    for h in holes:
        xs = [p[0] for p in h] + [h[0][0]]
        ys = [p[1] for p in h] + [h[0][1]]
        ax.plot(xs, ys, color='black', linewidth=2.0)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(title or 'Triangulation')
    ax.grid(True, linestyle=':', alpha=0.4)
    plt.show()


# --- CLI ---

def parse_args(argv: Optional[List[str]] = None):
    ap = argparse.ArgumentParser(description='Polygon triangulation demo (Finley ear-clipping variant)')
    ap.add_argument('--input', help='Path to JSON file with {"outer": [[x,y],...], "holes": [ [[x,y],...], ... ] }')
    ap.add_argument('--demo', choices=['ohio','ohio-hole','seven','six-hole'], action='append',
                    help='Run one or more built-in demos (can be repeated). Default: all demos if no input provided')
    ap.add_argument('--plot', action='store_true', help='Plot the triangulation with matplotlib')
    return ap.parse_args(argv)


def load_from_json(path: str) -> Tuple[List[Point], List[List[Point]]]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    outer = [(float(x), float(y)) for x, y in data['outer']]
    holes = []
    for h in data.get('holes', []) or []:
        holes.append([(float(x), float(y)) for x, y in h])
    return outer, holes


def run_case(name: str, outer: List[Point], holes: List[List[Point]], do_plot: bool) -> None:
    tris = triangulate(outer, holes)
    print(f"Case: {name}")
    if tris is None:
        print(f"  ERROR: {FAIL_MESSAGE}")
        return
    print(f"  Triangles: {len(tris)}")
    # Show first few triangles as sample
    for i, t in enumerate(tris[:5]):
        print(f"   {i+1:02d}: {t}")
    if do_plot:
        plot_triangulation(outer, holes, tris, title=name)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    if args.input:
        outer, holes = load_from_json(args.input)
        run_case('input', outer, holes, do_plot=args.plot)
        return

    demos = demo_polygons()
    selected = args.demo or list(demos.keys())
    for key in selected:
        outer, holes = demos[key]
        run_case(key, outer, holes, do_plot=args.plot)


if __name__ == '__main__':
    main()
