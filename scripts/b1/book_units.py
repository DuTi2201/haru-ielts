"""Unit boxes of Destination B1, read from the opening page of each vocabulary unit
(book pages 12, 24, 36, 48, 60, 72, 84, 100, 112, 124, 136, 148, 160, 172).
Only the item names are kept here. Run: python3 scripts/b1/book_units.py
It checks unit_assignment.json against these boxes and rewrites it when --write is given."""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
BOXES = {
 3: dict(PV="carry on; eat out; give up; join in; send off; take up; turn down; turn up",
  PP="for a long time; for fun; in the middle (of); in time (for); on CD/DVD/video; on stage",
  WF="act athlete child collect entertain hero music play sail sing",
  WP="bored with; crazy about; good at; interested in; keen on; popular with; feel like; listen to; take part in; a book (by sb) about; a fan of; a game against"),
 6: dict(PV="cross out; look up; point out; read out; rip up; rub out; turn over; write down",
  PP="by heart; for instance; in conclusion; in fact; in favour (of); in general",
  WF="begin brave correct divide educate instruct memory refer silent simple",
  WP="capable of; talented at; cheat at/in; confuse sth with; continue with; cope with; help (sb) with; know about; learn about; succeed in; an opinion about/of; a question about"),
 9: dict(PV="get in(to); get off; get on(to); get out (of); go away; go back (to); set off; take off",
  PP="by air/sea/bus/car/etc; on board; on foot; on holiday; on schedule; on the coast",
  WF="attract back choose comfort depart direct drive fly travel visit",
  WP="close to; famous for; far from; late for; suitable for; arrive at/in; ask (sb) about; ask for; look at; prepare for; provide sb with; wait for"),
 12: dict(PV="bring up; fall out (with); get on (with); go out with; grow up; let down; look after; split up",
  PP="by yourself; in common (with); in contact (with); in love (with); on purpose; on your own",
  WF="able admire care confident forgive honest introduce lie person relate",
  WP="fond of; jealous of; kind to; married to; proud of; admire sb for; apologise (to sb) for; argue (with sb) about; care about; chat (to sb) about; an argument (with sb) about; a relationship with"),
 15: dict(PV="add up; come back (from); give away; hurry up; pay back; save up (for); take back; take down",
  PP="by credit card/cheque; for rent; for sale; in cash; in debt; in good/bad condition",
  WF="add afford compare decide expense judge serve true use value",
  WP="wrong about/with; belong to; borrow sth from; buy sth from; choose between; compare sth to/with; decide on; lend sth to; pay for; spend sth on; an advert(isement) for"),
 18: dict(PV="break down; come across; find out; make up; pull off; throw away; turn off; turn on",
  PP="at last; by chance; in my opinion; in the end; in the future; out of order",
  WF="boil chemist conclude examine fascinate history identical long measure science",
  WP="different from/to; full of; begin sth with; connect sth to/with; disconnect sth from; fill sth with; result in; a difference between; an idea about; a number of; a reason for; a type of"),
 21: dict(PV="call back; come out; cut off; fill in; hang up; log off; log on(to); print out",
  PP="by e-mail/phone/letter; on the Internet; on the news; on the phone; on the radio; on TV",
  WF="certain communicate connect deliver express inform predict secret speak translate",
  WP="comment on; communicate with; glance at; receive sth from; reply to; send sth to sb; talk (to sb) about; tell sb about; translate (from sth) into; write (to sb) about; information about; a letter (from sb) about"),
 24: dict(PV="break in(to); catch up (with); get away with; get up; move in; put away; wake up; wash up",
  PP="against the law; at the age of; in public; in response to; in touch (with); in your teens/twenties/etc",
  WF="agree belief courage elect equal life nation peace prison shoot",
  WP="angry (with sb) about; guilty of; accuse sb of; blame sb for; blame sth on; criticise sb for; forget about; forgive sb for; invite sb to; punish sb for; share sth with; smile at"),
 27: dict(PV="call off; give back; go on; put off; set up; stay up; take away; take over",
  PP="at the moment; in charge (of); on business; on strike; on time; on/off duty",
  WF="assist beg boss employ fame occupy office retire safe succeed",
  WP="careful with; difficult for; fed up with; ready for; responsible for; apply for; depend on; inform sb about; refer to; work as; work for; a kind of"),
 30: dict(PV="cut down (on); fall down; get over; go off; lie down; put on; sit down; stand up",
  PP="at night; at risk; in addition (to); in comparison to/with; in shape; on a diet",
  WF="bake bend cook intend jog medicine pain reduce sense weigh",
  WP="addicted to; allergic to; covered in/with; pleased with; combine sth with; complain (to sb) about; die from/of; fight against; recover from; smell of; a cure for; a recipe for"),
 33: dict(PV="cut off; do up; fill up; have on; leave out; put on; take off; try on",
  PP="at the back (of); at the end (of); in fashion/style; in front (of); in the corner (of); out of fashion/style",
  WF="art break compose exhibit free hand imagine intelligent perfect prepare",
  WP="amazed at/by; disappointed with; familiar with; involved in; similar to; change sth (from sth) into; describe sth as; explain sth to; remind sb of; remove sth from; an influence on; a picture of"),
 36: dict(PV="blow up; build up; clear up; go out; keep out; put down; put out; put up",
  PP="at most; at the top/bottom (of); in the beginning; in the distance; in total; on top (of)",
  WF="centre circle danger deep destroy fog garden invade nature pollute",
  WP="afraid of; aware of; enthusiastic about; serious about; short of; escape from; prevent sb from; save sth from; think about; worry about; damage to; an increase in"),
 39: dict(PV="calm down; cheer up; come on; go on; hang on; run away (from); shut up; speak up",
  PP="at first; at least; at times; in secret; in spite of; in tears",
  WF="bore comedy emotion energy excite feel happy hate noise sympathy",
  WP="ashamed of; embarrassed about; frightened of; happy about/with; nervous about; scared of; sorry about/for; surprised at/by; tired of; congratulate sb on; laugh at; a joke about"),
 42: dict(PV="hang up; pick up; put back; run out (of); share out; sort out; watch out; work out",
  PP="by accident/mistake; in a mess; in danger (of); in my view; in trouble; under pressure",
  WF="advice confuse except help luck prefer recommend refuse solve suggest",
  WP="sure about/of; advise against; agree (with sb) about; approve of; believe in; deal with; happen to; hide sth from sb; insist on; rely on; an advantage of; a solution to"),
}

def items(unit, kind):
    s = BOXES[unit][kind]
    return s.split() if kind == "WF" else [x.strip() for x in s.split(";")]

def norm(s):
    s = s.lower().replace("e-mail", "email").replace("advert(isement)", "advertisement")
    s = re.sub(r"\([^)]*\)", " ", s).replace("/etc", "")
    s = re.sub(r"\b(sb|sth|a|an|the|your|my)\b", " ", s)
    return set(re.split(r"[\s/]+", s.strip())) - {""}

def match(head, kind):
    """Units whose box holds this head, best overlap first."""
    h = norm(head); out = []
    exact = [(u, it) for u in BOXES for it in items(u, kind) if it.lower() == head.lower()]
    if exact:
        return exact
    for u in BOXES:
        for it in items(u, kind):
            b = norm(it)
            if kind in ("WF", "PV"):
                ok = h == b
            elif kind == "PP":
                ok = bool(h & b) and (h <= b or b <= h) and next(iter(sorted(h)), "") != "" and head.split()[0].lower().split("/")[0] in it.lower().split()[0].split("/")
            else:
                ok = h <= b or b <= h
            if ok:
                out.append((len(h & b), u, it))
    return [(u, it) for _, u, it in sorted(out, key=lambda t: (-t[0], t[1]))]

def main():
    path = HERE / "unit_assignment.json"
    a = json.loads(path.read_text(encoding="utf-8"))
    moved, missing = [], []
    for kind, heads in a["by_kind"].items():
        for head, unit in heads.items():
            m = match(head, kind)
            units = [u for u, _ in m]
            if not units:
                missing.append((kind, head, unit))
            elif unit not in units:
                moved.append((kind, head, unit, units[0]))
                heads[head] = units[0]
    print("moved:", len(moved))
    for x in moved: print("  ", x)
    print("not in any unit box:", len(missing))
    for x in missing: print("  ", x)
    # box items with no entry in the course lists
    for kind in ("PV", "PP", "WF", "WP"):
        for u in BOXES:
            for it in items(u, kind):
                if not any(u in [x for x, _ in match(h, kind)] and (norm(h) <= norm(it) or norm(it) <= norm(h)) for h in a["by_kind"][kind]):
                    print("   box item without a course entry:", kind, u, it)
    if "--write" in sys.argv:
        a["unverified"] = {k: sorted(h for kk, h, _ in missing if kk == k) for k in a["by_kind"]}
        a["note"] = "Checked against the unit boxes in scripts/b1/book_units.py (read from the book pages)."
        path.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("written")

if __name__ == "__main__":
    main()
