import copy
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from repoarena.harness import ArenaError, ISSUE, Ollama, SAMPLE, parse_object, run_arena, validate_judgment, validate_proposal
from repoarena.server import Handler


class HarnessTests(unittest.TestCase):
    def test_sample_is_explicit_and_overrides_user_issue(self):
        events = list(run_arena('Unrelated user input', '', 'unused', sample=True))
        session = events[-1]['session']
        self.assertEqual(events[-1]['type'], 'complete')
        self.assertEqual(session['mode'], 'sample')
        self.assertEqual(session['issue'], ISSUE)
        self.assertEqual([s['stage'] for s in session['stages']], ['A', 'B', 'critique', 'judgment'])
        self.assertEqual(session['stages'][-1]['result']['winner'], 'A')
        self.assertEqual(session['stages'][-1]['result']['totals']['A'], 8.8)

    def test_live_pipeline_preserves_evidence_and_independent_proposals(self):
        class Provider:
            calls = []
            def generate(self, model, system, prompt):
                self.calls.append(json.loads(prompt))
                stage = ['A', 'B', 'critique', 'judgment'][len(self.calls)-1]
                return json.dumps(SAMPLE[stage]), {'seconds': .1, 'output_tokens': 10}
        provider = Provider()
        session = list(run_arena('Build safe resets', 'PostgreSQL', 'test-model', provider))[-1]['session']
        self.assertEqual(session['mode'], 'live')
        self.assertNotIn('proposals', provider.calls[0])
        self.assertNotIn('proposals', provider.calls[1])
        self.assertEqual(set(provider.calls[2]['proposals']), {'A', 'B'})
        self.assertIn('critique', provider.calls[3])
        self.assertEqual(len(session['stages']), 4)
        for stage in session['stages']:
            self.assertIn('raw_response', stage)
            self.assertIn('system_prompt', stage)

    def test_model_cannot_choose_winner_instead_of_rubric(self):
        judgment = copy.deepcopy(SAMPLE['judgment'])
        judgment['winner'] = 'B'
        self.assertEqual(validate_judgment(judgment)['winner'], 'A')

    def test_tie_is_reported(self):
        judgment = copy.deepcopy(SAMPLE['judgment'])
        judgment['scores']['B'] = judgment['scores']['A'].copy()
        self.assertEqual(validate_judgment(judgment)['winner'], 'tie')

    def test_rejects_invalid_scores(self):
        for value in (-1, 11, True, float('nan'), float('inf'), '9'):
            with self.subTest(value=value):
                judgment = copy.deepcopy(SAMPLE['judgment'])
                judgment['scores']['A']['correctness'] = value
                with self.assertRaises(ArenaError):
                    validate_judgment(judgment)

    def test_rejects_missing_model_fields(self):
        with self.assertRaises(ArenaError):
            validate_proposal({'title': 'Incomplete'})

    def test_json_fences_and_invalid_json(self):
        self.assertEqual(parse_object('```json\n{"ok": true}\n```'), {'ok': True})
        for value in ('not json', '[]', 'null', None):
            with self.subTest(value=value), self.assertRaises(ArenaError):
                parse_object(value)

    def test_provider_failure_does_not_become_sample(self):
        class Broken:
            def generate(self, *args):
                raise ArenaError('offline')
        events = run_arena('Build safe resets', '', 'test', Broken())
        self.assertEqual(next(events)['session']['mode'], 'live')
        self.assertEqual(next(events)['type'], 'stage_start')
        with self.assertRaisesRegex(ArenaError, 'offline'):
            next(events)


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.client = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, body=None, headers=None):
        defaults = {'Content-Type': 'application/json'}
        defaults.update(headers or {})
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=defaults)
        return self.client.open(req, timeout=5)

    def test_health_and_static_assets(self):
        with self.request('/api/health') as response:
            self.assertEqual(json.load(response)['status'], 'ok')
        for path, expected in [('/', b'RepoArena'), ('/app.js', b'runArena'), ('/styles.css', b'--lime'), ('/theme.css', b'--bg'), ('/icon.svg', b'<svg')]:
            with self.subTest(path=path), self.request(path) as response:
                self.assertIn(expected, response.read())
                self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])

    def test_sample_full_http_workflow(self):
        with self.request('/api/arena', {'mode': 'sample'}) as response:
            events = [json.loads(line) for line in response]
        self.assertEqual(len(events), 10)
        self.assertEqual(events[-1]['type'], 'complete')
        self.assertEqual(events[-1]['session']['mode'], 'sample')

    def test_invalid_live_inputs_are_rejected(self):
        for body in ({'issue': 'short', 'model': 'test'}, {'issue': 'Long enough issue', 'model': ''}, {'mode': 'fake'}, []):
            with self.subTest(body=body), self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/arena', body)
            self.assertEqual(error.exception.code, 400)

    def test_cross_origin_and_wrong_content_type_are_rejected(self):
        for headers, expected in [({'Origin': 'https://unrelated.example'}, 403), ({'Content-Type': 'text/plain'}, 415)]:
            with self.subTest(headers=headers), self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/arena', {'mode': 'sample'}, headers)
            self.assertEqual(error.exception.code, expected)

    def test_does_not_serve_repository_files(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/../repoarena/server.py')
        self.assertEqual(error.exception.code, 404)

    def test_offline_model_discovery_is_explicit(self):
        with patch('repoarena.server.Ollama.models', side_effect=ArenaError('offline')):
            with self.request('/api/models') as response:
                result = json.load(response)
        self.assertFalse(result['available'])
        self.assertEqual(result['models'], [])
        self.assertIn('offline', result['error'])

    def test_live_provider_error_is_streamed(self):
        with patch('repoarena.harness.Ollama.generate', side_effect=ArenaError('offline')):
            with self.request('/api/arena', {'mode': 'live', 'issue': 'Build a safe reset flow', 'model': 'test'}) as response:
                events = [json.loads(line) for line in response]
        self.assertEqual(events[-1], {'type': 'error', 'error': 'offline'})
        self.assertNotIn('complete', [event['type'] for event in events])

    def test_capacity_limit(self):
        from repoarena.server import SLOTS
        SLOTS.acquire(); SLOTS.acquire()
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/arena', {'mode': 'sample'})
            self.assertEqual(error.exception.code, 429)
        finally:
            SLOTS.release(); SLOTS.release()


class OllamaProtocolTests(unittest.TestCase):
    def test_actual_http_adapter_and_live_pipeline_with_simulated_ollama(self):
        calls = []
        class SimulatedOllama(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'models': [{'name': 'simulated-model'}]}).encode())
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(request)
                stage = ['A', 'B', 'critique', 'judgment'][len(calls)-1]
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({'message': {'content': json.dumps(SAMPLE[stage])}, 'eval_count': 100}).encode())
        server = ThreadingHTTPServer(('127.0.0.1',0), SimulatedOllama)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            provider = Ollama(f'http://127.0.0.1:{server.server_port}')
            self.assertEqual(provider.models(), ['simulated-model'])
            session = list(run_arena('Build a safe reset flow', 'PostgreSQL', 'simulated-model', provider))[-1]['session']
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(call['format'] == 'json' and call['stream'] is False for call in calls))
            self.assertEqual(session['stages'][-1]['result']['winner'], 'A')
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
