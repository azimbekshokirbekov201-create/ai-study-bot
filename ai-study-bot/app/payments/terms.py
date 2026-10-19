def payment_terms(settings, language):
    if language == "uz":
        return (
            f"Shartlar · {settings.terms_version}\n\n"
            f"Premium: {settings.premium_stars} Stars / {settings.premium_days} kun. "
            "Bir martalik xarid, avtomatik uzaytirilmaydi. "
            f"AI limiti: {settings.ai_premium_daily_requests} so‘rov/kun (UTC); matn/audio budjetlari ham qo‘llanadi. "
            "Ovoz transkripsiyasi va audio yaratish ham so‘rov hisoblanadi. "
            "AI baholari taxminiy, rasmiy imtihon natijasi emas. Original mashqlar IELTS yoki College Board tomonidan tasdiqlanmagan.\n\n"
            f"To‘lov yoki qaytarish so‘rovi: /paysupport · {settings.support_contact}. "
            "Operator so‘rovlarni amaldagi qonun va xarid holatiga ko‘ra ko‘rib chiqadi. "
            "Tasdiqlangan qaytarish tegishli obuna muddatini bekor qiladi. "
            "Telegram yordami ushbu xarid bo‘yicha operator o‘rniga muammoni hal qila olmaydi.\n"
            f"Maxfiylik: /privacy · {settings.privacy_contact}.\n\n"
            "Xariddan oldin shartlarni o‘qib, roziligingizni tasdiqlang."
        )
    return (
        f"Terms · {settings.terms_version}\n\n"
        f"Premium: {settings.premium_stars} Stars / {settings.premium_days} days. "
        "One-time purchase; no automatic renewal. "
        f"AI limit: {settings.ai_premium_daily_requests} requests/day (UTC); content budgets also apply. "
        "Transcription and audio generation also count as requests. "
        "AI scores are estimates, never official exam results. Original practice is not endorsed by IELTS or College Board.\n\n"
        f"Payment issues or refund requests: /paysupport · {settings.support_contact}. "
        "The operator reviews requests under applicable law and the purchase circumstances. "
        "A verified refund revokes its associated subscription interval. "
        "Telegram support cannot resolve this purchase on the operator's behalf.\n"
        f"Privacy: /privacy · {settings.privacy_contact}.\n\n"
        "Confirm that you have read and agree to these terms before purchasing."
    )
