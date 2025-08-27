import os
import math
import reader
import index
import surf_eval as se

# Continuity checker for SURF seams
# Usage: python check_surf_continuity.py [path_to_vda]

EXAMPLE_PATH = os.path.join('examples', 'SURF_FLAE0001.vda')

def norm3(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

def eval_patch_point(p, uu, vv):
    x = se._eval_poly2d(p['coeffs_x'], uu, vv)
    y = se._eval_poly2d(p['coeffs_y'], uu, vv)
    z = se._eval_poly2d(p['coeffs_z'], uu, vv)
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
    nu = surf['nu']
    nv = surf['nv']
    print(f'SURF {surf_name}: nu={nu}, nv={nv}, patches={len(patches)}')

    # Build grid of patches by (u_idx, v_idx)
    grid = {(p['u_idx'], p['v_idx']): p for p in patches}

    samples = 101
    # Check seams along v (between v_idx and v_idx+1 at constant u_idx)
    for ui in range(nu):
        for vj in range(nv-1):
            pL = grid[(ui, vj)]
            pR = grid[(ui, vj+1)]
            errs = []
            for k in range(samples):
                uu = k/(samples-1)
                a = eval_patch_point(pL, uu, 1.0)  # right edge of left patch
                b = eval_patch_point(pR, uu, 0.0)  # left edge of right patch
                errs.append(norm3(a,b))
            print(f' seam (u_idx={ui}, v={vj}|{vj+1}) max={max(errs):.6g} mean={sum(errs)/len(errs):.6g}')

    # Check seams along u (between u_idx and u_idx+1 at constant v_idx)
    for vi in range(nv):
        for uj in range(nu-1):
            pB = grid[(uj, vi)]
            pT = grid[(uj+1, vi)]
            errs = []
            for k in range(samples):
                vv = k/(samples-1)
                a = eval_patch_point(pB, 1.0, vv)  # top edge of bottom patch
                b = eval_patch_point(pT, 0.0, vv)  # bottom edge of top patch
                errs.append(norm3(a,b))
            print(f' seam (v_idx={vi}, u={uj}|{uj+1}) max={max(errs):.6g} mean={sum(errs)/len(errs):.6g}')

    return 0

if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else EXAMPLE_PATH
    raise SystemExit(check_surf(path))
