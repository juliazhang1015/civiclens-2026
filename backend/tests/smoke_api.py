"""Dependency-free HTTP smoke tests for a running CivicScope FastAPI server.
Run: python3 backend/tests/smoke_api.py --pdf demo_samples/waterloo_lease_2pages.pdf
"""
import argparse
import json
import pathlib
import urllib.error
import urllib.request
import uuid


def request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=270) as res:
            return res.status, res.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode('utf-8', errors='replace')


def upload(url, filename, contents, mimetype='application/pdf'):
    boundary = 'civic-' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {mimetype}\r\n\r\n'.encode() + contents + f'\r\n--{boundary}--\r\n'.encode())
    return request(url, body, {'Content-Type': f'multipart/form-data; boundary={boundary}'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--pdf', default='demo_samples/waterloo_lease_2pages.pdf')
    parser.add_argument('--skip-ai', action='store_true', help='Only check health and invalid-PDF rejection; do not call AI')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    try:
        status, body = request(base + '/health')
    except Exception as exc:
        raise SystemExit(f'FAIL: backend unreachable: {exc}')
    print('GET /health:', status, body[:300])
    if status != 200:
        raise SystemExit('FAIL: health check')
    status, body = upload(base + '/analyze', 'not_a_pdf.pdf', b'not a pdf')
print('Invalid PDF:', status, body[:300])

if status != 400:
    raise SystemExit(
        f'FAIL: expected HTTP 400 for invalid PDF, got HTTP {status}'
    )

print('PASS: invalid PDF correctly rejected with HTTP 400')
    if args.skip_ai:
        print('PASS: basic smoke checks completed (AI analysis SKIPPED)')
        return
    path = pathlib.Path(args.pdf)
    if not path.is_file():
        raise SystemExit(f'FAIL: missing demo PDF: {path}')
    status, body = upload(base + '/analyze', path.name, path.read_bytes())
    print('Real PDF:', status, body[:1200])
    if status == 200:
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            raise SystemExit('FAIL: response is not JSON')
        expected = {'document_title', 'summary', 'proposed_changes', 'affected_groups', 'potential_benefits', 'potential_tradeoffs', 'participation', 'unknowns'}
        missing = expected - set(obj)
        if missing:
            raise SystemExit(f'FAIL: missing response fields: {sorted(missing)}')
        print('PASS: real PDF analyzed and response fields verified')
    else:
        raise SystemExit(f'FAIL: real PDF analysis returned HTTP {status}; check API key, network, PDF limits, and server logs')
    print('PASS: smoke checks completed, including real PDF analysis')


if __name__ == '__main__':
    main()
