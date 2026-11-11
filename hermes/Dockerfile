# Imagem do Hermes (API + agente + tools). Sem nenhuma chave dentro: tudo vem de variáveis de ambiente no runtime.
# Build a partir da RAIZ do repositório:  docker build -f hermes/Dockerfile -t spread-hermes .
FROM python:3.12.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY src/requirements.txt src/requirements.txt
RUN pip install -r src/requirements.txt python-dotenv==1.0.1

COPY src/ src/
COPY validacao/ validacao/

RUN useradd --create-home --uid 10001 hermes && mkdir -p /app/saida && chown -R hermes:hermes /app
USER hermes

# Railway define PORT; localmente 8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8080'))"
CMD ["python", "src/api.py"]
