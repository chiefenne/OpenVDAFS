"""
Decoders for VDA-FS CONS (curve on surface) and FACE entities.

This implements a pragmatic parser to pull out references and loop structures
for plotting and grouping. Geometry trimming is not performed here.
"""

from typing import Any, Dict, List, Tuple

Number = float


def decode_cons_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a CONS (curve-on-surface) entity.

    Layout handled (as seen in examples):
      CONS / SRnn, CVmm, t_start, t_end,
        n, (pars[n+1]),
        for k in 0..n-1: K, (K coeffs for s), (K coeffs for t)

    The per-segment s/t mappings are monomials evaluated over local u in [0,1].
    Returns a dict with pcurve mapping:
      {
        'surf': 'SRnn',
        'curve': 'CVmm',
        't_range': (t_start, t_end),
        'pc': {
           'n': n,
           'pars': [...],
           'segments': [ {'order':K, 'as': [...], 'at': [...], 't0': pars[i], 't1': pars[i+1]} ... ]
        }
      }
    """
    if entity.get('command') != 'CONS':
        raise ValueError("Entity is not a CONS")
    params = entity.get('params', [])
    if len(params) < 2:
        raise ValueError("CONS is missing SR/CV references")
    i = 0
    surf = params[i]; i += 1
    curve = params[i]; i += 1
    if not (isinstance(surf, str) and surf.startswith('SR')):
        raise ValueError("CONS first param must be SR reference")
    if not (isinstance(curve, str) and curve.startswith('CV')):
        raise ValueError("CONS second param must be CV reference")

    # Optional t_start, t_end (curve parameter range)
    t_start = None; t_end = None
    if i + 1 < len(params) and isinstance(params[i], (int, float)) and isinstance(params[i+1], (int, float)):
        t_start = float(params[i]); t_end = float(params[i+1]); i += 2

    # Number of segments for the pcurve mapping
    if i >= len(params) or not isinstance(params[i], (int, float)):
        # No mapping found; return minimal info
        return {'surf': surf, 'curve': curve, 't_range': (t_start, t_end), 'pc': None}
    try:
        n = _as_int(params[i]); i += 1
    except Exception:
        return {'surf': surf, 'curve': curve, 't_range': (t_start, t_end), 'pc': None}

    # Parameter vector of length n+1
    if i + (n + 1) > len(params):
        return {'surf': surf, 'curve': curve, 't_range': (t_start, t_end), 'pc': None}
    pars = []
    for _ in range(n + 1):
        pars.append(float(params[i])); i += 1

    segments = []
    for k in range(n):
        if i >= len(params) or not isinstance(params[i], (int, float)):
            break
        K = _as_int(params[i]); i += 1
        if i + K > len(params):
            break
        as_coeff = [float(params[i + j]) for j in range(K)]
        i += K
        if i + K > len(params):
            break
        at_coeff = [float(params[i + j]) for j in range(K)]
        i += K
        segments.append({'order': K, 'as': as_coeff, 'at': at_coeff, 't0': float(pars[k]), 't1': float(pars[k + 1])})

    pc = {'n': len(segments), 'pars': pars, 'segments': segments}
    return {'surf': surf, 'curve': curve, 't_range': (t_start, t_end), 'pc': pc}


def _as_int(x: Any) -> int:
    if isinstance(x, int):
        return x
    try:
        return int(round(float(x)))
    except Exception:
        raise ValueError(f"Expected integer, got {x!r}")


def decode_face_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a FACE entity.

    Pragmatic parser for the common form:
      FACE / SRnnn, [nloops?], count1, (CNxxx, u, v)*count1, count2, (CNyyy, u, v)*count2, ...

    Returns:
      {
        'surf': 'SRnnn',
        'loops': [ {'count': k, 'items': [ {'cons': 'CN..', 'u': u0, 'v': v0}, ... ]}, ... ]
      }

    Notes:
      - Some files include an explicit nloops just after SR; we skip it if present.
      - We only validate types lightly; unknown tails are ignored.
    """
    if entity.get('command') != 'FACE':
        raise ValueError("Entity is not a FACE")
    params = entity.get('params', [])
    if not params:
        raise ValueError("FACE missing parameters")
    surf = params[0]
    if not (isinstance(surf, str) and surf.startswith('SR')):
        raise ValueError("FACE first param must be SR reference")

    loops: List[Dict[str, Any]] = []
    i = 1

    # Detect and skip optional explicit loop count
    if i < len(params) and isinstance(params[i], (int, float)):
        # Peek ahead to decide if this looks like nloops (followed by another int)
        try:
            nloops = _as_int(params[i])
            if i + 1 < len(params) and isinstance(params[i + 1], (int, float)):
                # treat as explicit count and skip it; we'll parse by counts anyway
                i += 1
        except Exception:
            pass

    # Parse repeated: count, then count blocks of (CNref, u, v)
    while i < len(params):
        # A count must be numeric
        if not isinstance(params[i], (int, float)):
            break
        try:
            cnt = _as_int(params[i])
        except Exception:
            break
        i += 1
        items = []
        for _ in range(cnt):
            if i + 2 >= len(params):
                break
            cons_ref = params[i]; i += 1
            u = params[i]; i += 1
            v = params[i]; i += 1
            if not (isinstance(cons_ref, str) and cons_ref.startswith('CN')):
                # Not a CONS reference; stop parsing this loop
                i -= 3
                break
            items.append({'cons': cons_ref, 'u': float(u), 'v': float(v)})
        if items:
            loops.append({'count': len(items), 'items': items})
        else:
            # no valid items parsed, stop
            break

    return {
        'surf': surf,
        'loops': loops
    }
