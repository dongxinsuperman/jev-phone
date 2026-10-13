"""Generate the PyPI description from README without changing the original."""
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/dongxinsuperman/jev-phone'
RAW = 'https://raw.githubusercontent.com/dongxinsuperman/jev-phone/main/'


def remote(target, image=False):
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
        return target
    return (RAW if image else REPOSITORY + '/blob/main/') + quote(target, safe='/#')


def main():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    text = re.sub(r'(!?)\[([^\]]*)\]\(([^)]+)\)',
                  lambda m: f'{m[1]}[{m[2]}]({remote(m[3], bool(m[1]))})', text)
    text = re.sub(r'(href|src)="([^"]+)"',
                  lambda m: f'{m[1]}="{remote(m[2], m[1] == "src")}"', text)
    (ROOT / 'README.pypi.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
