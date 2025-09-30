-- Migration: Adicionar campos de contexto e criar tabelas auxiliares
-- Data: 2025-09-30
-- Descrição: Suporte para captura de contexto com categorias e projetos

-- 1. Adicionar novos campos na tabela bookmarks
ALTER TABLE bookmarks
ADD COLUMN IF NOT EXISTS user_context_raw TEXT,
ADD COLUMN IF NOT EXISTS user_context_processed TEXT,
ADD COLUMN IF NOT EXISTS categories TEXT[],
ADD COLUMN IF NOT EXISTS projects TEXT[],
ADD COLUMN IF NOT EXISTS tags TEXT[],
ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT FALSE;

-- 2. Criar tabela user_categories (cache de categorias do usuário)
CREATE TABLE IF NOT EXISTS user_categories (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  category_name TEXT NOT NULL,
  usage_count INTEGER DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, category_name)
);

-- 3. Criar índice para busca rápida de categorias
CREATE INDEX IF NOT EXISTS idx_user_categories_user_id ON user_categories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_categories_name ON user_categories(user_id, category_name);

-- 4. Criar tabela user_projects (projetos do usuário)
CREATE TABLE IF NOT EXISTS user_projects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  project_name TEXT NOT NULL,
  description TEXT,
  bookmarks_count INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, project_name)
);

-- 5. Criar índices para busca rápida de projetos
CREATE INDEX IF NOT EXISTS idx_user_projects_user_id ON user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_name ON user_projects(user_id, project_name);

-- 6. Criar índices para busca em bookmarks
CREATE INDEX IF NOT EXISTS idx_bookmarks_categories ON bookmarks USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_bookmarks_projects ON bookmarks USING GIN(projects);
CREATE INDEX IF NOT EXISTS idx_bookmarks_tags ON bookmarks USING GIN(tags);

-- 7. Inserir categorias padrão (seed data)
-- Nota: Essas serão criadas automaticamente quando o usuário usar pela primeira vez
-- mas podemos ter uma lista de sugestões no app

-- 8. Function para atualizar usage_count de categorias
CREATE OR REPLACE FUNCTION update_category_usage()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.categories IS NOT NULL THEN
    -- Para cada categoria no array, incrementar usage_count
    INSERT INTO user_categories (user_id, category_name, usage_count)
    SELECT NEW.user_id, unnest(NEW.categories), 1
    ON CONFLICT (user_id, category_name)
    DO UPDATE SET usage_count = user_categories.usage_count + 1;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 9. Trigger para atualizar usage_count automaticamente
DROP TRIGGER IF EXISTS trigger_update_category_usage ON bookmarks;
CREATE TRIGGER trigger_update_category_usage
  AFTER INSERT OR UPDATE OF categories ON bookmarks
  FOR EACH ROW
  EXECUTE FUNCTION update_category_usage();

-- 10. Function para atualizar bookmarks_count de projetos
CREATE OR REPLACE FUNCTION update_project_bookmarks_count()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.projects IS NOT NULL THEN
    -- Para cada projeto no array, criar/atualizar projeto
    INSERT INTO user_projects (user_id, project_name, bookmarks_count)
    SELECT NEW.user_id, unnest(NEW.projects), 1
    ON CONFLICT (user_id, project_name)
    DO UPDATE SET
      bookmarks_count = user_projects.bookmarks_count + 1,
      updated_at = NOW();
  END IF;

  -- Se for UPDATE e projetos foram removidos, decrementar count
  IF TG_OP = 'UPDATE' AND OLD.projects IS NOT NULL THEN
    UPDATE user_projects
    SET bookmarks_count = bookmarks_count - 1,
        updated_at = NOW()
    WHERE user_id = OLD.user_id
      AND project_name = ANY(OLD.projects)
      AND NOT (project_name = ANY(COALESCE(NEW.projects, ARRAY[]::TEXT[])));
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 11. Trigger para atualizar bookmarks_count automaticamente
DROP TRIGGER IF EXISTS trigger_update_project_count ON bookmarks;
CREATE TRIGGER trigger_update_project_count
  AFTER INSERT OR UPDATE OF projects ON bookmarks
  FOR EACH ROW
  EXECUTE FUNCTION update_project_bookmarks_count();

-- 12. Function para decrementar count quando bookmark é deletado
CREATE OR REPLACE FUNCTION decrease_project_count_on_delete()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.projects IS NOT NULL THEN
    UPDATE user_projects
    SET bookmarks_count = GREATEST(bookmarks_count - 1, 0),
        updated_at = NOW()
    WHERE user_id = OLD.user_id
      AND project_name = ANY(OLD.projects);
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- 13. Trigger para decrementar ao deletar bookmark
DROP TRIGGER IF EXISTS trigger_decrease_project_count ON bookmarks;
CREATE TRIGGER trigger_decrease_project_count
  BEFORE DELETE ON bookmarks
  FOR EACH ROW
  EXECUTE FUNCTION decrease_project_count_on_delete();

-- 14. Comentários para documentação
COMMENT ON COLUMN bookmarks.user_context_raw IS 'Contexto original do usuário (texto digitado ou transcrição do áudio)';
COMMENT ON COLUMN bookmarks.user_context_processed IS 'Contexto melhorado/processado pela IA';
COMMENT ON COLUMN bookmarks.categories IS 'Array de categorias (múltipla seleção)';
COMMENT ON COLUMN bookmarks.projects IS 'Array de projetos relacionados (múltipla seleção)';
COMMENT ON COLUMN bookmarks.tags IS 'Tags auto-geradas pela IA para busca';
COMMENT ON COLUMN bookmarks.ai_processed IS 'Flag indicando se foi processado pela IA';

COMMENT ON TABLE user_categories IS 'Cache de categorias usadas por cada usuário com contagem de uso';
COMMENT ON TABLE user_projects IS 'Projetos do usuário (método PARA do Second Brain)';