---
tip: sistem
status: în lucru
actualizat: 2026-09-23
---
# Planul JARVIS

**Obiectiv:** un AI care conduce afacerile lui Andu — campanii, magazine, decizii — și devine tot mai bun, mai deștept decât Andu. Nu trebuie să-i copieze stilul, trebuie să aibă rezultate.

## Arhitectura
| Piesă | Ce e | Stare |
|---|---|---|
| Creier | Claude (Cowork), cel mai bun model disponibil; motorul se schimbă când apare unul mai bun | ✅ |
| Memorie de cunoaștere | acest vault Obsidian (`P:\OBSIDIAN\JARVIS`) | ✅ creat 2026-09-23 |
| Memorie de cifre | Supabase/Postgres — istoric campanii, comenzi, jurnalul agenților | ⏳ |
| Mâini — reclame | Windsor.ai (citire + scriere Meta/Google/TikTok) | ✅ |
| Mâini — magazin | Shopify Admin API prin n8n / conector propriu | ⏳ |
| Automatizări 24/7 | n8n cloud (cont existent, nefolosit încă) | ⏳ |
| Interfață | aplicația Claude (voce, notificări); apoi bot Telegram prin n8n | 🟡 |

## Etape
1. **Acum** — vault-ul: structură, jurnal de experimente, tot ce se știe despre afaceri. ✅
2. **Luna 1** — raportul zilnic MundiShop scris automat în `05 Rapoarte`; fiecare schimbare devine experiment cu verdict.
3. **Luna 1–2** — n8n + Supabase: cifrele zilnice se strâng singure; n8n ca server MCP (unelte noi pentru Claude).
4. **Luna 2** — agent „media buyer” cu reguli de autonomie clare ([[JARVIS#Niveluri de autonomie]]).
5. **Luna 2–3** — conector Shopify: produse, prețuri, pachete, reduceri.
6. **Luna 3+** — playbook „lansează un magazin nou”, testat pe [[PRIVATE PROPERTY]].
7. **Paralel** — model local (Ollama) doar pentru munca de rutină, ca să scadă creditele; deciziile grele rămân pe cel mai bun model.

## Principii
- Memoria și experimentele sunt ale lui Andu; motorul e interschimbabil.
- Un AI care îți dă mereu dreptate nu e mai deștept decât tine.

## Metodă din cercetare
[[MundiShop_Research_2026-09-23/26_Claude_Obsidian|Claude + Obsidian]] · [[MundiShop_Research_2026-09-23/24_Cursuri_resurse|curriculum]] · harta: [[Hartă cunoaștere MundiShop]]
