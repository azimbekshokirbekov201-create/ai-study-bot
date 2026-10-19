"""Record explicit payment terms acceptance without inventing legacy consent."""

import sqlalchemy as sa
from alembic import op

revision = "ed3a120fe282"
down_revision = "f9244853068d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("terms_version", sa.String(40), nullable=True))
    op.add_column(
        "payments", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("payments", "terms_accepted_at")
    op.drop_column("payments", "terms_version")
