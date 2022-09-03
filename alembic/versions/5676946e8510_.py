"""empty message

Revision ID: 5676946e8510
Revises: c78c7304a0b9
Create Date: 2022-08-18 18:10:14.105900

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5676946e8510'
down_revision = 'c78c7304a0b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('apartments', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('apartments', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('houses', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('houses', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_viewed_at', sa.DateTime(), nullable=True))
    subscription_type = sa.Text()
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        subscription_type = sa.LargeBinary()
    op.add_column('users', sa.Column('subscription', subscription_type, nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'subscription')
    op.drop_column('users', 'last_viewed_at')
    op.drop_column('houses', 'updated_at')
    op.drop_column('houses', 'created_at')
    op.drop_column('apartments', 'updated_at')
    op.drop_column('apartments', 'created_at')
    # ### end Alembic commands ###
