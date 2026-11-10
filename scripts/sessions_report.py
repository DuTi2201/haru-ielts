"""What each hand-planned sitting holds and what is left over for the practice sittings."""
import sys, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.lesson_seed import load_all

def nq(it): return len(it.get("questions") or []) or len(it.get("blanks") or []) or 1

for r in load_all().lessons:
    s = r.seed
    if not s.sessions: continue
    items = {it["id"]: it for it in r.practice["items"]}
    used = {i for x in s.sessions for i in x.check}
    left = [it for k, it in items.items() if k not in used]
    print(f"{s.slug[:44]:44} leftover {len(left)} items/{sum(nq(i) for i in left)} q")
    for x in s.sessions:
        cq = sum(nq(items[i]) for i in x.check)
        core = sum(1 for w in x.vocab if any(v.hangul == w and v.priority == 'core' for v in s.vocab))
        flag = "  <-- no check" if cq == 0 else ""
        print(f"   {x.title_vi[:46]:46} words {len(x.vocab):2} (core {core:2}) cards {len(x.grammar)} check {cq}q{flag}")
