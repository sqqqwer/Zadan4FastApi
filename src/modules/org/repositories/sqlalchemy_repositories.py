from typing import override
from uuid import UUID, uuid4

from sqlalchemy import cast, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_expression

from ..models.position import Position
from ..models.struct_adm import StructAdm
from ..models.struct_adm_positions import StructAdmPositions
from ..models.types import LtreeType
from ..models.users_positions import UsersPositions
from ..schemas import (
    PositionCreateScheme,
    StructCreateScheme,
)
from .abstracts import OrgBaseRepository, PositionAbstractRepository, StructAbstractRepository


class OrgBaseSqlAlchemyRepository(OrgBaseRepository):
    """SQLAlchemy repository for org objects."""

    def __init__(self, session: AsyncSession, company_id: UUID):
        """Initialize the repository.

        Args:
            session: Database session used by the repository.
            company_id: Company ID.
        """
        super().__init__(company_id=company_id)
        self.session = session


class StructSqlAlchemyRepository(OrgBaseSqlAlchemyRepository, StructAbstractRepository):
    """SQLAlchemy repository for struct objects."""

    @override
    async def list_all(self, limit: int, offset: int) -> list[StructAdm]:
        stmt = (
            select(StructAdm)
            .where(StructAdm.company_id == self.company_id)
            .order_by(StructAdm.id)
            .offset(offset)
            .limit(limit)
        )
        structs = await self.session.scalars(stmt)
        return list(structs.all())

    @override
    async def retrieve(self, id: UUID) -> StructAdm | None:
        stmt = select(StructAdm).where(StructAdm.id == id, StructAdm.company_id == self.company_id)
        struct = await self.session.execute(stmt)
        return struct.scalar_one_or_none()

    @override
    async def create(self, scheme: StructCreateScheme) -> StructAdm:
        struct_id = uuid4()

        struct = StructAdm(id=struct_id, name=scheme.name, company_id=self.company_id, path=struct_id.hex)

        self.session.add(struct)
        return struct

    @override
    async def update(self, obj: StructAdm, scheme: StructCreateScheme) -> StructAdm:
        obj.name = scheme.name
        return obj

    @override
    async def delete(self, obj: StructAdm) -> None:
        stmt = (
            delete(StructAdm)
            .where(StructAdm.company_id == self.company_id, StructAdm.path.bool_op("<@")(obj.path))
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)

    @override
    async def assign_position(self, struct: StructAdm, position: Position) -> StructAdmPositions:
        struct_position = StructAdmPositions(struct_adm=struct, position=position)
        self.session.add(struct_position)
        return struct_position

    @override
    async def assign_director(self, struct: StructAdm, director_id: UUID | None) -> None:
        struct.director_user_id = director_id

    @override
    async def retrieve_with_tree(self, id: UUID) -> list[StructAdm]:
        root_path = (
            select(StructAdm.path).where(StructAdm.id == id, StructAdm.company_id == self.company_id).scalar_subquery()
        )
        stmt = (
            select(StructAdm)
            .where(StructAdm.company_id == self.company_id, StructAdm.path.bool_op("<@")(root_path))
            .order_by(StructAdm.path)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    @override
    async def retrieve_struct_position(self, struct_id: UUID, position_id: UUID) -> StructAdmPositions | None:
        stmt = (
            select(StructAdmPositions)
            .join(StructAdmPositions.struct_adm)
            .join(StructAdmPositions.position)
            .where(
                StructAdmPositions.struct_adm_id == struct_id,
                StructAdmPositions.position_id == position_id,
                StructAdm.company_id == self.company_id,
                Position.company_id == self.company_id,
            )
        )
        struct_position = await self.session.execute(stmt)
        return struct_position.scalar_one_or_none()

    @override
    async def delete_struct_position(self, struct_position: StructAdmPositions) -> None:
        await self.session.delete(struct_position)

    @override
    async def subtree_has_positions(self, struct: StructAdm) -> bool:
        root_path = struct.path

        matching_positions = (
            select(StructAdmPositions.id)
            .join(StructAdmPositions.struct_adm)
            .where(StructAdm.company_id == self.company_id, StructAdm.path.bool_op("<@")(root_path))
        )

        stmt = select(matching_positions.exists())

        result = await self.session.execute(stmt)
        return result.scalar_one()

    @override
    async def is_struct_in_subtree(self, struct: StructAdm, struct_to_check: StructAdm) -> bool:
        struct_in_subtree = select(StructAdm.id).where(
            StructAdm.company_id == self.company_id,
            StructAdm.id == struct_to_check.id,
            StructAdm.path.bool_op("<@")(struct.path),
        )

        stmt = select(struct_in_subtree.exists())

        result = await self.session.execute(stmt)
        return result.scalar_one()

    @override
    async def move_struct(self, struct: StructAdm, struct_target: StructAdm | None) -> None:
        old_path = cast(struct.path, LtreeType())
        target_path = cast(struct_target.path if struct_target is not None else "", LtreeType())

        tail = func.subpath(StructAdm.path, func.nlevel(old_path) - 1)

        stmt = (
            update(StructAdm)
            .where(StructAdm.company_id == self.company_id, StructAdm.path.bool_op("<@")(old_path))
            .values(path=target_path.op("||")(tail))
            .execution_options(synchronize_session="fetch")
        )

        await self.session.execute(stmt)

    @override
    async def lock_tree(self) -> None:
        lock_key = f"org-tree:{self.company_id}"

        stmt = select(
            func.pg_advisory_xact_lock(
                func.hashtextextended(lock_key, 0),
            )
        )
        await self.session.execute(stmt)


class PositionSqlAlchemyRepository(OrgBaseSqlAlchemyRepository, PositionAbstractRepository):
    """SQLAlchemy repository for position objects."""

    @override
    async def list_all(self, limit: int, offset: int) -> list[Position]:
        stmt = (
            select(Position)
            .options(with_expression(Position.users_count, func.count(UsersPositions.id)))
            .outerjoin(Position.users_position)
            .where(Position.company_id == self.company_id)
            .group_by(Position.id)
            .order_by(Position.id)
            .offset(offset)
            .limit(limit)
        )
        positions = await self.session.scalars(stmt)
        return list(positions.all())

    @override
    async def retrieve(self, id: UUID) -> Position | None:
        stmt = (
            select(Position)
            .options(selectinload(Position.users_position), joinedload(Position.struct_adm_positions))
            .where(Position.id == id, Position.company_id == self.company_id)
        )
        position = await self.session.execute(stmt)
        return position.unique().scalar_one_or_none()

    @override
    async def retrieve_for_update(self, id: UUID) -> Position | None:
        stmt = (
            select(Position)
            .options(selectinload(Position.users_position), joinedload(Position.struct_adm_positions))
            .where(Position.id == id, Position.company_id == self.company_id)
            .with_for_update(of=Position)
        )
        position = await self.session.execute(stmt)
        return position.unique().scalar_one_or_none()

    @override
    async def create(self, scheme: PositionCreateScheme) -> Position:
        position = Position(name=scheme.name, company_id=self.company_id)
        self.session.add(position)
        return position

    @override
    async def update(self, obj: Position, scheme: PositionCreateScheme) -> Position:
        obj.name = scheme.name
        return obj

    @override
    async def delete(self, obj: Position) -> None:
        await self.session.delete(obj)

    @override
    async def user_position_create(self, position: Position, user_id: UUID) -> UsersPositions:
        user_position = UsersPositions(user_id=user_id)
        position.users_position.append(user_position)
        return user_position

    @override
    async def user_position_retrieve(self, position: Position, user_id: UUID) -> UsersPositions | None:
        stmt = select(UsersPositions).where(
            UsersPositions.position == position,
            UsersPositions.user_id == user_id,
        )
        user_position = await self.session.execute(stmt)

        return user_position.scalar_one_or_none()

    @override
    async def user_position_delete(self, user_position: UsersPositions) -> None:
        await self.session.delete(user_position)
