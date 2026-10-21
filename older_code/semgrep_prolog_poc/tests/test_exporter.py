import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from export_ast_facts import atom, flatten


class ExportTests(unittest.TestCase):
    def test_variants_and_structure(self):
        # A deliberately synthetic generic-AST-shaped fixture.
        tree = {'Pr': [{'While': {'Call': [{'Plus': ['lower', 'upper']}, {'Div': 2}]}},
                       {'If': {'Eq': ['target', 'item']}}]}
        facts = '\n'.join(flatten(tree))
        for token in ("'Pr'", "'While'", "'Call'", "'Plus'", "'Div'", "'If'", "'Eq'"):
            self.assertIn(token, facts)
        self.assertIn("ast_scalar(", facts)
        self.assertIn("'2'", facts)
        self.assertIn("ast_node_count(", facts)

    def test_escaping_untrusted_strings(self):
        facts = '\n'.join(flatten({"text": "O'Brien\\n\\evil"}))
        self.assertIn("O\\'Brien", facts)
        self.assertIn('\\\\evil', facts)
        self.assertEqual(atom('a\nb'), "'a\\nb'")

    def test_nodes_limit(self):
        with self.assertRaisesRegex(ValueError, 'safety limit'):
            flatten({'Pr': [[1, 2, 3, 4]]}, max_nodes=2)

    def test_cli_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td)
            (path / 'input.json').write_text(json.dumps({'Pr': [1, 2]}), encoding='utf8')
            result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'export_ast_facts.py'),
                                     str(path / 'input.json'), str(path / 'out.pl')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ast_tag('n0000001', 'Pr')", (path / 'out.pl').read_text())

    def test_invalid_json_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td)
            (path / 'bad.json').write_text('NOT JSON', encoding='utf8')
            result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'export_ast_facts.py'),
                                     str(path / 'bad.json'), str(path / 'out.pl')],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((path / 'out.pl').exists())


if __name__ == '__main__':
    unittest.main()
