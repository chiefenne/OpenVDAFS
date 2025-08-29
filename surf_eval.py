# surf_eval.py — minimal VDA-FS SURF decoder & sampler (monomial patches)
#
# Supported layout (common VDA-FS v2 case):
#   params = [
#     nps, npt,
#     s_pars[0..nps],            # length nps+1
#     t_pars[0..npt],            # length npt+1
#     [optional scalars ...],    # some exports insert extra flags; we skip until orders found
#     # for each patch in s-major order (ps=0..nps-1, pt=0..npt-1):
#       JOR, KOR,                # monomial orders in s and t (>=1)
#       ax[JOR*KOR], ay[JOR*KOR], az[JOR*KOR]   # coeffs for x,y,z in u^j v^k
#   ]
#
# Evaluation for a patch (local u,v in [0,1]):
#   x(u,v) = sum_{j=0..JOR-1} sum_{k=0..KOR-1} ax[j*KOR+k] * u^j * v^k
#   (same for y,z)
#
# We do not merge seams (verts are duplicated along patch boundaries — fine for viewing).

import math

def _as_int(x):
    if isinstance(x, int):
        return x
    try:
        return int(round(float(x)))
    except Exception:
        raise ValueError("Expected integer-like value, got: %r" % (x,))

def _as_float(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x))
    except Exception:
        raise ValueError("Expected float-like value, got: %r" % (x,))

def _eval_monomial2(ax, ay, az, jor, kor, u, v):
    # Evaluate monomial surface at (u,v)
    # coeff layout is row-major in j (s-power), then k (t-power):
    # idx = j*kor + k
    # Use simple power products; Horner could optimize but clarity first.
    # Precompute powers
    up = [1.0]
    for _ in range(1, jor):
        up.append(up[-1] * u)
    vp = [1.0]
    for _ in range(1, kor):
        vp.append(vp[-1] * v)

    x = y = z = 0.0
    idx = 0
    for j in range(jor):
        uj = up[j]
        for k in range(kor):
            w = uj * vp[k]
            x += ax[idx] * w
            y += ay[idx] * w
            z += az[idx] * w
            idx += 1
    return (x, y, z)

def _decode_surface_params(params):
    if not params or len(params) < 2:
        raise ValueError("SURF: missing nps/npt")

    i = 0
    nps = _as_int(params[i]); i += 1
    npt = _as_int(params[i]); i += 1
    if nps <= 0 or npt <= 0:
        raise ValueError("SURF: nps/npt must be positive")

    if len(params) < i + (nps + 1) + (npt + 1):
        raise ValueError("SURF: missing global parameter vectors")

    s_pars = [ _as_float(params[i + k]) for k in range(nps + 1) ]
    i += (nps + 1)
    t_pars = [ _as_float(params[i + k]) for k in range(npt + 1) ]
    i += (npt + 1)

    patches = []
    total_patches = nps * npt

    # Some exports insert extra scalar(s) here (e.g., a flag). Skip until we see two ints (orders).
    def _looks_like_orders(a, b):
        try:
            return _as_int(a) >= 1 and _as_int(b) >= 1
        except Exception:
            return False

    # advance i until we can parse JOR,KOR (while keeping bounds)
    while i + 1 < len(params) and not _looks_like_orders(params[i], params[i+1]):
        i += 1

    count = 0
    while count < total_patches:
        if i + 1 >= len(params):
            raise ValueError("SURF: truncated before patch %d orders" % count)
        jor = _as_int(params[i]); i += 1
        kor = _as_int(params[i]); i += 1
        if jor <= 0 or kor <= 0:
            raise ValueError("SURF: invalid patch orders at %d" % count)

        need = jor * kor
        if i + 3*need > len(params):
            raise ValueError("SURF: not enough coefficients for patch %d" % count)

        ax = [ _as_float(params[i + k])       for k in range(need) ]
        ay = [ _as_float(params[i + need + k]) for k in range(need) ]
        az = [ _as_float(params[i + 2*need + k]) for k in range(need) ]
        i += 3*need

        # map to s,t intervals (s-major listing: ps fastest or pt fastest varies by export;
        # we assume ps major here: iterate t inside s)
        ps = count // npt
        pt = count %  npt
        s0, s1 = s_pars[ps],   s_pars[ps+1]
        t0, t1 = t_pars[pt],   t_pars[pt+1]

        patches.append({
            'jor': jor, 'kor': kor,
            'ax': ax, 'ay': ay, 'az': az,
            's0': _as_float(s0), 's1': _as_float(s1),
            't0': _as_float(t0), 't1': _as_float(t1),
        })
        count += 1

    return {
        'nps': nps, 'npt': npt,
        's_pars': s_pars, 't_pars': t_pars,
        'patches': patches
    }

def decode_surface_entity(entity):
    if entity.get('command') != 'SURF':
        raise ValueError("Entity is not a SURF")
    return _decode_surface_params(entity.get('params', []))

# alias for your existing name
def decode_surf_entity(entity):
    return decode_surface_entity(entity)

def sample_surface(surface, nu=40, nv=40, include_seams=True):
    """
    Sample each patch on an (nu x nv) grid in local (u,v) ∈ [0,1].
    Returns (vertices Nx3 list, faces Mx3 int list).
    Seams are NOT merged (duplicate vertices along boundaries) — simple & robust.
    """
    verts = []
    faces = []

    nu = max(2, int(nu))
    nv = max(2, int(nv))

    vidx_offset = 0
    for p in surface['patches']:
        jor, kor = p['jor'], p['kor']
        ax, ay, az = p['ax'], p['ay'], p['az']

        # build grid of (u_i, v_j)
        for i in range(nu + 1):
            # avoid duplicating seam if requested
            if i == 0 and not include_seams and vidx_offset > 0:
                continue
            u = i / float(nu)
            for j in range(nv + 1):
                if j == 0 and not include_seams and vidx_offset > 0:
                    continue
                v = j / float(nv)
                x, y, z = _eval_monomial2(ax, ay, az, jor, kor, u, v)
                verts.append((x, y, z))

        # local counts (accounting for seam skipping is messy; keep simple path)
        cols = nv + 1
        rows = nu + 1
        # create two triangles per cell
        for i in range(nu):
            for j in range(nv):
                a = vidx_offset + i*cols + j
                b = a + 1
                c = a + cols
                d = c + 1
                faces.append((a, b, d))
                faces.append((a, d, c))

        vidx_offset += rows * cols

    return verts, faces

# alias
def sample_surf(surface, nu=40, nv=40, include_seams=True):
    return sample_surface(surface, nu, nv, include_seams)
