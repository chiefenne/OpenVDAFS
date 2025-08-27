import os
import math
import reader
import index
import surf_eval as se

# Try multiple evaluation variants to diagnose SURF encoding mismatches.
# Run: python diagnose_surf_encoding.py [examples/SURF_FLAE0001.vda]

EXAMPLE_PATH = os.path.join('examples', 'SURF_FLAE0001.vda')


def norm3(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)


def eval_poly2d(coeffs, u, v, transpose=False):
    if not transpose:
        return se._eval_poly2d(coeffs, u, v)
    # Transposed: interpret given matrix as [v][u]
    Ku = len(coeffs)
    Kv = len(coeffs[0]) if Ku > 0 else 0
    # build transposed view on the fly without copying
    up = [1.0]
    for _ in range(1, Kv):
        up.append(up[-1] * u)
    vp = [1.0]
    for _ in range(1, Ku):
        vp.append(vp[-1] * v)
    s = 0.0
    for j in range(Kv):
        vj = vp[j] if j < len(vp) else (v ** j)
        for i in range(Ku):
            s += coeffs[i][j] * up[j] * vj
    return s


def eval_patch_point_variant(p, uu, vv, *, use_global=False, transpose=False, flip_v=False, centered_m11=False, offset_only=False):
    # uu,vv are local in [0,1] along the patch edge by construction
    if flip_v:
        vv = 1.0 - vv
    if use_global:
        u = p['u0'] + uu * (p['u1'] - p['u0'])
        v = p['v0'] + vv * (p['v1'] - p['v0'])
    else:
        u, v = uu, vv

    # Apply alternative mappings expected by some specs/tools
    if centered_m11:
        # Map local 0..1 -> -1..+1, equivalent to centering and scaling by half-range
        u = 2.0 * uu - 1.0
        v = 2.0 * vv - 1.0
    elif offset_only:
        # Use offsets from patch minima without scaling to unit length
        # Effectively u' = (global_u - u0), v' = (global_v - v0)
        ug = p['u0'] + uu * (p['u1'] - p['u0'])
        vg = p['v0'] + vv * (p['v1'] - p['v0'])
        u = ug - p['u0']
        v = vg - p['v0']

    x = eval_poly2d(p['coeffs_x'], u, v, transpose=transpose)
    y = eval_poly2d(p['coeffs_y'], u, v, transpose=transpose)
    z = eval_poly2d(p['coeffs_z'], u, v, transpose=transpose)
    return (x, y, z)


def check_surf_variants(path):
    model = reader.read_vdafs(path)
    idx = index.build_index(model)
    surf_name = next((nm for nm in idx['by_type'].get('SURF', [])), None)
    if not surf_name:
        print('No SURF found')
        return
    e = idx['by_name'][surf_name]
    surf = se.decode_surf_entity(e)

    # We assume seam along v between v_idx=0 and v_idx=1 for u_idx=0
    grid = {(p['u_idx'], p['v_idx']): p for p in surf['patches']}
    pL = grid.get((0, 0))
    pR = grid.get((0, 1))
    if not pL or not pR:
        print('Expected (0,0) and (0,1) patches not found')
        return

    variants = [
        ('local,normal', dict(use_global=False, transpose=False, flip_v=False)),
        ('local,transpose', dict(use_global=False, transpose=True, flip_v=False)),
        ('local,flipV', dict(use_global=False, transpose=False, flip_v=True)),
        ('local,transpose+flipV', dict(use_global=False, transpose=True, flip_v=True)),
        ('local,centered[-1,1]', dict(use_global=False, centered_m11=True)),
        ('local,centered[-1,1],flipV', dict(use_global=False, centered_m11=True, flip_v=True)),
        ('offset-only (u-u0,v-v0)', dict(offset_only=True)),
        ('offset-only+flipV', dict(offset_only=True, flip_v=True)),
        ('global,normal', dict(use_global=True, transpose=False, flip_v=False)),
        ('global,transpose', dict(use_global=True, transpose=True, flip_v=False)),
        ('global,flipV', dict(use_global=True, transpose=False, flip_v=True)),
        ('global,transpose+flipV', dict(use_global=True, transpose=True, flip_v=True)),
    ]

    samples = 101
    for name, opts in variants:
        errs = []
        for k in range(samples):
            uu = k/(samples-1)
            a = eval_patch_point_variant(pL, uu, 1.0, **opts)
            b = eval_patch_point_variant(pR, uu, 0.0, **opts)
            errs.append(norm3(a, b))
        print(f'{name:>24}: seam max={max(errs):.6g} mean={sum(errs)/len(errs):.6g}')


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else EXAMPLE_PATH
    check_surf_variants(path)
