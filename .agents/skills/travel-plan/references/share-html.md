# The share version

A share version is the plan rewritten **for the travel companion**, not an export of the working document. It goes to `data/travel/<slug>-分享版.html`, next to the `.md`.

## What changes from the .md

| drop | keep | add |
|---|---|---|
| version numbers, changelog, §12 sources | every ✅ fact, every ⚠️ trap | a lede sentence per day saying what the day *is* |
| the ❓ audit marks as marks | the **content** of each ❓, rewritten as an instruction ("到店问客栈老板当天票价") | why the plan differs from the guidebooks the companion will read |
| §10 re-verify checklist | the phone-call table — they may be the one calling | fallback blocks kept next to their day |
| internal notes about what earlier versions got wrong | the *correction* itself, stated as fact | |

The companion has not read the research. Anywhere the plan deliberately contradicts common advice, **say why in one line** — otherwise they will "helpfully" route the group back onto the wrong path.

## Build

1. Copy `assets/share.css` verbatim into a `<style>` block. It is already tuned for dark mode, A4 print, and ~400 px phone width — do not re-derive it.
2. Write the body against the class vocabulary below.
3. Assemble and validate:

```bash
python3 - <<'PY'
import html.parser, re, sys
p = "data/travel/<slug>-分享版.html"
s = open(p, encoding="utf-8").read()
class P(html.parser.HTMLParser):
    VOID = {"meta","br","img","link","hr","input"}
    def __init__(s2): super().__init__(); s2.stack=[]; s2.err=[]
    def handle_starttag(s2,t,a):
        if t not in s2.VOID: s2.stack.append(t)
    def handle_endtag(s2,t):
        if not s2.stack: s2.err.append(f"extra </{t}>"); return
        if s2.stack[-1]!=t: s2.err.append(f"<{s2.stack[-1]}> vs </{t}> L{s2.getpos()[0]}")
        else: s2.stack.pop()
pp=P(); pp.feed(s)
style = s[s.index("<style>"):s.index("</style>")]
body  = s[s.index("<body>"):]
used  = {c for m in re.finditer(r'class="([^"]+)"', body) for c in m.group(1).split()}
defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", style))
print("unclosed:", pp.stack, "errors:", pp.err)
print("classes not in stylesheet:", sorted(used - defined))
print("days:", s.count('class="daynum"'), "map links:", s.count("uri.amap.com"))
PY
```

Both lists must be empty, and the day count must match the itinerary.

## Class vocabulary

| class | use |
|---|---|
| `.alert` | seal-coloured left rule — traps, hard constraints, "do this now" |
| `.note` | autumn-coloured — context, fallbacks, "if you'd rather" |
| `.good` | green — a genuine upside worth naming |
| `.day` / `.dayhead` / `.daynum` / `.daydate` / `.daytitle` / `.daylede` | one day block |
| `.sched` > `li` > `.time` + `.what` (+ `.meta` inside `.what`) | the timeline. Add `class="key"` on the li for the day's load-bearing rows |
| `.map` | map link, right after the place name |
| `.tag`, `.tag.free`, `.tag.warn` | price / 免费 / a one-word warning |
| `.scroll` around every `<table>` | horizontal scroll on phones |
| `table.tot` | budget table with an emphasised final row |
| `.kv` (`dl`/`dt`/`dd`) | definition pairs, e.g. entry requirements |

Only `.map` links are needed in the share version — one map provider, not the dual `高德 + G` pair, since the file is read on a phone with one working network.

## Print

`@page` is A4, and `.day`, table rows, and the callout blocks all set `break-inside: avoid`. Printing to PDF from a browser is the supported path — no separate export step.
