import os
from supabase import create_client

url = os.getenv("SUPABASE_URL", "https://twwpcnyqpwznzarguzit.supabase.co")
key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3d3BjbnlxcHd6bnphcmd1eml0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjcxMTUzODMsImV4cCI6MjA0MjY5MTM4M30.tkF02VFr_3IvPpjh7gqYEWCNgOZtWCmr8fE2E8VfGVc")

supabase = create_client(url, key)

result = supabase.table('bookmarks').select('id, title, smart_title, platform').order('created_at', desc=True).limit(10).execute()

print("=" * 80)
print("🔍 VERIFICANDO SMART TITLES NO SUPABASE")
print("=" * 80)
print()

for bm in result.data:
    print(f"📱 Plataforma: {bm.get('platform', 'N/A')}")
    print(f"   ID: {bm['id'][:8]}...")
    print(f"   Título original: {bm.get('title', 'N/A')[:60]}")
    print(f"   Smart Title: {bm.get('smart_title', 'NULL')}")
    print()
