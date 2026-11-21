"""Verify exact raw Git-commit bytes. Standard library only; no API credentials.

Usage: python verify_anonymous.py FULL_COMMIT_SHA OUTPUT_DIRECTORY
Manifest excludes itself; its hash is recorded in the resulting receipt.
"""
from pathlib import Path, PurePosixPath
import concurrent.futures, datetime, hashlib, json, re, sys, urllib.request

REPOSITORY = 'yuanyue-yangtutu/Mem_GRU'
PREFIX = 'preregistrations/prs_matched_baselines_r3_20261121'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    commit, destination = sys.argv[1:]
    assert re.fullmatch(r'[0-9a-f]{40}', commit), 'A full immutable commit SHA is required'
    out = Path(destination).resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = f'https://raw.githubusercontent.com/{REPOSITORY}/{commit}/{PREFIX}/'

    def get(name):
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts
        # No .netrc, authentication handler, cookie processor or API token is used.
        request = urllib.request.Request(base + name, headers={
            'User-Agent': 'PRS-public-byte-verifier/1', 'Accept': 'application/octet-stream'})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
            record = dict(file=name, url=request.full_url, status=response.status,
                downloaded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                sha256=digest(raw), bytes=len(raw), request_authorization=False,
                request_cookie=False, CRLF_count=raw.count(b'\r\n'))
        target = out/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return raw, record

    raw, manifest_record = get('SHA256SUMS.json')
    manifest = json.loads(raw.decode('utf8'))
    assert manifest['hash_object'] == 'exact bytes in the Git commit'
    expected = manifest['files']
    assert 'SHA256SUMS.json' not in expected

    def check(name):
        body, record = get(name)
        spec = expected[name]
        record['match'] = record['sha256'] == spec['sha256'] and len(body) == spec['bytes']
        record['LF_only'] = b'\r' not in body and not body.startswith(b'\xef\xbb\xbf')
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(check, sorted(expected)))
    passed = all(r['match'] and r['LF_only'] for r in records)
    receipt = dict(commit=commit, repository=REPOSITORY, prefix=PREFIX,
        anonymous=True, method='HTTPS GET raw.githubusercontent.com, no Authorization/Cookie headers',
        hash_object=manifest['hash_object'], manifest=manifest_record,
        files=records, matched=sum(r['match'] for r in records), total=len(records), passed=passed,
        scientific_execution=False)
    (out/'ANONYMOUS_VERIFICATION_RECEIPT.json').write_bytes(
        (json.dumps(receipt, ensure_ascii=False, indent=2)+'\n').encode('utf8'))
    print(json.dumps(dict(commit=commit,matched=receipt['matched'],total=receipt['total'],
        passed=passed,manifest_sha256=digest(raw),receipt=str(out/'ANONYMOUS_VERIFICATION_RECEIPT.json'))))
    if not passed:
        raise SystemExit('Published byte verification failed')

if __name__ == '__main__':
    main()
