import os
import math
import reader
import index
import surf_eval as se

# Try multiple evaluation variants to diagnose SURF encoding mismatches.
# Run: python -m tools.diagnose_surf_encoding [examples/SURF_FLAE0001.vda]

EXAMPLE_PATH = os.path.join('examples', 'SURF_FLAE0001.vda')


def norm3(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)


def eval_poly2d(coeffs, u, v, transpose=False):
    # Fallback: evaluate coeffs as monomial matrix when not using se._eval_monomial2 directly
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
        for j in range(Kv):
            s += coeffs[i][j] * up[i] * vp[j]
    return s


def eval_patch_point_variant(p, uu, vv, *, transpose=False, flip_v=False):
    if flip_v:
        vv = 1.0 - vv
    # Our current representation is monomial with flat arrays; transpose not applicable here
    x, y, z = se._eval_monomial2(p['ax'], p['ay'], p['az'], p['jor'], p['kor'], uu, vv)
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

    # We assume seam between pt=0 and pt=1 for ps=0 if available
    patches = surf['patches']
    nps = surf['nps']
    npt = surf['npt']
    grid = {}
    for idx_p, p in enumerate(patches):
        ps = idx_p // npt
        pt = idx_p % npt
        grid[(ps, pt)] = p

    pL = grid.get((0, 0))
    pR = grid.get((0, 1))
    if not pL or not pR:
        print('Expected (ps,pt)=(0,0) and (0,1) patches not found')
        return

    variants = [
        ('normal', dict(transpose=False, flip_v=False)),
        ('flipV', dict(transpose=False, flip_v=True)),
    ]

    samples = 101
    for name, opts in variants:
        errs = []
        for k in range(samples):
            uu = k/(samples-1)
            a = eval_patch_point_variant(pL, uu, 1.0, **opts)
            b = eval_patch_point_variant(pR, uu, 0.0, **opts)
            errs.append(norm3(a, b))
        print(f'{name:>12}: seam max={max(errs):.6g} mean={sum(errs)/len(errs):.6g}')


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else EXAMPLE_PATH
    check_surf_variants(path)
