"""
Extrai schema completo da tabela bookmarks lendo todas as migrations.
Gera arquivo SCHEMA.md com lista de todas as colunas.
"""

import re
import os
from pathlib import Path

def extract_columns_from_migrations():
    """Extrai todas as colunas adicionadas nas migrations"""
    migrations_dir = Path("migrations")
    columns = {}

    # Colunas base (sempre existem - criadas na tabela inicial)
    columns['id'] = 'UUID PRIMARY KEY'
    columns['user_id'] = 'UUID REFERENCES users'
    columns['url'] = 'TEXT'
    columns['title'] = 'TEXT'
    columns['platform'] = 'TEXT'
    columns['metadata'] = 'JSONB'
    columns['created_at'] = 'TIMESTAMP WITH TIME ZONE'
    columns['updated_at'] = 'TIMESTAMP WITH TIME ZONE'

    # Ler todas as migrations
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        print(f"📄 Lendo {migration_file.name}...")

        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Procurar por ADD COLUMN
        add_column_pattern = r'ADD COLUMN(?: IF NOT EXISTS)?\s+(\w+)\s+([^,;]+)'
        matches = re.findall(add_column_pattern, content, re.IGNORECASE)

        for column_name, column_type in matches:
            column_name = column_name.strip()
            column_type = column_type.strip()

            # Remove constraints para simplificar
            column_type = re.sub(r'DEFAULT.*', '', column_type, flags=re.IGNORECASE).strip()
            column_type = re.sub(r'CHECK.*', '', column_type, flags=re.IGNORECASE).strip()
            column_type = re.sub(r'REFERENCES.*', '', column_type, flags=re.IGNORECASE).strip()

            if column_name not in columns:
                columns[column_name] = column_type
                print(f"   ✅ {column_name}: {column_type}")

    return columns

def generate_schema_file(columns):
    """Gera arquivo SCHEMA.md com documentação completa"""

    content = """# SCHEMA DA TABELA BOOKMARKS

**IMPORTANTE**: Este arquivo é gerado automaticamente lendo todas as migrations.
Sempre consulte este arquivo ANTES de adicionar campos em `background_processor.py`!

## ✅ COLUNAS QUE EXISTEM NO SUPABASE

"""

    # Agrupar por categoria
    categories = {
        'Básicas': ['id', 'user_id', 'url', 'created_at', 'updated_at'],
        'Metadados': ['title', 'platform', 'metadata'],
        'Processamento IA': ['auto_description', 'auto_tags', 'auto_categories', 'confidence', 'relevance_score'],
        'Análise Multimodal': ['video_transcript', 'visual_analysis', 'transcript_language', 'analyzed_at'],
        'Tradução': ['title_translated_pt', 'description_translated_pt', 'transcript_translated_pt'],
        'Contexto do Usuário': ['user_context_raw', 'user_context_processed'],
        'Download Local': ['local_video_path', 'downloaded_at', 'video_file_size_bytes', 'video_quality', 'frames_generated_at'],
        'Cloud Sync': ['cloud_video_url', 'cloud_upload_status', 'cloud_uploaded_at', 'cloud_file_size_bytes'],
        'Embeddings': ['embedding'],
        'Background Processing': ['processing_status', 'job_id', 'error_message', 'processing_started_at', 'processing_completed_at'],
    }

    for category, expected_columns in categories.items():
        content += f"\n### {category}\n\n"
        for col in expected_columns:
            if col in columns:
                content += f"- ✅ `{col}` - {columns[col]}\n"
            else:
                content += f"- ❌ `{col}` - **NÃO ENCONTRADO** (verificar migrations)\n"

    # Listar colunas que não foram categorizadas
    categorized = set()
    for cols in categories.values():
        categorized.update(cols)

    uncategorized = set(columns.keys()) - categorized
    if uncategorized:
        content += "\n### ⚠️ Outras Colunas (não categorizadas)\n\n"
        for col in sorted(uncategorized):
            content += f"- `{col}` - {columns[col]}\n"

    content += f"\n\n## 📊 TOTAL: {len(columns)} colunas\n"

    # Lista simples para copiar/colar
    content += "\n## 📋 LISTA SIMPLES (para validação rápida)\n\n```python\n"
    content += "BOOKMARKS_COLUMNS = [\n"
    for col in sorted(columns.keys()):
        content += f"    '{col}',\n"
    content += "]\n```\n"

    return content

def main():
    print("🔍 Extraindo schema da tabela bookmarks...\n")

    columns = extract_columns_from_migrations()

    print(f"\n✅ Total de colunas encontradas: {len(columns)}\n")

    schema_content = generate_schema_file(columns)

    with open('SCHEMA.md', 'w', encoding='utf-8') as f:
        f.write(schema_content)

    print("✅ Arquivo SCHEMA.md gerado com sucesso!")
    print("📖 Consulte SCHEMA.md antes de modificar background_processor.py")

if __name__ == "__main__":
    main()
