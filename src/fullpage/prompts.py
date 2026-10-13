"""Shared task input serialization for training and inference."""
from .serialization import canonical


def plan_prompt(request):
    return 'PLAN\n' + canonical(request)


def section_prompt(request, plan, descriptor):
    name = next(f['value'] for f in request['business_facts'] if f['kind'] == 'name')
    facts = [f for f in request['business_facts'] if f['id'] in descriptor['fact_ids']]
    summary = {'name': name, 'section': descriptor, 'facts': facts}
    if descriptor['role'] in ('navigation', 'hero', 'footer', 'pricing'):
        summary['links'] = [[s['id'], s['role']] for s in plan['sections']]
    return 'SECTION\n' + canonical(summary)


def retry_prompt(prompt, error):
    return prompt + '\nRETRY\n' + str(error)[:160]
