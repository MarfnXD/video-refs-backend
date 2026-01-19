#!/bin/bash
source venv/bin/activate
for i in {1..10}; do
  echo "===== RODADA $i ====="
  python force_delete_all_storage.py 2>&1 | grep -E "(thumbnails|Total de paths|Total deletado|COMPLETAMENTE LIMPO)" | head -4
  echo ""
  sleep 1
done
