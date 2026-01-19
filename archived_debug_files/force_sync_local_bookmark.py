"""
Script para forçar sincronização de bookmark local que falhou no Supabase
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client

# Configurações
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    print("❌ SUPABASE_KEY não encontrada")
    sys.exit(1)

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Dados do bookmark problemático
bookmark_id = "3fe5a14d-2770-4c51-a543-65ea3843f133"
user_id = "0ed9bb40-0041-4dca-9649-256cb418f403"
url = "https://www.instagram.com/reel/DPFquQ9DKc-/?igsh=eHhhYXhxbmdkdTBv"

print(f"\n{'='*80}")
print(f"🔧 FORÇANDO DELETAR BOOKMARK VAZIO DO SUPABASE")
print(f"{'='*80}\n")

print(f"ID: {bookmark_id}")
print(f"URL: {url}")

# Deleta do Supabase
print(f"\n🗑️ Deletando bookmark vazio do Supabase...")
try:
    response = supabase.table('bookmarks').delete().eq('id', bookmark_id).execute()
    print(f"✅ Bookmark deletado do Supabase!")
except Exception as e:
    print(f"⚠️ Erro ao deletar (pode não existir): {e}")

print(f"\n{'='*80}")
print(f"✅ CONCLUÍDO!")
print(f"{'='*80}")
print(f"\n📱 PRÓXIMOS PASSOS:")
print(f"1. No app, delete o bookmark localmente (deslize para deletar)")
print(f"2. Compartilhe o vídeo novamente do Instagram")
print(f"3. Backend agora está rápido e deve funcionar")
print(f"\nOU se preferir usar o botão 'Capturar metadados' no card:")
print(f"1. Toque nos 3 pontinhos no card")
print(f"2. Selecione 'Capturar metadados'")
print(f"3. Isso forçará nova extração + processamento de IA")
