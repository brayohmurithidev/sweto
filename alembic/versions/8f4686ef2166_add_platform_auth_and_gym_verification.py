"""add platform auth and gym verification

Revision ID: 8f4686ef2166
Revises: b5ddd0cac5de
Create Date: 2026-07-17 20:54:02.358876

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f4686ef2166"
down_revision: str | Sequence[str] | None = "b5ddd0cac5de"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.add_column(
        "users", sa.Column("password_hash", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum(
                "user",
                "admin",
                "super_admin",
                name="user_role",
                native_enum=False,
            ),
            server_default="user",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_system_protected",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    op.execute(
        "UPDATE users SET must_change_password = false "
        "WHERE must_change_password IS NULL"
    )
    op.execute(
        "UPDATE users SET is_system_protected = false WHERE is_system_protected IS NULL"
    )
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.VARCHAR(length=20),
        nullable=True,
    )
    op.create_unique_constraint(op.f("uq_users_email"), "users", ["email"])
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_check_constraint(
        op.f("ck_users_user_role_valid"),
        "users",
        "role IN ('user', 'admin', 'super_admin')",
    )
    op.create_check_constraint(
        op.f("ck_users_login_identity_required"),
        "users",
        "phone_number IS NOT NULL OR email IS NOT NULL",
    )
    op.create_check_constraint(
        op.f("ck_users_administrative_credentials_required"),
        "users",
        "role NOT IN ('admin', 'super_admin') "
        "OR (email IS NOT NULL AND password_hash IS NOT NULL)",
    )

    op.alter_column(
        "auth_events",
        "event_type",
        existing_type=sa.VARCHAR(length=23),
        type_=sa.Enum(
            "otp_requested",
            "otp_request_blocked",
            "otp_verified",
            "otp_verification_failed",
            "otp_expired",
            "otp_attempts_exceeded",
            "login_succeeded",
            "login_denied",
            "password_changed",
            "super_admin_bootstrapped",
            "admin_created",
            "admin_status_changed",
            "admin_role_changed",
            "admin_operation_blocked",
            "gym_verification_document_registered",
            "gym_verification_submitted",
            "gym_verification_approved",
            "gym_verification_rejected",
            "token_refreshed",
            "token_refresh_failed",
            "logout",
            "logout_all",
            "session_revoked",
            "session_expired",
            name="auth_event_type",
            native_enum=False,
        ),
        existing_nullable=False,
    )

    op.add_column(
        "gyms",
        sa.Column(
            "verification_submitted_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "gyms",
        sa.Column(
            "verification_reviewed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "gyms",
        sa.Column("verification_rejection_reason", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_gyms_gym_verification_status_valid"),
        "gyms",
        "verification_status IN ('not_submitted', 'pending', 'approved', 'rejected')",
    )
    op.create_index(
        "ix_gyms_verification_status_submitted_at",
        "gyms",
        ["verification_status", "verification_submitted_at"],
        unique=False,
    )

    op.create_table(
        "gym_verification_documents",
        sa.Column("gym_id", sa.Uuid(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "business_registration",
                "owner_identification",
                "tax_certificate",
                "operating_license",
                "proof_of_address",
                "other",
                name="gym_verification_document_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("document_name", sa.String(length=200), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("file_url", sa.String(length=1000), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0",
            name=op.f(
                "ck_gym_verification_documents_ck_gym_verification_documents_file_size_positive"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["gym_id"],
            ["gyms.id"],
            name=op.f("fk_gym_verification_documents_gym_id_gyms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_gym_verification_documents_uploaded_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gym_verification_documents")),
        sa.UniqueConstraint(
            "gym_id",
            "document_type",
            name="uq_gym_verification_documents_gym_document_type",
        ),
    )
    op.create_index(
        op.f("ix_gym_verification_documents_gym_id"),
        "gym_verification_documents",
        ["gym_id"],
        unique=False,
    )

    op.create_table(
        "gym_verification_reviews",
        sa.Column("gym_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "approve",
                "reject",
                name="gym_verification_decision",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')",
            name=op.f(
                "ck_gym_verification_reviews_ck_gym_verification_reviews_decision_valid"
            ),
        ),
        sa.CheckConstraint(
            "(decision = 'approve' AND rejection_reason IS NULL) "
            "OR (decision = 'reject' AND rejection_reason IS NOT NULL "
            "AND char_length(trim(rejection_reason)) > 0)",
            name=op.f(
                "ck_gym_verification_reviews_ck_gym_verification_reviews_rejection_reason_required"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["gym_id"],
            ["gyms.id"],
            name=op.f("fk_gym_verification_reviews_gym_id_gyms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            name=op.f("fk_gym_verification_reviews_reviewed_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gym_verification_reviews")),
    )
    op.create_index(
        "ix_gym_verification_reviews_gym_reviewed_at",
        "gym_verification_reviews",
        ["gym_id", "reviewed_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema when no email-only users or long audit events exist."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE phone_number IS NULL) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: email-only platform users must be removed or '
                    'migrated first.';
            END IF;
            IF EXISTS (
                SELECT 1 FROM auth_events WHERE char_length(event_type) > 23
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: audit events exceed the previous event_type '
                    'length.';
            END IF;
        END $$;
        """
    )

    op.drop_index(
        "ix_gym_verification_reviews_gym_reviewed_at",
        table_name="gym_verification_reviews",
    )
    op.drop_table("gym_verification_reviews")
    op.drop_index(
        op.f("ix_gym_verification_documents_gym_id"),
        table_name="gym_verification_documents",
    )
    op.drop_table("gym_verification_documents")

    op.drop_index(
        "ix_gyms_verification_status_submitted_at",
        table_name="gyms",
    )
    op.drop_constraint(
        op.f("ck_gyms_gym_verification_status_valid"),
        "gyms",
        type_="check",
    )
    op.drop_column("gyms", "verification_rejection_reason")
    op.drop_column("gyms", "verification_reviewed_at")
    op.drop_column("gyms", "verification_submitted_at")

    op.alter_column(
        "auth_events",
        "event_type",
        existing_type=sa.Enum(
            "otp_requested",
            "otp_request_blocked",
            "otp_verified",
            "otp_verification_failed",
            "otp_expired",
            "otp_attempts_exceeded",
            "login_succeeded",
            "login_denied",
            "password_changed",
            "super_admin_bootstrapped",
            "admin_created",
            "admin_status_changed",
            "admin_role_changed",
            "admin_operation_blocked",
            "gym_verification_document_registered",
            "gym_verification_submitted",
            "gym_verification_approved",
            "gym_verification_rejected",
            "token_refreshed",
            "token_refresh_failed",
            "logout",
            "logout_all",
            "session_revoked",
            "session_expired",
            name="auth_event_type",
            native_enum=False,
        ),
        type_=sa.VARCHAR(length=23),
        existing_nullable=False,
    )

    op.drop_constraint(
        op.f("ck_users_administrative_credentials_required"),
        "users",
        type_="check",
    )
    op.drop_constraint(op.f("ck_users_login_identity_required"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_user_role_valid"), "users", type_="check")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_constraint(op.f("uq_users_email"), "users", type_="unique")
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.VARCHAR(length=20),
        nullable=False,
    )
    op.drop_column("users", "is_system_protected")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
