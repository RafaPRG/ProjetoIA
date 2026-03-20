from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv

load_dotenv()

agent = Agent(
    model = Groq(id="llama-3.3-70b-versatile"),
    instructions="Use suas ferramentas para detectar se este email é malicioso. Use um texto para mostrar a resposta final, mostrando os principais pontos",
)


prompt = f"""
Remetente: naoresponda@bipa.app
assunto: Seu Informe de Rendimentos está disponível na Bipa
email:
Olá, RAFAEL!

Seu Informe de Rendimentos referente ao ano-base 2025 já está disponível.

Você pode acessá-lo diretamente pelo aplicativo Bipa, na seção "Documentos Importantes".

Sabia que você pode receber sua restituição do IR direto na sua conta Bipa?

É só cadastrar o seu CPF como chave Pix na Bipa e selecionar Pix como meio de pagamento no programa gerador da declaração do Imposto de Renda, para receber a restituição.

Equipe Bipa

Em caso de dúvidas, entre em contato com nosso suporte pelo app ou pelo e-mail contato@bipa.app.."""

agent.print_response(prompt)

