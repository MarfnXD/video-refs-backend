"""
Translation Service - Tradução automática de textos usando OpenAI GPT-4o-mini

Usado para traduzir transcrições e análises visuais para português.
Mantém versão original + tradução para busca multilíngue.
"""

from openai import OpenAI
import os

# Cliente OpenAI
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def translate_to_portuguese(text: str, source_language: str = "auto") -> str:
    """
    Traduz texto para português usando GPT-4o-mini.

    Args:
        text: Texto a ser traduzido
        source_language: Idioma de origem (auto-detecta se não especificado)

    Returns:
        Texto traduzido em português

    Custo: ~$0.0001-0.0003 por tradução (gpt-4o-mini muito barato)
    """

    if not text or len(text.strip()) == 0:
        return ""

    # Prompt otimizado para tradução técnica/natural
    prompt = f"""Traduza o seguinte texto para português brasileiro (PT-BR).

INSTRUÇÕES:
- Mantenha o tom e estilo do texto original
- Preserve termos técnicos quando apropriado (CGI, VFX, 3D, AR, etc)
- Use linguagem natural e fluente
- Não adicione explicações ou comentários extras
- Se o texto já estiver em português, retorne exatamente como está

TEXTO ORIGINAL ({source_language}):
{text}

TRADUÇÃO PT-BR:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo mais barato e rápido
            messages=[
                {
                    "role": "system",
                    "content": "Você é um tradutor profissional especializado em tradução técnica e natural para português brasileiro."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Baixa variação (tradução consistente)
            max_tokens=2000   # Suficiente para textos longos
        )

        translation = response.choices[0].message.content.strip()

        # Remove aspas extras que o modelo às vezes adiciona
        if translation.startswith('"') and translation.endswith('"'):
            translation = translation[1:-1]

        return translation

    except Exception as e:
        print(f"❌ Erro ao traduzir texto: {str(e)}")
        # Em caso de erro, retorna texto original
        return text


def translate_multimodal_analysis(
    video_transcript: str,
    visual_analysis: str,
    transcript_language: str
) -> dict:
    """
    Traduz transcrição + análise visual para português.

    Args:
        video_transcript: Transcrição original do áudio
        visual_analysis: Análise visual original dos frames
        transcript_language: Idioma detectado da transcrição (pt, en, es, etc)

    Returns:
        Dict com traduções:
        {
            'video_transcript_pt': str ou None,
            'visual_analysis_pt': str ou None
        }

    Retorna None se texto já estava em português.
    """

    result = {
        'video_transcript_pt': None,
        'visual_analysis_pt': None
    }

    # Se transcrição já está em PT, não traduz
    if transcript_language and transcript_language.lower() != 'pt':
        if video_transcript:
            print(f"🌐 Traduzindo transcrição ({transcript_language} → PT)...")
            result['video_transcript_pt'] = translate_to_portuguese(
                video_transcript,
                source_language=transcript_language
            )
            print(f"✅ Transcrição traduzida ({len(result['video_transcript_pt'])} chars)")

    # Análise visual geralmente está em inglês (GPT-4 Vision responde em EN por padrão)
    if visual_analysis:
        print("🌐 Traduzindo análise visual (EN → PT)...")
        result['visual_analysis_pt'] = translate_to_portuguese(
            visual_analysis,
            source_language="english"
        )
        print(f"✅ Análise visual traduzida ({len(result['visual_analysis_pt'])} chars)")

    return result


# ======================================================
# TESTES
# ======================================================

if __name__ == "__main__":
    # Teste básico de tradução
    print("\n🧪 TESTANDO SERVIÇO DE TRADUÇÃO\n")
    print("="*70)

    # Teste 1: Tradução de inglês para português
    text_en = "This video shows a 3D CGI object appearing in an outdoor urban environment. The visual effects are photorealistic and demonstrate advanced rendering techniques."

    print("\n📝 Teste 1: Inglês → Português")
    print(f"Original: {text_en}")
    translated = translate_to_portuguese(text_en, "english")
    print(f"Traduzido: {translated}")

    # Teste 2: Texto já em português (deve retornar igual)
    text_pt = "Este vídeo mostra um objeto CGI 3D aparecendo em um ambiente urbano externo."

    print("\n📝 Teste 2: Português → Português (sem alteração)")
    print(f"Original: {text_pt}")
    translated_pt = translate_to_portuguese(text_pt, "portuguese")
    print(f"Traduzido: {translated_pt}")

    print("\n" + "="*70)
    print("✅ Testes concluídos!")
