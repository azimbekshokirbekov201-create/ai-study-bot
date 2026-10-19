from app.handlers.common import send_text
from app.keyboards import choices
from app.localization import tr
from app.services.analytics import leaderboard, statistics
from app.services.subscriptions import premium_until


async def statistics_navigation(message, dest, student, session, runtime):
    lang = student.language
    if dest.startswith("leaderboard"):
        period = dest.split(":")[1] if ":" in dest else "week"
        if period not in ("day", "week", "month", "all"):
            period = "week"
        rows, mine = await leaderboard(session, period, student.id)
        text = f"🏆 {tr(period, lang)} (UTC)\n\n"
        text += (
            "\n".join(f"{row['rank']}. {row['display_name']} — {row['points']}" for row in rows)
            or "—"
        )
        text += (
            f"\n\n{'Siz / You'}: {mine['rank'] if mine else '—'} · {mine['points'] if mine else 0}"
        )
        text += (
            "\nBir savolga kuniga bir marta ball beriladi."
            if lang == "uz"
            else "\nEach question earns points once per UTC day."
        )
        return await send_text(
            message, text, choices(["day", "week", "month", "all"], lang, "leaderboard:", columns=2)
        )
    stats = await statistics(session, student.id)
    expiry = await premium_until(session, student.id)
    premium = f"Premium · {expiry:%Y-%m-%d %H:%M} UTC" if expiry else "Free"
    if dest == "profile":
        text = (
            f"👤 {student.display_name}\nID: {student.telegram_id}\n@{student.username or '—'}\n"
            f"{student.language.upper()} · CEFR {student.cefr_level}\n{student.registered_at:%Y-%m-%d}\n"
            f"🎯 {student.goals or '—'}\n💎 {premium}\n"
        )
    else:
        text = tr("statistics", lang) + "\n"
    labels = (
        ("Yakunlangan testlar", "Javoblar", "To‘g‘ri", "Xato", "Aniqlik", "Ball")
        if lang == "uz"
        else ("Completed quizzes", "Answers", "Correct", "Incorrect", "Accuracy", "Points")
    )
    text += "\n".join(
        f"{label}: {value}"
        for label, value in zip(
            labels,
            [
                stats["completed"],
                stats["answered"],
                stats["correct"],
                stats["incorrect"],
                f"{stats['accuracy']:.1f}%",
                stats["points"],
            ],
            strict=True,
        )
    )
    if stats["badges"]:
        text += "\n🏅 " + ", ".join(getattr(b, f"title_{lang}") for b in stats["badges"])
    if stats["progress"]:
        text += "\n\n" + ("Takrorlash tavsiyasi:" if lang == "uz" else "Recommended revision:")
        for p in stats["progress"][: (20 if expiry else 3)]:
            accuracy = p.correct / p.answered if p.answered else 0.0
            bar = "🟩" * round(accuracy * 5) + "⬜" * (5 - round(accuracy * 5))
            text += f"\n{tr(p.topic, lang)} {p.level}: {bar} {accuracy:.0%} ({p.answered})"
        if not expiry:
            text += "\n💎 " + (
                "Barcha mavzular tahlili Premium tarifida."
                if lang == "uz"
                else "Full topic analytics with Premium."
            )
    await send_text(message, text, choices(["goals", "statistics", "premium"], lang, ""))
