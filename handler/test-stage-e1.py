"""Isolated E1 tests: no Cinnamon, logind, sleep or filesystem writes."""
import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest

SOURCE = Path(__file__).resolve().parent / "lid-handler.py"
TEXT = SOURCE.read_text()
fake_gi = types.ModuleType("gi")
fake_repo = types.ModuleType("gi.repository")
fake_repo.Gio = types.SimpleNamespace(DBusSignalFlags=types.SimpleNamespace(NONE=0))
fake_repo.GLib = types.SimpleNamespace(SOURCE_REMOVE=False)
fake_gi.repository = fake_repo
sys.modules["gi"] = fake_gi
sys.modules["gi.repository"] = fake_repo
spec = importlib.util.spec_from_file_location("qv9_e1", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def handler():
    h = object.__new__(mod.LidHandler)
    h.state = "LID_CLOSED"
    h.lid_closed = True
    h.sleeping = False
    h.lock_accepted = True
    h.screen_active = True
    h.lock_ready_logged = False
    h.lock_failed = False
    h.lock_timer_id = None
    h.cycle = 4
    h.bus = types.SimpleNamespace(call=lambda *args: (_ for _ in ()).throw(
        AssertionError("unexpected system D-Bus call")))
    return h


class E1Safety(unittest.TestCase):
    def test_version_and_no_s4_flag(self):
        self.assertEqual(mod.VERSION, "0.8.4-e1")
        self.assertFalse(hasattr(mod, "ENABLE_S4"))

    def test_no_sleep_or_inhibit_path(self):
        tree = ast.parse(TEXT)
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for forbidden in ("acquire_lid_inhibitor", "ownership_probe", "maybe_request_s4"):
            self.assertNotIn(forbidden, names)
        for forbidden in ("SuspendThenHibernate", '"Inhibit"', "flock", "gsettings", "DRY-RUN S4"):
            self.assertNotIn(forbidden, TEXT)

    def test_log_lock_ready_once(self):
        h = handler()
        h.cancel_lock_timer = lambda: None
        with self.assertLogs(level="INFO") as logs:
            h.record_lock_ready()
            h.record_lock_ready()
        self.assertTrue(h.lock_ready_logged)
        self.assertEqual(sum("LOCK ready" in msg for msg in logs.output), 1)

    def test_refuse_if_screen_inactive(self):
        h = handler(); h.screen_active = False
        h.record_lock_ready(); self.assertFalse(h.lock_ready_logged)

    def test_refuse_if_sleeping(self):
        h = handler(); h.sleeping = True
        h.record_lock_ready(); self.assertFalse(h.lock_ready_logged)

    def test_refuse_if_lock_not_accepted(self):
        h = handler(); h.lock_accepted = False
        h.record_lock_ready(); self.assertFalse(h.lock_ready_logged)

    def test_refuse_if_lock_failed(self):
        h = handler(); h.lock_failed = True
        h.record_lock_ready(); self.assertFalse(h.lock_ready_logged)

    def test_closed_event_requests_lock_only(self):
        h = handler()
        h.state, h.lid_closed, h.cycle = "READY", False, 0
        h.screen_status = lambda reason: None
        h.cancel_lock_timer = lambda: None
        locks=[]
        h.request_lock = lambda: locks.append("lock")
        parameters = types.SimpleNamespace(unpack=lambda:(mod.MANAGER, {"LidClosed":True}, []))
        h.on_properties(None,None,None,None,None,parameters,None)
        self.assertEqual((h.state,h.cycle,locks,h.lock_ready_logged),("LID_CLOSED",1,["lock"],False))

    def test_open_event_cancels_state(self):
        h=handler(); h.cancel_lock_timer=lambda: None
        p=types.SimpleNamespace(unpack=lambda:(mod.MANAGER,{"LidClosed":False},[]))
        h.on_properties(None,None,None,None,None,p,None)
        self.assertEqual(h.state,"READY"); self.assertFalse(h.lock_accepted)

    def test_sleep_and_resume_events(self):
        h=handler(); h.screen_status=lambda why:None; h.cancel_lock_timer=lambda:None
        for v,s in ((True,"SLEEPING"),(False,"WAIT_LID_OPEN")):
            p=types.SimpleNamespace(unpack=lambda v=v:(v,))
            h.on_sleep(None,None,None,None,None,p,None)
            self.assertEqual(h.state,s)

    def test_subscription_only_and_loop(self):
        h=handler(); calls=[]
        class Bus:
            def signal_subscribe(self,*args): calls.append(args)
        class Loop:
            def run(self): calls.append("run")
        h.bus=Bus(); h.screen_bus=Bus(); h.loop=Loop()
        h.screen_status=lambda reason:calls.append("screen_status")
        h.lid_closed=False; h.sleeping=False; h.state="READY"
        h.run()
        self.assertEqual(len([x for x in calls if isinstance(x,tuple)]),3)
        self.assertEqual(calls[-1],"run")


if __name__ == "__main__":
    unittest.main(verbosity=2)
