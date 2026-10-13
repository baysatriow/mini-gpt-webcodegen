"""Shared task input serialization for training and inference."""
from .serialization import canonical


def plan_prompt(request):
    rules = ('Salin nilai business_facts dengan kind name secara persis ke title. '
             'Salin genre dan style_mode dari request tanpa perubahan.')
    return 'PLAN\n' + rules + '\n' + canonical(request)


def section_prompt(request, plan, descriptor):
    name = next(f['value'] for f in request['business_facts'] if f['kind'] == 'name')
    facts = [f for f in request['business_facts'] if f['id'] in descriptor['fact_ids']]
    summary = {'name': name, 'section': descriptor, 'facts': facts}
    if descriptor['role'] in ('navigation', 'hero', 'footer', 'pricing'):
        summary['links'] = [[s['id'], s['role']] for s in plan['sections']]
    rules = 'Gunakan hanya fakta ini; jangan tambah item atau klaim.'
    if descriptor['role'] in ('navigation', 'hero', 'footer'):
        rules += f' Salin nama usaha persis: {name}.'
    return 'SECTION\n' + rules + '\n' + canonical(summary)


def retry_prompt(prompt, error):
    return prompt + '\nRETRY\n' + str(error)[:160]
