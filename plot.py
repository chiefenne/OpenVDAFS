# Plotting helpers. One chart per call, no styles set.
import matplotlib.pyplot as plt
import curve_eval as ce
import surf_eval as se

def _plot_xyz_points(xyz, title=None):
    if not xyz:
        raise ValueError("No points to plot.")
    xs = [p[0] for p in xyz]
    ys = [p[1] for p in xyz]
    plt.figure()
    plt.plot(xs, ys, marker='o')
    if title:
        plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.axis('equal')
    plt.show()

def plot_entity(model, idx, name, samples_per_segment=30):
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
        _plot_xyz_points(xyz, title=f"{e['name']} ({cmd})")
        return

    if cmd == 'CURVE':
        curve = ce.decode_curve_entity(e)
        pts, seg_ranges = ce.sample_curve(
            curve,
            samples_per_segment=samples_per_segment,
            include_knots=True,
            return_segment_ranges=True,
        )

        # Plot each segment with a distinct color
        plt.figure()
        for seg_idx, start, end in seg_ranges:
            seg_pts = pts[start:end]
            xs = [p[0] for p in seg_pts]
            ys = [p[1] for p in seg_pts]
            color = plt.cm.tab20(seg_idx % 20)
            plt.plot(xs, ys, color=color)
        plt.title(f"{e['name']} (CURVE)")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.axis('equal')
        plt.show()
        return

    if cmd == 'SURF':
        surf = se.decode_surf_entity(e)
        u_lines, v_lines = se.sample_surf(surf, samples_u_per_patch=12, samples_v_per_patch=12, include_knots=True)

        plt.figure()
        # Plot u-iso lines (constant v)
        for line in u_lines:
            xs = [p[0] for p in line]
            ys = [p[1] for p in line]
            plt.plot(xs, ys, color='gray', linewidth=0.8)
        # Plot v-iso lines (constant u)
        for line in v_lines:
            xs = [p[0] for p in line]
            ys = [p[1] for p in line]
            plt.plot(xs, ys, color='black', linewidth=0.8, alpha=0.7)
        plt.title(f"{e['name']} (SURF wireframe)")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.axis('equal')
        plt.show()
        return

    raise NotImplementedError(f"Plotting for entity type '{cmd}' is not implemented.")

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
        axes[i, 0].grid(True, alpha=0.3)

        # Plot Y coefficients
        axes[i, 1].bar(range(order), ay, color='green', alpha=0.7)
        axes[i, 1].set_title(f"Segment {i+1} - Y Coefficients (Order {order})")
        axes[i, 1].set_xlabel("Coefficient Index")
        axes[i, 1].set_ylabel("Value")
        axes[i, 1].grid(True, alpha=0.3)

        # Plot Z coefficients
        axes[i, 2].bar(range(order), az, color='blue', alpha=0.7)
        axes[i, 2].set_title(f"Segment {i+1} - Z Coefficients (Order {order})")
        axes[i, 2].set_xlabel("Coefficient Index")
        axes[i, 2].set_ylabel("Value")
        axes[i, 2].grid(True, alpha=0.3)

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
    axes[0].grid(True, alpha=0.3)

    axes[1].bar(point_indices, ys, color='green', alpha=0.7)
    axes[1].set_title("Y Coordinates")
    axes[1].set_xlabel("Point Index")
    axes[1].set_ylabel("Y Value")
    axes[1].grid(True, alpha=0.3)

    axes[2].bar(point_indices, zs, color='blue', alpha=0.7)
    axes[2].set_title("Z Coordinates")
    axes[2].set_xlabel("Point Index")
    axes[2].set_ylabel("Z Value")
    axes[2].grid(True, alpha=0.3)

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
    plt.grid(True, alpha=0.3)
    plt.show()
