"""Closed schemas plus semantic checks for page tasks; never repair outputs."""
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from src.data.schema import INTERACTION_TARGETS, validate_page_spec
from .schema_definitions import REQUIRED_ROLES, ROLE_TYPES, VARIANTS
from .serialization import canonical, decode_plan

ROOT = Path(__file__).resolve().parents[2]


def contains_name(text, name):
    """Preserve the complete literal name, including its final word boundary."""
    return isinstance(text, str) and isinstance(name, str) and bool(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text))


@lru_cache(maxsize=4)
def validator(name):
    schema = json.loads((ROOT / f'configs/fullpage/{name}.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def schema_errors(name, value):
    return [f'{name}:{list(e.absolute_path)}: {e.message}' for e in validator(name).iter_errors(value)]


def unsafe_links(value):
    errors = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'href' and isinstance(item, str):
                try:
                    parsed = urlsplit(item)
                    hostname = parsed.hostname
                except ValueError:
                    errors.append('Malformed URL')
                    continue
                if item.startswith('#'):
                    if len(item) == 1:
                        errors.append('Empty anchor')
                elif parsed.scheme not in ('https', 'mailto', 'tel') or (parsed.scheme == 'https' and (not hostname or parsed.username or parsed.password)):
                    errors.append('Unsafe link: ' + item)
                if any(c in item for c in '<>"\r\n'):
                    errors.append('Unsafe link characters')
            errors.extend(unsafe_links(item))
    elif isinstance(value, list):
        for item in value:
            errors.extend(unsafe_links(item))
    return errors


def validate_request(request, catalog):
    errors = schema_errors('request', request)
    if errors:
        return errors
    facts = request['business_facts']
    if len({f['id'] for f in facts}) != len(facts):
        errors.append('Duplicate business fact id')
    for kind in ('name', 'description'):
        if sum(f['kind'] == kind for f in facts) != 1:
            errors.append('missing_information: exactly one ' + kind + ' required')
    if not any(f['kind'] == 'service' for f in facts):
        errors.append('missing_information: service required')
    assets = catalog.get('assets', {})
    if len(set(request['asset_ids'])) != len(request['asset_ids']) or any(a not in assets for a in request['asset_ids']):
        errors.append('Unknown or duplicate request asset id')
    from src.data.tokenizer import SPECIAL_TOKENS
    if any(token in canonical(request) for token in SPECIAL_TOKENS):
        errors.append('Reserved delimiter in request')
    return errors + unsafe_links(request)


def validate_plan_wire(wire, request, catalog):
    errors = validate_request(request, catalog) + schema_errors('plan', wire)
    if errors:
        return errors
    plan = decode_plan(wire)
    name = next(f['value'] for f in request['business_facts'] if f['kind'] == 'name')
    if plan['genre'] != request['genre'] or plan['style_mode'] != request['style_mode'] or plan['title'] != name:
        errors.append('Plan request identity/style mismatch')
    ids = [s['id'] for s in plan['sections']]
    if len(set(ids)) != len(ids):
        errors.append('Duplicate section id')
    roles = [s['role'] for s in plan['sections']]
    if not REQUIRED_ROLES[plan['genre']] <= set(roles):
        errors.append('Missing required page roles')
    if roles[0] != 'navigation' or roles[-1] != 'footer':
        errors.append('Navbar/footer order mismatch')
    facts = {f['id'] for f in request['business_facts']}
    for s in plan['sections']:
        if s['type'] not in ROLE_TYPES[s['role']] or s['variant'] not in VARIANTS[s['type']]:
            errors.append('Incompatible role/type/variant: ' + s['id'])
        if not set(s['fact_ids']) <= facts or not set(s['asset_ids']) <= set(request['asset_ids']):
            errors.append('Unknown fact/asset reference: ' + s['id'])
        if len(set(s['fact_ids'])) != len(s['fact_ids']) or len(set(s['asset_ids'])) != len(s['asset_ids']):
            errors.append('Duplicate descriptor references: ' + s['id'])
    return errors


def media_ids(value):
    if isinstance(value, dict):
        return ([value['asset_id']] if 'asset_id' in value else []) + [a for v in value.values() for a in media_ids(v)]
    if isinstance(value, list):
        return [a for v in value for a in media_ids(v)]
    return []


def validate_section(section, descriptor, request, catalog):
    errors = schema_errors('section', section)
    if errors:
        return errors
    if any(section[key] != descriptor[key] for key in ('id', 'type', 'role', 'variant')):
        errors.append('Section descriptor identity mismatch')
    if section['type'] not in ROLE_TYPES[section['role']] or section['variant'] not in VARIANTS[section['type']]:
        errors.append('Section variant/type mismatch')
    if not set(media_ids(section)) <= set(descriptor['asset_ids']):
        errors.append('Unplanned media asset')
    name = next((f['value'] for f in request['business_facts'] if f['kind'] == 'name'), None)
    if section['type'] == 'navbar' and section['props']['brand'] != name:
        errors.append('Brand fact mismatch')
    if section['type'] == 'hero' and not contains_name(section['props']['heading'], name):
        errors.append('Hero brand fact mismatch')
    if section['type'] == 'footer' and not contains_name(section['props']['text'], name):
        errors.append('Footer brand fact mismatch')
    return errors + unsafe_links(section)


def validate_composed_page(spec):
    if isinstance(spec, dict) and spec.get('schema_version') == '1.0':
        return validate_page_spec(spec)
    errors = schema_errors('page', spec)
    if errors:
        return errors
    sections = {s['id']: s for s in spec['sections']}
    if len(sections) != len(spec['sections']):
        errors.append('Duplicate section id')
    roles = [s['role'] for s in spec['sections']]
    if roles[0] != 'navigation' or roles[-1] != 'footer' or not REQUIRED_ROLES[spec['genre']] <= set(roles):
        errors.append('Incomplete page roles/order')
    for s in sections.values():
        if s['type'] not in ROLE_TYPES[s['role']]:
            errors.append('Incompatible role/type')
    def anchors(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == 'href' and isinstance(item, str) and item.startswith('#') and item[1:] not in sections:
                    errors.append('Unknown anchor: ' + item)
                anchors(item)
        elif isinstance(value, list):
            for item in value:
                anchors(item)
    anchors(spec)
    for action in spec['interactions']:
        if action['target_id'] not in sections or sections[action['target_id']]['type'] not in INTERACTION_TARGETS[action['type']]:
            errors.append('Invalid interaction target')
    return errors + unsafe_links(spec)
