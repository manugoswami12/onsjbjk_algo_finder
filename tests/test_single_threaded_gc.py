"""Every SWI-Prolog run collects garbage in its own thread (doc 04 section 19.16): learn_facts wraps env_run.run so
the goal starts with set_prolog_flag(gc_thread, false); with the collector thread AP13's scan gave different
matches on identical input."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import learn_facts
import env_run


class SingleThreadedGc(unittest.TestCase):
    def test_flag_first_in_every_goal(self):
        self.assertTrue(getattr(env_run.run, 'single_threaded_gc', False))
        out = env_run.swipl('current_prolog_flag(gc_thread, V), write(V), nl', [], [])
        self.assertEqual(out, ['false'])

    def test_wrapped_once(self):
        import importlib
        importlib.reload(learn_facts)
        out = env_run.swipl('write(ok), nl', [], [])
        self.assertEqual(out, ['ok'])


if __name__ == '__main__':
    unittest.main()
