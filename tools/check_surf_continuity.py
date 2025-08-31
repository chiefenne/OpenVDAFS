import os
import math
import reader
import index
import surf_eval as se

# Continuity checker for SURF seams
# Usage: python -m tools.check_surf_continuity [path_to_vda]

EXAMPLE_PATH = os.path.join('examples', 'SURF_FLAE0001.vda')

def norm3(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

def eval_patch_point(p, uu, vv):
    # p is a monomial patch dict with keys: ax, ay, az, jor, kor
    x, y, z = se._eval_monomial2(p['ax'], p['ay'], p['az'], p['jor'], p['kor'], uu, vv)
    return (x, y, z)

def check_surf(path):
    model = reader.read_vdafs(path)
    idx = index.build_index(model)
    # find first SURF
    surf_name = next((nm for nm in idx['by_type'].get('SURF', [])), None)
    if not surf_name:
        print('No SURF found')
        return 1
    e = idx['by_name'][surf_name]
    surf = se.decode_surf_entity(e)

    patches = surf['patches']
    nps = surf['nps']
    npt = surf['npt']
    print(f'SURF {surf_name}: nps={nps}, npt={npt}, patches={len(patches)}')

    # Build grid of patches by (ps, pt) from enumeration order
    grid = {}
    for idx_p, p in enumerate(patches):
        ps = idx_p // npt
        pt = idx_p % npt
        grid[(ps, pt)] = p

    samples = 101
    # Check seams along v (between v_idx and v_idx+1 at constant u_idx)
    for ps in range(nps):
        for pt in range(npt-1):
            pL = grid[(ps, pt)]
            pR = grid[(ps, pt+1)]
            errs = []
            for k in range(samples):
                uu = k/(samples-1)
                a = eval_patch_point(pL, uu, 1.0)  # right edge of left patch
                b = eval_patch_point(pR, uu, 0.0)  # left edge of right patch
                errs.append(norm3(a,b))
            print(f' seam (ps={ps}, pt={pt}|{pt+1}) max={max(errs):.6g} mean={sum(errs)/len(errs):.6g}')

    # Check seams along u (between u_idx and u_idx+1 at constant v_idx)
    for pt in range(npt):
        for ps in range(nps-1):
            pB = grid[(ps, pt)]
            pT = grid[(ps+1, pt)]
            errs = []
            for k in range(samples):
                vv = k/(samples-1)
                a = eval_patch_point(pB, 1.0, vv)  # top edge of bottom patch
                b = eval_patch_point(pT, 0.0, vv)  # bottom edge of top patch
                errs.append(norm3(a,b))
            print(f' seam (pt={pt}, ps={ps}|{ps+1}) max={max(errs):.6g} mean={sum(errs)/len(errs):.6g}')

    return 0

if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else EXAMPLE_PATH
    raise SystemExit(check_surf(path))
