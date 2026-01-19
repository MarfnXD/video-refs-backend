#!/bin/bash

echo "=========================================="
echo "📦 MOVENDO ARQUIVOS TEMPORÁRIOS PARA ARQUIVO"
echo "=========================================="
echo ""

# Criar pasta de arquivo se não existir
mkdir -p archived_debug_files

# Lista de padrões de arquivos para mover
patterns=(
  "test_*.py"
  "check_*.py"
  "debug_*.py"
  "verify_*.py"
  "cleanup_*.py"
  "migrate_*.py"
  "monitor_*.py"
  "process_*.py"
  "reprocess_*.py"
  "diagnose_*.py"
  "investigate_*.py"
  "analyze_*.py"
  "mark_*.py"
  "dispatch_*.py"
  "find_*.py"
  "fix_*.py"
  "force_*.py"
  "generate_*.py"
  "get_*.py"
  "list_*.py"
  "query_*.py"
  "regenerate_*.py"
  "reset_*.py"
  "sync_*.py"
  "wait_*.py"
  "create_*.py"
  "delete_*.py"
  "backup_*.py"
  "fetch_*.py"
  "*_bookmark_ids.txt"
  "reprocess_*.txt"
  "quality_report_*.md"
  "phase_details_output.txt"
  "all_migrated_bookmark_ids.txt"
  "bookmarks_processing_ids.txt"
  "*.csv"
  "COMPLETE_TEST_REPORT_*.md"
  "COMPLETE_TEST_REPORT_*.txt"
  "*.md"
  "analise_logs_sistema.md"
  "cleanup_summary.md"
  "fix_verification_summary.md"
  "MIGRATION_REPORT_*.md"
  "SMART_TITLES_*.md"
  "SETUP_GEMINI_KEY.md"
  "loop_cleanup.sh"
)

# Arquivos importantes para NÃO mover
keep_files=(
  "main.py"
  "models.py"
  "tasks.py"
  "background_processor.py"
  "requirements.txt"
  "README.md"
  ".env"
  ".gitignore"
)

count=0

for pattern in "${patterns[@]}"; do
  for file in $pattern 2>/dev/null; do
    if [ -f "$file" ]; then
      # Verificar se não está na lista de arquivos importantes
      keep=false
      for keep_file in "${keep_files[@]}"; do
        if [ "$file" == "$keep_file" ]; then
          keep=true
          break
        fi
      done
      
      if [ "$keep" == "false" ]; then
        echo "Movendo: $file → archived_debug_files/"
        mv "$file" archived_debug_files/
        ((count++))
      fi
    fi
  done
done

echo ""
echo "=========================================="
echo "✅ $count arquivos movidos para archived_debug_files/"
echo "=========================================="
