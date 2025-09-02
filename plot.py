# Plotting helpers. One chart per call, no styles set.
import matplotlib.pyplot as plt
import math
import curve_eval as ce
import surf_eval as se
import query as q
import face_eval as fe
from typing import List, Tuple, Optional
import os

def _axis_labels(projection):
    """Return appropriate axis labels for the given projection."""
    if projection == 'xy':
        return 'X', 'Y'
    elif projection == 'xz':
        return 'X', 'Z'
    elif projection == 'yz':
        return 'Y', 'Z'
    elif projection == 'iso':
        return 'Iso-X', 'Iso-Y'
    else:
        return 'X', 'Y'  # default to xy

def _project_point(point, projection):
    """Project a 3D point to 2D based on the projection type."""
    x, y, z = point[:3]  # handle both tuples and arrays
    if projection == 'xy':
        return (x, y)
    elif projection == 'xz':
        return (x, z)
    elif projection == 'yz':
        return (y, z)
    elif projection == 'iso':
        # Simple isometric-like projection (no perspective): rotate axes to 30°/35.264°
        # Using a common approximation: u = x - y, v = (x + y)/2 - z * 0.816
        # We'll use a normalized variant to keep scales reasonable.
        # Reference: isometric projection matrix with rotations about X and Z.
        import math
        angle_x = math.radians(35.26438968)
        angle_z = math.radians(45)
        # Rotate around Z
        xr = x * math.cos(angle_z) - y * math.sin(angle_z)
        yr = x * math.sin(angle_z) + y * math.cos(angle_z)
        zr = z
        # Then rotate around X
        yr2 = yr * math.cos(angle_x) - zr * math.sin(angle_x)
        zr2 = yr * math.sin(angle_x) + zr * math.cos(angle_x)
        # Drop Z
        return (xr, yr2)
    else:
        return (x, y)  # default to xy

"""
Note: FACE triangulation and trimming have been removed per request. This module now
only draws CONS (via their referenced CURVEs) and SURF wireframes.
"""

def _plot_xyz_points(xyz, title=None, colors=None, segment_labels=None, projection='xy'):
    if not xyz:
        raise ValueError("No points to plot.")

    # Apply projection to points
    projected_points = [_project_point(p, projection) for p in xyz]
    xs = [p[0] for p in projected_points]
    ys = [p[1] for p in projected_points]

    plt.figure()

    if colors is None or segment_labels is None:
        # Single color plot (for points, etc.)
        plt.plot(xs, ys, marker='o')
    else:
        # Multi-segment plot with different colors
        start_idx = 0
        for i, (color, label) in enumerate(zip(colors, segment_labels)):
            end_idx = start_idx + label['point_count']
            segment_xs = xs[start_idx:end_idx]
            segment_ys = ys[start_idx:end_idx]
            plt.plot(segment_xs, segment_ys, marker='o', color=color,
                    label=f"Segment {i+1}", linewidth=2, markersize=4)
            start_idx = end_idx
        plt.legend()

    if title:
        plt.title(title)
    xl, yl = _axis_labels(projection)
    plt.xlabel(xl)
    plt.ylabel(yl)
    plt.axis('equal')
    plt.show()

def plot_entity(model, idx, name, samples_per_segment=30, projection='xy',
                surf_iso_lines=3, surf_line_samples=5):
    e = idx['by_name'].get(name)
    if not e:
        raise KeyError("No such entity: " + name)
    cmd = e['command']

    if cmd in ('POINT', 'PSET', 'MDI'):
        # naive attempt: treat params as flat xyz list
        nums = [v for v in e.get('params', []) if isinstance(v, (int,float))]
        if len(nums) % 3 != 0:
            raise ValueError("Entity does not contain 3D point triplets.")
        xyz = []
        it = iter(nums)
        for x in it:
            y = next(it); z = next(it)
            xyz.append((float(x), float(y), float(z)))
        _plot_xyz_points(xyz, title=f"{e['name']} ({cmd})", projection=projection)
        return

    if cmd == 'CURVE':
        curve = ce.decode_curve_entity(e)

        # Generate colors for segments using a predefined color list
        color_palette = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        n_segments = curve['n']
        colors = [color_palette[i % len(color_palette)] for i in range(n_segments)]

        # Sample each segment separately to track segment boundaries
        all_points = []
        segment_info = []

        for idx, seg in enumerate(curve['segments']):
            # Sample this segment
            seg_curve = {'n': 1, 'pars': [seg['t0'], seg['t1']], 'segments': [seg]}
            seg_points = ce.sample_curve(seg_curve, samples_per_segment=samples_per_segment, include_knots=True)

            # Avoid duplicating points at segment boundaries (except for first segment)
            if idx > 0 and all_points:
                seg_points = seg_points[1:]  # Skip first point to avoid duplication

            all_points.extend(seg_points)
            segment_info.append({'point_count': len(seg_points)})

        _plot_xyz_points(all_points, title=f"{e['name']} (CURVE)",
                        colors=colors, segment_labels=segment_info, projection=projection)
        return

    if cmd == 'SURF':
        surf = se.decode_surf_entity(e)
        # Get vertices and faces from surface sampling
        vertices, faces = se.sample_surf(surf, nu=12, nv=12)

        plt.figure()

        # Create wireframe by plotting patch boundaries
        # This is a simplified wireframe - just plot some iso-parameter lines
        n_patches = len(surf['patches'])
        # Build equally spaced parameter samples; keep same density for u and v for now
        def _linspace01(n):
            n = max(2, int(n))
            if n == 2:
                return [0.0, 1.0]
            step = 1.0 / float(n - 1)
            return [i * step for i in range(n)]

        iso_vals = _linspace01(surf_iso_lines)
        samp_vals = _linspace01(surf_line_samples)

        for i, patch in enumerate(surf['patches']):
            # u-direction iso-lines (vary v along line)
            for u_val in iso_vals:
                line_points = []
                for v_val in samp_vals:
                    x, y, z = se._eval_monomial2(
                        patch['ax'], patch['ay'], patch['az'],
                        patch['jor'], patch['kor'], u_val, v_val
                    )
                    line_points.append((x, y, z))
                proj = [_project_point(p, projection) for p in line_points]
                xs = [p[0] for p in proj]
                ys = [p[1] for p in proj]
                plt.plot(xs, ys, color='gray', linewidth=0.8)

            # v-direction iso-lines (vary u along line)
            for v_val in iso_vals:
                line_points = []
                for u_val in samp_vals:
                    x, y, z = se._eval_monomial2(
                        patch['ax'], patch['ay'], patch['az'],
                        patch['jor'], patch['kor'], u_val, v_val
                    )
                    line_points.append((x, y, z))
                proj = [_project_point(p, projection) for p in line_points]
                xs = [p[0] for p in proj]
                ys = [p[1] for p in proj]
                plt.plot(xs, ys, color='black', linewidth=0.8, alpha=0.7)

        plt.title(f"{e['name']} (SURF wireframe: {projection})")
        xl, yl = _axis_labels(projection)
        plt.xlabel(xl)
        plt.ylabel(yl)
        plt.axis('equal')
        plt.show()
        return

    raise NotImplementedError(f"Plotting for entity type '{cmd}' is not implemented.")

def plot_all(model, idx, projection='xy', samples_per_segment=30,
             surf_iso_lines=3, surf_line_samples=5):
    """
    Plot all CONS (as their referenced 3D CURVEs) and SURF entities in one figure.
    """
    cons_names = q.list_names_by_type(idx, 'CONS')
    surf_names = q.list_names_by_type(idx, 'SURF')

    plt.figure(figsize=(16, 10))
    ax = plt.gca()

    # Draw CONS by sampling their referenced CURVEs in 3D
    for cname in cons_names:
        econs = q.get_entity(idx, cname)
        if not econs:
            continue
        try:
            cons = fe.decode_cons_entity(econs)
        except Exception:
            continue
        cv_ref = cons.get('curve')
        if not cv_ref:
            continue
        ecv = q.get_entity(idx, cv_ref)
        if not ecv:
            continue
        try:
            curve = ce.decode_curve_entity(ecv)
        except Exception:
            continue
        all_points = []
        for sidx, seg in enumerate(curve['segments']):
            seg_curve = {'n': 1, 'pars': [seg['t0'], seg['t1']], 'segments': [seg]}
            seg_points = ce.sample_curve(seg_curve, samples_per_segment=samples_per_segment, include_knots=True)
            if sidx > 0 and all_points:
                seg_points = seg_points[1:]
            all_points.extend(seg_points)
        if not all_points:
            continue
        proj = [_project_point(p, projection) for p in all_points]
        ax.plot([p[0] for p in proj], [p[1] for p in proj], linewidth=1.4, alpha=0.95)

    # Draw SURF wireframes
    def _linspace01(n):
        n = max(2, int(n))
        if n == 2:
            return [0.0, 1.0]
        step = 1.0 / float(n - 1)
        return [i * step for i in range(n)]

    iso_vals = _linspace01(surf_iso_lines)
    samp_vals = _linspace01(surf_line_samples)

    for sname in surf_names:
        e = q.get_entity(idx, sname)
        try:
            surf = se.decode_surf_entity(e)
        except Exception:
            continue
        for patch in surf.get('patches', []):
            # u-lines
            for u_val in iso_vals:
                line_points = []
                for v_val in samp_vals:
                    x, y, z = se._eval_monomial2(patch['ax'], patch['ay'], patch['az'], patch['jor'], patch['kor'], u_val, v_val)
                    line_points.append((x, y, z))
                proj = [_project_point(p, projection) for p in line_points]
                ax.plot([p[0] for p in proj], [p[1] for p in proj], color='gray', linewidth=0.6, alpha=0.6)
            # v-lines
            for v_val in iso_vals:
                line_points = []
                for u_val in samp_vals:
                    x, y, z = se._eval_monomial2(patch['ax'], patch['ay'], patch['az'], patch['jor'], patch['kor'], u_val, v_val)
                    line_points.append((x, y, z))
                proj = [_project_point(p, projection) for p in line_points]
                ax.plot([p[0] for p in proj], [p[1] for p in proj], color='black', linewidth=0.6, alpha=0.5)

    # Finalize
    xl, yl = _axis_labels(projection)
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(f"All entities: {len(cons_names)} CONS, {len(surf_names)} SURF ({projection})")
    # make axis equal
    ax.set_box_aspect(1)  # aspect ratio 1:1
    plt.show()

# (FACE triangulation helpers removed)

def plot_entity_data(model, idx, name):
    """Plot the raw data/parameters of an entity (e.g., order and coefficients for CURVE)."""
    e = idx['by_name'].get(name)
    if not e:
        raise KeyError("No such entity: " + name)
    cmd = e['command']

    if cmd == 'CURVE':
        curve = ce.decode_curve_entity(e)
        _plot_curve_data(curve, e['name'])
        return

    if cmd in ('POINT', 'PSET', 'MDI'):
        _plot_point_data(e)
        return

    if cmd == 'SURF':
        _plot_surf_data(e)
        return

    raise NotImplementedError(f"Data plotting for entity type '{cmd}' is not implemented.")

def _plot_curve_data(curve, name):
    """Plot CURVE order and coefficients as bar charts."""
    n_segments = curve['n']
    segments = curve['segments']

    # Create subplots for each segment
    fig, axes = plt.subplots(n_segments, 3, figsize=(15, 4 * n_segments))
    if n_segments == 1:
        axes = axes.reshape(1, -1)

    fig.suptitle(f"CURVE Data: {name}", fontsize=16)

    for i, seg in enumerate(segments):
        order = seg['order']
        ax = seg['ax']
        ay = seg['ay']
        az = seg['az']

        # Plot X coefficients
        axes[i, 0].bar(range(order), ax, color='red', alpha=0.7)
        axes[i, 0].set_title(f"Segment {i+1} - X Coefficients (Order {order})")
        axes[i, 0].set_xlabel("Coefficient Index")
        axes[i, 0].set_ylabel("Value")

        # Plot Y coefficients
        axes[i, 1].bar(range(order), ay, color='green', alpha=0.7)
        axes[i, 1].set_title(f"Segment {i+1} - Y Coefficients (Order {order})")
        axes[i, 1].set_xlabel("Coefficient Index")
        axes[i, 1].set_ylabel("Value")

        # Plot Z coefficients
        axes[i, 2].bar(range(order), az, color='blue', alpha=0.7)
        axes[i, 2].set_title(f"Segment {i+1} - Z Coefficients (Order {order})")
        axes[i, 2].set_xlabel("Coefficient Index")
        axes[i, 2].set_ylabel("Value")

    plt.tight_layout()
    plt.show()

def _plot_point_data(entity):
    """Plot point/pset data as coordinates."""
    params = entity.get('params', [])
    nums = [v for v in params if isinstance(v, (int, float))]

    if len(nums) % 3 != 0:
        raise ValueError("Entity does not contain 3D point triplets.")

    n_points = len(nums) // 3
    xs, ys, zs = [], [], []

    for i in range(n_points):
        xs.append(nums[i * 3])
        ys.append(nums[i * 3 + 1])
        zs.append(nums[i * 3 + 2])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.suptitle(f"{entity['command']} Data: {entity['name']}", fontsize=16)

    point_indices = list(range(n_points))

    axes[0].bar(point_indices, xs, color='red', alpha=0.7)
    axes[0].set_title("X Coordinates")
    axes[0].set_xlabel("Point Index")
    axes[0].set_ylabel("X Value")

    axes[1].bar(point_indices, ys, color='green', alpha=0.7)
    axes[1].set_title("Y Coordinates")
    axes[1].set_xlabel("Point Index")
    axes[1].set_ylabel("Y Value")

    axes[2].bar(point_indices, zs, color='blue', alpha=0.7)
    axes[2].set_title("Z Coordinates")
    axes[2].set_xlabel("Point Index")
    axes[2].set_ylabel("Z Value")

    plt.tight_layout()
    plt.show()

def _plot_surf_data(entity):
    """Plot surface parameter data."""
    params = entity.get('params', [])

    plt.figure(figsize=(16, 10))
    plt.bar(range(len(params)), params, color='purple', alpha=0.7)
    plt.title(f"SURF Parameters: {entity['name']}")
    plt.xlabel("Parameter Index")
    plt.ylabel("Parameter Value")
    plt.show()


# --- FACE UV-plane plotting for debugging ---

def _eval_monomial1(coeffs: List[float], order: int, u: float) -> float:
    """Evaluate a 1D monomial series sum_{j=0..order-1} coeffs[j] * u^j."""
    if order <= 0:
        return 0.0
    up = 1.0
    acc = 0.0
    for j in range(order):
        if j == 0:
            up = 1.0
        elif j == 1:
            up = u
        else:
            up *= u
        acc += coeffs[j] * up
    return acc

def _sample_pcurve(pc: Optional[dict], samples_per_segment: int = 50) -> List[Tuple[float, float]]:
    """Sample a p-curve mapping (s(u), t(u)) across its segments, returning (s,t) points.

    pc layout (from fe.decode_cons_entity):
      {'n': n, 'pars': [...], 'segments': [ {'order':K, 'as': [...], 'at': [...], 't0': ..., 't1': ...}, ... ]}
    """
    if not pc or not pc.get('segments'):
        return []
    pts: List[Tuple[float, float]] = []
    n = pc.get('n', 0)
    for i, seg in enumerate(pc['segments']):
        K = int(seg.get('order', 0))
        as_coeff = seg.get('as', [])
        at_coeff = seg.get('at', [])
        m = max(2, int(samples_per_segment))
        for k in range(m):
            u = k / float(m - 1)
            s = _eval_monomial1(as_coeff, K, u)
            t = _eval_monomial1(at_coeff, K, u)
            # avoid duplicate at segment joints except for first
            if i > 0 and k == 0 and pts:
                continue
            pts.append((s, t))
    return pts

def _eval_pcurve_at_t(pc: Optional[dict], t_value: float) -> Optional[Tuple[float, float]]:
    """Evaluate p-curve mapping (s,t) at a given underlying curve parameter t_value.

    pc: {'n': n, 'pars': [t0..tn], 'segments': [{order, as, at, ...}, ...]}
    Returns (s_norm, t_norm) in local [0,1] space or None if not evaluable.
    """
    if not pc or not pc.get('segments') or not pc.get('pars'):
        return None
    pars = pc['pars']
    segs = pc['segments']
    n = len(segs)
    if n == 0 or len(pars) < n + 1:
        return None
    # Clamp t_value to [pars[0], pars[-1]]
    t0 = pars[0]
    tN = pars[-1]
    if tN == t0:
        return None
    t = min(max(t_value, t0), tN)
    # Find segment index k such that pars[k] <= t <= pars[k+1]
    k = 0
    for i in range(n):
        if t <= pars[i+1] or i == n - 1:
            k = i
            break
    a = pars[k]
    b = pars[k+1]
    if b == a:
        u = 0.0
    else:
        u = (t - a) / (b - a)
    seg = segs[k]
    K = int(seg.get('order', 0))
    as_coeff = seg.get('as', [])
    at_coeff = seg.get('at', [])
    s_norm = _eval_monomial1(as_coeff, K, u)
    t_norm = _eval_monomial1(at_coeff, K, u)
    return (s_norm, t_norm)

def plot_face_uv(model, idx, face_name: str, pcurve_samples: int = 50, show_local_midlines: bool = True):
    """Plot FACE items (CONS pcurves) in the surface parameter domain (s,t).

    - Draw global grid lines using SURF s_pars and t_pars (patch boundaries).
    - Optionally draw local midlines (u=0.5, v=0.5 within each patch) as hints.
    - Plot each CONS pcurve in (s,t) using its p-curve mapping (if present).
    - Mark FACE-provided (u,v) anchor points for each item.
    """
    eface = idx['by_name'].get(face_name)
    if not eface or eface.get('command') != 'FACE':
        raise KeyError(f"No such FACE: {face_name}")

    f = fe.decode_face_entity(eface)
    sref = f.get('surf')
    esurf = q.get_entity(idx, sref)
    if not esurf:
        raise KeyError(f"FACE {face_name}: SURF {sref} not found")
    surf = se.decode_surf_entity(esurf)

    s_pars = surf.get('s_pars', [])
    t_pars = surf.get('t_pars', [])
    smin = s_pars[0] if s_pars else 0.0
    smax = s_pars[-1] if s_pars else 1.0
    tmin = t_pars[0] if t_pars else 0.0
    tmax = t_pars[-1] if t_pars else 1.0

    plt.figure(figsize=(10, 8))
    ax = plt.gca()

    # Global grid (patch boundaries)
    if s_pars and t_pars:
        for s in s_pars:
            ax.plot([s, s], [tmin, tmax], color='lightgray', linewidth=1.0)
        for t in t_pars:
            ax.plot([smin, smax], [t, t], color='lightgray', linewidth=1.0)

        # Local midlines per patch (u=0.5 / v=0.5)
        if show_local_midlines:
            for i in range(len(s_pars) - 1):
                smid = 0.5 * (s_pars[i] + s_pars[i + 1])
                ax.plot([smid, smid], [tmin, tmax], color='silver', linewidth=0.6, linestyle='--', alpha=0.7)
            for j in range(len(t_pars) - 1):
                tmid = 0.5 * (t_pars[j] + t_pars[j + 1])
                ax.plot([smin, smax], [tmid, tmid], color='silver', linewidth=0.6, linestyle='--', alpha=0.7)

    # Color palette for loops/items
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']

    # Plot each loop's items
    loop_idx = 0
    for loop in f.get('loops', []) or []:
        for item_idx, item in enumerate(loop.get('items', []) or []):
            cons_ref = item.get('cons')
            color = colors[(loop_idx + item_idx) % len(colors)]
            if cons_ref:
                econs = q.get_entity(idx, cons_ref)
                if econs:
                    cons = fe.decode_cons_entity(econs)
                    pc = cons.get('pc')
                    pts = _sample_pcurve(pc, pcurve_samples)
                    # Deterministically map local [0,1] p-curve params to global SURF parameters
                    if pts:
                        xs = [smin + p[0] * (smax - smin) for p in pts]
                        ys = [tmin + p[1] * (tmax - tmin) for p in pts]
                        ax.plot(xs, ys, color=color, linewidth=1.8, alpha=0.95, label=f"{cons_ref}")
                    # Annotate underlying CURVE parameter ranges per p-curve segment
                    if pc and pc.get('pars') and pc.get('segments'):
                        pars = pc['pars']
                        segs = pc['segments']
                        for si in range(min(len(segs), len(pars) - 1)):
                            ta = float(pars[si]); tb = float(pars[si + 1])
                            st_a = _eval_pcurve_at_t(pc, ta)
                            st_b = _eval_pcurve_at_t(pc, tb)
                            tm = 0.5 * (ta + tb)
                            st_m = _eval_pcurve_at_t(pc, tm)
                            if st_a is not None:
                                ax.plot([smin + st_a[0] * (smax - smin)], [tmin + st_a[1] * (tmax - tmin)],
                                        marker='o', color=color, markersize=2, alpha=0.9)
                            if st_b is not None:
                                ax.plot([smin + st_b[0] * (smax - smin)], [tmin + st_b[1] * (tmax - tmin)],
                                        marker='o', color=color, markersize=2, alpha=0.9)
                            if st_m is not None:
                                mx = smin + st_m[0] * (smax - smin)
                                my = tmin + st_m[1] * (tmax - tmin)
                                ax.text(mx, my, f" [{ta:.3g},{tb:.3g}]", fontsize=7, color=color,
                                        va='bottom', ha='left', alpha=0.9)
                    # Plot FACE-provided endpoints as markers by evaluating p-curve at those curve parameters
                    if 'u' in item and 'v' in item:
                        for t_val in (float(item['u']), float(item['v'])):
                            st_local = _eval_pcurve_at_t(pc, t_val)
                            if st_local is None:
                                continue
                            sx = smin + st_local[0] * (smax - smin)
                            ty = tmin + st_local[1] * (tmax - tmin)
                            ax.plot([sx], [ty], marker='o', color=color, markersize=3)
                        # Label near the first endpoint
                        st0 = _eval_pcurve_at_t(pc, float(item['u']))
                        if st0 is not None:
                            sx0 = smin + st0[0] * (smax - smin)
                            ty0 = tmin + st0[1] * (tmax - tmin)
                            ax.text(sx0, ty0, f" {cons_ref}", fontsize=8, color=color, va='bottom', ha='left')
        loop_idx += 1

    # Fix axes to global parameter box
    ax.set_xlim(smin, smax)
    ax.set_ylim(tmin, tmax)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('s (global)')
    ax.set_ylabel('t (global)')
    ax.set_title(f"FACE {face_name} in parameter space (s,t)")
    # Avoid crowded duplicate labels
    handles, labels = ax.get_legend_handles_labels()
    if labels:
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='best', fontsize=8)
    plt.show()


def export_face_uv_loops(model, idx, face_name: str, out_dir: str, pcurve_samples: int = 50, eps: float = 1e-9) -> List[str]:
    """Export each FACE loop as a CSV of SURF (s,t) points.

    Rules for duplicate handling within a loop L of CONSs [C0, C1, ..., Ck-1]:
      - For C0: include all sampled points.
      - For Ci (i>0): skip the first sampled point (to avoid duplicating the previous end).
      - After concatenating all points, if last point equals first (within eps), drop the last.

    Returns list of written file paths.
    """
    eface = idx['by_name'].get(face_name)
    if not eface or eface.get('command') != 'FACE':
        raise KeyError(f"No such FACE: {face_name}")

    f = fe.decode_face_entity(eface)
    sref = f.get('surf')
    esurf = q.get_entity(idx, sref)
    if not esurf:
        raise KeyError(f"FACE {face_name}: SURF {sref} not found")
    surf = se.decode_surf_entity(esurf)

    s_pars = surf.get('s_pars', [])
    t_pars = surf.get('t_pars', [])
    smin = s_pars[0] if s_pars else 0.0
    smax = s_pars[-1] if s_pars else 1.0
    tmin = t_pars[0] if t_pars else 0.0
    tmax = t_pars[-1] if t_pars else 1.0

    os.makedirs(out_dir, exist_ok=True)

    written: List[str] = []
    loops = f.get('loops', []) or []
    for li, loop in enumerate(loops, start=1):
        loop_pts: List[Tuple[float, float]] = []
        items = loop.get('items', []) or []
        for ci, item in enumerate(items):
            cons_ref = item.get('cons')
            if not cons_ref:
                continue
            econs = q.get_entity(idx, cons_ref)
            if not econs:
                continue
            try:
                cons = fe.decode_cons_entity(econs)
            except Exception:
                continue
            pc = cons.get('pc')
            pts_local = _sample_pcurve(pc, pcurve_samples)
            if not pts_local:
                continue
            # Map to global SURF params
            pts = [(smin + s * (smax - smin), tmin + t * (tmax - tmin)) for (s, t) in pts_local]
            # Skip first point for all but the first CONS in loop
            if ci > 0 and len(pts) > 0:
                pts = pts[1:]
            loop_pts.extend(pts)

        # Close-loop duplicate suppression: drop last if equals first (within eps)
        if len(loop_pts) >= 2:
            if abs(loop_pts[-1][0] - loop_pts[0][0]) <= eps and abs(loop_pts[-1][1] - loop_pts[0][1]) <= eps:
                loop_pts = loop_pts[:-1]

        # Write CSV
        if loop_pts:
            path = os.path.join(out_dir, f"{face_name}_loop{li}.csv")
            with open(path, 'w', encoding='utf-8', newline='') as fh:
                fh.write(f"# FACE: {face_name}\n")
                fh.write(f"# SURF: {sref}\n")
                fh.write(f"# loop: {li}\n")
                fh.write(f"# points: {len(loop_pts)}\n")
                fh.write("s,t\n")
                for (sx, ty) in loop_pts:
                    fh.write(f"{sx:.17g},{ty:.17g}\n")
            written.append(path)

    return written
