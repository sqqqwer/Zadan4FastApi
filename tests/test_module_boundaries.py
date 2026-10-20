import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MODULES = ('auth', 'org', 'tasks')
SRC = Path(__file__).parents[1] / 'src' / 'modules'


def _imported_names(path: Path) -> list[str]:
    """Resolve absolute and relative imports in a Python source file.

    Args:
        path: Python source file to inspect.

    Returns:
        list[str]: Fully qualified imported module and object names.
    """
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if node.level:
                package = ".".join(path.parent.relative_to(SRC.parents[1]).parts)
                module_name = resolve_name("." * node.level + module_name, package)
            for alias in node.names:
                names.append(module_name if alias.name == "*" else f"{module_name}.{alias.name}")
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
                prefix = f'src.modules.{other}'
                if name.startswith(prefix) and not name.startswith(f'{prefix}.public'):
                    violations.append(f'{path.relative_to(SRC)}:{name}')
    assert not violations, 'Импорт внутренностей чужого модуля:\n' + '\n'.join(violations)


async def test_no_foreign_keys_between_schemas(test_db: AsyncSession) -> None:
    """Check that foreign keys do not reference tables in other schemas.

    Args:
        test_db: Database session used by the test.
    """
    result = await test_db.execute(
        text(
            """
            SELECT c.conname, ns_src.nspname AS from_schema, ns_tgt.nspname AS to_schema
            FROM pg_constraint c
            JOIN pg_class      src    ON src.oid    = c.conrelid
            JOIN pg_class      tgt    ON tgt.oid    = c.confrelid
            JOIN pg_namespace  ns_src ON ns_src.oid = src.relnamespace
            JOIN pg_namespace  ns_tgt ON ns_tgt.oid = tgt.relnamespace
            WHERE c.contype = 'f' AND ns_src.nspname <> ns_tgt.nspname;
            """
        )
    )
    violations = result.all()
    assert not violations, f"Внешние ключи между схемами: {violations}"
