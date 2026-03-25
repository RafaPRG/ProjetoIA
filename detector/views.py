import json
import os
import random
import re
import unicodedata

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv

load_dotenv()

agent = Agent(
    model=Groq(id="llama-3.3-70b-versatile"),
    instructions=(
        "Analise se o email é malicioso (phishing/spam). "
        "Obrigatório cobrir três partes: remetente (domínio, legitimidade), assunto e corpo. "
        "Foque em analisar o remetente e domínios suspeitos. "
        "Evite causar dúvida constante; dê um veredito claro. "
        "Se houver incerteza, peça confirmação ao usuário com base nos sinais apontados. "
        "Aponte sinais suspeitos e dê um veredito final objetivo. "
        "Coloque numeros para identificar os tópicos, ao invés de # ou *"
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

PROMPT_BY_LEVEL = {
    "easy": (
        "Gere UM e-mail curto em português para treino de phishing nível FÁCIL. "
        "Use sinais bem evidentes: erros de ortografia, urgência exagerada, links estranhos OU, se legítimo, tom institucional claro e sem pedidos de clique. "
        "Mantenha estrutura simples (3-5 frases). "
    ),
    "medium": (
        "Gere UM e-mail em português nível MÉDIO com sinais moderados. "
        "Se for phishing, misture credibilidade com 1-2 sinais reais (domínio estranho, pedido de dados, discrepância de valor). "
        "Se legítimo, mantenha tom profissional coerente, sem exageros. "
        "Evite erros grotescos; mantenha verossimilhança. "
    ),
    "hard": (
        "Gere UM e-mail em português nível DIFÍCIL, verossímil e sutil. "
        "Se for phishing, inclua sinais discretos porém reais (domínio quase idêntico, link mascarado coerente, pedido fora de canal usual, senso de urgência leve). "
        "Se legítimo, mantenha consistência completa (domínio correto, contexto claro, ausência de pedidos de credenciais). "
        "Nada de exageros óbvios; evite instruções genéricas. "
    ),
}


def _cleanup_json(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()


def _extract_verdict(text: str) -> str:
    lowered = _normalize(text)
    safe_markers = [
        "legitimo",
        "seguro",
        "confiavel",
        "nao e phishing",
        "nao eh phishing",
        "nao parece phishing",
        "sem sinais de phishing",
        "sem indicios",
        "nao encontrei indicios",
    ]
    mal_markers = ["phishing", "malicioso", "suspeito", "golpe", "spam"]

    negates_phishing = re.search(r"nao[^\.\n]{0,80}(phishing|golpe|malicioso|suspeito|spam)", lowered)
    has_safe = any(s in lowered for s in safe_markers) or bool(negates_phishing)
    has_mal = any(m in lowered for m in mal_markers)

    if has_safe and not has_mal:
        return "Legítimo"
    if has_mal and not has_safe:
        return "Malicioso"
    if has_safe and has_mal:
        if negates_phishing:
            return "Legítimo"
        return "Malicioso"
    return "Legítimo"


def index(request):
    if request.method == "POST":
        remetente = request.POST.get("remetente")
        assunto = request.POST.get("assunto")
        corpo = request.POST.get("corpo")

        prompt = (
            "Classifique o e-mail a seguir. Responda em texto curto. "
            "Remetente: {remetente}\nAssunto: {assunto}\nEmail: {corpo}"
        ).format(remetente=remetente, assunto=assunto, corpo=corpo)

        try:
            response = agent.run(prompt)
            resultado = response.content.replace("**", "")
            veredito = _extract_verdict(resultado)
            request.session["ultima_analise"] = {
                "resultado": resultado,
                "veredito": veredito,
                "remetente": remetente,
                "assunto": assunto,
            }
        except Exception:
            request.session["ultima_analise"] = {
                "erro": "Não foi possível analisar agora. Tente novamente em instantes."
            }
        return redirect("index")

    contexto = request.session.pop("ultima_analise", None)
    return render(request, "detector/index.html", contexto or {})


@require_GET
def game_case(request):
    """
    Gera um único caso de e-mail (phishing ou legítimo) para o jogo.
    """
    try:
        difficulty = request.GET.get("difficulty", "easy")
        if difficulty not in PROMPT_BY_LEVEL:
            difficulty = "easy"
        theme = random.choice(THEMES)
        target_phishing = random.choice([True, False])
        prompt = (
            PROMPT_BY_LEVEL[difficulty]
            + f"Tema sorteado (use, sem ficar nichado): {theme}. "
            + "Varie remetente, assunto, tom, vocabulário e formato. "
            + "Defina o campo phishing exatamente como: " + ("true" if target_phishing else "false") + ". "
            + "Retorne APENAS JSON (sem markdown) com chaves: "
            + '{"from":"remetente","subject":"assunto","body":"corpo","phishing":true|false,"hints":["pista1","pista2","pista3"]}. '
            + "Regras das pistas: (1) cada pista deve citar algo que REALMENTE aparece no e-mail "
            + "(remetente, domínio, link explícito se existir, palavra específica, valor, anexo mencionado), "
            + "(2) NÃO invente links encurtados ou detalhes ausentes, "
            + "(3) seja direto e curto (até 12 palavras), "
            + "(4) inclua variedade de sinais técnicos e de contexto, consistentes com o texto. "
            + "Evite repetir 'URGENTE' ou usar alertas se o texto não tiver isso."
        )
        response = agent.run(prompt)
        raw = _cleanup_json(response.content)
        data = json.loads(raw)

        data["phishing"] = target_phishing if "phishing" not in data else bool(data.get("phishing"))
        data["hints"] = [h for h in data.get("hints", []) if h][:4]
        if not data["hints"]:
            raise ValueError("Hints vazios")
    except Exception:
        return JsonResponse({"error": "generation_failed"}, status=502)

    return JsonResponse(data)
