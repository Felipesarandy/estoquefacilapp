"""auditoria_e_incidentes (trilha de auditoria imutável e gestão de incidentes ITIL)

Revision ID: 84631ed584e8
Revises: d2b9e292d1e5
Create Date: 2026-11-17 22:11:27.053728

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84631ed584e8'
down_revision = 'd2b9e292d1e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stable_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('entity', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('before_json', sa.JSON(), nullable=True),
    sa.Column('after_json', sa.JSON(), nullable=True),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.ForeignKeyConstraint(['stable_id'], ['stables.id'], name='fk_audit_logs_stable_id'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_logs_user_id'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index('ix_audit_logs_entity', ['entity', 'entity_id'], unique=False)
        batch_op.create_index('ix_audit_logs_stable_created', ['stable_id', 'created_at'], unique=False)

    op.create_table('incidents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stable_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='aberto', nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('resolution', sa.Text(), nullable=True),
    sa.Column('opened_by_id', sa.Integer(), nullable=True),
    sa.Column('assigned_to_id', sa.Integer(), nullable=True),
    sa.Column('opened_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("severity IN ('baixa', 'media', 'alta', 'critica')", name='ck_incidents_severity'),
    sa.CheckConstraint("status IN ('aberto', 'em_analise', 'resolvido', 'fechado')", name='ck_incidents_status'),
    sa.CheckConstraint("type IN ('ruptura', 'divergencia_inventario', 'avaria', 'vencimento', 'furto', 'outro')", name='ck_incidents_type'),
    sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], name='fk_incidents_assigned_to_id'),
    sa.ForeignKeyConstraint(['opened_by_id'], ['users.id'], name='fk_incidents_opened_by_id'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_incidents_product_id'),
    sa.ForeignKeyConstraint(['stable_id'], ['stables.id'], name='fk_incidents_stable_id'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.create_index('ix_incidents_product_type', ['product_id', 'type'], unique=False)
        batch_op.create_index('ix_incidents_stable_status', ['stable_id', 'status'], unique=False)


def downgrade():
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.drop_index('ix_incidents_stable_status')
        batch_op.drop_index('ix_incidents_product_type')

    op.drop_table('incidents')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_logs_stable_created')
        batch_op.drop_index('ix_audit_logs_entity')

    op.drop_table('audit_logs')
