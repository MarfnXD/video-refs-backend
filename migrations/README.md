# Database Migrations

## Como aplicar a migration

### Opção 1: Supabase Dashboard (Recomendado)

1. Acesse: https://supabase.com/dashboard/project/twwpcnyqpwznzarguzit
2. Vá em **SQL Editor**
3. Copie todo conteúdo de `add_context_fields.sql`
4. Cole e execute
5. Verifique se não houve erros

### Opção 2: Supabase CLI

```bash
# Instalar CLI (se não tiver)
npm install -g supabase

# Login
supabase login

# Aplicar migration
supabase db push --db-url "postgresql://postgres:[PASSWORD]@db.twwpcnyqpwznzarguzit.supabase.co:5432/postgres"
```

## Migrations disponíveis

### `add_context_fields.sql` (2025-09-30)
Adiciona suporte para captura de contexto com IA:

**Novos campos em `video_bookmarks`:**
- `user_context_raw` - Contexto original (texto/transcrição)
- `user_context_processed` - Contexto melhorado pela IA
- `categories` - Array de categorias (multi-seleção)
- `projects` - Array de projetos (multi-seleção)
- `tags` - Tags auto-geradas pela IA
- `ai_processed` - Flag se foi processado

**Novas tabelas:**
- `user_categories` - Cache de categorias do usuário
- `user_projects` - Projetos do usuário (PARA method)

**Triggers automáticos:**
- Atualiza `usage_count` em categorias
- Atualiza `bookmarks_count` em projetos
- Mantém contadores sincronizados

## Verificar se aplicou corretamente

```sql
-- Verificar se colunas foram adicionadas
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'video_bookmarks'
  AND column_name IN ('user_context_raw', 'categories', 'projects', 'tags');

-- Verificar se tabelas foram criadas
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('user_categories', 'user_projects');

-- Verificar triggers
SELECT trigger_name
FROM information_schema.triggers
WHERE event_object_table = 'video_bookmarks';
```