"""Read-only audit of build.json write_fill answerability. Run: python3 A_audit.py"""
import json, re, collections
it = json.load(open('/home/claude/haru-ielts/app/seed/exercises/g1/build.json'))['items']
wf = [i for i in it if i['type'] == 'write_fill']
def grp(i):
    p = re.sub(r'-\d+$', '', i['id']) if '-' in i['id'] else re.sub(r'\d+$', '', i['id'])
    return re.sub(r'^G1D\d+', '', p)
PAREN = re.compile(r'\)\s*\(([^)]+)\)')
CAT = {}
def put(i, c): CAT[i['id']] = c
for i in wf:
    g, t, ins = grp(i), i['text'], i['instruction_vi']
    if g in ('KB', 'KU3C1', 'KC4'): c = 'B1 chan: cau goc sai/dong tu goc bi an'
    elif g in ('O5', 'O6'): c = 'B2 chan: On lai khong hien nghia tieng Viet'
    elif g in ('KTY', 'KLT', 'KXI'): c = 'B3 chan: phu thuoc audio/bai doc/2 cau khac khong hien'
    elif g in ('KCB',): c = 'B4 chan: ngan hang tu bi cat "..."'
    elif g in ('KXL', 'KXC'): c = 'B5 chan: bai noi co khung/bo tu nhung khong liet ke'
    elif g == 'KA18': c = 'W1 yeu: khung tu chi la cac cap gach cheo trong instruction'
    elif g in ('KXB', 'KD', 'KC3', 'KF'): c = 'W2 yeu: ngan hang tu la chu thuong trong instruction (khong chip)'
    elif g == 'F' and not PAREN.search(t) : c = 'B6 chan: F khong goi y loai tu (Do/Does/since)'
    elif g == 'F': c = 'W3 yeu: instruction chung chung, co (dong tu) trong ngoac'
    elif g == 'KCA' and not PAREN.search(t): c = 'B7 chan: instruction bao chia dong tu nhung o trong la tro dong tu'
    elif g in ('KI', 'KU3C4', 'KXJ', 'KG18'): c = 'W4 yeu: cau roi khoi doan van (mat boi canh)'
    else: c = 'OK lam duoc (co the con loi nho)'
    put(i, c)
cnt = collections.Counter(CAT.values())
for k, v in sorted(cnt.items()): print(v, k)
print('TOTAL', sum(cnt.values()))
blk = sum(v for k, v in cnt.items() if k.startswith('B'))
wk = sum(v for k, v in cnt.items() if k.startswith('W'))
print('blocker', blk, round(100*blk/381), '% ; weak', wk, round(100*wk/381), '% ; ok', cnt['OK lam duoc (co the con loi nho)'])
# accepted-set defects
pron = re.compile(r"^(?:.*[\s'\"(])?(I|you|we|they|he|she|it|You|We|They|I)\s*\(\s*㉠")
miss = [i['id'] for i in wf
        if re.search(r"\b(I|you|You|we|We|they|They|she|She|he|He)\s+\( ㉠", i['text']) and len(i['blanks'][0]['accepted']) and
        any(re.match(r"^(have|has|are|am|is|will)\b", a) for a in i['blanks'][0]['accepted']) and
        not any(a.startswith("'") for a in i['blanks'][0]['accepted'])]
print('missing contraction variants', len(miss), miss)
print('uk spelling only', [i['id'] for i in wf if 'recognise' in i['blanks'][0]['accepted']])
print('duplicate texts', sum(1 for i in wf if [j['text'] for j in wf].count(i['text']) > 1))
