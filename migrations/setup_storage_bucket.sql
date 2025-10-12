-- =========================================
-- SUPABASE STORAGE SETUP PARA SYNC DE VÍDEOS
-- =========================================
--
-- IMPORTANTE: Execute este script no Supabase Dashboard
-- SQL Editor > New Query > Cole e Execute
--
-- =========================================

-- 1. Criar bucket 'user-videos' (se não existir)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'user-videos',
  'user-videos',
  false,  -- Privado (só usuário autenticado acessa seus vídeos)
  104857600,  -- 100MB por arquivo
  ARRAY['video/mp4']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- 2. Políticas RLS (Row Level Security)

-- Política: Usuário pode fazer upload dos próprios vídeos
CREATE POLICY "Users can upload own videos"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'user-videos' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Política: Usuário pode ler próprios vídeos
CREATE POLICY "Users can read own videos"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'user-videos' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Política: Usuário pode deletar próprios vídeos
CREATE POLICY "Users can delete own videos"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'user-videos' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Política: Usuário pode atualizar próprios vídeos (re-upload)
CREATE POLICY "Users can update own videos"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'user-videos' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- =========================================
-- ✅ CONCLUÍDO!
--
-- Próximo passo: Executar migration add_cloud_sync_fields.sql
-- =========================================
