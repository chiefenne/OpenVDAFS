# CURVE decoder & evaluator for VDA-FS (monomial basis).
# Decodes the params of a CURVE entity into per-segment structures, then
# evaluates points either by global parameter t or by uniform sampling.

def _decode_curve_params(params):
    """
    Decode a CURVE params list into:
      - n (segments)
      - pars (list of n+1 global parameters)
      - segments: list of dicts with keys:
          {'order': K, 'ax': [...], 'ay': [...], 'az': [...], 't0': par[k], 't1': par[k+1]}
    Returns a dict {'n': n, 'pars': pars, 'segments': segments}
    """
    if not params or len(params) < 1:
        raise ValueError("CURVE has no parameters")

    # number of segments
    n = int(params[0])
    if n <= 0:
        raise ValueError("CURVE segment count must be positive")

    # n+1 global parameters
    need = 1 + (n + 1)
    if len(params) < need:
        raise ValueError("CURVE missing global parameters")
    pars = params[1:1 + (n + 1)]

    # remaining are segment blocks: for each seg -> [K, K ax, K ay, K az]
    seg_data = params[1 + (n + 1):]
    segs = []
    i = 0
    for k in range(n):
        if i >= len(seg_data):
            raise ValueError("CURVE missing segment block")
        K = int(seg_data[i]); i += 1
        if K <= 0:
            raise ValueError("CURVE segment order must be positive")

        end = i + 3 * K
        if end > len(seg_data):
            raise ValueError("CURVE segment coefficients incomplete")
        ax = seg_data[i: i + K]; i += K
        ay = seg_data[i: i + K]; i += K
        az = seg_data[i: i + K]; i += K

        # sanity: all numbers?
        for arr in (ax, ay, az):
            for v in arr:
                if not isinstance(v, (int, float)):
                    raise ValueError("CURVE coefficients must be numeric")

        t0, t1 = float(pars[k]), float(pars[k + 1])
        if t1 == t0:
            raise ValueError("CURVE global parameter interval has zero length")

        segs.append({'order': K, 'ax': ax, 'ay': ay, 'az': az, 't0': t0, 't1': t1})

    return {'n': n, 'pars': pars, 'segments': segs}


def _eval_monomial(coeffs, u):
    """Evaluate Σ c[j] u^j for j=0..K-1."""
    # Horner would be faster; monomial is fine & clear:
    s = 0.0
    p = 1.0
    for c in coeffs:
        s += c * p
        p *= u
    return s


def eval_curve_at_t(curve, t):
    """
    Evaluate decoded curve (from _decode_curve_params) at global parameter t.
    Returns (x, y, z).
    """
    segs = curve['segments']
    pars = curve['pars']

    # Clamp t into [pars[0], pars[-1]] for robustness
    tmin, tmax = float(pars[0]), float(pars[-1])
    if t < tmin: t = tmin
    if t > tmax: t = tmax

    # Find segment k with t in [pars[k], pars[k+1]]; rightmost on boundary
    # Linear scan is fine; n is usually small. Could be binary search later.
    k = None
    for i in range(len(segs)):
        if t <= float(pars[i + 1]):
            k = i
            break
    if k is None:
        k = len(segs) - 1

    seg = segs[k]
    t0, t1 = seg['t0'], seg['t1']
    u = (t - t0) / (t1 - t0)

    x = _eval_monomial(seg['ax'], u)
    y = _eval_monomial(seg['ay'], u)
    z = _eval_monomial(seg['az'], u)
    return (x, y, z)


def sample_curve(curve, samples_per_segment=20, include_knots=True):
    """
    Uniformly sample each segment in local u in [0,1].
    Returns a list of (x,y,z).
    """
    pts = []
    for idx, seg in enumerate(curve['segments']):
        # local u samples
        m = max(2, int(samples_per_segment))
        for j in range(m + (1 if include_knots or idx == 0 else 0)):
            # generate u in [0,1]; avoid duplicating interior knot if not include_knots
            if j == 0 and idx > 0 and not include_knots:
                continue
            u = j / float(m)
            x = _eval_monomial(seg['ax'], u)
            y = _eval_monomial(seg['ay'], u)
            z = _eval_monomial(seg['az'], u)
            pts.append((x, y, z))
    return pts


def decode_curve_entity(entity):
    """
    Convenience: given a parsed entity dict {'command','params',...} for CURVE,
    return the decoded structure produced by _decode_curve_params.
    """
    if entity.get('command') != 'CURVE':
        raise ValueError("Entity is not a CURVE")
    return _decode_curve_params(entity.get('params', []))
