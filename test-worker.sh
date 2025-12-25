#!/bin/bash
# Script para testar processamento de um bookmark manualmente
# Uso: ./test-worker.sh <bookmark_id> <url> <user_id>

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "❌ Uso: ./test-worker.sh <bookmark_id> <url> <user_id>"
    echo ""
    echo "Exemplo:"
    echo "  ./test-worker.sh abc123 'https://youtube.com/watch?v=...' user-uuid-456"
    exit 1
fi

BOOKMARK_ID="$1"
URL="$2"
USER_ID="$3"

echo "🧪 Testando processamento de bookmark..."
echo ""
echo "📝 Parâmetros:"
echo "   - Bookmark ID: $BOOKMARK_ID"
echo "   - URL: $URL"
echo "   - User ID: $USER_ID"
echo ""

# Ativar venv se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Criar script Python temporário
cat > /tmp/test_worker.py << 'EOF'
import sys
import os
from dotenv import load_dotenv

# Carregar env vars
load_dotenv()

# Importar tasks
from tasks import process_bookmark_complete_task

# Pegar parâmetros
bookmark_id = sys.argv[1]
url = sys.argv[2]
user_id = sys.argv[3]

print(f"🚀 Enfileirando job...")
print("")

# Enfileirar job
result = process_bookmark_complete_task.apply_async(
    kwargs={
        'bookmark_id': bookmark_id,
        'url': url,
        'user_id': user_id,
        'extract_metadata': True,
        'analyze_video': True,
        'process_ai': True,
        'upload_to_cloud': False,  # Não faz upload (teste rápido)
    }
)

print(f"✅ Job enfileirado com sucesso!")
print(f"   Job ID: {result.id}")
print("")
print("📊 Monitore o progresso em:")
print(f"   - Flower: http://localhost:5555/task/{result.id}")
print(f"   - Logs: tail -f /tmp/celery_logs/worker.log")
print("")
print("⏳ Aguarde ~90-180 segundos para completar")
print("")
EOF

# Executar
python3 /tmp/test_worker.py "$BOOKMARK_ID" "$URL" "$USER_ID"

# Cleanup
rm /tmp/test_worker.py
