"""empty message

Revision ID: a4861fcb8f06
Revises: 67e69262171e
Create Date: 2022-11-19 19:48:56.272269

"""
import geoalchemy2
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4861fcb8f06'
down_revision = '67e69262171e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('geodata',
    sa.Column('address', sa.String(), nullable=False),
    sa.Column('district', sa.String(), nullable=False),
    sa.Column('map_link', sa.String(), nullable=False),
    sa.Column('coordinates', geoalchemy2.types.Geometry(geometry_type='POINT', from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.PrimaryKeyConstraint('address', 'district')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('geodata')
    # ### end Alembic commands ###
