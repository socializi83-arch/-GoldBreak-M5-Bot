@app.route("/debug")
def debug():
    try:
        import bot
        candles = []
        if hasattr(bot, 'get_candles'):
            candles = bot.get_candles()
        elif hasattr(bot, 'get_candles_binance'):
            candles = bot.get_candles_binance()
        if not candles and hasattr(bot, 'get_candles_yf'):
            candles = bot.get_candles_yf()
        if not candles:
            return "DEBUG: vide"
        last = candles[-1]
        real = bot.get_real_spot() if hasattr(bot, 'get_real_spot') else None
        return f"DEBUG: candles={len(candles)} last={last['close']:.2f} real_spot={real:.2f} highs={len(bot.find_swings(candles)[0])} lows={len(bot.find_swings(candles)[1])}"
    except Exception as e:
        import traceback
        return f"DEBUG ERREUR: {e}<br>{traceback.format_exc()}", 500
