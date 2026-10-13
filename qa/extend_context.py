"""Create a new 2048-position initialization from the verified project model."""
import argparse
import json
from pathlib import Path
from src.training.context_extension import extend_project_context
from src.fullpage.schema_definitions import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--report', type=Path, default=Path('reports/training/INIT-2048-001.json'))
    args = parser.parse_args()
    root = args.root.resolve()
    report_path = root / args.report
    if report_path.exists(): raise ValueError('Report exists')
    report = extend_project_context(root / args.source, root / args.output, root=root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2); handle.write('\n')
    config_path = root / 'configs/model_fullpage_2048.json'
    with config_path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report['model_config'], handle, indent=2); handle.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('lineage', 'unchanged_tensors')}, indent=2))


if __name__ == '__main__':
    main()
