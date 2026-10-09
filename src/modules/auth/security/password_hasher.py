from typing import Final

from pwdlib import PasswordHash

password_hasher: Final[PasswordHash] = PasswordHash.recommended()
