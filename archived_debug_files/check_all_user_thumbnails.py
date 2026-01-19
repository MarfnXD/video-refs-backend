"""
Verifica TODAS as thumbnails do usuário no banco
Para entender quantas realmente estão OK vs quebradas
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
USER_ID = '0ed9bb40-0041-4dca-9649-256cb418f403'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("🔍 VERIFICANDO TODAS AS THUMBNAILS NO BANCO")
print("=" * 80)
print()

# Buscar todos os bookmarks processados
result = supabase.table('bookmarks')\
    .select('id, smart_title, cloud_thumbnail_url, url')\
    .eq('user_id', USER_ID)\
    .eq('processing_status', 'completed')\
    .execute()

bookmarks = result.data or []

print(f"Total de bookmarks processados: {len(bookmarks)}")
print()

# Categorizar
ok_supabase = []
null_thumb = []
instagram_cdn = []
supabase_truncado = []
outros = []

for bm in bookmarks:
    cloud_thumb = bm.get('cloud_thumbnail_url')
    
    if not cloud_thumb:
        null_thumb.append(bm)
    elif 'supabase.co/storage/v1/object/sign/thumbnails' in cloud_thumb:
        # Verificar se está completo (tem user_id/thumbnails/bookmark_id)
        expected = f"{USER_ID}/thumbnails/{bm['id']}"
        if expected in cloud_thumb:
            ok_supabase.append(bm)
        else:
            supabase_truncado.append(bm)
    elif 'instagram.com' in cloud_thumb or 'cdninstagram' in cloud_thumb:
        instagram_cdn.append(bm)
    elif 'supabase.co/storage/v1/object/public/thumbnails' in cloud_thumb:
        supabase_truncado.append(bm)
    else:
        outros.append(bm)

print("=" * 80)
print("📊 ESTATÍSTICAS")
print("=" * 80)
print()
print(f"✅ Thumbnails OK (Supabase completo):   {len(ok_supabase)} ({len(ok_supabase)*100//len(bookmarks)}%)")
print(f"❌ Thumbnails NULL:                     {len(null_thumb)} ({len(null_thumb)*100//len(bookmarks) if len(bookmarks) > 0 else 0}%)")
print(f"❌ Instagram CDN (não funciona no app): {len(instagram_cdn)} ({len(instagram_cdn)*100//len(bookmarks) if len(bookmarks) > 0 else 0}%)")
print(f"❌ Supabase truncado/public:            {len(supabase_truncado)} ({len(supabase_truncado)*100//len(bookmarks) if len(bookmarks) > 0 else 0}%)")
print(f"⚠️  Outros:                              {len(outros)}")
print()

# Mostrar exemplos de cada categoria
if instagram_cdn:
    print("=" * 80)
    print("❌ THUMBNAILS COM URL DO INSTAGRAM (primeiras 5):")
    print("=" * 80)
    for bm in instagram_cdn[:5]:
        print(f"  ID: {bm['id']}")
        print(f"  Título: {bm.get('smart_title', 'Sem título')[:60]}...")
        print(f"  Thumb: {bm['cloud_thumbnail_url'][:80]}...")
        print()

if supabase_truncado:
    print("=" * 80)
    print("❌ THUMBNAILS SUPABASE TRUNCADAS (primeiras 5):")
    print("=" * 80)
    for bm in supabase_truncado[:5]:
        print(f"  ID: {bm['id']}")
        print(f"  Título: {bm.get('smart_title', 'Sem título')[:60]}...")
        print(f"  Thumb: {bm['cloud_thumbnail_url'][:80]}...")
        print()

if null_thumb:
    print("=" * 80)
    print("❌ THUMBNAILS NULL (primeiras 5):")
    print("=" * 80)
    for bm in null_thumb[:5]:
        print(f"  ID: {bm['id']}")
        print(f"  Título: {bm.get('smart_title', 'Sem título')[:60]}...")
        print(f"  Instagram URL: {bm['url']}")
        print()

print("=" * 80)
print("💡 INTERPRETAÇÃO")
print("=" * 80)
print()

if len(ok_supabase) >= len(bookmarks) * 0.8:
    print("✅ Maioria das thumbnails estão OK!")
    print("   Se quase todas aparecem no app, confirma que está funcionando.")
elif len(instagram_cdn) > len(ok_supabase):
    print("❌ Maioria das thumbnails apontam para Instagram!")
    print("   Essas NÃO funcionam no app (precisam de headers/cookies).")
else:
    print("⚠️  Situação mista. Verificar caso a caso.")

print()
