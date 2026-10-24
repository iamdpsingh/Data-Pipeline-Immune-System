import json
from pathlib import Path

def test_schema_json_parseable():
    schemas = list(Path("schemas").glob("**/*.json"))
    assert len(schemas) > 0
    for s in schemas:
        with open(s) as fp:
            data = json.load(fp)
            assert isinstance(data, dict)
