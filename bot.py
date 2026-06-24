import os
import asyncio
import urllib.request
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8080))

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
- Iniciativas: Kombona Mutirona / Besta Mutirosa, Associação ANARCOECO em formação
- Renda complementar: Vi dirige pela 99pop
- Meta médio prazo: ecossistema de vivências autofinanciado que permita comprar terra
- Meta longo prazo: sistema funcionando sem depender da presença direta de Vi

NO INÍCIO DE CADA CONVERSA:
- Perguntar como Vi tá (rapidinho)
- Perguntar o que precisa acontecer hoje
- Se Vi não souber, ajudar a descobrir

NUNCA:
- Fazer listas enormes logo de cara
- Sugerir mais de 3 coisas ao mesmo tempo
- Fingir que tudo é fácil quando Vi tá travada
- Dar sermão ou ser formal

Respostas curtas. Máximo 4-5 linhas, a não ser que Vi peça mais."""

conversation_histories = {}

def call_groq(user_id: int, user_message: str) -> str:
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []

    conversation_histories[user_id].append({
        "role": "user",
        "content": user_message
    })

    if len(conversation_histories[user_id]) > 20:
        conversation_histories[user_id] = conversation_histories[user_id][-20:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_histories[user_id]

    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.7
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"]

    conversation_histories[user_id].append({
        "role": "assistant",
        "content": reply
    })
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    response = call_groq(user_id, "Vi acabou de abrir o bot. Cumprimente ela de forma curta e pergunte como ela tá e o que precisa acontecer hoje.")
    await update.message.reply_text(response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    response = call_groq(user_id, update.message.text)
    await update.message.reply_text(response)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    await update.message.reply_text("Histórico zerado. Começando do zero 🌱")

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"Bot rodando via webhook na porta {PORT}...")
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    asyncio.run(main())
