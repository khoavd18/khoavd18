"""Show a contribution visual only after its SVG files exist and parse correctly."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]


def valid_svg(relative_path: str) -> bool:
    path = ROOT / relative_path
    if not path.is_file():
        return False
    try:
        return ET.parse(path).getroot().tag == '{http://www.w3.org/2000/svg}svg'
    except (ET.ParseError, OSError):
        return False


def replace_region(content: str, name: str, body: str) -> str:
    start = f'<!-- {name}:START -->'
    end = f'<!-- {name}:END -->'
    if content.count(start) != 1 or content.count(end) != 1:
        raise ValueError(f'Expected exactly one {name} marker pair in README.md')
    pattern = re.escape(start) + r'.*?' + re.escape(end)
    result, count = re.subn(pattern, lambda _: f'{start}\n{body}\n{end}', content, flags=re.S)
    if count != 1:
        raise ValueError(f'Could not update {name} region')
    return result


def main() -> None:
    readme = ROOT / 'README.md'
    content = readme.read_text(encoding='utf-8')
    if valid_svg('assets/generated/activity.svg'):
        content = replace_region(content, 'PROFILE_ACTIVITY', '''## 📈 Activity in Motion

<p align="center">
  <img src="./assets/generated/activity.svg" width="100%" alt="Khoa's GitHub contributions over the last 31 days, using UTC dates" />
</p>''')
        print('Recent contribution graph enabled.')
    if valid_svg('profile-3d-contrib/profile-night-rainbow.svg'):
        content = replace_region(content, 'PROFILE_3D', '''## 🌃 My Contribution Skyline

<p align="center">
  <img src="./profile-3d-contrib/profile-night-rainbow.svg" width="100%" alt="Khoa's GitHub contributions as a 3D skyline" />
</p>''')
        print('3D contribution map enabled.')
    if all(valid_svg(p) for p in ('assets/generated/snake.svg', 'assets/generated/snake-dark.svg')):
        content = replace_region(content, 'PROFILE_SNAKE', '''## 🐍 One Contribution at a Time

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/generated/snake-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="./assets/generated/snake.svg" />
    <img src="./assets/generated/snake.svg" width="100%" alt="An animated snake moving through Khoa's GitHub contribution grid" />
  </picture>
</p>''')
        print('Contribution snake enabled.')
    if content != readme.read_text(encoding='utf-8'):
        readme.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    main()
