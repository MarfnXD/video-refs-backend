# Use Python 3.11 slim (compatível com Render)
FROM python:3.11-slim

# Instalar FFmpeg e dependências
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório de armazenamento de vídeos
RUN mkdir -p /opt/render/project/videos

# Expor porta
EXPOSE 8000

# Comando para iniciar aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
