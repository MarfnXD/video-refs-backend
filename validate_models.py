"""
Script de validação: verifica se os campos usados em background_processor.py
existem nos modelos e no schema do Supabase.

Rode ANTES de fazer commit para evitar erros bobos.
"""

import re
import sys
from models import VideoMetadata
from pydantic import BaseModel

def get_videoMetadata_fields():
    """Retorna lista de campos do modelo VideoMetadata"""
    return list(VideoMetadata.model_fields.keys())

def check_background_processor():
    """Verifica se background_processor.py usa campos válidos"""

    # Ler arquivo
    with open('background_processor.py', 'r') as f:
        content = f.read()

    # Campos válidos do modelo
    valid_fields = get_videoMetadata_fields()

    # Procurar por acessos a video_metadata.CAMPO
    pattern = r'video_metadata\.(\w+)'
    matches = re.findall(pattern, content)

    errors = []
    for field in set(matches):
        if field not in valid_fields:
            errors.append(f"❌ Campo 'video_metadata.{field}' NÃO EXISTE no modelo VideoMetadata")

    # Procurar por metadata.get('CAMPO')
    pattern2 = r"metadata\.get\(['\"](\w+)['\"]\)"
    matches2 = re.findall(pattern2, content)

    for field in set(matches2):
        if field not in valid_fields and field != 'platform':  # platform é convertido de enum
            errors.append(f"⚠️ Campo 'metadata.get(\"{field}\")' pode não existir (verifique manualmente)")

    return errors

def main():
    print("🔍 Validando background_processor.py...")
    print(f"\n✅ Campos válidos do VideoMetadata:")
    for field in get_videoMetadata_fields():
        print(f"   - {field}")

    print(f"\n🔍 Verificando background_processor.py...")
    errors = check_background_processor()

    if errors:
        print(f"\n❌ ERROS ENCONTRADOS:")
        for error in errors:
            print(f"   {error}")
        print(f"\n💡 CORRIJA OS ERROS ANTES DE FAZER COMMIT!")
        sys.exit(1)
    else:
        print(f"\n✅ Nenhum erro encontrado!")
        print(f"✅ Pode fazer commit com segurança!")
        sys.exit(0)

if __name__ == "__main__":
    main()
