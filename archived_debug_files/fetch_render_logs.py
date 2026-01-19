"""
Busca logs do Render via HTTP e filtra apenas os logs relevantes do processamento
"""
import requests
import sys

# IDs dos bookmarks do último teste
BOOKMARK_IDS = [
    "d0348b36-5c75-45c7-ae64-dd591a25f887",  # ✅ Funcionou
    "ab2d7e21",  # ❌ Falhou (ID parcial)
]

print("=" * 80)
print("🔍 BUSCANDO LOGS DO RENDER")
print("=" * 80)
print()

# URL dos logs públicos do Render (se disponível)
# Alternativa: usar Render API com token

print("⚠️  INSTRUÇÕES PARA BUSCAR LOGS MANUALMENTE:")
print()
print("1. No dashboard do Render (https://dashboard.render.com)")
print("2. Abra seu serviço 'video-refs-backend'")
print("3. Vá na aba 'Logs'")
print("4. Use o filtro de busca e procure por:")
print()

for bookmark_id in BOOKMARK_IDS:
    short_id = bookmark_id[:8]
    print(f"   📋 Bookmark {short_id}:")
    print(f"      - Busque: '{short_id}'")
    print(f"      - Ou: '[TASKS.PY]'")
    print(f"      - Ou: '📸' ou '🔍' ou '💾'")
    print()

print("5. Copie TODAS as linhas que aparecerem para cada bookmark")
print("6. Cole aqui no chat")
print()
print("=" * 80)
print()
print("💡 DICA: Se os logs forem muito longos, procure especificamente por:")
print()
print("   📸 [TASKS.PY] Chamando ThumbnailService.upload_thumbnail()")
print("   🔍 [TASKS.PY] ANTES DE SALVAR:")
print("   💾 [TASKS.PY] SALVO NO BANCO:")
print()
print("=" * 80)
