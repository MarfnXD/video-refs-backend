"""
Script para monitorar o processamento dos 5 vídeos em tempo real
"""
import os
import time
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
user_id = '0ed9bb40-0041-4dca-9649-256cb418f403'

# Ler IDs dos bookmarks
try:
    with open('bookmarks_processing_ids.txt', 'r') as f:
        bookmark_ids = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    print("❌ Arquivo bookmarks_processing_ids.txt não encontrado")
    print("   Execute primeiro: python migrate_5_videos_with_cloud.py")
    exit(1)

print("="*80)
print(f"🔍 MONITORANDO {len(bookmark_ids)} VÍDEOS")
print("="*80)
print()

# Buscar URLs
result = supabase.table('bookmarks').select('id, url').in_('id', bookmark_ids).execute()
urls_map = {bm['id']: bm['url'] for bm in result.data} if result.data else {}

print("📋 Vídeos sendo processados:")
for idx, bm_id in enumerate(bookmark_ids, 1):
    url = urls_map.get(bm_id, 'URL não encontrada')
    print(f"  {idx}. {url[:60]}...")
    print(f"     ID: {bm_id}")
print()

print("⏰ Aguardando processamento completar (máx 20 minutos)...")
print("   (Verificando a cada 30 segundos)")
print()

for i in range(40):  # 40 verificações x 30s = 20 minutos max
    # Buscar status de todos
    statuses = []
    for bookmark_id in bookmark_ids:
        res = supabase.table('bookmarks').select('processing_status, error_message').eq('id', bookmark_id).execute()
        if res.data:
            status = res.data[0]['processing_status']
            error = res.data[0].get('error_message', '')
            statuses.append((status, error))
        else:
            statuses.append(('not_found', ''))

    # Contar por status
    completed = sum(1 for s, _ in statuses if s == 'completed')
    failed = sum(1 for s, _ in statuses if s == 'failed')
    processing = sum(1 for s, _ in statuses if s in ['queued', 'processing'])
    pending = sum(1 for s, _ in statuses if s == 'pending')

    # Mostrar progresso
    print(f"[{i+1}/40] ✅ {completed}/5 | ⚙️  {processing}/5 | ⏳ {pending}/5 | ❌ {failed}/5", end='')

    # Se todos completaram ou falharam, parar
    if completed + failed == 5:
        print()
        print()
        print("="*80)
        print("🎉 PROCESSAMENTO FINALIZADO!")
        print("="*80)
        print(f"   ✅ Completos: {completed}")
        print(f"   ❌ Falhados: {failed}")

        if failed > 0:
            print()
            print("⚠️  ERROS ENCONTRADOS:")
            for idx, (status, error) in enumerate(statuses, 1):
                if status == 'failed':
                    url = urls_map.get(bookmark_ids[idx-1], 'URL desconhecida')
                    print(f"\n  Vídeo {idx}: {url[:60]}...")
                    print(f"  Erro: {error[:200]}")
        break

    # Aguardar antes de próxima verificação
    print("\r", end='')  # Limpar linha
    time.sleep(30)

else:
    print()
    print()
    print("⚠️  Timeout: Processamento ainda em andamento após 20 minutos")
    print("   Verifique manualmente o status no Supabase")

print()
print("✓ Monitoramento concluído")
