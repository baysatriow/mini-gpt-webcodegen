"""Record an immutable final result, runtime decision and executed-evidence notebook09."""
import argparse
from datetime import datetime, timezone
import json
import nbformat as nbf

from qa.diagnose_curriculum_copying import differences
from src.data.curriculum import ROOT
from src.data.sources import sha256_file, write_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--gallery-report', default=None)
    args = parser.parse_args(); run = args.run_id
    read = lambda path: json.loads((ROOT / path).read_text(encoding='utf-8'))
    selection = read(f'reports/training/{run}_FINAL_SELECTION.json')
    final = read(f'reports/training/{run}-FINAL_curriculum_evaluation.json')
    if (final['split'] != 'final' or final['checkpoint_sha256'] != selection['checkpoint_sha256']
            or final['prompt_file_sha256'] != selection['final_suite']['sha256']
            or final['decode_config'] != selection['decode']):
        raise ValueError('Final differs from frozen selection')
    if sha256_file(ROOT / final['outputs_path']) != final['outputs_sha256']: raise ValueError('Raw outputs changed')
    raw = read(final['outputs_path'])
    failures = [{'example_id': r['example_id'], 'recipe':r['recipe'], 'style_mode':r['target_spec']['style_mode'],
        'differences':differences(r['target_spec'],r['parsed_spec'])} for r in raw if not r['exact_contract']]
    gallery = read(args.gallery_report) if args.gallery_report else None
    if gallery and (not final['contract_gate_passed'] or gallery['checkpoint_sha256'] != final['checkpoint_sha256']):
        raise ValueError('Gallery requires a passed matching final')
    result = {'recorded_at_utc':datetime.now(timezone.utc).isoformat(), 'run_id':run,
        'selection_sha256':sha256_file(ROOT / f'reports/training/{run}_FINAL_SELECTION.json'),
        'final_report_sha256':sha256_file(ROOT / f'reports/training/{run}-FINAL_curriculum_evaluation.json'),
        'schema_valid':final['schema_valid'], 'exact_contract':final['exact_contract'], 'count':final['count'],
        'gate_passed':final['contract_gate_passed'], 'failures':failures,
        'selected_runtime':f'{run}/best' if final['contract_gate_passed'] else 'TRAIN-012/best',
        'checkpoint_sha256':final['checkpoint_sha256'], 'gallery_report':args.gallery_report,
        'exported_websites':gallery['output_count'] if gallery else 0,
        'status':'controlled-contract-passed' if final['contract_gate_passed'] else 'needs-model-work',
        'browser_evaluated':False, 'generator_ui_implemented':False,
        'limits':['Synthetic shared recipes with heldout fictional brands; arbitrary prompts/layouts not established',
                  'This final is now consumed; future tuning requires a new independent final',
                  'No retraining or checkpoint reselection from this result in AI-013',
                  'Browser review and application UI remain next stages']}
    destination = ROOT / f'reports/training/{run}_FINAL_GATE.json'
    report_path = ROOT / 'reports/FINAL_GATE_2026-10-13.md'
    notebook_path = ROOT / 'notebooks/09_evaluasi_final_dan_output.ipynb'
    if any(p.exists() for p in (destination,report_path,notebook_path)): raise ValueError('Preserve final evidence')
    write_manifest(destination,result)
    gallery_text = (f"[Gallery {gallery['output_count']} website](../{gallery['output_dir']}/index.html), "
        f"[ZIP hasil](../{gallery['output_dir']}/websites.zip). Hanya raw output yang valid dan sesuai kontrak diekspor; "
        f"{len(gallery['rejected'])} output ditolak. HTML/CSS/JS dan Tailwind lokal disediakan, tanpa substitusi target."
        if gallery else 'Gallery final tidak diekspor pada fase ini.')
    report_path.write_text(f'''# Gerbang final model, AI-013

Kandidat {run} best dikunci lewat best full validation CE dan development24/24exact sebelum evaluasi final. [Keputusan sebelum final](training/{run}_FINAL_SELECTION.json) mencatat checkpoint/decode/prompt hash. Hanya satu evaluasi final dilakukan, tanpa memilih ulang checkpoint atau melatih ulang dari hasilnya.

| Pengukuran final | Hasil |
| --- | --- |
| JSON/schema valid | {final['schema_valid']}/{final['count']} |
| Sesuai target persis | {final['exact_contract']}/{final['count']} ({final['exact_contract_rate']*100:.2f}%) |
| Link terselesaikan | {final['resolved_links']}/{final['count']} |
| Seluruh output EOS | {final['all_ended_eos']} |
| Full test token CE / PPL | {final['token_metrics']['loss']:.8f} / {final['token_metrics']['perplexity']:.8f} |
| Gerbang controlled contract | {final['contract_gate_passed']} |
| Runtime terpilih | {result['selected_runtime']} |

Final v6 byte-identik dengan v5 yang belum dipakai untuk pengembangan. Ambang95%schema/90%exact dan greedy768 tetap. Model memakai bobot dari proyek, bukan pretrained LLM eksternal. {len(failures)}kesalahan disimpan dalam [record final](training/{run}_FINAL_GATE.json), tidak diperbaiki setelah decoding.

{gallery_text}

## Batas kesiapan

Ini benchmark sintetis dengan recipe komponen yang sama dan keluarga nama baru. Hasil final bukan bukti generalisasi prompt bebas atau layout baru. Benchmark final ini sudah terpakai dan tidak boleh dipakai untuk pemilihan eksperimen berikutnya. Hasil TRAIN-01243/48 berasal dari finalv4 yang berbeda, sehingga bukan perbandingan paired dengan final ini.

**Browser acceptance belum dilakukan. UI aplikasi generator belum dibuat.** Browser lokal sebelumnya ditolak kebijakan tool; tidak memakai jalur alternatif untuk melewati pembatasan tersebut. Preview/interaksi visual tetap tahap terpisah. Setelah kualitas dikaji, tahap berikutnya adalah UI input, validasi, preview sandbox dan unduhan untuk grammar prompt yang didukung.

[Notebook08 training/development](../notebooks/08_kualitas_penyalinan_dan_training.ipynb), [notebook09 final/output](../notebooks/09_evaluasi_final_dan_output.ipynb), [training log](../logs/LOG_TRAINING.md), [evaluasi final](training/{run}-FINAL_curriculum_evaluation.json).
''',encoding='utf-8')
    cells=[]
    md=lambda text:cells.append(nbf.v4.new_markdown_cell(text))
    code=lambda text:cells.append(nbf.v4.new_code_cell(text))
    md('# 09. Evaluasi final dan output\n\nAI-013. Hasil satu final setelah kandidat dikunci. Sel membaca bukti aktual, tanpa training atau final rerun. Notebook08 mempertahankan snapshot development sebelumnya.')
    code('''from pathlib import Path
import sys,json,hashlib
import pandas as pd
from IPython.display import display
ROOT=Path.cwd()
if ROOT.name=='notebooks':ROOT=ROOT.parent
read=lambda path:json.loads((ROOT/path).read_text(encoding='utf-8'))
print('Project interpreter:',sys.executable)''')
    md('## 1. Candidate selection before final\n\nBest ordinary CE after completed fixed budget, then development gate. Never choose a new checkpoint from final failures.')
    code(f"selection=read('reports/training/{run}_FINAL_SELECTION.json')\ndisplay(selection)")
    md('## 2. Raw final measurement and hashes\n\nFinal now consumed. No JSON repair or target substitution.')
    code(f'''final=read('reports/training/{run}-FINAL_curriculum_evaluation.json')
gate=read('reports/training/{run}_FINAL_GATE.json')
assert final['checkpoint_sha256']==selection['checkpoint_sha256']
assert final['prompt_file_sha256']==selection['final_suite']['sha256']
assert hashlib.sha256((ROOT/final['outputs_path']).read_bytes()).hexdigest()==final['outputs_sha256']
display({{k:final[k] for k in ('schema_valid','exact_contract','count','resolved_links','all_ended_eos','contract_gate_passed','token_metrics')}})''')
    md('## 3. Every failed output remains visible\n\nComparisons are for reporting after final. They are not additional train labels in this session.')
    code('''display(gate['failures'])
raw=read(final['outputs_path'])
display(pd.DataFrame([{'recipe':r['recipe'],'style':r['target_spec']['style_mode'],
    'expected_name':r['target_spec']['title'],'actual_name':(r['parsed_spec'] or {}).get('title'),
    'exact':r['exact_contract'],'EOS':r['stop_reason']=='eos'} for r in raw]))''')
    md('## 4. Renderer artifacts\n\nOnly strict accepted raw outputs are exported. Local CSS/JavaScript packaging is not browser proof.')
    code('''if gate['gallery_report']:
    gallery=read(gate['gallery_report'])
    display({k:gallery[k] for k in ('output_count','output_dir','archive_sha256','rejected','browser_evaluated')})
    display(pd.DataFrame([{'title':e['title'],'recipe':e['recipe'],'style':e['style_mode'],'directory':e['directory']} for e in gallery['entries']]))
else:
    print('No passed-final gallery exported.')''')
    md('## 5. Next phase and honest readiness\n\nControlled contracts are distinct from general prompts, reviewed human SFT and browser acceptance.')
    code("display({k:gate[k] for k in ('status','selected_runtime','exported_websites','browser_evaluated','generator_ui_implemented','limits')})")
    notebook=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':'mini-gpt-webcodegen','language':'python',
        'display_name':'Python (.venv - Mini GPT WebCodeGen)'},'language_info':{'name':'python','version':'3.11.9'}})
    nbf.validate(notebook);nbf.write(notebook,notebook_path)
    with (ROOT/'logs/LOG_TRAINING.md').open('a',encoding='utf-8') as handle:
        handle.write(f'''\n#### {run}: Satu evaluasi final setelah kandidat dikunci\n\n- Final {final['schema_valid']}/{final['count']}schema, {final['exact_contract']}/{final['count']}exact ({final['exact_contract_rate']*100:.2f}%), link {final['resolved_links']}, semuaEOS {final['all_ended_eos']}; tokenmetrics {final['token_metrics']}. Gate {final['contract_gate_passed']}, runtime {result['selected_runtime']}.\n- CheckpointSHA `{final['checkpoint_sha256']}`, suiteSHA `{final['prompt_file_sha256']}`, rawSHA `{final['outputs_sha256']}`, selectionSHA `{result['selection_sha256']}`. Kandidat dipilih sebelum final; tidak melakukan reselection/retraining dari hasil ini. Final sekarang consumed.\n- {result['exported_websites']}website diekspor dari raw accepted jika gate lulus. Bukan aplikasi UI atau browser acceptance. [Gerbang final](../reports/FINAL_GATE_2026-10-13.md), [notebook09](../notebooks/09_evaluasi_final_dan_output.ipynb).\n''')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
