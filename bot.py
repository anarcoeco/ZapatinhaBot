import os
import asyncio
import urllib.request
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
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
- Produtos: vivências regenerativas, Jogo Muda, cards Muda, insumos naturais
- Clientes pagantes: empresas Sistema B, ESG, terceiro setor
- Iniciativas: Kombona Mutirona, Associação ANARCOECO em formação
- Meta: ecossistema de vivências autofinanciado que permita comprar terra

NO INÍCIO DE CADA CONVERSA:
- Perguntar como Vi tá e o que precisa acontecer hoje

NUNCA: listas enormes, mais de 3 sugestões, sermão, formalidade.
Respostas curtas, máximo 4-5 linhas."""

conversation_histories = {}

def call_groq(user_id: int, user_message: str) -> str:
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    conversation_histories[user_id].append({"role": "user", "content": user_message})
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
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"]
    conversation_histories[user_id].append({"role": "assistant", "content": reply})
    return reply

app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"COMANDO /start recebido de {update.effective_user.id}")
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    try:
        response = call_groq(user_id, "Vi acabou de abrir o bot. Cumprimente ela de forma curta e pergunte como ela tá e o que precisa acontecer hoje.")
        await update.message.reply_text(response)
        print("Resposta enviada com sucesso")
    except Exception as e:
        print(f"ERRO no start: {e}")
        await update.message.reply_text("Eai! Tô aqui 🌱")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"MENSAGEM recebida: {update.message.text[:30]}")
    user_id = update.effective_user.id
    try:
        response = call_groq(user_id, update.message.text)
        await update.message.reply_text(response)
    except Exception as e:
        print(f"ERRO na mensagem: {e}")
        await update.message.reply_text("Tive um problema aqui, tenta de novo.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_histories[user_id] = []
    await update.message.reply_text("Histórico zerado 🌱")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK - Zapatinha bot rodando")
        print(f"GET recebido: {self.path}")

    def do_POST(self):
        print(f"POST recebido: {self.path}")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        try:
            update = Update.de_json(json.loads(body), app.bot)
            loop.run_until_complete(app.process_update(update))
            print("Update processado com sucesso")
        except Exception as e:
            print(f"ERRO no webhook: {e}")

    def log_message(self, format, *args):
        print(f"HTTP: {format % args}")

async def setup():
    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook: {WEBHOOK_URL}")
    print(f"Porta: {PORT}")

loop.run_until_complete(setup())
server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
server.serve_forever()
