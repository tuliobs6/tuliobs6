import json
import os
import urllib.request
from collections import defaultdict
from xml.sax.saxutils import escape

USER = os.environ["GH_USER"]
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
)
data = json.load(urllib.request.urlopen(req))
if "errors" in data:
    raise SystemExit(data["errors"])

user = data["data"]["user"]
cc = user["contributionsCollection"]
repos = user["repositories"]

FONT = "Segoe UI, Helvetica, Arial, sans-serif"


def card(width, height, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="8" '
        f'fill="#000000" stroke="#30363d"/>{body}</svg>'
    )


def text(x, y, s, size=13, fill="#bdbdbd", weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(str(s))}</text>'
    )


# ---------- Stats ----------
stars = sum(r["stargazerCount"] for r in repos["nodes"])
rows = [
    ("Repositórios públicos", repos["totalCount"]),
    ("Estrelas recebidas", stars),
    ("Commits (último ano)", cc["totalCommitContributions"]),
    ("Pull requests", cc["totalPullRequestContributions"]),
    ("Issues", cc["totalIssueContributions"]),
]
body = text(24, 36, "Estatísticas do GitHub", 17, "#ffffff", "600")
for i, (label, value) in enumerate(rows):
    y = 68 + i * 26
    body += text(24, y, label, 13, "#bdbdbd")
    body += text(376, y, value, 13, "#ffffff", "600", "end")
stats_svg = card(400, 200, body)

# ---------- Linguagens ----------
sizes = defaultdict(int)
colors = {}
for r in repos["nodes"]:
    for e in r["languages"]["edges"]:
        name = e["node"]["name"]
        sizes[name] += e["size"]
        colors[name] = e["node"]["color"] or "#8b949e"

total = sum(sizes.values()) or 1
top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:5]
body = text(24, 36, "Principais linguagens", 17, "#ffffff", "600")
for i, (name, size) in enumerate(top):
    y = 68 + i * 26
    pct = size / total * 100
    body += text(24, y, name, 13, "#bdbdbd")
    body += text(376, y, f"{pct:.1f}%", 13, "#ffffff", "600", "end")
    body += f'<rect x="24" y="{y+6}" width="352" height="4" rx="2" fill="#2b2b2b"/>'
    body += f'<rect x="24" y="{y+6}" width="{max(3, 352*pct/100):.1f}" height="4" rx="2" fill="{colors[name]}"/>'
langs_svg = card(400, 200, body)

# ---------- Atividade (últimos 30 dias) ----------
days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]][-30:]
peak = max([d["contributionCount"] for d in days] + [1])
W, H = 820, 220
body = text(24, 36, "Atividade nos últimos 30 dias", 17, "#ffffff", "600")
base = 180
slot = (W - 48) / len(days)
for i, d in enumerate(days):
    h = d["contributionCount"] / peak * 110
    x = 24 + i * slot + (slot - 16) / 2
    if d["contributionCount"] == 0:
        body += f'<rect x="{x:.1f}" y="{base-3}" width="16" height="3" rx="1.5" fill="#2b2b2b"/>'
    else:
        body += f'<rect x="{x:.1f}" y="{base-h:.1f}" width="16" height="{h:.1f}" rx="3" fill="#ffffff"/>'
body += text(24, 205, days[0]["date"], 11, "#8b949e")
body += text(W - 24, 205, days[-1]["date"], 11, "#8b949e", anchor="end")
activity_svg = card(W, H, body)

os.makedirs("assets", exist_ok=True)
for name, svg in [("stats", stats_svg), ("langs", langs_svg), ("activity", activity_svg)]:
    with open(f"assets/{name}.svg", "w", encoding="utf-8") as f:
        f.write(svg)
print("Cards gerados em assets/")
