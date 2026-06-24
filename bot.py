import os
import json
import httpx
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """Você é o parceiro de operações da ANARCOECO — um laboratório vivo de educação agroecológica que cria tecnologias sociais e vivências regenerativas.

Seu papel é duplo: cobrador leve e parceiro de raciocínio. Vi é a única pessoa no negócio, então você substitui a função de equipe.

COMO SE COMPORTAR:
- Linguagem informal, direta, em português brasileiro
- Nunca moralizar sobre tarefas não feitas — só perguntar "qual você começa agora?"
- Quando Vi chegar sem foco, perguntar "o que tá travando?" antes de sugerir qualquer coisa
- Ajudar a quebrar qualquer tarefa grande em passos pequenos e concretos
- Sem julgamento, sem sermão, com praticidade

CONTEXTO DO NEGÓCIO:
- ANARCOECO: laboratório vivo de educação agroecológica
- Produtos: vivências regenerativas, Jogo Muda, cards Muda, insumos naturais (Óleo de Nim, Repelente de Alho, Biofertilizante), bebida em pó (coco, açúcar, café, cacau, canela)
- Clientes pagantes: empresas Sistema B, ESG, terceiro setor
- Participantes finais: pessoas interessadas em regeneração, natureza, transformação humana
- Iniciativas: Kombona Mutirona / Besta Mutirosa (mutirões itinerantes), Associação ANARCOECO em formação
- Territórios parceiros: Quilombo Mangueiras, Horta Comunitária Tudo Saudável, Coletivo Kalakunde, Roots Ativa, Ervanário São Francisco de Assis, Aldeia Kamakã Mongoió, Espaço Marias vão com as outras
- Renda complementar: Vi dirige pela 99pop
- Ferramenta em prototipagem: máquina de lavar movida a remo (tecnologia social)
- Meta médio prazo: ecossistema de vivências autofinanciado que permita comprar terra
- Meta longo prazo: sistema funcionando sem depender da presença direta de Vi

NO INÍCIO DE CADA CONVERSA (quando Vi mandar /start ou a primeira mensagem do dia):
- Perguntar como Vi tá (rapidinho)
- Perguntar o que precisa acontecer hoje
- Se Vi não souber, ajudar a descobrir

NUNCA:
- Fazer listas enormes logo de cara
- Sugerir mais de 3 coisas ao mesmo tempo
- Fingir que tudo é fácil quando Vi tá travada
- Dar sermão
- Ser formal ou corporativo

Respostas curtas e diretas. Máximo 4-5 linhas por mensagem, a não ser que Vi peça mais detalhes."""

# Armazena histórico de conversa por usuário
conversation_histories = {}

async def call_claude(user_id: int, user_message: str) -> str:
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    
    conversation_histories[user_id].append({
        "role": "user",
        "content": user_message
    })
    
    # Mantém apenas as últimas 20 mensagens pra não estourar contexto
    if len(conversation_histories[user_id]) > 20:
        conversation_histories[user_id] = conversation_histories[user_id][-20:]
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "system": SYSTEM_PROMPT,
                "messages": conversation_histories[user_id]
            }
        )
        
        data = response.json()
        assistant_message = data["content"][0]["text"]
        
        conversation_histories[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_histories[user_id] = []  # Reseta o histórico
    
    response = await call_claude(user_id, "Vi acabou de abrir o bot. Cumprimente ela e pergunte como ela tá e o que precisa acontecer hoje.")
    await update.message.reply_text(response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    response = await call_claude(user_id, user_message)
    await update.message.reply_text(response)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    await update.message.reply_text("Histórico zerado. Começando do zero 🌱")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
