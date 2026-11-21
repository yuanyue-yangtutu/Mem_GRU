"""Detached viewer only. Closing this window never stops controller."""
from pathlib import Path
import json,tkinter as tk
R=Path(__file__).parent
w=tk.Tk();w.title('PRS Stage1 R3.1 | LOCAL RTX4060 | source T only')
t=tk.Text(w,width=110,height=35,font=('Consolas',11));t.pack(fill='both',expand=True)
def dur(x):return 'waiting measured' if x is None else '%.2f h'%(x/3600)
def tick():
    try:
        v=json.loads((R/'LIVE.json').read_bytes());n=v['completed'];bar='#'*int(n*40/81)+'-'*(40-int(n*40/81))
        lines=['LOCAL GPU | no PPU | no held/E/OpenBMI | no target inference',f'[{bar}] {n}/81 completed | failed {len(v["failed"])}',f'GPU h {v["charged_GPU_hours"]:.4f}/80 | overall ETA {dur(v["overall_eta_seconds"])}',v['eta_note'],'']
        r=v.get('running')
        if r:lines += [str(r.get('fit_id')),f'{r.get("stage")} | epoch {r.get("epoch",0)}/{r.get("max_epochs","?")} | step {r.get("batch",0)}/{r.get("steps","?")} | fit ETA {dur(r.get("eta_seconds"))}']
        lines+=['','WAITING: '+', '.join(v['waiting']),'','FAILED: '+', '.join(v['failed']),'','Status: '+('FINAL: '+json.loads((R/'FINAL.json').read_bytes())['status'] if (R/'FINAL.json').exists() else v['status'])]
        t.delete('1.0','end');t.insert('end','\n'.join(lines))
    except Exception as e:t.delete('1.0','end');t.insert('end','Waiting controller metadata: '+str(e))
    if not (R/'FINAL.json').exists() and not (R/'STOP.json').exists():w.after(2000,tick)
tick();w.mainloop()
