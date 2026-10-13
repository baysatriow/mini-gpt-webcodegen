"""Write new closed schemas; preserve the original PageSpec v1 file."""
import argparse
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from src.fullpage.schema_definitions import build_schemas, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    for name, schema in build_schemas().items():
        Draft202012Validator.check_schema(schema)
        path = ROOT / f'configs/fullpage/{name}.schema.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(schema, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        print(f'{name}: {path.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
