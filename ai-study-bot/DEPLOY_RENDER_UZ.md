# AI Study Bot — Render deploy qo‘llanmasi

## Xavfsizlik
- `.env` GitHub/ZIP ichiga kiritilmaydi. `.env.example` faqat namuna.
- Oldingi yuborilgan ZIP ichida haqiqiy maxfiy kalitlar bo‘lgan: BotFather tokenini bekor qilib yangisini yarating, OpenAI API kalitini almashtiring va ADMIN_API_TOKEN ni qayta yarating.
- Yangi kalitlarni faqat Render Environment bo‘limida saqlang.

## Render Blueprint
1. Ushbu loyiha fayllarini GitHub'dagi **Private** repository ildiziga yuklang.
2. Render Dashboard → New → Blueprint → repository'ni ulang.
3. Blueprint xizmatlarni ko‘rsatganda **xarajatlarni tekshiring**: `render.yaml` `starter` web va `basic-1gb` PostgreSQL rejalarini belgilaydi; bu bepul konfiguratsiya emas.
4. `BOT_TOKEN`, `OPENAI_API_KEY`, `ADMIN_IDS`, `SUPPORT_CONTACT`, `PRIVACY_CONTACT` qiymatlarini Render so‘raganida kiriting. `ADMIN_API_TOKEN` va `WEBHOOK_SECRET` Blueprint tomonidan avtomatik yaratiladi.
5. `DATABASE_URL` Blueprint orqali PostgreSQL'dan olinadi; local `localhost` URL ni Render'ga ko‘chirmang.
6. Deploy tugagach `/health/ready` holatini tekshiring va Telegram botga `/start` yuboring.
7. Render loglarini tekshiring. Haqiqiy Telegram webhook, OpenAI va Stars to‘lovlarini alohida sinang.

## Muhim
- `BOT_MODE=webhook`, `APP_ENV=production` va HTTPS URL Render Blueprint'da belgilanadi.
- `render.yaml` `preDeployCommand` yordamida migration va seed ishga tushiradi; deploydan oldin Render tanlangan rejada ushbu imkoniyat qo‘llab-quvvatlanishini tekshiring.
- Telegram Stars orqali haqiqiy to‘lovlarni qabul qilishdan oldin kontaktlar, shartlar va refund jarayonini tekshiring.
