"""Join validated raw sections without synthesizing missing model content."""
import copy
from .contracts import validate_plan_wire, validate_section, validate_composed_page
from .serialization import encode_plan


def values(value, key=None):
    if isinstance(value, dict):
        return [v for k,v in value.items() if key == k] + [x for v in value.values() for x in values(v, key)]
    if isinstance(value, list): return [x for v in value for x in values(v, key)]
    return [] if key is not None else [value]


def fact_errors(section, descriptor, request):
    errors = []; props = section['props']; leaves = values(props)
    by_id = {f['id']: f for f in request['business_facts']}
    for identifier in descriptor['fact_ids']:
        fact = by_id[identifier]; kind, value = fact['kind'], fact['value']
        if kind in ('description', 'value') and value not in leaves:
            errors.append('Required fact text mismatch: ' + identifier)
        elif kind in ('service', 'project', 'team', 'process', 'faq'):
            if not any(item.get('heading') == value['title'] and item.get('text') == value['text'] for item in props.get('items', [])):
                errors.append('Required fact item mismatch: ' + identifier)
        elif kind == 'price' and value not in props.get('plans', []): errors.append('Required price mismatch: ' + identifier)
        elif kind == 'testimonial' and value not in props.get('items', []): errors.append('Required testimonial mismatch: ' + identifier)
        elif kind == 'contact' and value not in values(props, 'links') and value not in values(props, 'button'):
            if value not in [link for links in values(props, 'links') for link in links]: errors.append('Required contact mismatch: ' + identifier)
    allowed_prices = [f['value'] for f in by_id.values() if f['kind'] == 'price']
    if any(p not in allowed_prices for p in props.get('plans', [])): errors.append('Unprovided price')
    allowed_hrefs = set(values(request, 'href'))
    if any(not href.startswith('#') and href not in allowed_hrefs for href in values(props, 'href')): errors.append('Unprovided external contact/link')
    if section['type'] == 'hero' and props.get('layout', 'centered') != section['variant']: errors.append('Hero variant/layout mismatch')
    return errors


def compose_page(plan, sections, request, catalog):
    errors = validate_plan_wire(encode_plan(plan), request, catalog)
    if errors: raise ValueError(errors)
    if [s.get('id') for s in sections] != [d['id'] for d in plan['sections']]: raise ValueError('Section order/count mismatch')
    referenced = {r for d in plan['sections'] for r in d['fact_ids']}
    essential = {f['id'] for f in request['business_facts']}
    if not essential <= referenced: raise ValueError('Plan omits supplied facts: ' + ','.join(sorted(essential-referenced)))
    interactions = []
    for descriptor, section in zip(plan['sections'], sections, strict=True):
        errors += validate_section(section, descriptor, request, catalog) + fact_errors(section, descriptor, request)
        action = {'navigation': 'menu_toggle', 'contact': 'form_validate', 'faq': 'accordion'}.get(section['role'])
        if action: interactions.append({'type': action, 'target_id': section['id']})
    page = {'schema_version': '2.0', **{k: copy.deepcopy(plan[k]) for k in ('genre','title','language','style_mode','theme')},
            'sections': copy.deepcopy(sections), 'interactions': interactions, 'fictitious': request['fictitious']}
    errors += validate_composed_page(page)
    if errors: raise ValueError(errors)
    return page
