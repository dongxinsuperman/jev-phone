"""One device, a symbol-separated sequence. Run after installing the matching platform extra."""
import argparse
from getpass import getpass
import json
import os
from pathlib import Path
from jev_phone import AndroidClicker, IOSClicker, HarmonyClicker


def make_clicker(platform, device, key, provider):
    cls = {'android': AndroidClicker, 'ios': IOSClicker, 'harmony': HarmonyClicker}[platform]
    return cls(device, key, provider=provider)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform', choices=['android', 'ios', 'harmony'])
    parser.add_argument('device', help='ADB/HDC serial, or WDA URL for iOS')
    parser.add_argument('target', help='Click targets separated by punctuation or newlines')
    parser.add_argument('--provider', choices=['openrouter', 'openai'], default='openrouter')
    parser.add_argument('--evidence', type=Path, help='Optional local evidence directory')
    args = parser.parse_args()
    env = 'OPENROUTER_API_KEY' if args.provider == 'openrouter' else 'OPENAI_API_KEY'
    key = os.environ.get(env) or getpass(env + ': ')
    if args.evidence:
        args.evidence.mkdir(parents=True, exist_ok=True)
    def event(data):
        print(data['phase'], data.get('message', ''))
        if args.evidence:
            for field, name in [('image_bytes', 'candidates.jpg'), ('before_bytes', 'before.jpg')]:
                if field in data:
                    (args.evidence / (f"step-{data['step']}-" + name)).write_bytes(data[field])
    with make_clicker(args.platform, args.device, key, args.provider) as phone:
        result = phone.run(args.target, on_event=event)
        if args.evidence:
            # This immediate frame is evidence, not a page-stability assertion.
            (args.evidence / 'after.image').write_bytes(phone.screenshot())
            (args.evidence / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
