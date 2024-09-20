import re

def validate_id(id: str) -> bool:
    # Allow empty ids
    return not id or re.match(r'^[A-Za-z0-9]+(?:[ _-][A-Za-z0-9]+)*$', id) is not None

validateId = validate_id