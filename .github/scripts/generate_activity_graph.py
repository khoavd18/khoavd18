"""Render a 31-day contribution graph using live GitHub GraphQL data."""

from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import json
import os
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
QUERY = '''query ProfileActivity($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''


def fetch_days(username: str, token: str) -> list[tuple[str, int]]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    payload = json.dumps({'query': QUERY, 'variables': {
        'login': username, 'from': start.isoformat(), 'to': now.isoformat(),
    }}).encode('utf-8')
    req = Request('https://api.github.com/graphql', data=payload, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'github-profile-visuals',
    })
    with urlopen(req, timeout=45) as response:
        data = json.load(response)
    if data.get('errors'):
        raise RuntimeError('GitHub GraphQL could not return contribution data.')
    user = data.get('data', {}).get('user')
    if not user:
        raise RuntimeError('GitHub user was not found.')
    weeks = user['contributionsCollection']['contributionCalendar']['weeks']
    counts = {day['date']: day['contributionCount'] for week in weeks for day in week['contributionDays']}
    dates = [(start + timedelta(days=i)).date().isoformat() for i in range(31)]
    if any(day not in counts for day in dates):
        raise RuntimeError('GitHub returned an incomplete contribution calendar.')
    return [(day, int(counts[day])) for day in dates]


def build_svg(username: str, days: list[tuple[str, int]]) -> str:
    if len(days) != 31 or any(count < 0 for _, count in days):
        raise ValueError('Expected 31 daily nonnegative contribution counts.')
    total = sum(count for _, count in days)
    peak = max(count for _, count in days)
    # Keep integer y-axis labels and a visible baseline for an all-zero period.
    step = max(1, (peak + 3) // 4)
    ceiling = step * 4
    left, right, top, bottom = 64, 950, 88, 236
    points = [(left + i * (right-left) / 30, bottom - count / ceiling * (bottom-top))
              for i, (_, count) in enumerate(days)]
    line = 'M ' + ' L '.join(f'{x:.2f},{y:.2f}' for x, y in points)
    area = line + f' L {right},{bottom} L {left},{bottom} Z'
    grid = []
    for tick in range(5):
        value = tick * step
        y = bottom - tick / 4 * (bottom-top)
        grid.append(f'<path d="M {left},{y} H {right}" stroke="#2B3048" stroke-dasharray="4 6"/>')
        grid.append(f'<text x="48" y="{y+4}" text-anchor="end" class="muted small">{value}</text>')
    dots = ''.join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#BB9AF7"><title>{escape(date)}: {count} contributions</title></circle>'
                   for (x, y), (date, count) in zip(points, days))
    labels = ''.join(f'<text x="{points[i][0]:.2f}" y="261" text-anchor="middle" class="muted small">{days[i][0][5:]}</text>'
                     for i in (0, 5, 10, 15, 20, 25, 30))
    name = escape(username)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 320" role="img" aria-labelledby="title desc">
<title id="title">{name}: contributions over the last 31 days</title>
<desc id="desc">{total} contributions. Peak daily count: {peak}. Dates use UTC.</desc>
<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#7DCFFF" stop-opacity=".25"/><stop offset="1" stop-color="#7DCFFF" stop-opacity="0"/></linearGradient></defs>
<style>text{{font-family:Segoe UI,Arial,sans-serif;fill:#C0CAF5}}.muted{{fill:#A9B1D6}}.small{{font-size:12px}}.trace{{animation:draw 1.6s ease both}}@keyframes draw{{from{{stroke-dashoffset:1}}to{{stroke-dashoffset:0}}}}@media(prefers-reduced-motion:reduce){{.trace{{animation:none}}}}</style>
<rect width="1000" height="320" rx="16" fill="#1A1B27"/>
<text x="40" y="38" font-size="20" font-weight="600">Activity in Motion</text>
<text x="40" y="61" class="muted" font-size="13">{name} / Last 31 days / UTC</text>
<text x="950" y="42" text-anchor="end" font-size="15" font-weight="600">{total} contributions</text>
{''.join(grid)}
<path d="{area}" fill="url(#fill)"/>
<path d="{line}" fill="none" stroke="#7DCFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" class="trace"/>
{dots}{labels}
<text x="40" y="298" class="muted small">Source: GitHub contribution calendar</text>
<text x="950" y="298" text-anchor="end" class="muted small">{days[0][0]} - {days[-1][0]}</text>
</svg>'''


def main() -> None:
    username = os.environ['PROFILE_GRAPH_USERNAME']
    token = os.environ['PROFILE_GRAPH_TOKEN']
    days = fetch_days(username, token)
    output = ROOT / 'assets/generated/activity.svg'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_svg(username, days), encoding='utf-8')
    print('Saved the contribution graph from live GitHub data.')


if __name__ == '__main__':
    main()
