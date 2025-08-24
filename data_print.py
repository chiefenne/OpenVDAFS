# Print entity data to terminal (order, parameters, coefficients etc.)
import curve_eval as ce
import surf_eval as se

def print_entity_data(model, idx, name):
    """Print the raw data/parameters of an entity to the terminal."""
    e = idx['by_name'].get(name)
    if not e:
        raise KeyError("No such entity: " + name)
    cmd = e['command']

    print(f"Entity: {name}")
    print(f"Type: {cmd}")
    print()

    if cmd == 'CURVE':
        curve = ce.decode_curve_entity(e)
        _print_curve_data(curve, name)
        return

    if cmd in ('POINT', 'PSET', 'MDI'):
        _print_point_data(e)
        return

    if cmd == 'SURF':
        try:
            surf = se.decode_surf_entity(e)
            _print_surf_data(surf, name)
        except Exception as ex:
            print(f"Error decoding SURF: {ex}")
            _print_surf_data_raw(e)
        return

    print(f"Detailed data printing for entity type '{cmd}' is not implemented.")

def _print_curve_data(curve, name):
    """Print CURVE order, parameters, and coefficients."""
    print("=== CURVE DETAILS ===")
    print(f"Number of segments: {curve['n']}")
    print(f"Global parameters: {curve['pars']}")
    print()

    for i, seg in enumerate(curve['segments']):
        print(f"--- Segment {i+1} ---")
        print(f"Order: {seg['order']}")
        print(f"Parameter range: [{seg['t0']}, {seg['t1']}]")
        print(f"X coefficients: {seg['ax']}")
        print(f"Y coefficients: {seg['ay']}")
        print(f"Z coefficients: {seg['az']}")
        print()

def _print_point_data(entity):
    """Print point/pset coordinate data."""
    params = entity.get('params', [])
    nums = [v for v in params if isinstance(v, (int, float))]

    if len(nums) % 3 != 0:
        print("Warning: Entity does not contain complete 3D point triplets.")
        return

    n_points = len(nums) // 3
    print(f"=== {entity['command']} DETAILS ===")
    print(f"Number of points: {n_points}")
    print()

    for i in range(n_points):
        x = nums[i * 3]
        y = nums[i * 3 + 1]
        z = nums[i * 3 + 2]
        print(f"Point {i+1}: ({x}, {y}, {z})")

def _print_surf_data(surf, name):
    """Print decoded SURF patch data."""
    print("=== SURF DETAILS ===")
    print(f"Number of patches: {surf['nu']} x {surf['nv']} (u x v)")
    print(f"U parameters: {surf['u_pars']}")
    print(f"V parameters: {surf['v_pars']}")
    print()

    for i, patch in enumerate(surf['patches']):
        print(f"--- Patch {i+1} (u_idx={patch['u_idx']}, v_idx={patch['v_idx']}) ---")
        print(f"Orders: {patch['order_u']} x {patch['order_v']} (u x v)")
        print(f"U parameter range: [{patch['u0']}, {patch['u1']}]")
        print(f"V parameter range: [{patch['v0']}, {patch['v1']}]")
        print()

        print("X coefficients:")
        for u_idx, row in enumerate(patch['coeffs_x']):
            print(f"  u^{u_idx}: {row}")
        print()

        print("Y coefficients:")
        for u_idx, row in enumerate(patch['coeffs_y']):
            print(f"  u^{u_idx}: {row}")
        print()

        print("Z coefficients:")
        for u_idx, row in enumerate(patch['coeffs_z']):
            print(f"  u^{u_idx}: {row}")
        print()

def _print_surf_data_raw(entity):
    """Print raw SURF parameter data when decoding fails."""
    params = entity.get('params', [])
    print("=== SURF DETAILS (RAW) ===")
    print(f"Number of parameters: {len(params)}")
    print("Parameters:")
    for i, param in enumerate(params):
        print(f"  [{i}]: {param}")
