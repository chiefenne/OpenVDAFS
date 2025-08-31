# Plotting helpers. One chart per call, no styles set.
import matplotlib.pyplot as plt
import math
import curve_eval as ce
import surf_eval as se
import query as q
import face_eval as fe

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

def plot_entity(model, idx, name, samples_per_segment=30, projection='xy'):
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
        for i, patch in enumerate(surf['patches']):
            # Sample a few lines across each patch for wireframe visualization
            for u_val in [0.0, 0.5, 1.0]:
                line_points = []
                for v_val in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    # Evaluate the patch at (u_val, v_val)
                    x, y, z = se._eval_monomial2(patch['ax'], patch['ay'], patch['az'],
                                               patch['jor'], patch['kor'], u_val, v_val)
                    line_points.append((x, y, z))

                # Project and plot this line
                proj = [_project_point(p, projection) for p in line_points]
                xs = [p[0] for p in proj]
                ys = [p[1] for p in proj]
                plt.plot(xs, ys, color='gray', linewidth=0.8)

            # Plot v-direction lines
            for v_val in [0.0, 0.5, 1.0]:
                line_points = []
                for u_val in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    x, y, z = se._eval_monomial2(patch['ax'], patch['ay'], patch['az'],
                                               patch['jor'], patch['kor'], u_val, v_val)
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

def plot_all(model, idx, projection='xy', samples_per_segment=30):
    """
    Plot all CONS (as their referenced 3D CURVEs) and SURF entities in one figure.
    """
    cons_names = q.list_names_by_type(idx, 'CONS')
    surf_names = q.list_names_by_type(idx, 'SURF')

    plt.figure()
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
    for sname in surf_names:
        e = q.get_entity(idx, sname)
        try:
            surf = se.decode_surf_entity(e)
        except Exception:
            continue
        for patch in surf.get('patches', []):
            # u-lines
            for u_val in (0.0, 0.5, 1.0):
                line_points = []
                for v_val in (0.0, 0.25, 0.5, 0.75, 1.0):
                    x, y, z = se._eval_monomial2(patch['ax'], patch['ay'], patch['az'], patch['jor'], patch['kor'], u_val, v_val)
                    line_points.append((x, y, z))
                proj = [_project_point(p, projection) for p in line_points]
                ax.plot([p[0] for p in proj], [p[1] for p in proj], color='gray', linewidth=0.6, alpha=0.6)
            # v-lines
            for v_val in (0.0, 0.5, 1.0):
                line_points = []
                for u_val in (0.0, 0.25, 0.5, 0.75, 1.0):
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

    plt.figure(figsize=(10, 6))
    plt.bar(range(len(params)), params, color='purple', alpha=0.7)
    plt.title(f"SURF Parameters: {entity['name']}")
    plt.xlabel("Parameter Index")
    plt.ylabel("Parameter Value")
    plt.show()
