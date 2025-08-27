# SURF decoder & evaluator for VDA-FS (monomial basis).
# Decodes the params of a SURF entity into patch structures and evaluates points
# either by global parameters (u,v) or by uniform sampling per patch.

def _decode_surf_params(params):
    """
    Decode a SURF params list into:
      - nu, nv (number of patches in u and v directions)
      - u_pars, v_pars (parameter knot vectors)
      - patches: list of dicts with orders and coefficient matrices
    Returns a dict {'nu': nu, 'nv': nv, 'u_pars': u_pars, 'v_pars': v_pars, 'patches': patches}
    """
    if not params or len(params) < 2:
        raise ValueError("SURF has insufficient parameters")

    # number of patches in u and v directions
    nu = int(params[0])
    nv = int(params[1])
    if nu <= 0 or nv <= 0:
        raise ValueError("SURF patch counts must be positive")

    # (nu+1) u-parameters and (nv+1) v-parameters
    need = 2 + (nu + 1) + (nv + 1)
    if len(params) < need:
        raise ValueError("SURF missing parameter vectors")

    u_pars = params[2:2 + (nu + 1)]
    v_pars = params[2 + (nu + 1):2 + (nu + 1) + (nv + 1)]

    # remaining are patch blocks
    patch_data = params[2 + (nu + 1) + (nv + 1):]
    patches = []
    i = 0

    for u_idx in range(nu):
        for v_idx in range(nv):
            if i >= len(patch_data):
                raise ValueError("SURF missing patch block")

            # Orders in u and v directions
            Ku = int(patch_data[i]); i += 1
            Kv = int(patch_data[i]); i += 1
            if Ku <= 0 or Kv <= 0:
                raise ValueError("SURF patch orders must be positive")

            # Total coefficients needed: Ku * Kv for each of X, Y, Z
            total_coeffs = 3 * Ku * Kv
            end = i + total_coeffs
            if end > len(patch_data):
                raise ValueError("SURF patch coefficients incomplete")

            # Extract coefficient matrices for X, Y, Z
            # Coefficients are typically ordered as: all X, then all Y, then all Z
            # Each coordinate has Ku*Kv coefficients arranged in u-major order
            coeffs_x = []
            coeffs_y = []
            coeffs_z = []

            # X coefficients
            for u in range(Ku):
                row = []
                for v in range(Kv):
                    row.append(patch_data[i])
                    i += 1
                coeffs_x.append(row)

            # Y coefficients
            for u in range(Ku):
                row = []
                for v in range(Kv):
                    row.append(patch_data[i])
                    i += 1
                coeffs_y.append(row)

            # Z coefficients
            for u in range(Ku):
                row = []
                for v in range(Kv):
                    row.append(patch_data[i])
                    i += 1
                coeffs_z.append(row)

            # Validate coefficients are numeric
            for matrix in (coeffs_x, coeffs_y, coeffs_z):
                for row in matrix:
                    for val in row:
                        if not isinstance(val, (int, float)):
                            raise ValueError("SURF coefficients must be numeric")

            u0, u1 = float(u_pars[u_idx]), float(u_pars[u_idx + 1])
            v0, v1 = float(v_pars[v_idx]), float(v_pars[v_idx + 1])

            if u1 == u0 or v1 == v0:
                raise ValueError("SURF parameter intervals have zero length")

            patches.append({
                'u_idx': u_idx,
                'v_idx': v_idx,
                'order_u': Ku,
                'order_v': Kv,
                'coeffs_x': coeffs_x,
                'coeffs_y': coeffs_y,
                'coeffs_z': coeffs_z,
                'u0': u0, 'u1': u1,
                'v0': v0, 'v1': v1
            })

    return {
        'nu': nu,
        'nv': nv,
        'u_pars': u_pars,
        'v_pars': v_pars,
        'patches': patches
    }

def _eval_poly2d(coeffs, u, v):
    """Evaluate 2D monomial polynomial sum_{i,j} coeffs[i][j] * u^i * v^j."""
    # Precompute powers for clarity
    Ku = len(coeffs)
    Kv = len(coeffs[0]) if Ku > 0 else 0
    up = [1.0]
    for _ in range(1, Ku):
        up.append(up[-1] * u)
    vp = [1.0]
    for _ in range(1, Kv):
        vp.append(vp[-1] * v)
    s = 0.0
    for i in range(Ku):
        ci = coeffs[i]
        ui = up[i]
        for j in range(Kv):
            s += ci[j] * ui * vp[j]
    return s

def eval_surf_at_uv(surf, u, v):
    """
    Evaluate decoded surface (from _decode_surf_params) at global parameters (u,v).
    Returns (x, y, z).
    """
    patches = surf['patches']
    u_pars = surf['u_pars']
    v_pars = surf['v_pars']

    if not patches:
        raise ValueError("SURF has no patches")

    # Clamp into global ranges
    umin, umax = float(u_pars[0]), float(u_pars[-1])
    vmin, vmax = float(v_pars[0]), float(v_pars[-1])
    if u < umin: u = umin
    if u > umax: u = umax
    if v < vmin: v = vmin
    if v > vmax: v = vmax

    # Find patch indices (u_idx, v_idx)
    ui = None
    for i in range(len(u_pars) - 1):
        if u <= float(u_pars[i + 1]):
            ui = i
            break
    if ui is None:
        ui = len(u_pars) - 2

    vi = None
    for j in range(len(v_pars) - 1):
        if v <= float(v_pars[j + 1]):
            vi = j
            break
    if vi is None:
        vi = len(v_pars) - 2

    # Find the matching patch (stored row-major over u_idx, v_idx)
    patch = None
    for p in patches:
        if p['u_idx'] == ui and p['v_idx'] == vi:
            patch = p
            break
    if patch is None:
        # Fallback to last patch if not found (shouldn't happen)
        patch = patches[-1]

    u0, u1 = patch['u0'], patch['u1']
    v0, v1 = patch['v0'], patch['v1']
    uu = (u - u0) / (u1 - u0)
    vv = (v - v0) / (v1 - v0)

    x = _eval_poly2d(patch['coeffs_x'], uu, vv)
    y = _eval_poly2d(patch['coeffs_y'], uu, vv)
    z = _eval_poly2d(patch['coeffs_z'], uu, vv)
    return (x, y, z)

def sample_surf(surf, samples_u_per_patch=10, samples_v_per_patch=10, include_knots=True):
    """
    Uniformly sample each patch, returning wireframe polylines.
    Returns a tuple (u_lines, v_lines), where each element is a list of polylines;
    a polyline is a list of (x,y,z) points.
    """
    u_lines = []  # lines of constant v within each patch, swept along u
    v_lines = []  # lines of constant u within each patch, swept along v

    for p in surf['patches']:
        u0, u1 = p['u0'], p['u1']
        v0, v1 = p['v0'], p['v1']

        # how many samples along each direction within this patch
        mu = max(2, int(samples_u_per_patch))
        mv = max(2, int(samples_v_per_patch))

        # Build v-iso lines (constant v; sweep u)
        for j in range(mv + 1):
            # avoid duplicating interior v-boundary lines across patches if include_knots=False
            if j == 0 and p['v_idx'] > 0 and not include_knots:
                continue
            vv = j / float(mv)
            line = []
            for i in range(mu + 1):
                # avoid duplicating interior u-boundary points is not critical for polylines
                uu = i / float(mu)
                x = _eval_poly2d(p['coeffs_x'], uu, vv)
                y = _eval_poly2d(p['coeffs_y'], uu, vv)
                z = _eval_poly2d(p['coeffs_z'], uu, vv)
                line.append((x, y, z))
            u_lines.append(line)

        # Build u-iso lines (constant u; sweep v)
        for i in range(mu + 1):
            if i == 0 and p['u_idx'] > 0 and not include_knots:
                continue
            uu = i / float(mu)
            line = []
            for j in range(mv + 1):
                vv = j / float(mv)
                x = _eval_poly2d(p['coeffs_x'], uu, vv)
                y = _eval_poly2d(p['coeffs_y'], uu, vv)
                z = _eval_poly2d(p['coeffs_z'], uu, vv)
                line.append((x, y, z))
            v_lines.append(line)

    return u_lines, v_lines

def decode_surf_entity(entity):
    """
    Convenience: given a parsed entity dict {'command','params',...} for SURF,
    return the decoded structure produced by _decode_surf_params.
    """
    if entity.get('command') != 'SURF':
        raise ValueError("Entity is not a SURF")
    return _decode_surf_params(entity.get('params', []))
