# Build simple indices over the parsed model for fast lookup.

def build_index(model):
    by_name = {}
    by_type = {}
    for e in model['entities']:
        nm = e['name']
        cmd = e['command']
        by_name[nm] = e
        bucket = by_type.get(cmd)
        if bucket is None:
            bucket = []
            by_type[cmd] = bucket
        bucket.append(nm)
    return {
        'by_name': by_name,
        'by_type': by_type
    }
