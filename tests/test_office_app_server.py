"""Exercise JSONL protocol through a deterministic synthetic executable."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lib.office.app_server import AppServer

FAKE = '''#!/usr/bin/env python3
import json,sys
for line in sys.stdin:
 p=json.loads(line)
 with open(__file__+'.requests','a') as f:f.write(json.dumps(p)+'\\n')
 m=p.get('method')
 if m=='initialized':continue
 result={}
 if m=='thread/start':result={'thread':{'id':'synthetic-thread'},'sandbox':{'type':'readOnly'},'approvalPolicy':'never'}
 if m=='turn/start':result={'turn':{'id':'synthetic-turn'}}
 print(json.dumps({'id':p.get('id'),'result':result}),flush=True)
 if m=='turn/start':
  print(json.dumps({'method':'item/completed','params':{'threadId':'synthetic-thread','item':{'type':'agentMessage','text':'Synthetic completed result'}}}),flush=True)
  print(json.dumps({'method':'turn/completed','params':{'threadId':'synthetic-thread','turn':{'id':'synthetic-turn','status':'completed'}}}),flush=True)
'''


class AppServerTests(unittest.TestCase):
    def test_real_jsonl_boundary_uses_readonly_policies_and_returns_final_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "fake-codex"
            binary.write_text(FAKE)
            binary.chmod(0o700)
            client = AppServer(str(binary), Path(directory), 10)
            try:
                self.assertEqual(client.start(Path(directory), "worker"), "synthetic-thread")
                self.assertEqual(client.turn("Inspect synthetic fixture"), "Synthetic completed result")
            finally:
                client.close()
            calls = [json.loads(line) for line in Path(str(binary) + ".requests").read_text().splitlines()]
            start = next(call["params"] for call in calls if call.get("method") == "thread/start")
            turn = next(call["params"] for call in calls if call.get("method") == "turn/start")
            self.assertEqual(start["sandbox"], "read-only")
            self.assertEqual(turn["sandboxPolicy"], {"type": "readOnly"})
            self.assertEqual(start["approvalPolicy"], "never")
            self.assertEqual(turn["approvalPolicy"], "never")
            self.assertFalse(any(call.get("method") == "thread/resume" for call in calls))

    def test_cancelled_runtime_never_reports_a_result(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "fake-codex"
            binary.write_text(FAKE)
            binary.chmod(0o700)
            cancelled = [False]
            client = AppServer(str(binary), Path(directory), 10, cancelled=lambda: cancelled[0])
            try:
                client.start(Path(directory), "worker")
                cancelled[0] = True
                with self.assertRaisesRegex(RuntimeError, "team_cancelled"):
                    client.turn("Inspect fixture")
            finally:
                client.close()

    def test_cleanup_kills_descendant_even_after_the_server_leader_exits(self):
        import subprocess
        import time
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "fake-codex"
            pidfile = Path(directory) / "child.pid"
            binary.write_text('''#!/usr/bin/env python3
import json,sys,subprocess
for line in sys.stdin:
 p=json.loads(line)
 if p.get('method')=='initialize':
  child=subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)'])
  open(__file__+'.pid','w').write(str(child.pid))
  print(json.dumps({'id':p['id'],'result':{}}),flush=True)
 if p.get('method')=='initialized':break
''')
            binary.chmod(0o700)
            client = AppServer(str(binary), Path(directory), 10)
            child = int(Path(str(binary) + ".pid").read_text())
            client.process.wait(timeout=5)
            client.close()
            time.sleep(.1)
            state = subprocess.run(["ps", "-p", str(child), "-o", "stat="], capture_output=True, text=True).stdout.strip()
            self.assertTrue(not state or state.startswith("Z"), state)


if __name__ == "__main__":
    unittest.main()
