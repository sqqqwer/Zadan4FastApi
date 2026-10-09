import ast
from pathlib import Path

import pytest

MODULES = ('auth', 'org', 'tasks')
SRC = Path(__file__).parents[1] / 'src' / 'modules'


def _imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


@pytest.mark.parametrize('module', MODULES)
def test_module_does_not_touch_others_internals(module: str) -> None:
    """Check that the module does not import internal parts of other modules.

    Args:
        module: Name of the module to check.
    """
    foreign = [m for m in MODULES if m != module]
    violations = []
    for path in (SRC / module).rglob('*.py'):
        for name in _imported_names(path):
            for other in foreign:
                prefix = f'modules.{other}'
                if name.startswith(prefix) and not name.startswith(f'{prefix}.public'):
                    violations.append(f'{path.relative_to(SRC)}:{name}')
    assert not violations, 'Импорт внутренностей чужого модуля:\n' + '\n'.join(violations)
