"""
Script para verificar os 4 bookmarks de teste criados
Checa se cloud_thumb_url e gemini_analysis foram salvos corretamente
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# IDs dos bookmarks criados no teste
bookmark_ids = [
    '9d0a8bf8-3006-4c99-9b02-1b4b11cd1c5f',
    'eefc288c-655a-4abb-b1c7-ac79460d3cf6',
    '88788190-2bf6-474c-9391-60bc63c6c8ec',
    'f49ad048-d3b8-4669-b3f8-113c66a382f5'
]

print("=" * 80)
print("🔍 VERIFICAÇÃO DOS BOOKMARKS DE TESTE")
print("=" * 80)
print()

all_ok = True

for idx, bookmark_id in enumerate(bookmark_ids, 1):
    print(f"📋 [{idx}/4] Verificando bookmark: {bookmark_id}")

    result = supabase.table('bookmarks').select('*').eq('id', bookmark_id).single().execute()

    if not result.data:
        print(f"  ❌ Bookmark não encontrado!")
        all_ok = False
        print()
        continue

    data = result.data

    # Campos críticos
    processing_status = data.get('processing_status')
    cloud_video_url = data.get('cloud_video_url')
    cloud_thumb_url = data.get('cloud_thumb_url')
    thumbnail_url = data.get('thumbnail_url')
    smart_title = data.get('smart_title')
    gemini_analysis = data.get('gemini_analysis')
    claude_analysis = data.get('claude_analysis')

    print(f"  Status: {processing_status}")
    print(f"  Smart Title: {smart_title[:60] if smart_title else 'NULL'}...")
    print()

    # Verificar cloud_video_url
    if not cloud_video_url:
        print(f"  ❌ cloud_video_url: NULL")
        all_ok = False
    elif 'supabase' in cloud_video_url.lower():
        print(f"  ✅ cloud_video_url: {cloud_video_url[:80]}...")
    else:
        print(f"  ❌ cloud_video_url NÃO aponta para Supabase: {cloud_video_url[:80]}...")
        all_ok = False

    # Verificar cloud_thumb_url
    if not cloud_thumb_url:
        print(f"  ❌ cloud_thumb_url: NULL")
        all_ok = False
    elif 'supabase' in cloud_thumb_url.lower():
        print(f"  ✅ cloud_thumb_url: {cloud_thumb_url[:80]}...")
    elif 'instagram.com' in cloud_thumb_url.lower() or 'cdninstagram' in cloud_thumb_url.lower():
        print(f"  ❌ cloud_thumb_url aponta para Instagram: {cloud_thumb_url[:80]}...")
        all_ok = False
    else:
        print(f"  ⚠️  cloud_thumb_url: {cloud_thumb_url[:80]}...")

    # Verificar thumbnail_url (Instagram original)
    if thumbnail_url:
        print(f"  ℹ️  thumbnail_url (Instagram): {thumbnail_url[:80]}...")
    else:
        print(f"  ℹ️  thumbnail_url (Instagram): NULL")

    print()

    # Verificar gemini_analysis
    if not gemini_analysis:
        print(f"  ❌ gemini_analysis: NULL")
        all_ok = False
    else:
        print(f"  ✅ gemini_analysis: OK (tem dados)")
        # Mostrar preview
        if isinstance(gemini_analysis, dict):
            analysis_text = gemini_analysis.get('analysis', gemini_analysis.get('text', ''))
        else:
            analysis_text = str(gemini_analysis)
        print(f"     Preview: {analysis_text[:100]}...")

    print()

    # Verificar claude_analysis
    if not claude_analysis:
        print(f"  ⚠️  claude_analysis: NULL (pode estar processando)")
    else:
        print(f"  ✅ claude_analysis: OK (tem dados)")

    print()
    print("-" * 80)
    print()

print()
print("=" * 80)
print("📊 RESUMO FINAL")
print("=" * 80)
print()

if all_ok:
    print("🎉 TODOS OS CAMPOS ESTÃO CORRETOS!")
    print("✅ cloud_video_url: OK")
    print("✅ cloud_thumb_url: OK")
    print("✅ gemini_analysis: OK")
    print()
    print("✅ Pode rodar a migração completa com segurança.")
else:
    print("⚠️  ALGUNS CAMPOS AINDA ESTÃO FALTANDO")
    print()
    print("Possíveis causas:")
    print("  1. Processamento ainda em andamento (Render pode estar lento)")
    print("  2. Cold start do servidor Render")
    print("  3. Erro no processamento de algum vídeo")
    print()
    print("Aguarde mais alguns minutos e rode este script novamente.")
    print("Ou verifique os logs do Render para ver se há erros.")

print()
