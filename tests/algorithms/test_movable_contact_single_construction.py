"""B020 scope-only control: no full paired constructor calls."""
import ast
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored'
PAIRED = DIRECTORY/'movable_contact_construction.py'
SINGLE = DIRECTORY/'movable_contact_single_construction.py'


class ScopeCheck(unittest.TestCase):
    def test_only_scope_and_diagnostic_identity_change(self):
        self.assertEqual(hashlib.sha256(PAIRED.read_bytes()).hexdigest(),
                         '86d5b6dcc3cfee449ae499b727f4d201e5730db451ee07e7553aaddb02a9d65b')
        paired, single = ast.parse(PAIRED.read_text()), ast.parse(SINGLE.read_text())
        # Diagnostic identity and module prose cannot affect proposals.
        single.body[0] = paired.body[0]
        replacements = {'movable-contact-single': 'movable-contact-trees', 'B020': 'B019'}
        for node in ast.walk(single):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                node.value = replacements.get(node.value, node.value)
        def context(tree):
            return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_Context')
        def partner(cls):
            return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'partner')
        first, second = context(paired), context(single)
        second.body[second.body.index(partner(second))] = partner(first)
        self.assertEqual(ast.dump(paired, include_attributes=False), ast.dump(single, include_attributes=False))

    def test_primary_only_without_incident_lookup(self):
        spec = importlib.util.spec_from_file_location('b020_scope', SINGLE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        class NoIncident:
            def __getitem__(self, key):
                raise AssertionError('single control must not enumerate partner candidates')
        meter = module._Meter(float('inf'))
        ctx = SimpleNamespace(m=meter, incident=NoIncident())
        edge = (17, 93)
        self.assertEqual(module._Context.partner(ctx, None, edge), [edge])
        self.assertEqual((meter.work, dict(meter.counts)), (1, {'schedule': 1}))
        meter.limit = 1
        with self.assertRaisesRegex(module._Stop, 'search_work_limit'):
            module._Context.partner(ctx, None, edge)
        self.assertEqual(meter.work, 1)


if __name__ == '__main__':
    unittest.main()
