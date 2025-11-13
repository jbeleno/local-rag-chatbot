"""Initial migration with sessions, messages and documents

Revision ID: 409a8e2b2103
Revises: 
Create Date: 2025-11-12 17:45:23.599387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '409a8e2b2103'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - idempotent version that handles existing tables."""
    # Verificar si las tablas ya existen antes de crearlas/modificarlas
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Crear tabla documents solo si no existe
    if 'documents' not in existing_tables:
        op.create_table('documents',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('filename', sa.String(), nullable=False),
            sa.Column('file_path', sa.String(), nullable=False),
            sa.Column('file_extension', sa.String(), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('text_length', sa.Integer(), nullable=True),
            sa.Column('chunks_count', sa.Integer(), nullable=True),
            sa.Column('metadata', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('version', sa.Integer(), server_default='1', nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_documents_created_at'), 'documents', ['created_at'], unique=False)
        op.create_index(op.f('ix_documents_deleted_at'), 'documents', ['deleted_at'], unique=False)
        op.create_index(op.f('ix_documents_file_extension'), 'documents', ['file_extension'], unique=False)
        op.create_index(op.f('ix_documents_filename'), 'documents', ['filename'], unique=False)
        op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
        op.create_index(op.f('ix_documents_is_deleted'), 'documents', ['is_deleted'], unique=False)
        op.create_index(op.f('ix_documents_updated_at'), 'documents', ['updated_at'], unique=False)
    
    # Modificar tabla messages solo si existe
    if 'messages' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('messages')]
        
        if 'deleted_at' not in existing_columns:
            op.add_column('messages', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        
        if 'version' not in existing_columns:
            op.add_column('messages', sa.Column('version', sa.Integer(), server_default='1', nullable=False))
        
        # Intentar crear índices solo si no existen
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('messages')]
        
        if 'ix_messages_created_at' not in existing_indexes:
            op.create_index(op.f('ix_messages_created_at'), 'messages', ['created_at'], unique=False)
        if 'ix_messages_deleted_at' not in existing_indexes:
            op.create_index(op.f('ix_messages_deleted_at'), 'messages', ['deleted_at'], unique=False)
        if 'ix_messages_id' not in existing_indexes:
            op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
        if 'ix_messages_role' not in existing_indexes:
            op.create_index(op.f('ix_messages_role'), 'messages', ['role'], unique=False)
        if 'ix_messages_session_id' not in existing_indexes:
            op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)
    
    # Modificar tabla sessions solo si existe
    if 'sessions' in existing_tables:
        existing_sessions_columns = [col['name'] for col in inspector.get_columns('sessions')]
        
        if 'deleted_at' not in existing_sessions_columns:
            op.add_column('sessions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        
        # Intentar crear índices solo si no existen
        existing_sessions_indexes = [idx['name'] for idx in inspector.get_indexes('sessions')]
        
        if 'ix_sessions_created_at' not in existing_sessions_indexes:
            op.create_index(op.f('ix_sessions_created_at'), 'sessions', ['created_at'], unique=False)
        if 'ix_sessions_deleted_at' not in existing_sessions_indexes:
            op.create_index(op.f('ix_sessions_deleted_at'), 'sessions', ['deleted_at'], unique=False)
        if 'ix_sessions_session_id' not in existing_sessions_indexes:
            op.create_index(op.f('ix_sessions_session_id'), 'sessions', ['session_id'], unique=False)
        if 'ix_sessions_updated_at' not in existing_sessions_indexes:
            op.create_index(op.f('ix_sessions_updated_at'), 'sessions', ['updated_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Nota: El downgrade puede fallar si hay datos, pero es útil para desarrollo
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'sessions' in existing_tables:
        existing_sessions_indexes = [idx['name'] for idx in inspector.get_indexes('sessions')]
        if 'ix_sessions_updated_at' in existing_sessions_indexes:
            op.drop_index(op.f('ix_sessions_updated_at'), table_name='sessions')
        if 'ix_sessions_session_id' in existing_sessions_indexes:
            op.drop_index(op.f('ix_sessions_session_id'), table_name='sessions')
        if 'ix_sessions_deleted_at' in existing_sessions_indexes:
            op.drop_index(op.f('ix_sessions_deleted_at'), table_name='sessions')
        if 'ix_sessions_created_at' in existing_sessions_indexes:
            op.drop_index(op.f('ix_sessions_created_at'), table_name='sessions')
        
        existing_sessions_columns = [col['name'] for col in inspector.get_columns('sessions')]
        if 'deleted_at' in existing_sessions_columns:
            op.drop_column('sessions', 'deleted_at')
    
    if 'messages' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('messages')]
        if 'ix_messages_session_id' in existing_indexes:
            op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
        if 'ix_messages_role' in existing_indexes:
            op.drop_index(op.f('ix_messages_role'), table_name='messages')
        if 'ix_messages_id' in existing_indexes:
            op.drop_index(op.f('ix_messages_id'), table_name='messages')
        if 'ix_messages_deleted_at' in existing_indexes:
            op.drop_index(op.f('ix_messages_deleted_at'), table_name='messages')
        if 'ix_messages_created_at' in existing_indexes:
            op.drop_index(op.f('ix_messages_created_at'), table_name='messages')
        
        existing_columns = [col['name'] for col in inspector.get_columns('messages')]
        if 'version' in existing_columns:
            op.drop_column('messages', 'version')
        if 'deleted_at' in existing_columns:
            op.drop_column('messages', 'deleted_at')
    
    if 'documents' in existing_tables:
        existing_doc_indexes = [idx['name'] for idx in inspector.get_indexes('documents')]
        if 'ix_documents_updated_at' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_updated_at'), table_name='documents')
        if 'ix_documents_is_deleted' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_is_deleted'), table_name='documents')
        if 'ix_documents_id' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_id'), table_name='documents')
        if 'ix_documents_filename' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_filename'), table_name='documents')
        if 'ix_documents_file_extension' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_file_extension'), table_name='documents')
        if 'ix_documents_deleted_at' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_deleted_at'), table_name='documents')
        if 'ix_documents_created_at' in existing_doc_indexes:
            op.drop_index(op.f('ix_documents_created_at'), table_name='documents')
        op.drop_table('documents')
