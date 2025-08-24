# Queries over the indexed model: list names by type, get entity by name.

def list_names_by_type(idx, entity_type):
    # entity_type in uppercase, e.g., "CURVE", "SURF", "POINT", "PSET", "MDI", etc.
    return idx['by_type'].get(entity_type.upper(), [])

def get_entity(idx, name):
    return idx['by_name'].get(name)
