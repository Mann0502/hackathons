"""All bot text in English, Hindi and Punjabi. `t(lang, key, **values)` picks one."""

LANGS = {"en": "English", "hi": "हिन्दी", "pa": "ਪੰਜਾਬੀ"}

TEXT = {
    "welcome": {
        "en": "🌾 Welcome to FasalKavach!\nI watch the weather for your field and tell you what to do before it hits - and whether it's worth the cost.\n\nChoose your language:",
        "hi": "🌾 फसलकवच में आपका स्वागत है!\nमैं आपके खेत का मौसम देखता हूँ और नुकसान से पहले बताता हूँ कि क्या करना है - और क्या वो खर्च के लायक है।\n\nअपनी भाषा चुनें:",
        "pa": "🌾 ਫ਼ਸਲਕਵਚ ਵਿੱਚ ਜੀ ਆਇਆਂ ਨੂੰ!\nਮੈਂ ਤੁਹਾਡੇ ਖੇਤ ਦਾ ਮੌਸਮ ਵੇਖਦਾ ਹਾਂ ਅਤੇ ਨੁਕਸਾਨ ਤੋਂ ਪਹਿਲਾਂ ਦੱਸਦਾ ਹਾਂ ਕਿ ਕੀ ਕਰਨਾ ਹੈ - ਅਤੇ ਕੀ ਇਹ ਖ਼ਰਚੇ ਦੇ ਯੋਗ ਹੈ।\n\nਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ:",
    },
    "ask_location": {
        "en": "📍 Where is your field? Tap the button to share your location, or type your village/town name.",
        "hi": "📍 आपका खेत कहाँ है? लोकेशन भेजने के लिए बटन दबाएँ, या अपने गाँव/शहर का नाम लिखें।",
        "pa": "📍 ਤੁਹਾਡਾ ਖੇਤ ਕਿੱਥੇ ਹੈ? ਲੋਕੇਸ਼ਨ ਭੇਜਣ ਲਈ ਬਟਨ ਦਬਾਓ, ਜਾਂ ਆਪਣੇ ਪਿੰਡ/ਸ਼ਹਿਰ ਦਾ ਨਾਮ ਲਿਖੋ।",
    },
    "share_location_button": {"en": "📍 Share my location", "hi": "📍 मेरी लोकेशन भेजें", "pa": "📍 ਮੇਰੀ ਲੋਕੇਸ਼ਨ ਭੇਜੋ"},
    "location_error": {
        "en": "❌ {error}\nPlease share your location or type a village/town in Punjab.",
        "hi": "❌ {error}\nकृपया लोकेशन भेजें या पंजाब के किसी गाँव/शहर का नाम लिखें।",
        "pa": "❌ {error}\nਕਿਰਪਾ ਕਰਕੇ ਲੋਕੇਸ਼ਨ ਭੇਜੋ ਜਾਂ ਪੰਜਾਬ ਦੇ ਕਿਸੇ ਪਿੰਡ/ਸ਼ਹਿਰ ਦਾ ਨਾਮ ਲਿਖੋ।",
    },
    "ask_crop": {
        "en": "Got it: {place}. Which crop is in this field?",
        "hi": "ठीक है: {place}। इस खेत में कौन सी फसल है?",
        "pa": "ਠੀਕ ਹੈ: {place}। ਇਸ ਖੇਤ ਵਿੱਚ ਕਿਹੜੀ ਫ਼ਸਲ ਹੈ?",
    },
    "crop_wheat": {"en": "🌾 Wheat", "hi": "🌾 गेहूँ", "pa": "🌾 ਕਣਕ"},
    "crop_rice": {"en": "🌾 Rice (Paddy)", "hi": "🌾 धान", "pa": "🌾 ਝੋਨਾ"},
    "ask_date_wheat": {
        "en": "📅 When did you sow the wheat? Send the date like 25-11-2026.",
        "hi": "📅 गेहूँ की बुवाई कब की? तारीख ऐसे भेजें: 25-11-2026",
        "pa": "📅 ਕਣਕ ਦੀ ਬਿਜਾਈ ਕਦੋਂ ਕੀਤੀ? ਤਾਰੀਖ਼ ਇੰਝ ਭੇਜੋ: 25-11-2026",
    },
    "ask_date_rice": {
        "en": "📅 When did you transplant the paddy? Send the date like 25-06-2026.",
        "hi": "📅 धान की रोपाई कब की? तारीख ऐसे भेजें: 25-06-2026",
        "pa": "📅 ਝੋਨੇ ਦੀ ਲੁਆਈ ਕਦੋਂ ਕੀਤੀ? ਤਾਰੀਖ਼ ਇੰਝ ਭੇਜੋ: 25-06-2026",
    },
    "date_error": {
        "en": "❌ {error}\nPlease send the date like 25-06-2026.",
        "hi": "❌ {error}\nकृपया तारीख ऐसे भेजें: 25-06-2026",
        "pa": "❌ {error}\nਕਿਰਪਾ ਕਰਕੇ ਤਾਰੀਖ਼ ਇੰਝ ਭੇਜੋ: 25-06-2026",
    },
    "ask_area": {
        "en": "📏 How many acres is this field? (e.g. 5)",
        "hi": "📏 यह खेत कितने एकड़ का है? (जैसे 5)",
        "pa": "📏 ਇਹ ਖੇਤ ਕਿੰਨੇ ਏਕੜ ਦਾ ਹੈ? (ਜਿਵੇਂ 5)",
    },
    "area_error": {
        "en": "❌ Please send a number of acres between 0.1 and 1000, e.g. 5",
        "hi": "❌ कृपया 0.1 से 1000 के बीच एकड़ की संख्या भेजें, जैसे 5",
        "pa": "❌ ਕਿਰਪਾ ਕਰਕੇ 0.1 ਤੋਂ 1000 ਵਿਚਕਾਰ ਏਕੜ ਦੀ ਗਿਣਤੀ ਭੇਜੋ, ਜਿਵੇਂ 5",
    },
    "registered": {
        "en": "✅ Field saved! I'll check the weather for it every {hours} hours and message you only when something needs your attention.\nHere is today's check:",
        "hi": "✅ खेत सेव हो गया! मैं हर {hours} घंटे में मौसम देखूँगा और ज़रूरत होने पर ही संदेश भेजूँगा।\nआज की जाँच:",
        "pa": "✅ ਖੇਤ ਸੇਵ ਹੋ ਗਿਆ! ਮੈਂ ਹਰ {hours} ਘੰਟੇ ਮੌਸਮ ਵੇਖਾਂਗਾ ਅਤੇ ਲੋੜ ਪੈਣ ‘ਤੇ ਹੀ ਸੁਨੇਹਾ ਭੇਜਾਂਗਾ।\nਅੱਜ ਦੀ ਜਾਂਚ:",
    },
    "checking": {
        "en": "⏳ Checking live weather, soil and mandi prices...",
        "hi": "⏳ मौसम, मिट्टी और मंडी भाव देख रहा हूँ...",
        "pa": "⏳ ਮੌਸਮ, ਮਿੱਟੀ ਅਤੇ ਮੰਡੀ ਦੇ ਭਾਅ ਵੇਖ ਰਿਹਾ ਹਾਂ...",
    },
    "check_failed": {
        "en": "⚠️ Could not check field {name} right now ({error}). I'll try again later.",
        "hi": "⚠️ अभी खेत {name} की जाँच नहीं हो सकी ({error})। मैं बाद में फिर कोशिश करूँगा।",
        "pa": "⚠️ ਹੁਣੇ ਖੇਤ {name} ਦੀ ਜਾਂਚ ਨਹੀਂ ਹੋ ਸਕੀ ({error})। ਮੈਂ ਬਾਅਦ ਵਿੱਚ ਫਿਰ ਕੋਸ਼ਿਸ਼ ਕਰਾਂਗਾ।",
    },
    "no_fields": {
        "en": "You have no fields yet. Send /add to register one.",
        "hi": "आपका कोई खेत नहीं है। खेत जोड़ने के लिए /add भेजें।",
        "pa": "ਤੁਹਾਡਾ ਕੋਈ ਖੇਤ ਨਹੀਂ ਹੈ। ਖੇਤ ਜੋੜਨ ਲਈ /add ਭੇਜੋ।",
    },
    "fields_header": {"en": "🗂 Your fields:", "hi": "🗂 आपके खेत:", "pa": "🗂 ਤੁਹਾਡੇ ਖੇਤ:"},
    "stopped": {
        "en": "🔕 Alerts paused. Send /resume to turn them back on.",
        "hi": "🔕 अलर्ट बंद। फिर से चालू करने के लिए /resume भेजें।",
        "pa": "🔕 ਅਲਰਟ ਬੰਦ। ਮੁੜ ਚਾਲੂ ਕਰਨ ਲਈ /resume ਭੇਜੋ।",
    },
    "resumed": {
        "en": "🔔 Alerts are on again.",
        "hi": "🔔 अलर्ट फिर से चालू हैं।",
        "pa": "🔔 ਅਲਰਟ ਮੁੜ ਚਾਲੂ ਹਨ।",
    },
    "help": {
        "en": "Commands:\n/add - register a field\n/status - check all my fields now\n/fields - list my fields\n/language - change language\n/stop - pause alerts\n/resume - turn alerts on\n\nYou can also just ask a question, e.g. \"Should I spray tomorrow?\"",
        "hi": "कमांड:\n/add - खेत जोड़ें\n/status - अभी सभी खेतों की जाँच\n/fields - मेरे खेत\n/language - भाषा बदलें\n/stop - अलर्ट बंद\n/resume - अलर्ट चालू\n\nआप सीधे सवाल भी पूछ सकते हैं, जैसे \"क्या कल स्प्रे करूँ?\"",
        "pa": "ਕਮਾਂਡਾਂ:\n/add - ਖੇਤ ਜੋੜੋ\n/status - ਹੁਣੇ ਸਾਰੇ ਖੇਤਾਂ ਦੀ ਜਾਂਚ\n/fields - ਮੇਰੇ ਖੇਤ\n/language - ਭਾਸ਼ਾ ਬਦਲੋ\n/stop - ਅਲਰਟ ਬੰਦ\n/resume - ਅਲਰਟ ਚਾਲੂ\n\nਤੁਸੀਂ ਸਿੱਧਾ ਸਵਾਲ ਵੀ ਪੁੱਛ ਸਕਦੇ ਹੋ, ਜਿਵੇਂ \"ਕੀ ਕੱਲ੍ਹ ਸਪਰੇ ਕਰਾਂ?\"",
    },
    "ask_needs_field": {
        "en": "To answer questions about your crop I first need your field. Send /add to register it.",
        "hi": "फसल के बारे में जवाब देने के लिए पहले आपका खेत चाहिए। /add भेजें।",
        "pa": "ਫ਼ਸਲ ਬਾਰੇ ਜਵਾਬ ਦੇਣ ਲਈ ਪਹਿਲਾਂ ਤੁਹਾਡਾ ਖੇਤ ਚਾਹੀਦਾ ਹੈ। /add ਭੇਜੋ।",
    },
    "agent_offline": {
        "en": "🤖 The AI assistant is not available right now. Here is your latest field check instead:",
        "hi": "🤖 AI सहायक अभी उपलब्ध नहीं है। आपके खेत की ताज़ा जाँच:",
        "pa": "🤖 AI ਸਹਾਇਕ ਹੁਣੇ ਉਪਲਬਧ ਨਹੀਂ ਹੈ। ਤੁਹਾਡੇ ਖੇਤ ਦੀ ਤਾਜ਼ਾ ਜਾਂਚ:",
    },
    # ---- field report ----
    "report_title": {
        "en": "🌾 {crop} · {place} · {area} acres",
        "hi": "🌾 {crop} · {place} · {area} एकड़",
        "pa": "🌾 {crop} · {place} · {area} ਏਕੜ",
    },
    "report_stage": {
        "en": "🌱 Stage: {stage} (day {days})",
        "hi": "🌱 अवस्था: {stage} (दिन {days})",
        "pa": "🌱 ਪੜਾਅ: {stage} (ਦਿਨ {days})",
    },
    "report_risk_header": {"en": "Next 7 days:", "hi": "अगले 7 दिन:", "pa": "ਅਗਲੇ 7 ਦਿਨ:"},
    "report_loss": {
        "en": "💰 Expected loss if you do nothing: {loss}/acre",
        "hi": "💰 कुछ न करने पर अनुमानित नुकसान: {loss}/एकड़",
        "pa": "💰 ਕੁਝ ਨਾ ਕਰਨ ‘ਤੇ ਅੰਦਾਜ਼ਨ ਨੁਕਸਾਨ: {loss}/ਏਕੜ",
    },
    "report_do": {"en": "✅ What to do:", "hi": "✅ क्या करें:", "pa": "✅ ਕੀ ਕਰਨਾ ਹੈ:"},
    "report_saves": {
        "en": "saves ~{amount}/acre",
        "hi": "~{amount}/एकड़ की बचत",
        "pa": "~{amount}/ਏਕੜ ਦੀ ਬੱਚਤ",
    },
    "report_no_action": {
        "en": "✅ No protective action needed - continue normal work.",
        "hi": "✅ कोई बचाव ज़रूरी नहीं - सामान्य काम जारी रखें।",
        "pa": "✅ ਕੋਈ ਬਚਾਅ ਜ਼ਰੂਰੀ ਨਹੀਂ - ਆਮ ਕੰਮ ਜਾਰੀ ਰੱਖੋ।",
    },
    "report_price": {
        "en": "Price used: {price}/quintal ({basis})",
        "hi": "भाव: {price}/क्विंटल ({basis})",
        "pa": "ਭਾਅ: {price}/ਕੁਇੰਟਲ ({basis})",
    },
    "report_source": {
        "en": "Forecast: {source}",
        "hi": "पूर्वानुमान: {source}",
        "pa": "ਪੂਰਵ ਅਨੁਮਾਨ: {source}",
    },
    "alert_title": {
        "en": "⚠️ ALERT: weather risk has changed for your field",
        "hi": "⚠️ अलर्ट: आपके खेत के लिए मौसम का खतरा बदला है",
        "pa": "⚠️ ਅਲਰਟ: ਤੁਹਾਡੇ ਖੇਤ ਲਈ ਮੌਸਮ ਦਾ ਖ਼ਤਰਾ ਬਦਲਿਆ ਹੈ",
    },
    "alert_change": {
        "en": "{event}: {old} → {new}",
        "hi": "{event}: {old} → {new}",
        "pa": "{event}: {old} → {new}",
    },
}

EVENTS = {
    "rain": {"en": "🌦 Rain", "hi": "🌦 बारिश", "pa": "🌦 ਮੀਂਹ"},
    "heavy_rain": {"en": "🌧 Heavy rain", "hi": "🌧 भारी बारिश", "pa": "🌧 ਭਾਰੀ ਮੀਂਹ"},
    "strong_wind": {"en": "💨 Strong wind", "hi": "💨 तेज़ हवा", "pa": "💨 ਤੇਜ਼ ਹਵਾ"},
    "heat_stress": {"en": "🔥 Heat stress", "hi": "🔥 अधिक गर्मी", "pa": "🔥 ਜ਼ਿਆਦਾ ਗਰਮੀ"},
    "frost": {"en": "❄️ Frost", "hi": "❄️ पाला", "pa": "❄️ ਕੋਰਾ"},
}

STAGES = {
    "establishment": {"en": "establishment", "hi": "जमाव", "pa": "ਜੰਮ"},
    "tillering": {"en": "tillering", "hi": "कल्ले निकलना", "pa": "ਬੂਝਾ ਮਾਰਨਾ"},
    "jointing_booting": {"en": "jointing / booting", "hi": "गाँठ / गोभ", "pa": "ਗੰਢਾਂ / ਗੋਭ"},
    "heading_flowering": {"en": "heading / flowering", "hi": "बाली / फूल", "pa": "ਸਿੱਟੇ / ਫੁੱਲ"},
    "panicle_initiation": {"en": "panicle initiation", "hi": "बाली बनना", "pa": "ਮੁੰਜਰਾਂ ਬਣਨਾ"},
    "flowering": {"en": "flowering", "hi": "फूल", "pa": "ਫੁੱਲ"},
    "grain_filling": {"en": "grain filling", "hi": "दाना भरना", "pa": "ਦਾਣਾ ਭਰਨਾ"},
    "maturity_harvest": {"en": "ready for harvest", "hi": "कटाई के लिए तैयार", "pa": "ਵਾਢੀ ਲਈ ਤਿਆਰ"},
}

ACTIONS = {
    "postpone_spray": {"en": "Postpone spraying until after the rain",
                       "hi": "बारिश के बाद तक स्प्रे टालें",
                       "pa": "ਮੀਂਹ ਤੋਂ ਬਾਅਦ ਤੱਕ ਸਪਰੇ ਰੋਕੋ"},
    "skip_irrigation": {"en": "Skip the next irrigation - rain expected",
                        "hi": "अगली सिंचाई न करें - बारिश की संभावना",
                        "pa": "ਅਗਲੀ ਸਿੰਚਾਈ ਨਾ ਕਰੋ - ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ"},
    "early_harvest": {"en": "Harvest early, before the weather hits",
                      "hi": "मौसम बिगड़ने से पहले जल्दी कटाई करें",
                      "pa": "ਮੌਸਮ ਵਿਗੜਨ ਤੋਂ ਪਹਿਲਾਂ ਜਲਦੀ ਵਾਢੀ ਕਰੋ"},
    "drain_field": {"en": "Open drainage channels to avoid waterlogging",
                    "hi": "जलभराव से बचने के लिए नालियाँ खोलें",
                    "pa": "ਪਾਣੀ ਖੜ੍ਹਨ ਤੋਂ ਬਚਣ ਲਈ ਨਾਲੀਆਂ ਖੋਲ੍ਹੋ"},
    "light_irrigation_frost": {"en": "Give a light irrigation against frost",
                               "hi": "पाले से बचाव के लिए हल्की सिंचाई करें",
                               "pa": "ਕੋਰੇ ਤੋਂ ਬਚਾਅ ਲਈ ਹਲਕੀ ਸਿੰਚਾਈ ਕਰੋ"},
    "light_irrigation_heat": {"en": "Give a light irrigation against heat stress",
                              "hi": "गर्मी से बचाव के लिए हल्की सिंचाई करें",
                              "pa": "ਗਰਮੀ ਤੋਂ ਬਚਾਅ ਲਈ ਹਲਕੀ ਸਿੰਚਾਈ ਕਰੋ"},
    "maintain_standing_water": {"en": "Keep 5 cm standing water during the heat",
                                "hi": "गर्मी में खेत में 5 सेमी पानी खड़ा रखें",
                                "pa": "ਗਰਮੀ ਦੌਰਾਨ ਖੇਤ ਵਿੱਚ 5 ਸੈਂਟੀਮੀਟਰ ਪਾਣੀ ਖੜ੍ਹਾ ਰੱਖੋ"},
}


def t(lang: str, key: str, **values) -> str:
    entry = TEXT[key]
    return entry.get(lang, entry["en"]).format(**values)


def label(table: dict, key: str, lang: str) -> str:
    entry = table.get(key)
    if not entry:
        return key.replace("_", " ")
    return entry.get(lang, entry["en"])


def rupees(amount: float) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567"""
    n = int(round(amount))
    sign, n = ("-" if n < 0 else ""), abs(n)
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{sign}₹{s}"
