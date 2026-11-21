"""Read-only detached progress view; closing it never signals the probe processes."""
from pathlib import Path
import tkinter as tk,json
ROOT=Path(__file__).resolve().parent
window=tk.Tk();window.title('PRS Stage0.5 | source-only H1 | RTX4060')
text=tk.Text(window,width=105,height=20,font=('Consolas',11));text.pack(fill='both',expand=True)
def tick():
    lines=['SOURCE-ONLY PROBES | max2 epochs/model | no held/E/OpenBMI | formal training0','']
    for m in ['EEGNet','EEGNeX','ATCNet']:
        try:
            v=json.loads((ROOT/f'output/{m}/LIVE.json').read_bytes());eta=v.get('eta_seconds');lines.append(f"{m:8} {v['stage']} | epoch {v['epoch']}/2 | {v['batch']}/{v['batches_per_phase']} | ETA {round(eta,1) if eta is not None else 'waiting measured'}s")
        except Exception:lines.append(m+' waiting')
    try:lines+=['',json.dumps(json.loads((ROOT/'LIVE.json').read_bytes()),ensure_ascii=False,indent=2)]
    except Exception:pass
    text.delete('1.0','end');text.insert('end','\n'.join(lines))
    if not ((ROOT/'COMPLETE.json').exists() or (ROOT/'CONTROLLER_FAILURE.json').exists()):window.after(1000,tick)
tick();window.mainloop()
