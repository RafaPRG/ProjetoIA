import json
import random
import re
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

agent = Agent(
    model=Groq(id="llama-3.3-70b-versatile"),
    instructions=(
        "Analise se o email é malicioso (phishing/spam). "
        "Obrigatório cobrir três partes: remetente (domínio, legitimidade), assunto e corpo. "
        "Foque bem em analisar o remtente e enxergar domínios suspeitos"
        "Evite causar duvida no usuário, falando que pode ser ou não ser sempre"
        "Se tiver duvida se é malicioso ou não, indique e peça para o usuário analisar os sinais que você apontou, e procurar a legitimidade. "
        "Aponte sinais suspeitos e dê um veredito final objetivo."
    ),
)

THEMES = [
    "banco digital",
    "varejo e-commerce",
    "entregas e logística",
    "streaming e entretenimento",
    "redes sociais",
    "órgão público/serviço cidadão",
    "recursos humanos corporativo",
    "saúde/planos e exames",
    "educação/universidade",
    "cloud e contas corporativas",
    "viagens e passagens",
    "energia/serviços domésticos",
]

# Remove cercas markdown e espaços para tentar carregar o JSON vindo do modelo
def _cleanup_json(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned

def index(request):
    if request.method == "POST":
        remetente = request.POST.get("remetente")
        assunto = request.POST.get("assunto")
        corpo = request.POST.get("corpo")

        # Montamos o prompt dinamicamente
        prompt = f"""
        Remetente: {remetente}
        Assunto: {assunto}
        Email: {corpo}
        """
        
        # Executamos a análise
        response = agent.run(prompt)
        resultado = response.content.replace("**", "")
        messages.success(request, resultado)
        return redirect("index")

    return render(request, "detector/index.html")


@require_GET
def game_case(request):
    """
    Gera um único caso de e-mail (phishing ou legítimo) para o jogo.
    Usa fallback local quando não conseguimos parsear a resposta da IA.
    """
    try:
        theme = random.choice(THEMES)
        target_phishing = random.choice([True, False])
        prompt = (
            "Gere UM e-mail curto em português para treino de phishing. "
            f"Tema sorteado (use, sem ficar nichado): {theme}. "
            "Varie remetente, assunto, tom, vocabulário e formato. "
            "Defina o campo phishing exatamente como: " + ("true" if target_phishing else "false") + ". "
            "Retorne APENAS JSON (sem markdown) com chaves: "
            '{"from":"remetente","subject":"assunto","body":"corpo","phishing":true|false,"hints":["pista1","pista2","pista3"]}. '
            "Regras das pistas: (1) cada pista deve citar algo que REALMENTE aparece no e-mail "
            "(remetente, domínio, link, palavra específica, valor, anexo mencionado), "
            "(2) não invente links encurtados ou detalhes ausentes, "
            "(3) seja direto e curto (até 12 palavras), "
            "(4) inclua variedade de sinais técnicos e de contexto. "
            "Evite repetição de 'URGENTE' ou formatação de alerta em todos os casos."
        )
        response = agent.run(prompt)
        raw = _cleanup_json(response.content)
        data = json.loads(raw)

        # Normalização defensiva
        data["phishing"] = target_phishing if "phishing" not in data else bool(data.get("phishing"))
        data["hints"] = [h for h in data.get("hints", []) if h][:4]
        if not data["hints"]:
            raise ValueError("Hints vazios")
    except Exception:
        return JsonResponse({"error": "generation_failed"}, status=502)

    return JsonResponse(data)
