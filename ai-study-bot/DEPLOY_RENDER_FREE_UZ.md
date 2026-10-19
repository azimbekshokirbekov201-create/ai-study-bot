# AI Study Bot — Render bepul sinov (production emas)

## O'zgarishlar
- Web va PostgreSQL: `free`.
- `preDeployCommand` olib tashlandi. Migratsiya va seed start skriptida ishlaydi.
- Repository ichida loyiha `ai-study-bot/` papkasida: Docker context va Dockerfile yo'llari moslangan.

## Render'da
1. New → Blueprint → `azimbekshokirbekov201-create/ai-study-bot`.
2. Branch: `main`. Blueprint Path: `ai-study-bot/render.yaml`.
3. Narxlarni tekshiring: web Free va database Free. Pullik bo'lsa tasdiqlamang.
4. `BOT_TOKEN`, `ADMIN_IDS`, `OPENAI_API_KEY` (AI uchun), `SUPPORT_CONTACT`, `PRIVACY_CONTACT` ni Render'da maxfiy env qiymatlari sifatida kiriting.
5. `DATABASE_URL` Render PostgreSQL'dan olinadi. `ADMIN_API_TOKEN` va `WEBHOOK_SECRET` avtomatik yaratiladi.
6. Deploy logida migrations → seed → web server ketma-ketligini tekshiring. `/health/ready` va Telegram `/start` ni sinang.

## Cheklovlar
- Free web uxlab qoladi, Telegram webhook ishlashi kechikishi mumkin.
- Free PostgreSQL vaqtinchalik, ma'lumotlar uchun zaxira oling.
- Stars to'lovlarini haqiqiy foydalanuvchilar bilan sinamang.
- OpenAI API alohida pullik bo'lishi mumkin.
- Kartani so'rasa, to'lovni tasdiqlamasdan tekshiring.
- Oldin ulashilgan tokenlarni yangilang. `.env` faylini GitHub'ga yuklamang.
