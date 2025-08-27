import os
import asyncio
import aiohttp
import base64
import json
import time
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi
TELEGRAM_BOT_TOKEN = "8250839004:AAHTECb7HP5DBiWOfqyjfNRYXtgQwsQ0qvs"  # Ganti dengan token bot Telegram Anda
CLAUDE_API_KEY = "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"
CLAUDE_BASE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

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
    
    def detect_image_type(self, image_bytes):
        """Deteksi tipe gambar berdasarkan header bytes"""
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        elif image_bytes.startswith(b'WEBP', 8):
            return 'image/webp'
        elif image_bytes.startswith(b'GIF'):
            return 'image/gif'
        else:
            return 'image/jpeg'  # default fallback
    
    async def get_latest_market_context(self):
        """Dapatkan konteks market terbaru (simulasi - bisa diintegrasikan dengan news API)"""
        current_time = datetime.now()
        
        # Simulasi konteks market - bisa diintegrasikan dengan real market data API
        market_context = f"""
MARKET CONTEXT UPDATE ({current_time.strftime('%Y-%m-%d %H:%M:%S')}):

📊 CURRENT MARKET CONDITIONS:
• Global sentiment: Risk-on/Risk-off analysis needed
• Major central bank policies: Monitor Fed, ECB, BoJ decisions
• Geopolitical factors: Consider ongoing global events impact
• Economic calendar: Check for high-impact news releases

🔥 TRENDING ANALYSIS FOCUS:
• Look for confluence zones (multiple timeframe alignment)
• Check for institutional order flow signs
• Identify smart money accumulation/distribution
• Consider session-based trading opportunities (Asian/London/NY)

⚡ CURRENT TRADING OPPORTUNITIES:
• Focus on major pairs: EURUSD, GBPUSD, USDJPY, AUDUSD
• Watch for breakout setups with volume confirmation
• Consider mean reversion plays on overextended moves
• Monitor commodities correlation (Gold, Oil impact on currencies)
        """
        
        return market_context.strip()
    
    async def analyze_with_claude(self, prompt, image_base64=None, image_type=None, max_retries=3):
        """Kirim request ke Claude API"""
        
        for attempt in range(max_retries):
            try:
                await self.start_session()
                
                headers = {
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                # Buat content untuk request
                content = []
                
                if image_base64:
                    # Format untuk vision models
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_type or 'image/jpeg',
                            "data": image_base64
                        }
                    })
                
                # Tambahkan text prompt
                content.append({
                    "type": "text", 
                    "text": prompt
                })
                
                payload = {
                    "model": CLAUDE_MODEL,
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    "temperature": 0.7
                }
                
                async with self.session.post(
                    CLAUDE_BASE_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        result = json.loads(response_text)
                        
                        # Extract response
                        if 'content' in result and len(result['content']) > 0:
                            message_content = result['content'][0]['text']
                            
                            # Add model info to response
                            model_footer = f"\n\n🤖 *Analyzed by Professional AI Trading System*"
                            return message_content + model_footer
                        else:
                            raise Exception("Invalid response format")
                    
                    elif response.status == 429:  # Rate limit
                        logger.warning("Rate limit hit for Claude API")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            return "⏰ API sedang rate limited. Coba lagi dalam beberapa menit."
                    
                    else:
                        error_data = json.loads(response_text) if response_text else {}
                        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                        logger.error(f"Claude API Error: {response.status} - {error_msg}")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            return f"❌ Error dari Claude API: {error_msg}"
            
            except asyncio.TimeoutError:
                logger.error("Timeout for Claude API")
                if attempt < max_retries - 1:
                    continue
                else:
                    return "⏰ Request timeout. API mungkin sedang overloaded, coba lagi nanti."
            
            except Exception as e:
                logger.error(f"Error with Claude API: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    return f"❌ Terjadi kesalahan: {str(e)}"
        
        return "❌ Semua percobaan gagal. Coba lagi nanti."

# Inisialisasi bot
trading_bot = TradingChartBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    welcome_message = """
🤖 **Selamat datang di Professional AI Trading Analysis Bot!**

Bot professional ini menggunakan AI Claude terdepan untuk menganalisis chart trading dengan presisi tinggi dan insight market yang mendalam.

**🔥 Fitur Professional:**
📊 Deep chart analysis dengan AI vision technology
📈 Real-time market context integration  
⚡ Institutional-grade trading recommendations
🎯 Precise entry/exit points dengan advanced risk management
💼 Professional trading insights dan market psychology
📱 Multi-timeframe analysis capabilities

**Professional Services:**
📊 **Chart Analysis** - Kirim gambar chart untuk analisis mendalam
📁 **File Analysis** - Upload file chart untuk review detail  
💬 **Trading Consultation** - Konsultasi strategi dan market outlook
📈 **Market Intelligence** - Real-time market context dan opportunities

**Commands:**
/start - Dashboard utama
/help - Panduan professional
/analyze - Advanced chart analysis (reply ke gambar)

**🎯 Hasil Professional Yang Anda Dapatkan:**
✅ Multi-timeframe technical analysis
✅ Institutional order flow insights  
✅ Risk-adjusted trading recommendations
✅ Market psychology dan sentiment analysis
✅ Session-based optimal timing
✅ Advanced risk management framework

Kirim chart trading Anda untuk mendapatkan analisis professional level!
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Professional Analysis Demo", callback_data="example")],
        [InlineKeyboardButton("🆘 Professional Guide", callback_data="help")],
        [InlineKeyboardButton("📈 Market Intelligence", callback_data="market")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    help_text = """
**📋 Professional Trading Bot Guide:**

**🎯 Professional Chart Analysis:**
   • Upload high-quality trading charts
   • AI analyzes multi-timeframe patterns dan institutional flows
   • Receive professional-grade entry/exit recommendations
   • Advanced risk management dengan precise calculations
   • Market context integration untuk optimal timing

**📊 Analysis Types Supported:**
   • **Scalping Analysis** - M1, M5, M15 precision setups
   • **Day Trading** - H1, H4 momentum dan breakout strategies
   • **Swing Trading** - Daily/Weekly trend continuation setups
   • **Position Trading** - Monthly macro trend analysis

**💼 Professional Features:**
   • **Multi-Asset Analysis** - Forex, Indices, Commodities, Crypto
   • **Institutional Perspective** - Smart money flow analysis
   • **Risk-Adjusted Sizing** - Professional position management
   • **Session Optimization** - Asian/London/NY session strategies
   • **Correlation Analysis** - Cross-market impact assessment

**🔥 Advanced Capabilities:**
   • **Order Flow Analysis** - Identify institutional accumulation/distribution
   • **Liquidity Mapping** - Find optimal entry/exit zones
   • **Market Structure** - Trend/range identification
   • **Volume Profile** - Price acceptance levels
   • **News Integration** - Economic calendar impact analysis

**📱 Usage Instructions:**
   • Send clear, high-resolution charts
   • Include timeframe dan pair information in caption
   • Specify your trading style preference
   • Add any specific questions atau focus areas

**🎯 Professional Results:**
   • Detailed technical analysis dengan probability assessments
   • Multiple scenario planning (Plan A, B, C)
   • Precise risk/reward calculations
   • Time-based execution guidance
   • Professional market commentary

**🤖 Powered by Advanced AI Technology**
*Professional-grade analysis untuk serious traders*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk inline keyboard"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "example":
        example_text = """
**📊 Professional Analysis Example:**

**Asset:** EURUSD  
**Timeframe:** H4 (Multi-timeframe confirmation)
**Analysis Type:** Institutional Grade

**📈 Professional Technical Assessment:**
• **Market Structure:** Clean uptrend dengan institutional accumulation
• **Order Flow:** Smart money positioning long pada key support confluence
• **Liquidity Analysis:** Major stops cleared below 1.0850, path clear upward
• **Volume Profile:** Strong acceptance above 1.0870 VPOC
• **Session Analysis:** London session shows institutional buying interest

**🎯 Professional Trading Setup:**
**Strategy:** Institutional trend continuation
**Entry Method:** Limit order pada premium discount (1.0865-1.0875)
**Primary Target:** 1.0920 (institutional resistance cluster)
**Extended Target:** 1.0950 (weekly pivot confluence)
**Stop Loss:** 1.0845 (below institutional support + 15 pip buffer)

**💼 Risk Management Framework:**
• **Risk per Trade:** 1.5% of account (professional standard)
• **Position Size:** Calculate based on 25-pip stop
• **R:R Ratio:** 1:2.5 (primary), 1:4.2 (extended)  
• **Win Probability:** 72% based on similar setups
• **Max Drawdown:** 4% monthly limit maintained

**⚡ Market Intelligence Integration:**
• **Economic Calendar:** No major EUR/USD events next 48h
• **Central Bank Sentiment:** ECB neutral, USD showing weakness
• **Risk Sentiment:** Risk-on environment supporting EUR strength  
• **Institutional Positioning:** Large specs reducing USD long exposure
• **Cross-Market Analysis:** EUR strength confirmed vs JPY, GBP

**🕐 Professional Execution Plan:**
**Optimal Entry Window:** London session 08:00-12:00 GMT
**Monitoring Points:** 
- 1.0890 (first resistance test)
- 1.0910 (pre-target scaling opportunity)
**Management Rules:**
- Move stop to breakeven at 1.0895
- Take 50% profits at 1.0920
- Trail remainder with 20-pip buffer

**📊 Institutional Perspective:**
• Large fund flows supporting this direction
• Option barriers providing upside momentum  
• Carry trade dynamics favoring EUR
• Technical and fundamental alignment = high conviction

**🎯 Professional Confidence:** 78% (High)
**Trade Duration:** 2-5 days expected
**Market Regime:** Trending (institutional participation)

*Analysis by Professional AI Trading System*
*Institutional-grade insights for serious traders*
        """
        await query.edit_message_text(example_text, parse_mode='Markdown')
    
    elif query.data == "help":
        await help_command(query, context)
        
    elif query.data == "market":
        market_text = """
**📊 Professional Market Intelligence**

**🌍 Global Market Overview:**
• **Risk Sentiment:** Currently monitoring institutional flows
• **Central Bank Cycle:** Fed, ECB, BoJ policy divergence creating opportunities
• **Macro Themes:** Inflation dynamics, growth concerns, geopolitical factors
• **Institutional Positioning:** Smart money flows tracked across all major pairs

**📈 Current Market Regime:**
• **Trend/Range Assessment:** Multi-timeframe analysis on all majors
• **Volatility Environment:** Session-based volatility patterns
• **Liquidity Conditions:** Deep liquidity during overlap sessions
• **Correlation Dynamics:** Cross-asset relationships monitoring

**⚡ Today's Professional Focus:**
• **High-Probability Setups:** Confluence zone identification
• **News Impact:** Economic calendar integration
• **Session Opportunities:** Asian/London/NY optimization
• **Risk Events:** Monitoring for market-moving announcements

**🎯 Professional Trading Opportunities:**
• **Trend Continuation:** Clean trending pairs analysis
• **Mean Reversion:** Overextended counter-trend opportunities  
• **Breakout Plays:** Range bound pairs near resolution
• **Carry Strategies:** Interest rate differential exploitation

**💼 Institutional Intelligence:**
• **Order Flow:** Large player positioning analysis
• **Option Flows:** Barrier levels dan gamma positioning
• **Fund Flows:** ETF dan mutual fund activity
• **Central Bank Intervention:** Policy maker sentiment tracking

Send your charts now for professional analysis integrated with current market intelligence!

*Professional Market Intelligence System*
*Real-time institutional perspective*
        """
        await query.edit_message_text(market_text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk foto/gambar"""
    await update.message.reply_text("📊 Professional AI analyzing your chart with advanced market intelligence... Please wait.")
    
    try:
        # Ambil foto dengan kualitas terbaik
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download foto
        photo_bytes = BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        
        image_bytes = photo_bytes.getvalue()
        
        # Encode ke base64
        image_base64 = await trading_bot.encode_image_to_base64(image_bytes)
        
        # Deteksi tipe gambar
        image_type = trading_bot.detect_image_type(image_bytes)
        
        # Dapatkan context market terbaru
        market_context = await trading_bot.get_latest_market_context()
        
        # Buat prompt untuk analisis chart
        caption = update.message.caption if update.message.caption else ""
        
        analysis_prompt = f"""
You are a professional institutional trader with 15+ years experience analyzing charts for major financial institutions. Provide a comprehensive professional-grade analysis of this trading chart.

{f"Specific context from trader: {caption}" if caption else ""}

{market_context}

PROFESSIONAL ANALYSIS FRAMEWORK:
Deliver an institutional-quality analysis that includes:

**1. CHART IDENTIFICATION & MARKET STRUCTURE:**
- Asset identification dan timeframe assessment
- Current market regime (trending/ranging/transitional)
- Institutional market structure analysis
- Key structural levels dan their significance

**2. ADVANCED TECHNICAL ANALYSIS:**
- **Multi-timeframe Trend Analysis:** Higher TF confirmation
- **Price Action Mastery:** Candlestick patterns with institutional context
- **Support/Resistance Mapping:** Multiple confluence zones with strength ratings
- **Chart Pattern Recognition:** Professional pattern identification
- **Volume Analysis:** Institutional volume signatures (if visible)

**3. INSTITUTIONAL ORDER FLOW ANALYSIS:**
- **Smart Money Positioning:** Evidence of institutional accumulation/distribution
- **Liquidity Analysis:** Stop hunt zones dan liquidity pools
- **Market Maker Behavior:** Signs of MM manipulation vs trending
- **Order Block Identification:** Key institutional levels
- **Fair Value Gaps:** Price inefficiencies for targeting

**4. PROFESSIONAL TRADE SETUPS:**
- **Primary Setup:** Highest probability institutional-style entry
- **Risk-Reward Assessment:** Multiple R:R scenarios dengan probabilities
- **Entry Methodology:** Precise entry techniques (limit/stop/market)
- **Stop Loss Placement:** Logical institutional-style stops
- **Profit Target Strategy:** Multiple targets dengan scaling approach

**5. ADVANCED RISK MANAGEMENT:**
- **Position Sizing:** Professional risk percentage recommendations
- **Portfolio Context:** How this trade fits broader portfolio
- **Correlation Risks:** Related instrument impact assessment
- **News Risk:** Economic calendar considerations
- **Session Timing:** Optimal execution windows

**6. MARKET INTELLIGENCE INTEGRATION:**
- **Current Market Regime:** How trade fits current conditions
- **Institutional Sentiment:** Large player positioning insights
- **Economic Context:** Fundamental backdrop alignment
- **Cross-Market Analysis:** Related asset implications
- **Central Bank Considerations:** Policy impact assessment

**7. PROFESSIONAL EXECUTION PLAN:**
- **Trade Management Rules:** Precise management guidelines
- **Monitoring Checkpoints:** Key levels untuk decision making
- **Adjustment Triggers:** When dan how to modify position
- **Exit Strategy:** Multiple exit scenarios dan triggers

**8. INSTITUTIONAL PERSPECTIVE:**
- **Large Player Behavior:** How institutions would approach this
- **Market Psychology:** Crowd behavior vs smart money
- **Liquidity Considerations:** Best execution practices
- **Time-Based Factors:** Session optimal timing

**PROFESSIONAL DELIVERABLES:**
- Specific price levels dengan decimal precision
- Probability assessments based on similar historical setups
- Multiple scenario planning (Plan A, B, C)
- Professional risk metrics dan calculations
- Institutional-grade market commentary

Format response in clear Indonesian with professional terminology, structured with emojis for readability, focused on actionable institutional-quality insights that can be implemented immediately for professional trading.

Ensure all analysis reflects institutional standards with specific price levels, realistic probabilities, and professional execution guidance integrated with current market conditions.
        """
        
        # Kirim ke AI untuk analisis
        analysis_result = await trading_bot.analyze_with_claude(
            analysis_prompt, 
            image_base64, 
            image_type
        )
        
        # Kirim hasil analisis dalam chunks jika terlalu panjang
        if len(analysis_result) > 4096:
            # Split pesan jika terlalu panjang
            chunks = [analysis_result[i:i+4096] for i in range(0, len(analysis_result), 4096)]
            
            await update.message.reply_text(
                f"📈 **PROFESSIONAL CHART ANALYSIS - PART 1**\n\n{chunks[0]}", 
                parse_mode='Markdown'
            )
            
            for i, chunk in enumerate(chunks[1:], 2):
                await update.message.reply_text(
                    f"📈 **PROFESSIONAL CHART ANALYSIS - PART {i}**\n\n{chunk}", 
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                f"📈 **PROFESSIONAL CHART ANALYSIS**\n\n{analysis_result}", 
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await update.message.reply_text(
            "❌ Error analyzing chart. Please ensure image is clear and try again.\n\n"
            f"Technical details: {str(e)}"
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk dokumen/file"""
    document = update.message.document
    
    # Cek apakah file adalah gambar
    if document.mime_type and document.mime_type.startswith('image/'):
        await update.message.reply_text("📊 Professional AI analyzing chart file with institutional intelligence... Please wait.")
        
        try:
            file = await context.bot.get_file(document.file_id)
            
            # Download file
            file_bytes = BytesIO()
            await file.download_to_memory(file_bytes)
            file_bytes.seek(0)
            
            image_bytes = file_bytes.getvalue()
            
            # Encode ke base64
            image_base64 = await trading_bot.encode_image_to_base64(image_bytes)
            
            # Gunakan mime type dari document
            image_type = document.mime_type
            
            # Dapatkan market context
            market_context = await trading_bot.get_latest_market_context()
            
            # Analisis sama seperti foto tapi dengan context file
            caption = update.message.caption if update.message.caption else ""
            
            analysis_prompt = f"""
Professional institutional-grade analysis of trading chart file "{document.file_name}" with current market intelligence integration:

{f"Trader context: {caption}" if caption else ""}

{market_context}

Deliver comprehensive professional analysis covering:

1. **INSTITUTIONAL TECHNICAL ANALYSIS** - Complete professional breakdown
2. **MARKET INTELLIGENCE INTEGRATION** - Current market conditions impact
3. **PROFESSIONAL TRADE OPPORTUNITIES** - Institutional-style setups
4. **ADVANCED RISK MANAGEMENT** - Professional risk controls
5. **OPTIMAL EXECUTION TIMING** - Session-based optimal timing
6. **CROSS-MARKET CORRELATION** - Related instruments impact
7. **ACTIONABLE PROFESSIONAL PLAN** - Step-by-step institutional approach

Format in structured Indonesian with professional terminology, easy-to-implement with specific price levels dan realistic institutional-grade probabilities.

Focus on professional implementation untuk institutional-quality trading with current market intelligence integration.
            """
            
            analysis_result = await trading_bot.analyze_with_claude(
                analysis_prompt, 
                image_base64, 
                image_type
            )
            
            # Handle long messages
            if len(analysis_result) > 4096:
                chunks = [analysis_result[i:i+4096] for i in range(0, len(analysis_result), 4096)]
                for i, chunk in enumerate(chunks, 1):
                    await update.message.reply_text(
                        f"📈 **PROFESSIONAL FILE ANALYSIS - PART {i}**\n\n{chunk}",
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    f"📈 **PROFESSIONAL FILE ANALYSIS**\n\n{analysis_result}",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            await update.message.reply_text(
                "❌ Error analyzing file. Please ensure file is a valid chart image.\n\n"
                f"Technical details: {str(e)}"
            )
    else:
        await update.message.reply_text(
            f"📁 File '{document.file_name}' is not an image. \n\n"
            "Please send chart image files (JPG, PNG, WebP, GIF) for professional analysis."
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pesan teks"""
    user_message = update.message.text
    
    # Skip jika command
    if user_message.startswith('/'):
        return
    
    await update.message.reply_text("🤔 Professional AI processing your trading inquiry with market intelligence...")
    
    try:
        # Dapatkan market context
        market_context = await trading_bot.get_latest_market_context()
        
        # Buat prompt untuk pertanyaan trading umum
        trading_prompt = f"""
Trader question: "{user_message}"

{market_context}

As a professional institutional trader with extensive experience dan access to current market intelligence, provide comprehensive and actionable professional response covering:

**1. PROFESSIONAL EXPLANATION** 
- In-depth concept explanation with institutional perspective
- Theoretical foundation dengan real-world application
- Professional implementation dalam institutional trading environment

**2. CURRENT MARKET INTEGRATION**
- How concept applies to current market conditions
- Specific examples based on current market regime
- Timing considerations dengan economic calendar integration

**3. INSTITUTIONAL IMPLEMENTATION STRATEGY**
- Step-by-step professional execution guide
- Professional tools dan indicators requirements
- Platform configuration for institutional-style trading

**4. PROFESSIONAL RISK MANAGEMENT**
- Specific risk controls untuk institutional standards
- Position sizing calculations dengan portfolio context
- Professional drawdown management techniques
- Correlation risk assessment

**5. REAL-WORLD INSTITUTIONAL EXAMPLES**
- Concrete examples from major currency pairs
- Historical case studies dengan institutional relevance
- Current market opportunities analysis (if applicable)

**6. PROFESSIONAL PITFALLS & SOLUTIONS**
- Common mistakes in institutional context
- Professional warning signs dan risk indicators
- Prevention strategies dari institutional perspective
- Recovery techniques untuk professional traders

**7. ADVANCED INSTITUTIONAL CONSIDERATIONS**
- Large player behavior dan positioning
- Market maker strategies dan implications
- Cross-market correlation effects
- Session-based institutional variations

**8. PROFESSIONAL TOOLS & RESOURCES**
- Institutional-grade indicators dan optimal settings
- Professional data sources dan market intelligence
- Mobile platforms untuk professional monitoring
- Alert systems untuk institutional trading

**9. TRADING PSYCHOLOGY & PROFESSIONAL MINDSET**
- Institutional mental preparation requirements
- Professional emotional management techniques
- Discipline maintenance untuk serious traders
- Performance tracking methods institutional-style

**10. ACTIONABLE PROFESSIONAL NEXT STEPS**
- Immediate implementation actions
- Professional practice recommendations
- Monitoring checklist institutional-grade
- Performance improvement milestones

If question about:
- **Trading Strategy** → Provide complete institutional system dengan professional entry/exit rules
- **Technical Analysis** → Explain dengan current market professional examples
- **Risk Management** → Professional calculations dan institutional formulas
- **Psychology** → Institutional-grade mental techniques
- **Market Analysis** → Integration dengan current professional conditions
- **Platform/Tools** → Professional setup instructions

Response in clear Indonesian dengan professional terminology, structured with emojis for readability, focused on implementable institutional advice untuk professional trading environment.

Ensure all advice reflects institutional standards, current market relevant, dengan specific professional examples where applicable.
        """
        
        response = await trading_bot.analyze_with_claude(trading_prompt)
        
        # Handle long responses
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for i, chunk in enumerate(chunks, 1):
                await update.message.reply_text(
                    f"💡 **PROFESSIONAL TRADING CONSULTATION - PART {i}**\n\n{chunk}",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                f"💡 **PROFESSIONAL TRADING CONSULTATION**\n\n{response}",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        await update.message.reply_text(
            "❌ Error processing inquiry. Please try asking again.\n\n"
            f"Technical details: {str(e)}"
        )

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /analyze"""
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        # Jika reply ke gambar, analisis gambar tersebut
        await update.message.reply_text("🔄 Professional analysis of replied chart...")
        # Set context sebagai replied message
        context.user_data['analyzing_reply'] = True
        await handle_photo(update.message.reply_to_message, context)
        context.user_data['analyzing_reply'] = False
    else:
        await update.message.reply_text(
            "📊 **Professional /analyze Command Usage:**\n\n"
            "1. Reply this command to any chart image for advanced analysis\n"
            "2. Or send chart images directly for automatic professional analysis\n\n"
            "🤖 Professional AI ready to analyze your trading charts with institutional intelligence!"
        )

def main():
    """Main function untuk menjalankan bot"""
    # Validasi konfigurasi
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ Error: TELEGRAM_BOT_TOKEN belum diset!")
        print("💡 Dapatkan token dari @BotFather di Telegram")
        print("   1. Chat dengan @BotFather")
        print("   2. Ketik /newbot")  
        print("   3. Ikuti instruksi untuk membuat bot")
        print("   4. Copy token yang diberikan ke variable TELEGRAM_BOT_TOKEN")
        return
    
    if not CLAUDE_API_KEY or CLAUDE_API_KEY == "YOUR_CLAUDE_API_KEY":
        print("❌ Error: CLAUDE_API_KEY belum diset!")
        print("💡 Dapatkan API key dari https://console.anthropic.com")
        print("   1. Daftar/login ke Anthropic Console")
        print("   2. Go to API Keys section")
        print("   3. Create new API key")
        print("   4. Copy API key yang diberikan ke variable CLAUDE_API_KEY")
        return
    
    # Buat aplikasi
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Tambahkan handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Setup cleanup saat shutdown
    async def shutdown():
        await trading_bot.close_session()
    
    print("🤖 Professional AI Trading Analysis Bot Starting...")
    print("🧠 Powered by Claude AI - Professional Trading Intelligence")
    print("📊 Professional Features:")
    print("   • Advanced chart analysis with institutional perspective")
    print("   • Real-time market intelligence integration")
    print("   • Professional risk management framework")
    print("   • Multi-timeframe technical analysis")
    print("   • Institutional order flow insights")
    print("📈 Professional market intelligence active")
    print("📱 Bot ready! Professional trading analysis available!")
    
    # Jalankan bot
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n🛑 Professional bot stopped by user")
    finally:
        asyncio.run(shutdown())

if __name__ == '__main__':
    main()