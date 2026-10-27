def detect():
    try:
        candles = get_candles()
        if len(candles) < 10: return None
        highs, lows = find_swings(candles)
        if not highs or not lows: return None
        
        real_spot = get_real_spot()
        last = candles[-1]
        price = real_spot if real_spot else last["close"]
        prev = candles[-2]
        
        # Toujours prendre les 5 dernières bougies = temps réel comme FibAlgo 4006.170
        recent_lows = [l for l in lows if l[0] >= len(candles)-5]
        recent_highs = [h for h in highs if h[0] >= len(candles)-5]
        if not recent_lows or not recent_highs: return None

        swing_low = min([l[1] for l in recent_lows])
        swing_high = max([candles[h[0]]["high"] for h in recent_highs])
        diff = swing_high - swing_low
        if diff <= 0: return None

        zone_bottom_sell = swing_low + diff*0.618
        zone_top_sell = swing_low + diff*0.786
        zone_bottom_buy = swing_high - diff*0.786
        zone_top_buy = swing_high - diff*0.618

        # 1. CHECK SELL EN PREMIER comme ton image 08:23 à 4006.170 avec Sell Zone 4007
        if zone_bottom_sell <= price <= zone_top_sell:
            entry = price
            sl = zone_top_sell + 1.0
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*4
            return {"type":"SELL","signal":"ENTRY","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if price < swing_low:
            entry = (zone_top_sell+zone_bottom_sell)/2
            sl = zone_top_sell + 1.0
            tp1 = entry - (sl - entry)
            tp2 = entry - (sl - entry)*4
            return {"type":"SELL","signal":"BREAK","price":price,"zone_bottom":zone_bottom_sell,"zone_top":zone_top_sell,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}

        # 2. CHECK BUY APRES
        if zone_bottom_buy <= price <= zone_top_buy:
            entry = price
            sl = zone_bottom_buy - 1.0
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*4
            return {"type":"BUY","signal":"ENTRY","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
        if price > swing_high:
            entry = (zone_top_buy+zone_bottom_buy)/2
            sl = zone_bottom_buy - 1.0
            tp1 = entry + (entry - sl)
            tp2 = entry + (entry - sl)*4
            return {"type":"BUY","signal":"BREAK","price":price,"zone_bottom":zone_bottom_buy,"zone_top":zone_top_buy,"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}
                
    except: return None
    return None
