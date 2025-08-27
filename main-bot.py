import os
import asyncio
import aiohttp
import base64
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import logging

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi
TELEGRAM_BOT_TOKEN = "8250839004:AAHTECb7HP5DBiWOfqyjfNRYXtgQwsQ0qvs"  # Ganti dengan token bot Telegram Anda
OPENROUTER_API_KEY = "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"  # Ganti dengan API key OpenRouter Anda
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

class TradingChartBot:
    def __init__(self):
        self.session = None
    
    async def start_session(self):
        """Mulai session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Tutup session HTTP"""
        if self.session:
            await self.session.close()
    
    async def encode_image_to_base64(self, image_bytes):
        """Encode gambar ke base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    async def analyze_with_openrouter(self, prompt, image_base64=None):
        """Kirim request ke OpenRouter dengan DeepSeek model"""
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/telegram-trading-bot",
            "X-Title": "Trading Chart Analyzer Bot"
        }
        
        # Buat payload untuk request
        messages = []
        
        if image_base64:
            # Jika ada gambar, gunakan format vision
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            })
        else:
            # Jika hanya teks
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        payload = {
            "model": "mistralai/mistral-small-3.2-24b-instruct",  # Model DeepSeek gratis
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        try:
            await self.start_session()
            async with self.session.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API Error: {response.status} - {error_text}")
                    return f"Error dari OpenRouter API: {response.status}"
        except Exception as e:
            logger.error(f"Error saat menghubungi OpenRouter: {e}")
            return f"Terjadi kesalahan: {str(e)}"

# Inisialisasi bot
trading_bot = TradingChartBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    welcome_message = """
🤖 **Selamat datang di Trading Chart Analyzer Bot!**

Bot ini dapat membantu Anda menganalisis chart trading dengan AI DeepSeek.

**Cara penggunaan:**
📊 Kirim gambar chart trading untuk analisis otomatis
📁 Kirim file gambar lainnya dengan caption untuk analisis khusus  
💬 Ketik pesan untuk analisis teknikal umum

**Commands:**
/start - Tampilkan pesan ini
/help - Bantuan penggunaan
/analyze - Analisis chart (reply ke gambar)

Kirim gambar chart Anda sekarang!
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Contoh Analisis", callback_data="example")],
        [InlineKeyboardButton("🆘 Bantuan", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    help_text = """
**📋 Panduan Penggunaan Bot:**

**1. Analisis Chart Otomatis:**
   • Kirim gambar chart langsung ke bot
   • Bot akan otomatis menganalisis pola, support/resistance, indikator, dll

**2. Analisis Custom:**
   • Kirim gambar dengan caption khusus
   • Contoh: "Analisis timeframe H4 untuk EURUSD"

**3. Pertanyaan Trading:**
   • Tanya tentang strategi trading
   • Contoh: "Bagaimana cara mengidentifikasi trend reversal?"

**4. Format File yang Didukung:**
   • JPG, JPEG, PNG, WebP
   • Maksimal ukuran: 20MB

**5. Tips untuk Hasil Terbaik:**
   • Gunakan chart yang jelas dan tidak blur
   • Sertakan timeframe dan pair jika memungkinkan
   • Berikan konteks tambahan dalam caption

Selamat trading! 📈
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "example":
        example_text = """
**📊 Contoh Hasil Analisis:**

**Pair:** EURUSD
**Timeframe:** H1
**Trend:** Bullish (naik)

**Analisis Teknikal:**
• Support kuat di 1.0850
• Resistance di 1.0920
• RSI menunjukkan momentum bullish (65)
• Moving Average crossover bullish
• Volume meningkat saat breakout

**Rekomendasi:**
📈 BUY di area support 1.0850-1.0860
🎯 Target Profit: 1.0900-1.0920  
🛑 Stop Loss: 1.0840

**Risk Management:** 
Gunakan lot size 1-2% dari balance
        """
        await query.edit_message_text(example_text, parse_mode='Markdown')
    
    elif query.data == "help":
        await help_command(query, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk foto/gambar"""
    await update.message.reply_text("📊 Sedang menganalisis chart... Mohon tunggu sebentar.")
    
    try:
        # Ambil foto dengan kualitas terbaik
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download foto
        photo_bytes = BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        
        # Encode ke base64
        image_base64 = await trading_bot.encode_image_to_base64(photo_bytes.getvalue())
        
        # Buat prompt untuk analisis chart
        caption = update.message.caption if update.message.caption else ""
        
        analysis_prompt = f"""
Saya adalah seorang trader profesional. Tolong analisis chart trading ini dengan detail:

{f"Context tambahan: {caption}" if caption else ""}

Berikan analisis yang mencakup:

1. **Identifikasi Pair & Timeframe** (jika terlihat)
2. **Trend Analysis:**
   - Arah trend utama (bullish/bearish/sideways)
   - Struktur higher highs/lower lows
   
3. **Support & Resistance:**
   - Level support dan resistance key
   - Area supply dan demand
   
4. **Technical Indicators:**
   - Pattern yang teridentifikasi (triangle, flag, head & shoulders, dll)
   - Candlestick patterns penting
   - Volume analysis (jika ada)
   
5. **Trading Setup:**
   - Entry point potensial
   - Target profit yang realistis
   - Stop loss yang tepat
   - Risk/reward ratio
   
6. **Market Sentiment:**
   - Momentum saat ini
   - Kemungkinan pergerakan selanjutnya
   
7. **Risk Management:**
   - Saran position sizing
   - Money management tips

Berikan analisis dalam bahasa Indonesia yang mudah dipahami dengan emoji untuk memperjelas struktur analisis.
        """
        
        # Kirim ke OpenRouter untuk analisis
        analysis_result = await trading_bot.analyze_with_openrouter(analysis_prompt, image_base64)
        
        # Kirim hasil analisis
        await update.message.reply_text(
            f"📈 **HASIL ANALISIS CHART**\n\n{analysis_result}", 
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text(
            "❌ Maaf, terjadi kesalahan saat menganalisis gambar. Coba lagi dengan gambar yang lebih jelas."
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk dokumen/file"""
    document = update.message.document
    
    # Cek apakah file adalah gambar
    if document.mime_type and document.mime_type.startswith('image/'):
        await update.message.reply_text("📊 Sedang menganalisis file gambar... Mohon tunggu.")
        
        try:
            file = await context.bot.get_file(document.file_id)
            
            # Download file
            file_bytes = BytesIO()
            await file.download_to_memory(file_bytes)
            file_bytes.seek(0)
            
            # Encode ke base64
            image_base64 = await trading_bot.encode_image_to_base64(file_bytes.getvalue())
            
            # Analisis sama seperti foto
            caption = update.message.caption if update.message.caption else ""
            
            analysis_prompt = f"""
Analisis chart trading dalam file ini dengan detail:

{f"Context: {caption}" if caption else ""}

Berikan analisis teknikal yang komprehensif mencakup trend, support/resistance, pattern, setup trading, dan risk management dalam bahasa Indonesia.
            """
            
            analysis_result = await trading_bot.analyze_with_openrouter(analysis_prompt, image_base64)
            
            await update.message.reply_text(
                f"📈 **ANALISIS FILE CHART**\n\n{analysis_result}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            await update.message.reply_text(
                "❌ Error menganalisis file. Pastikan file adalah gambar chart yang valid."
            )
    else:
        await update.message.reply_text(
            "📁 File ini bukan gambar. Kirim file gambar chart (JPG, PNG, dll) untuk analisis."
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pesan teks"""
    user_message = update.message.text
    
    # Skip jika command
    if user_message.startswith('/'):
        return
    
    await update.message.reply_text("🤔 Sedang memproses pertanyaan trading Anda...")
    
    try:
        # Buat prompt untuk pertanyaan trading umum
        trading_prompt = f"""
Saya adalah trader yang bertanya: {user_message}

Tolong berikan jawaban yang detail dan praktis sebagai expert trading dengan fokus pada:

1. Analisis teknikal dan fundamental yang relevan
2. Strategi trading yang bisa diterapkan
3. Risk management yang tepat  
4. Tips praktis untuk implementasi
5. Contoh konkret jika diperlukan

Jawab dalam bahasa Indonesia dengan format yang mudah dipahami.
        """
        
        response = await trading_bot.analyze_with_openrouter(trading_prompt)
        
        await update.message.reply_text(
            f"💡 **JAWABAN TRADING:**\n\n{response}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        await update.message.reply_text(
            "❌ Maaf, terjadi kesalahan. Coba tanyakan lagi."
        )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /analyze"""
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        # Jika reply ke gambar, analisis gambar tersebut
        await handle_photo(update, context)
    else:
        await update.message.reply_text(
            "📊 Untuk menggunakan /analyze, reply command ini ke gambar chart yang ingin dianalisis.\n\n"
            "Atau kirim gambar langsung ke bot untuk analisis otomatis."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk error yang tidak tertangani"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Jika ada update dan pesan, kirim error ke user
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Terjadi kesalahan internal. Silakan coba lagi atau hubungi admin."
        )

def main():
    """Main function untuk menjalankan bot"""
    # Validasi konfigurasi
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ Error: TELEGRAM_BOT_TOKEN belum diset!")
        print("Dapatkan token dari @BotFather di Telegram")
        return
    
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY":
        print("❌ Error: OPENROUTER_API_KEY belum diset!")
        print("Daftar di https://openrouter.ai untuk mendapatkan API key gratis")
        return
    
    # Buat aplikasi
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Tambahkan error handler
    application.add_error_handler(error_handler)
    
    # Tambahkan handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Trading Chart Analyzer Bot starting...")
    print("📊 Bot siap menganalisis chart trading!")
    
    # Jalankan bot
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 Bot dihentikan oleh user")
    finally:
        asyncio.run(trading_bot.close_session())

if __name__ == '__main__':
    main()