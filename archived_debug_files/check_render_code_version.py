"""
Verifica se o Render está usando o código corrigido
"""
import requests

print("=" * 80)
print("🔍 VERIFICANDO VERSÃO DO CÓDIGO NO RENDER")
print("=" * 80)
print()

url = "https://video-refs-backend.onrender.com/api/debug/code-version"

print(f"Consultando: {url}")
print()

try:
    response = requests.get(url, timeout=10)

    if response.status_code == 200:
        data = response.json()

        print("📋 RESULTADO:")
        print("=" * 80)
        print(f"Service: {data['service']}")
        print(f"Status: {data['status']}")
        print(f"Code Hash: {data['code_hash']}")
        print()
        print(f"Has Double Upload Bug: {data['has_double_upload_bug']}")
        print(f"Has Fix Comment: {data['has_fix_comment']}")
        print()
        print(f"Message: {data['message']}")
        print()

        if data['status'] == 'FIXED':
            print("✅✅✅ CÓDIGO CORRIGIDO DEPLOYADO! ✅✅✅")
            print()
            print("Pode prosseguir com testes!")
        else:
            print("❌ CÓDIGO BUGADO AINDA EM PRODUÇÃO!")
            print()
            print("Snippet do código:")
            print(data['snippet'])
            print()
            print("Ações recomendadas:")
            print("1. Verificar se deploy foi concluído")
            print("2. Reiniciar workers do Celery no Render")
            print("3. Limpar cache Python (.pyc) no Render")

        print()
        print("=" * 80)
    else:
        print(f"❌ Erro: HTTP {response.status_code}")
        print(f"   {response.text}")

except requests.exceptions.Timeout:
    print("❌ Timeout ao conectar com Render")
    print("   Deploy pode ainda estar em andamento")
except Exception as e:
    print(f"❌ Erro: {str(e)}")

print()
print("=" * 80)
