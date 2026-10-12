"""Independent devices in parallel; steps on each device remain sequential."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from getpass import getpass
import json
import os
from click import make_clicker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', help='JSON list of {platform, device, targets: [...]}')
    parser.add_argument('--provider', choices=['openrouter', 'openai'], default='openrouter')
    args = parser.parse_args()
    with open(args.config) as f:
        jobs = json.load(f)
    if not isinstance(jobs, list) or not jobs:
        parser.error('config must contain a nonempty list')
    identities = []
    for job in jobs:
        if job['platform'] not in ('android', 'ios', 'harmony') or not isinstance(job['targets'], list) or not job['targets']:
            parser.error('each job needs a supported platform and nonempty targets list')
        identities.append((job['platform'], job['device'].rstrip('/')))
    if len(set(identities)) != len(identities):
        parser.error('use one job per device; put its steps in targets')
    env = 'OPENROUTER_API_KEY' if args.provider == 'openrouter' else 'OPENAI_API_KEY'
    key = os.environ.get(env) or getpass(env + ': ')
    def run(job):
        with make_clicker(job['platform'], job['device'], key, args.provider) as phone:
            return phone.run('\n'.join(job['targets']))
    failed = False
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        pending = {pool.submit(run, job): job for job in jobs}
        for future in as_completed(pending):
            job = pending[future]
            try:
                print(json.dumps({'device': job['device'], 'results': future.result()}, ensure_ascii=False))
            except Exception as error:
                failed = True
                print(json.dumps({'device': job['device'], 'error': str(error)}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
