"""
Testa a correção do bug de double upload de thumbnail.

Processa 1 bookmark novo do Instagram e valida:
1. cloud_thumbnail_url → URL do Supabase Storage
2. metadata.thumbnail_url → URL original do Instagram CDN
3. cloud_video_url → URL do Supabase Storage
4. video_transcript e visual_analysis → Gemini
5. smart_title → Gerado
"""
import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

# URL de teste (Instagram Reel novo) - escolher da lista do CSV
# Pegando uma URL aleatória que ainda não foi migrada
TEST_URL = "https://www.instagram.com/reel/DBeO5RoOBx5/"  # Nova URL para testar correção

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🧪 TESTE DE CORREÇÃO - Double Upload Bug")
print("=" * 80)
print()

# 1. Criar bookmark
print(f"📌 Criando bookmark de teste...")
print(f"   URL: {TEST_URL}")
print()

result = supabase.table('bookmarks').insert({
    'user_id': USER_ID,
    'url': TEST_URL,
    'processing_status': 'pending'
}).execute()

bookmark_id = result.data[0]['id']
print(f"✅ Bookmark criado: {bookmark_id}")
print()

# 2. Enfileirar processamento completo
print(f"🔄 Enfileirando processamento completo...")

response = requests.post(
    'https://video-refs-backend.onrender.com/api/process-bookmark-complete',
    json={
        'bookmark_id': bookmark_id,
        'url': TEST_URL,
        'user_id': USER_ID,
        'upload_to_cloud': True,
        'analyze_video': True
    }
)

if response.status_code == 200:
    print(f"✅ Processamento enfileirado com sucesso")
else:
    print(f"❌ Erro ao enfileirar: {response.status_code}")
    print(f"   {response.text}")
    exit(1)

print()

# 3. Aguardar processamento (max 3 minutos)
print(f"⏳ Aguardando processamento (max 3 minutos)...")
print()

max_wait = 180  # 3 minutos
start_time = time.time()

while (time.time() - start_time) < max_wait:
    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()
    bookmark = result.data

    status = bookmark.get('processing_status')

    if status == 'completed':
        print(f"✅ Processamento completo!")
        break
    elif status == 'failed':
        print(f"❌ Processamento falhou!")
        print(f"   Erro: {bookmark.get('error_message')}")
        exit(1)
    else:
        elapsed = int(time.time() - start_time)
        print(f"   Status: {status} ({elapsed}s)", end='\r')
        time.sleep(5)

print()
print()

# 4. Validar campos críticos
print("=" * 80)
print("🔍 VALIDAÇÃO DOS CAMPOS")
print("=" * 80)
print()

metadata = bookmark.get('metadata') or {}
cloud_thumbnail = bookmark.get('cloud_thumbnail_url')
cloud_video = bookmark.get('cloud_video_url')
video_transcript = bookmark.get('video_transcript')
visual_analysis = bookmark.get('visual_analysis')
smart_title = bookmark.get('smart_title')

issues = []

# 1. cloud_thumbnail_url deve ser Supabase Storage
print(f"1️⃣ cloud_thumbnail_url:")
if cloud_thumbnail:
    if 'supabase' in cloud_thumbnail.lower():
        print(f"   ✅ {cloud_thumbnail[:80]}...")

        # Verificar formato correto
        if '/object/public/thumbnails/' in cloud_thumbnail or '/object/sign/thumbnails/' in cloud_thumbnail:
            print(f"   ✅ Formato de URL válido")
        else:
            print(f"   ⚠️  Formato de URL suspeito")
            issues.append("cloud_thumbnail_url com formato estranho")
    else:
        print(f"   ❌ Não é URL do Supabase!")
        print(f"   {cloud_thumbnail}")
        issues.append("cloud_thumbnail_url não aponta para Supabase")
else:
    print(f"   ❌ NULL")
    issues.append("cloud_thumbnail_url está NULL")

print()

# 2. metadata.thumbnail_url deve ser Instagram CDN
print(f"2️⃣ metadata.thumbnail_url:")
thumb_in_meta = metadata.get('thumbnail_url')
if thumb_in_meta:
    if 'cdninstagram' in thumb_in_meta or 'instagram' in thumb_in_meta:
        print(f"   ✅ {thumb_in_meta[:80]}...")
        print(f"   ✅ URL original do Instagram CDN preservada!")
    elif 'supabase' in thumb_in_meta.lower():
        print(f"   ❌ CORROMPIDA! Contém URL do Supabase:")
        print(f"   {thumb_in_meta[:80]}...")
        issues.append("⚠️ CRÍTICO: metadata.thumbnail_url foi corrompida com URL do Supabase!")
    else:
        print(f"   ⚠️  URL desconhecida:")
        print(f"   {thumb_in_meta[:80]}...")
        issues.append("metadata.thumbnail_url com domínio desconhecido")
else:
    print(f"   ❌ NULL")
    issues.append("metadata.thumbnail_url está NULL")

print()

# 3. cloud_video_url
print(f"3️⃣ cloud_video_url:")
if cloud_video:
    if 'supabase' in cloud_video.lower():
        print(f"   ✅ {cloud_video[:80]}...")
    else:
        print(f"   ⚠️  Não é do Supabase: {cloud_video[:80]}...")
        issues.append("cloud_video_url não aponta para Supabase")
else:
    print(f"   ❌ NULL")
    issues.append("cloud_video_url está NULL")

print()

# 4. Análise Gemini
print(f"4️⃣ Análise Gemini:")
if video_transcript and visual_analysis:
    print(f"   ✅ video_transcript: {len(video_transcript)} caracteres")
    print(f"   ✅ visual_analysis: {len(visual_analysis)} caracteres")
else:
    if not video_transcript:
        print(f"   ❌ video_transcript: NULL")
        issues.append("video_transcript está NULL")
    if not visual_analysis:
        print(f"   ❌ visual_analysis: NULL")
        issues.append("visual_analysis está NULL")

print()

# 5. Smart Title
print(f"5️⃣ Smart Title:")
if smart_title:
    print(f"   ✅ {smart_title}")
else:
    print(f"   ❌ NULL")
    issues.append("smart_title está NULL")

print()

# Resultado final
print("=" * 80)
print("📊 RESULTADO DO TESTE")
print("=" * 80)
print()

if issues:
    print(f"❌ TESTE FALHOU - {len(issues)} problema(s) encontrado(s):")
    for issue in issues:
        print(f"   - {issue}")
    print()
    print(f"🔍 ID do bookmark para investigação: {bookmark_id}")
else:
    print(f"✅ TESTE PASSOU COM SUCESSO!")
    print()
    print(f"Todos os campos estão corretos:")
    print(f"   ✅ cloud_thumbnail_url → Supabase Storage")
    print(f"   ✅ metadata.thumbnail_url → Instagram CDN original")
    print(f"   ✅ cloud_video_url → Supabase Storage")
    print(f"   ✅ Análise Gemini completa")
    print(f"   ✅ Smart Title gerado")
    print()
    print(f"🎉 Correção do bug de double upload confirmada!")

print()
print("=" * 80)
