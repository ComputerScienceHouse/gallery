"""empty message

Revision ID: c5793935c735
Revises: 18c4f0e138f4
Create Date: 2017-11-05 17:42:40.057518

"""

# revision identifiers, used by Alembic.
revision = 'c5793935c735'
down_revision = '18c4f0e138f4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('files', sa.Column('s3_id', sa.String(length=32), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('files', 's3_id')
    # ### end Alembic commands ###