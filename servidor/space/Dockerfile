# Space do Hugging Face (Docker) para o servidor do juiz. O código vem do GitHub, então este arquivo
# não muda a cada versão: para atualizar, use "Factory rebuild" nas configurações do Space.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app

ARG REPO=nicollaspaulo51-cyber/wishlens
ARG RAMO=claude/vibrant-feynman-4fhs11

# Dependências e pesos do CLIP primeiro: só são refeitos quando o requirements muda
ADD https://raw.githubusercontent.com/${REPO}/refs/heads/${RAMO}/servidor/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt
RUN python -c "from transformers import CLIPModel, CLIPProcessor; m = 'openai/clip-vit-base-patch32'; CLIPModel.from_pretrained(m); CLIPProcessor.from_pretrained(m)"

# Muda quando há commit novo no ramo: o clone abaixo é refeito só nesse caso
ADD https://api.github.com/repos/${REPO}/git/refs/heads/${RAMO} /tmp/versao.json
RUN git clone --depth 1 --branch ${RAMO} https://github.com/${REPO}.git .

EXPOSE 7860
CMD ["uvicorn", "servidor.app:app", "--host", "0.0.0.0", "--port", "7860"]
