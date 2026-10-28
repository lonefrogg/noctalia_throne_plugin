import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'throne-vpn/backend.py'
spec = importlib.util.spec_from_file_location('throne_backend', SCRIPT)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class FakeClient:
    def __init__(self, fail_tun=False, state='idle', last=101):
        self.fail_tun, self.calls = fail_tun, []
        self.value = {'state': state, 'tun': False, 'last_profile_id': last,
                      'route': {'name': 'Default'}, 'profile': None}

    def status(self, **kwargs):
        self.calls.append(('status',))
        return app.normalize_status(self.value)

    def call(self, *args, **kwargs):
        self.calls.append(args)
        if args == ('tun', 'on'):
            if self.fail_tun:
                raise app.BackendError('TUN privileges missing')
            self.value['tun'] = True
        elif args[0] == 'connect':
            self.value['state'] = 'running'
            self.value['profile'] = {'id': 101 if args[1] == 'last' else args[1], 'name': 'Example'}
        elif args == ('disconnect',):
            self.value['state'], self.value['profile'] = 'idle', None
        elif args == ('profiles',):
            return {'profiles': [{'id': 101, 'name': 'Example'}]}
        return self.value.copy()


class BackendTests(unittest.TestCase):
    def test_numeric_sort_missing_failed_and_ties(self):
        rows = app.profile_rows({'profiles': [
            {'id': 101, 'download_bps': 9_000_000},
            {'id': 102, 'download_bps': 100_000_000, 'upload_bps': 20_000_000},
            {'id': 103, 'download_bps': -1}, {'id': 104},
            {'id': 105, 'download_bps': 100_000_000, 'upload_bps': 30_000_000},
            {'id': True}, {'id': -1}, {'id': 2**60}, None,
        ]})
        self.assertEqual([r['id'] for r in rows], [105,102,101,104,103])
        self.assertEqual(rows[0]['download'], '100.00 Mbps')

    def test_malformed_numbers_and_duplicate_ids_are_safe(self):
        rows = app.profile_rows({'profiles': [{'id': 101, 'download_bps': float('nan'), 'upload_bps': 10**500},
                                             {'id': 101, 'name': 'duplicate'}, {'id': 102, 'latency_ms': True}]})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['download'], '—')
        json.dumps(rows, allow_nan=False)

    def test_metric_units(self):
        self.assertEqual(app.traffic_text(1024**3), '1.0 GiB')
        self.assertEqual(app.speed_text(8_000_000), '8.00 Mbps')
        self.assertEqual(app.ping_text(-2), 'unavailable')
        self.assertEqual(app.speed_text(-1), 'failed')

    def test_profile_names_are_clean_display_text(self):
        rows = app.profile_rows({'profiles': [{'id': 101, 'name': 'A\nB\x00C\u202eD'},
                                             {'id': 102, 'name': 'A\nB\x00C\u202eD'}]})
        self.assertEqual(rows[0]['name'], 'A B C D')
        self.assertEqual([r['id'] for r in rows], [101,102])

    def test_snapshot_is_read_only(self):
        client = FakeClient()
        data = app.snapshot(client)
        self.assertEqual(client.calls, [('status',), ('profiles',)])
        self.assertEqual(data['status']['route']['name'], 'Default')

    def test_tun_precedes_connect_and_routes_are_not_edited(self):
        client = FakeClient()
        app.connect(client, 102)
        self.assertEqual(client.calls, [('status',), ('tun', 'on'), ('connect', 102)])
        self.assertEqual(client.value['route']['name'], 'Default')

    def test_failed_tun_never_connects_proxy_only(self):
        client = FakeClient(fail_tun=True)
        with self.assertRaises(app.BackendError): app.connect(client, 102)
        self.assertEqual(client.calls, [('status',), ('tun','on')])

    def test_busy_and_absent_last_do_not_change_modes(self):
        for client in (FakeClient(state='connecting'), FakeClient(last=-1)):
            with self.assertRaises(app.BackendError): app.connect(client, 'last')
            self.assertEqual(client.calls, [('status',)])

    def test_disconnect_reports_confirmed_state(self):
        client = FakeClient(state='running')
        self.assertEqual(app.disconnect(client)['status']['state'], 'idle')
        self.assertEqual(client.calls, [('disconnect',)])

    def test_bad_status_fields_do_not_escape_to_luau(self):
        data = app.normalize_status({'state':'idle','tun':'false','profile':[], 'route':'wrong',
                                     'capabilities': {'tun': 1},'last_profile_id':True})
        self.assertIsNone(data['route'])
        self.assertIsNone(data['profile'])
        self.assertFalse(data['tun'])
        self.assertIsNone(data['capabilities']['tun'])
        self.assertEqual(data['last_profile_id'], -1)

    def test_raw_errors_never_echo_tokens_or_paths(self):
        raw = 'unrecognized error: token=FICTIONAL_SECRET /private/example'
        self.assertNotIn('FICTIONAL_SECRET', app.classify_error(raw))
        self.assertNotIn('/private/example', app.classify_error(raw))

    def test_client_uses_argv_and_only_key_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp)/'key with spaces';key.write_text('FICTIONAL_TEST_SECRET')
            fake = Path(tmp)/'thronectl';fake.touch(mode=0o755)
            with patch.object(app.subprocess, 'run') as run:
                run.return_value = subprocess.CompletedProcess([],0,'{"state":"idle"}','')
                app.Client('127.0.0.1:9095',str(key),str(fake)).call('connect',102)
                argv = run.call_args.args[0]
                self.assertIn(str(key), argv)
                self.assertNotIn('FICTIONAL_TEST_SECRET', str(argv))
                self.assertEqual(argv[-2:], ['connect','102'])
                self.assertFalse(run.call_args.kwargs.get('shell',False))

    def test_actions_are_serialized_and_lock_is_private(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'XDG_RUNTIME_DIR':tmp}):
            with app.action_lock():
                with self.assertRaises(app.BackendError):
                    with app.action_lock(): pass
            directory = Path(tmp)/'noctalia-throne-vpn'
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode),0o700)
            self.assertEqual(stat.S_IMODE((directory/'action.lock').stat().st_mode),0o600)


FAKE_CLI = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
root=Path(os.environ['FAKE_STATE'])
a=sys.argv[sys.argv.index('--json')+1:]
with (root/'calls').open('a') as f:f.write(json.dumps(a)+'\\n')
if a==['profiles']:
 print(json.dumps({'profiles':[{'id':101,'name':'Example','download_bps':100000000}]}));sys.exit(0)
if a==['tun','on']:
 print('needs_privileges TOKEN_MUST_NOT_LEAK',file=sys.stderr);sys.exit(1)
print(json.dumps({'state':'idle','tun':False,'last_profile_id':101,'profile':None}))
'''


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cli = self.root/'thronectl';self.cli.write_text(FAKE_CLI);self.cli.chmod(0o755)
        self.key = self.root/'api key';self.key.write_text('FICTIONAL_TEST_SECRET')
        self.argv = [sys.executable,str(SCRIPT),'--key-file='+str(self.key),'--thronectl='+str(self.cli)]
        self.env = dict(os.environ, FAKE_STATE=str(self.root), XDG_RUNTIME_DIR=str(self.root))

    def run_helper(self,*args):
        return subprocess.run(self.argv+list(args),env=self.env,capture_output=True,text=True,timeout=5)

    def test_snapshot_process_returns_sorted_json_and_no_key(self):
        p=self.run_helper('--snapshot');self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(p.stdout);self.assertEqual(data['profiles'][0]['id'],101)
        self.assertNotIn(self.key.read_text(),p.stdout)
        self.assertEqual(p.stderr,'')

    def test_permission_failure_process_has_no_traceback_or_proxy_action(self):
        p=self.run_helper('--connect','101');self.assertEqual(p.returncode,1)
        data=json.loads(p.stdout);self.assertFalse(data['ok'])
        self.assertNotIn('TOKEN_MUST_NOT_LEAK',p.stdout)
        self.assertEqual(p.stderr,'')
        calls=[json.loads(s) for s in (self.root/'calls').read_text().splitlines()]
        self.assertEqual(calls,[['status'],['tun','on']])

    def test_missing_key_is_actionable_json(self):
        self.key.unlink();p=self.run_helper('--snapshot')
        self.assertEqual(p.returncode,1)
        self.assertIn('API key file',json.loads(p.stdout)['error'])
        self.assertFalse((self.root/'calls').exists())


if __name__ == '__main__': unittest.main()
