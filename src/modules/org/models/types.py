from sqlalchemy.types import UserDefinedType


class LtreeType(UserDefinedType):
    """SQLAlchemy type for PostgreSQL LTREE columns.

    Attributes:
        cache_ok: bool
    """

    cache_ok = True

    def get_col_spec(self, **kw):
        """Get the SQL column type name.

        Args:
            **kw: Additional SQLAlchemy keyword arguments.

        Returns:
            str: SQL column type name: LTREE.
        """
        return "LTREE"
