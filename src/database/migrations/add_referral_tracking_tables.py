"""
Database migration for job referral tracking system
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'a1b2c3d4e5f6'
down_revision = 'previous_migration_id'
branch_labels = None
depends_on = None


def upgrade():
    # Create job_referrals table
    op.create_table('job_referrals',
                    sa.Column('referral_id', postgresql.UUID(as_uuid=True), primary_key=True),
                    sa.Column('job_id', sa.String(36), sa.ForeignKey('jobs.job_id'), nullable=False),
                    sa.Column('referrer_id', sa.String(36), sa.ForeignKey('jobseeker_profiles.user_uid'),
                              nullable=False),
                    sa.Column('referred_email', sa.String(255), nullable=False),
                    sa.Column('referral_code', sa.String(64), unique=True, nullable=False),
                    sa.Column('shared_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
                    sa.Column('application_id', sa.String(36), sa.ForeignKey('job_applications.application_id'),
                              nullable=True),
                    sa.Column('application_date', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('status', sa.String(20), server_default='pending', nullable=False),
                    sa.Column('bonus_awarded', sa.Float, server_default='0.0', nullable=False),
                    sa.Column('bonus_paid', sa.Boolean, server_default='false', nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
                    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                              onupdate=sa.func.now())
                    )

    # Create indexes
    op.create_index('idx_referral_job', 'job_referrals', ['job_id'])
    op.create_index('idx_referral_referrer', 'job_referrals', ['referrer_id'])
    op.create_index('idx_referral_code', 'job_referrals', ['referral_code'])
    op.create_index('idx_referral_status', 'job_referrals', ['status'])

    # Add referral stats columns to jobseeker_profiles
    op.add_column('jobseeker_profiles',
                  sa.Column('referral_count', sa.Integer, server_default='0', nullable=False))
    op.add_column('jobseeker_profiles',
                  sa.Column('referral_bonus_earned', sa.Float, server_default='0.0', nullable=False))


def downgrade():
    op.drop_table('job_referrals')
    op.drop_column('jobseeker_profiles', 'referral_count')
    op.drop_column('jobseeker_profiles', 'referral_bonus_earned')
