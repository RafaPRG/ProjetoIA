from django.shortcuts import render
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

# Inicializamos o agente fora da função para não recarregar a cada clique
agent = Agent(
    model=Groq(id="llama-3.3-70b-versatile"),
    instructions="Analise se o email é malicioso (phishing/spam). Retorne uma análise detalhada.",
)

def index(request):
    resultado = None
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
        resultado = response.content # Captura o texto da resposta

    return render(request, "detector/index.html", {"resultado": resultado})