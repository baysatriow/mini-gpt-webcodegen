"""Execute the new notebooks using the actual project kernel, without training."""
import argparse
import json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from src.fullpage.curriculum import write_json
from src.data.sources import sha256_file


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--only',choices=['10','11','all'],default='all'); p.add_argument('--report',default='reports/fullpage/NOTEBOOK_EXECUTION.json')
    args=p.parse_args(); root=args.root.resolve(); results=[]
    for prefix,name in [('10','10_fullpage_data_context_dan_gpu.ipynb'),('11','11_fullpage_training_dan_generation.ipynb')]:
        if args.only not in ('all',prefix): continue
        path=root/'notebooks'/name; nb=nbformat.read(path,as_version=4); nbformat.validate(nb)
        NotebookClient(nb,timeout=180,kernel_name='mini-gpt-webcodegen',resources={'metadata':{'path':str(root)}}).execute()
        nbformat.validate(nb); nbformat.write(nb,path)
        results.append({'path':str(path.relative_to(root)),'sha256':sha256_file(path),'executed_code_cells':sum(c.cell_type=='code' and c.execution_count is not None for c in nb.cells),
                        'errors':sum(o.output_type=='error' for c in nb.cells if c.cell_type=='code' for o in c.get('outputs',[]))})
    write_json(root/args.report,{'kernel':'mini-gpt-webcodegen','training_started_by_notebook':False,'notebooks':results}); print(json.dumps(results,indent=2))


if __name__=='__main__': main()
