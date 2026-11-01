import datetime
from uuid import UUID, uuid4

from shared.jwt.claims_scheme import AccessTokenClaims
from shared.resources.enums import RoleEnum

from .constants import COMPANY_ID


def stub_get_current_claims() -> AccessTokenClaims:
    """Create access token claims for a test admin.

    Returns:
        AccessTokenClaims: Test admin claims.
    """
    return AccessTokenClaims(
        sub=uuid4(),
        company_id=UUID(COMPANY_ID),
        role=RoleEnum.ADMIN,
        iss="test",
        aud="test",
        iat=datetime.datetime.now(datetime.UTC),
        exp=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3),
        jti=uuid4(),
    )
