"""enable_vector_extension

Revision ID: 55204699a1fc
Revises: 0655057dc2ac
Create Date: 2026-04-23 11:17:31.966469

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '55204699a1fc'
down_revision: Union[str, Sequence[str], None] = '0655057dc2ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS vector;")
