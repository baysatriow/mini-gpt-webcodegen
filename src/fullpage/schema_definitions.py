"""Build closed v2 schemas from a snapshot of the supported v1 components."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ID = {'type': 'string', 'pattern': '^[a-z][a-z0-9_-]{0,63}$'}
TYPES = ('navbar', 'hero', 'feature_grid', 'text_section', 'testimonial', 'pricing_table', 'contact_form', 'footer')
ROLES = ('navigation', 'hero', 'about', 'services', 'benefits', 'process', 'faq', 'values', 'portfolio', 'team', 'pricing', 'testimonials', 'contact', 'footer')
VARIANTS = {'navbar': ('inline',), 'hero': ('centered', 'split'), 'feature_grid': ('cards', 'numbered'),
            'text_section': ('prose', 'split'), 'testimonial': ('quote',), 'pricing_table': ('cards',),
            'contact_form': ('panel',), 'footer': ('columns',)}
ROLE_TYPES = {'navigation': {'navbar'}, 'hero': {'hero'}, 'about': {'text_section'},
              'services': {'feature_grid'}, 'benefits': {'feature_grid'}, 'process': {'feature_grid'},
              'faq': {'feature_grid'}, 'values': {'text_section', 'feature_grid'},
              'portfolio': {'feature_grid'}, 'team': {'feature_grid'}, 'pricing': {'pricing_table'},
              'testimonials': {'testimonial'}, 'contact': {'contact_form'}, 'footer': {'footer'}}
REQUIRED_ROLES = {'landing_page': {'navigation', 'hero', 'about', 'services', 'benefits', 'process', 'faq', 'contact', 'footer'},
                  'company_profile': {'navigation', 'hero', 'about', 'values', 'services', 'process', 'contact', 'footer'}}


def text(limit=180):
    return {'type': 'string', 'minLength': 1, 'maxLength': limit}


def closed(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required,
            'additionalProperties': False}


def array(items, minimum=0, maximum=16):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


def build_schemas():
    old = json.loads((ROOT / 'configs/page_spec.schema.json').read_text(encoding='utf-8'))
    media = closed({'asset_id': ID, 'alt': text(180), 'caption': text(240)}, ['asset_id', 'alt'])
    components = []
    for original in old['properties']['sections']['items']['oneOf']:
        component = copy.deepcopy(original)
        kind = component['properties']['type']['const']
        component['properties'].update(role={'enum': list(ROLES)}, variant={'enum': list(VARIANTS[kind])})
        component['required'] += ['role', 'variant']
        props = component['properties']['props']
        if kind in ('hero', 'text_section'):
            props['properties']['media'] = copy.deepcopy(media)
        if kind == 'feature_grid':
            props['properties']['items']['items']['properties']['media'] = copy.deepcopy(media)
        components.append(component)
    defs = copy.deepcopy(old['$defs'])
    defs['component'] = {'oneOf': components}
    metadata = {'$schema': old['$schema']}
    refs = array(ID, 0, 12)
    pair = closed({'title': text(100), 'text': text(1000)})
    fact_values = {'name': text(100), 'description': text(3000), 'value': text(1000),
                   'service': pair, 'project': pair, 'team': pair, 'process': pair, 'faq': pair,
                   'contact': copy.deepcopy(defs['link']),
                   'price': copy.deepcopy(next(c for c in components if c['properties']['type']['const'] == 'pricing_table')['properties']['props']['properties']['plans']['items']),
                   'testimonial': closed({'quote': text(1000), 'author': text(100)})}
    facts = {'oneOf': [closed({'id': ID, 'kind': {'const': kind}, 'value': value}) for kind, value in fact_values.items()]}
    request = closed({'request_id': ID, 'prompt': text(1000), 'genre': {'enum': list(REQUIRED_ROLES)},
                      'style_mode': {'enum': ['plain_css', 'tailwind']}, 'business_facts': array(facts, 3, 24),
                      'asset_ids': refs, 'fictitious': {'type': 'boolean'}},
                     ['request_id', 'prompt', 'genre', 'style_mode', 'business_facts', 'asset_ids', 'fictitious'])
    descriptor = {'type': 'array', 'prefixItems': [ID, {'enum': list(TYPES)}, {'enum': list(ROLES)},
                  {'enum': sorted({v for values in VARIANTS.values() for v in values})}, refs, refs],
                  'items': False, 'minItems': 6, 'maxItems': 6}
    appearance = {key: copy.deepcopy(old['properties'][key]) for key in ('title', 'language', 'style_mode', 'theme')}
    appearance['language'] = {'const': 'id'}
    plan = closed({'schema_version': {'const': '1.0'}, 'genre': {'enum': list(REQUIRED_ROLES)},
                   **appearance, 'sections': array(descriptor, 8, 16)})
    section = {'oneOf': components}
    page = closed({'schema_version': {'const': '2.0'}, 'genre': {'enum': list(REQUIRED_ROLES)},
                   **appearance, 'sections': array({'$ref': '#/$defs/component'}, 8, 16),
                   'interactions': copy.deepcopy(old['properties']['interactions']), 'fictitious': {'type': 'boolean'}})
    return {name: {**metadata, '$id': 'urn:mini-gpt-webcodegen:fullpage:' + name + ':1',
                   **value, '$defs': copy.deepcopy(defs)} for name, value in
            {'request': request, 'plan': plan, 'section': section, 'page': page}.items()}
