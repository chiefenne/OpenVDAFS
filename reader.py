# Minimal VDA-FS reader — simple and readable.
# - Uses only columns 1..72 for data (73..80 are sequence numbers)
# - Skips lines starting with "$$" (after optional spaces)
# - Merges records into statements by detecting "NAME = WORD"
# - Parses "NAME = COMMAND / params"
# - Parameters: try int/float else keep string (so SR85, CV57 remain strings)
# - Special handling: HEADER / N reads the next N raw records
# - END stops parsing

import re

_stmt_start = re.compile(r'^\s*[A-Z][A-Z0-9]{0,7}\s*=\s*[A-Z]+')
_stmt_parse = re.compile(r'^\s*([A-Z][A-Z0-9]{0,7})\s*=\s*([A-Z]+)\s*(?:/\s*(.*))?\s*$')

def _is_comment(s):
    return s.lstrip().startswith('$$')

def _iter_records(path):
    with open(path, 'r', encoding='latin-1') as f:
        for i, raw in enumerate(f, start=1):
            if raw.endswith('\n'):
                raw = raw[:-1]
            yield i, raw

def _coalesce_statements(records):
    buf = []
    start_no = None

    def flush(end_no):
        nonlocal buf, start_no
        if buf:
            merged = ''.join(buf)
            out = (start_no, end_no, merged)
            buf = []
            start_no = None
            return out
        return None

    for lineno, raw in records:
        data = raw[:72]  # only data columns
        # Stop coalescing when encountering END (standalone terminator)
        if data.strip().upper() == 'END':
            flushed = flush(lineno - 1)
            if flushed:
                yield flushed
            break
        if not data.strip() or _is_comment(data):
            continue

        if _stmt_start.match(data):
            if buf:
                flushed = flush(lineno - 1)
                if flushed:
                    yield flushed
            start_no = lineno
            buf.append(data)
        else:
            if start_no is None:
                # skip stray text
                continue
            buf.append(data)

    if buf:
        flushed = flush(records[-1][0] if records else 0)
        if flushed:
            yield flushed

def _to_number(tok):
    t = tok.strip()
    if t == '':
        return t
    if re.match(r'^[\+\-]?\d+$', t):
        try:
            return int(t)
        except:
            pass
    try:
        return float(t)
    except:
        return t

def _split_params(s):
    if s is None or s.strip() == '':
        return []
    parts = [p.strip() for p in s.split(',')]
    out = []
    for p in parts:
        if p == '':
            continue
        # Keep references like SR85, CV57 as strings; numbers to numeric
        if re.match(r'^[A-Z]{2}\d+$', p):
            out.append(p)
        else:
            out.append(_to_number(p))
    return out

def read_vdafs(path):
    recs = list(_iter_records(path))
    ln_to_text = {ln: tx for ln, tx in recs}

    header = None
    entities = []

    for ln0, ln1, text in _coalesce_statements(recs):
        m = _stmt_parse.match(text)
        if not m:
            continue
        name, word, rest = m.group(1), m.group(2), m.group(3)

        if word == 'HEADER':
            n = 0
            if rest:
                # Extract leading integer count even if coalesced text follows
                m_hdr = re.match(r"\s*([\+\-]?\d+)", rest)
                if m_hdr:
                    try:
                        n = int(m_hdr.group(1))
                    except Exception:
                        n = 0
            lines = []
            # Always read the next N raw records starting immediately after the HEADER statement line
            ln0_int = ln0 if isinstance(ln0, int) else int(ln0 or 0)
            ln = ln0_int + 1
            for _ in range(max(0, n)):
                lines.append(ln_to_text.get(ln, ''))
                ln += 1
            header = {
                'name': name,
                'n_lines': n,
                'lines': lines,
                'lineno_start': ln0_int,
                'lineno_end': ln0_int + n
            }
            continue

        if word == 'END':
            break

        params = _split_params(rest)
        entities.append({
            'name': name,
            'command': word,
            'params': params,
            'raw': text,
            'lineno_start': ln0,
            'lineno_end': ln1
        })

    return {
        'path': path,
        'header': header,
        'entities': entities
    }
