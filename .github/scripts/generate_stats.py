#!/usr/bin/env python3
"""Generate static stats/top-langs/pin SVG cards from the GitHub REST API.

Runs entirely inside GitHub Actions using the built-in GITHUB_TOKEN, so it
never depends on a shared third-party proxy (which is what was hitting
GitHub's API rate limit and breaking the profile README).
"""
import json
import os
import urllib.request
from html import escape

USERNAME = os.environ["GH_USERNAME"]
TOKEN = os.environ["GH_TOKEN"]
OUT_DIR = "dist"

BG = "#0d1117"
ACCENT = "#00FF41"
TEXT = "#c9d1d9"
BORDER = "#30363d"

PINNED_REPOS = [
    "Real-Time-AI-Assistant-Using-RAG-Langchain",
    "MentalHealthChatBot",
    "DynamicPricingStrategy",
    "BlinkitDashboard",
    "LEETCODE_DSA",
    "Hackerrank_SQL",
    "GSC2025",
    "21DaysOfCode-2025",
    "tanayprabhakar/Quant-Analytics-Tool",
]

LANG_COLORS = {
    "Python": "#3572A5", "Java": "#b07219", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "HTML": "#e34c26", "CSS": "#563d7c",
    "Jupyter Notebook": "#DA5B0B", "C++": "#f34b7d", "C": "#555555",
    "Shell": "#89e051", "Dockerfile": "#384d54", "SQL": "#e38c00",
    "Go": "#00ADD8", "Rust": "#dea584",
}


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USERNAME,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_all_repos():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USERNAME}/repos?per_page=100&page={page}&type=owner")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def card(width, height, body):
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 16px 'Segoe UI', Ubuntu, sans-serif; fill: {ACCENT}; }}
    .text {{ font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: {TEXT}; }}
    .stat {{ font: 600 13px 'Segoe UI', Ubuntu, sans-serif; fill: {TEXT}; }}
  </style>
  <rect x="0.5" y="0.5" rx="8" width="{width - 1}" height="{height - 1}" fill="{BG}" stroke="{BORDER}"/>
  {body}
</svg>'''


def make_stats_svg(user, repos):
    total_stars = sum(r["stargazers_count"] for r in repos)
    total_forks = sum(r["forks_count"] for r in repos)
    rows = [
        ("⭐", "Total Stars", total_stars),
        ("📦", "Public Repos", user["public_repos"]),
        ("👥", "Followers", user["followers"]),
        ("🍴", "Total Forks", total_forks),
    ]
    body = '<text x="25" y="35" class="title">Aditya\'s GitHub Stats</text>'
    for i, (icon, label, value) in enumerate(rows):
        y = 68 + i * 30
        body += f'<text x="25" y="{y}" class="text">{icon} {escape(label)}:</text>'
        body += f'<text x="275" y="{y}" class="stat" text-anchor="end">{value}</text>'
    return card(300, 195, body)


def make_langs_svg(repos):
    totals = {}
    for r in repos:
        try:
            langs = api(f"/repos/{USERNAME}/{r['name']}/languages")
        except Exception:
            continue
        for lang, n in langs.items():
            totals[lang] = totals.get(lang, 0) + n
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    body = '<text x="25" y="35" class="title">Most Used Languages</text>'
    for i, (lang, n) in enumerate(top):
        pct = n / total * 100
        y = 60 + i * 24
        color = LANG_COLORS.get(lang, "#8b949e")
        body += f'<circle cx="30" cy="{y - 5}" r="5" fill="{color}"/>'
        body += f'<text x="45" y="{y}" class="text">{escape(lang)} {pct:.1f}%</text>'
    return card(300, max(195, 60 + len(top) * 24 + 15), body)


def make_pin_svg(repo):
    name = repo["name"]
    desc = repo.get("description") or ""
    if len(desc) > 66:
        desc = desc[:63] + "..."
    lang = repo.get("language") or "N/A"
    color = LANG_COLORS.get(lang, "#8b949e")
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]
    body = f'''
  <text x="20" y="30" class="title">📌 {escape(name)}</text>
  <text x="20" y="55" class="text">{escape(desc)}</text>
  <circle cx="26" cy="88" r="6" fill="{color}"/>
  <text x="38" y="93" class="text">{escape(lang)}</text>
  <text x="150" y="93" class="text">⭐ {stars}</text>
  <text x="220" y="93" class="text">🍴 {forks}</text>
'''
    return card(400, 120, body)


def main():
    os.makedirs(f"{OUT_DIR}/pins", exist_ok=True)
    user = api(f"/users/{USERNAME}")
    repos = api_all_repos()

    with open(f"{OUT_DIR}/stats.svg", "w", encoding="utf-8") as f:
        f.write(make_stats_svg(user, repos))

    with open(f"{OUT_DIR}/top-langs.svg", "w", encoding="utf-8") as f:
        f.write(make_langs_svg(repos))

    by_name = {r["name"]: r for r in repos}
    for spec in PINNED_REPOS:
        owner, _, repo_name = spec.rpartition("/") if "/" in spec else (USERNAME, "/", spec)
        repo = by_name.get(repo_name) if owner == USERNAME else None
        if repo is None:
            try:
                repo = api(f"/repos/{owner}/{repo_name}")
            except Exception:
                continue
        with open(f"{OUT_DIR}/pins/{repo_name}.svg", "w", encoding="utf-8") as f:
            f.write(make_pin_svg(repo))


if __name__ == "__main__":
    main()
