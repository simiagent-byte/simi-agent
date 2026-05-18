import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPTS = {
    "brief": """Sei JADS Agent, assistente AI di JADS, content creation agency milanese di Simone (@simovecchio_) e Andres. Guida in 3 fasi: 1) BRIEF: chiedi cliente, settore, obiettivo, tone of voice, piattaforma. Una domanda alla volta. 2) STRATEGIA: proponi 2-3 format video, tono visivo, hook narrativo, frequenza. 3) COPY: 3 caption Instagram con emoji e hashtag, 2 titoli Reels, 1 hook​​​​​​​​​​​​​​​​

cat > jads_bot.py << 'ENDOFFILE'
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPTS = {
    "brief": """Sei JADS Agent, assistente AI di JADS, content creation agency milanese di Simone (@simovecchio_) e Andres. Guida in 3 fasi: 1) BRIEF: chiedi cliente, settore, obiettivo, tone of voice, piattaforma. Una domanda alla volta. 2) STRATEGIA: proponi 2-3 format video, tono visivo, hook narrativo, frequenza. 3) COPY: 3 caption Instagram con emoji e hashtag, 2 titoli Reels, 1 hook per i primi 3 secondi. Tono diretto e creativo. Lingua italiana. Usa *grassetto* per Telegram.""",
    "clienti": """Sei JADS Agent, specializzato nella ricerca clienti per JADS agency milanese. Quando Simone descrive un tipo di cliente fornisci: lista 5-8 lead specifici (brand reali milanesi o tipologie realistiche), per ognuno: nome, settore, perché ha bisogno di content, presenza social. Dove cercarli: hashtag Instagram, zone Milano, query Google Maps. Strategia di approccio. Sii specifico. Lingua italiana. Usa *grassetto* per Telegram.""",
    "outreach": """Sei JADS Agent, esperto outreach per agenzie creative italiane. Genera: 1) *DM Instagram* (max 5 righe, riferimento specifico al loro lavoro) 2) *Email* (oggetto + corpo professionale) 3) *Follow-up* dopo 7 giorni. Posiziona JADS come partner creativo non solo editor. Se mancano info chiedi prima. Lingua italiana.""",
    "portfolio": """Sei JADS Agent. Aiuta Simone a gestire il portfolio JADS. Puoi registrare progetti (chiedi: titolo, cliente, tipo contenuto, link), elencarli, suggerire come presentarli, creare bio JADS. Lingua italiana."""
}

MODE_HINTS = {
    "brief": "🎯 *Brief & Copy attivo*\n\nDimmi cliente, settore e obiettivo. Ti guido dalla strategia al copy pronto.",
    "clienti": "🔍 *Ricerca clienti attiva*\n\nDimmi settore, zona e tipo di business. Trovo lead per JADS.",
    "outreach": "💬 *Outreach attivo*\n\nDimmi chi vuoi contattare e cosa sai di loro.",
    "portfolio": "📁 *Portfolio attivo*\n\nPosso registrare progetti, elencarli o aiutarti a presentare JADS."
}

user_states = {}

def get_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = {"mode": "brief", "history": {m: [] for m in SYSTEM_PROMPTS}}
    return user_states[user_id]

def mode_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Brief & Copy", callback_data="mode_brief"), InlineKeyboardButton("🔍 Clienti", callback_data="mode_clienti")],
        [InlineKeyboardButton("💬 Outreach", callback_data="mode_outreach"), InlineKeyboardButton("📁 Portfolio", callback_data="mode_portfolio")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Cambia modalità", callback_data="show_menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Ciao Simone! Sono il tuo *JADS Agent*.\n\nScegli cosa vuoi fare:", parse_mode="Markdown", reply_markup=mode_keyboard())

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Scegli modalità:", parse_mode="Markdown", reply_markup=mode_keyboard())

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_user.id)
    state["history"][state["mode"]] = []
    await update.message.reply_text("🔄 Chat resettata.", parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = get_state(query.from_user.id)
    if query.data == "show_menu":
        await query.message.reply_text("Scegli modalità:", reply_markup=mode_keyboard())
        return
    if query.data.startswith("mode_"):
        mode = query.data.replace("mode_", "")
        state["mode"] = mode
        await query.message.reply_text(MODE_HINTS[mode], parse_mode="Markdown", reply_markup=back_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_state(user_id)
    text = update.message.text
    mode = state["mode"]
    history = state["history"][mode]
    history.append({"role": "user", "content": text})
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPTS[mode],
            messages=history[-20:]
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})
        if len(reply) > 4000:
            for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
                await update.message.reply_text(chunk, parse_mode="Markdown")
        else:
            await update.message.reply_text(reply, parse_mode="Markdown", reply_markup=back_keyboard())
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("⚠️ Errore. Riprova.", reply_markup=back_keyboard())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("JADS Agent avviato ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
