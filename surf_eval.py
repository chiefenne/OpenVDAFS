# SURF decoder for VDA-FS (monomial basis).
# Decodes the params of a SURF entity into patch structures.

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

def decode_surf_entity(entity):
    """
    Convenience: given a parsed entity dict {'command','params',...} for SURF,
    return the decoded structure produced by _decode_surf_params.
    """
    if entity.get('command') != 'SURF':
        raise ValueError("Entity is not a SURF")
    return _decode_surf_params(entity.get('params', []))
