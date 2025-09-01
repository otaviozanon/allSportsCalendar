# Usar Python 3.11 oficial
FROM python:3.11-slim

# Instalar Tesseract OCR e português
RUN apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-por libtesseract-dev && \
    rm -rf /var/lib/apt/lists/*

# Criar diretório da aplicação
WORKDIR /app

# Copiar arquivos do repositório
COPY . /app

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Comando padrão ao rodar o container
CMD ["python", "generate_ics.py"]
