#!/usr/bin/env python3
"""Script rápido para pegar user_id válido do Supabase"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Consultar tabela auth.users via RPC ou endpoint específico
    # Como service_role_key, podemos consultar diretamente

    # Tentar via SQL direto (auth.users é acessível com service_role_key)
    result = supabase.auth.admin.list_users()

    if result and len(result) > 0:
        print(f"✅ Usuários encontrados: {len(result)}")
        for user in result[:5]:  # Mostrar primeiros 5
            print(f"   - ID: {user.id}")
            print(f"     Email: {user.email}")
            print()
    else:
        print("❌ Nenhum usuário encontrado no Supabase Auth")

except Exception as e:
    print(f"❌ Erro: {e}")
    print("\nTentando método alternativo...")

    # Se não funcionar, podemos usar um UUID fixo que sabemos que existe
    # Baseado nos arquivos SQL que foram lidos:
    # - create_test_user_marco.sql
    # - create_test_user_bianca.sql
    # - create_user_larissa.sql

    print("\n💡 Você pode usar um destes user_ids dos scripts SQL:")
    print("   - Marco: (verificar arquivo create_test_user_marco.sql)")
    print("   - Bianca: (verificar arquivo create_test_user_bianca.sql)")
    print("   - Larissa: (verificar arquivo create_user_larissa.sql)")
