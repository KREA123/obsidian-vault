---
tip: listă de lucru
afacere: Micul Șmecher
actualizat: 2026-09-24
---

# De continuat — SOUL (lista pentru Claude)

> Dacă sesiunea s-a oprit (credite terminate), Claude reia de aici, în ordine. Fiecare pas se salvează în main imediat ce e gata.

## Regulile lui Andu (valabile pentru tot)
- Numele: **SOUL** (un cuvânt). Sistemul: **SoulOS**.
- Pe **față nimic** în afară de corp și ecran. Difuzor pe **lateral/spate**, încărcare **jos**, cu **dock / capsulă de încărcare**.
- **Fără toartă** (agățatul din husă). **Mai mare** decât v1 (Ø52), bun în mână, stă **în picioare**, portabil.
- Forme cu **caracter** (piatra ovală din prototipul SoulOS, nor, lacrimă, amuletă) — **nu** cerc simplu, **nu** piatră mată culcată, **nu** colier.
- **Premium, „șmecher”**, inovativ — dar **ieftin de făcut** (carcasă ≤ ~$10/buc. la 10k).
- SOUL merge **fără AI**, cu **Claude-ul tău** sau cu **ChatGPT-ul tău**; tastatură în SoulOS (scrii lui Claude, notițe, alarme).

> **Prima serie = 10–25 bucăți** (test de vânzare): fără matrițe; aluminiu CNC + anodizat; costuri și kit de prototip pentru această cantitate.

## Pași
- [x] 1. Randări **v4** (familia de forme, mai mari, nimic pe față, capsula) → `micul-smecher/renders/v4/` → trimise lui Andu.
- [x] 2. Research **design la maxim** → `micul-smecher/research/09-product-design-max-2026-09-24.md` + `research/design-max/render-brief.md`.
- [ ] 3. Randări ale **designului final** + dock/capsulă (din render-brief) → `micul-smecher/renders/final/`.
- [ ] 4. **Tastatura + Alarme** în prototipul SoulOS (`micul-smecher/os/index.html`), copiat în `site/os.html`; module în firmware (TextInput, TimePicker, Alarms + teste); `os/ARCHITECTURE.md`.
- [ ] 5. **Pagina de lansare**: secțiunea Design cu randările finale + capsula, secțiunea SoulOS (tastatură), republicată la https://claude.ai/artifact/BUAPPdP1W5xnCvSVcsQXoX.
- [ ] 6. **Planurile tehnice** pentru designul final (`micul-smecher/blueprints/final/`).
- [ ] 7. Note în Obsidian: [[Design produs v3 — SOUL amuleta]] → designul final, [[Micul Șmecher]] (stare), Jurnal decizii.

## Faza 2 — după ce e gata lista de mai sus (cerut de Andu, 2026-09-24)
> „Trebuie să inovăm exact cum a revoluționat Apple.” Primele prototipuri le construiește **Andu**, deci totul trebuie să fie construibil de el.
- [ ] 8. **Prețuri și costuri reale**: BOM complet pe piese cu prețuri de la furnizori (Waveshare, LCSC, Mouser, AliExpress, magazine din RO), materiale, costuri de injecție/matriță (oferte de cerut), cost ajuns în depozit, marjă, prețuri de vânzare pe ediții → `micul-smecher/research/10-costuri-bom.md` + notă în vault.
- [ ] 9. **Kit de prototip pentru Andu** (în română, pas cu pas): lista de cumpărături cu linkuri și prețuri (RON/EUR), unelte, fișiere STL pentru carcasa designului final (printabile 3D, cu toleranțe), unde printezi în România, asamblare cu desene, flash firmware, testare → `micul-smecher/prototip/`.
- [x] 10. **Competitori în profunzime**: Meta Muse Charm, dispozitivul OpenAI/Jony Ive, Friend, Rabbit, Humane, Plaud, Bee, Limitless, Fuzozo, BubblePal, Eilik, Ropet, Loona, Moflin, Tamagotchi etc. — matrice funcții/preț/vânzări, ce fac bine/prost, unde câștigăm → `micul-smecher/research/11-competitori.md`.
- [ ] 11. **Software**: SoulOS mai departe (cadrul de aplicații, cartonașe, notificări), aplicația de telefon (pairing, tastatură de pe telefon, conectare conturi AI; ex. PWA cu Web Bluetooth), serviciul AI (`micul-smecher/ai/`), conectorul pentru Claude (server MCP), aplicația pentru ChatGPT, cheia API proprie criptată; cu teste.
- [ ] 12. **Inovația „Apple”**: momentul „one more thing”, gestul-semnătură, scenariul filmului de lansare actualizat pe designul final.
