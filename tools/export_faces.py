"""Export selected FACE entities and their dependencies to new VDA-FS files.

Writes:
- HEADER (copied from source, with same name and line count)
- SURF referenced by FACE
- All CONS referenced by FACE loops
- All CURVE referenced by those CONS
- The FACE itself
- END

Entities are written using their original 'raw' statement text on single lines.
"""
from __future__ import annotations

import os
from typing import Dict, List, Set

import face_eval as fe


def _collect_face_deps(model: Dict, idx: Dict, face_name: str) -> List[str]:
    by_name = idx['by_name']
    face = by_name.get(face_name)
    if not face or face.get('command') != 'FACE':
        raise KeyError(f"FACE not found: {face_name}")

    f = fe.decode_face_entity(face)
    needed: List[str] = []
    seen: Set[str] = set()

    def add(nm: str):
        if nm and nm not in seen:
            seen.add(nm)
            needed.append(nm)

    # SURF first
    add(f['surf'])
    # CONS and CURVE
    for loop in f.get('loops', []):
        for it in loop.get('items', []):
            cn = it.get('cons')
            add(cn)
            ecn = by_name.get(cn)
            if ecn and ecn.get('command') == 'CONS':
                d = fe.decode_cons_entity(ecn)
                cv = d.get('curve')
                if isinstance(cv, str):
                    add(cv)
    # FACE last
    add(face_name)
    return needed


essential_order = ('CURVE', 'SURF', 'CONS', 'FACE')


def write_face_file(model: Dict, idx: Dict, face_name: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    deps = _collect_face_deps(model, idx, face_name)

    header = model.get('header')
    lines: List[str] = []
    if header:
        hname = header.get('name', 'HD')
        n = int(header.get('n_lines') or 0)
        lines.append(f"{hname} = HEADER / {n}")
        for ln in header.get('lines', [])[:n]:
            lines.append(ln)

    # Group dependencies in desired order: CURVE, SURF, CONS, FACE
    by_name = idx['by_name']

    def _names_by_cmd(cmd: str) -> List[str]:
        return [nm for nm in deps if (by_name.get(nm) or {}).get('command') == cmd]

    ordered: List[str] = []
    for cmd in essential_order:
        if cmd == 'FACE':
            if face_name in deps:
                ordered.append(face_name)
        else:
            ordered.extend(sorted(_names_by_cmd(cmd)))

    for nm in ordered:
        e = by_name.get(nm)
        if not e:
            continue
        raw = e.get('raw')
        if not raw:
            continue
        for chunk in _wrap_72(raw):
            lines.append(chunk)

    lines.append('END')

    with open(out_path, 'w', encoding='latin-1') as f:
        for ln in lines:
            if not ln.endswith('\n'):
                f.write(ln + '\n')
            else:
                f.write(ln)


def _wrap_72(text: str) -> List[str]:
    """Split a single statement string into 72-char data lines.
    Columns 73.. are omitted (reader ignores them anyway).
    """
    s = text.rstrip('\n')
    out: List[str] = []
    while s:
        out.append(s[:72])
        s = s[72:]
    if not out:
        out = ['']
    return out
