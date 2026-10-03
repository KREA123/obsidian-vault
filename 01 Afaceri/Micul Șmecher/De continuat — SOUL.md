---
tip: listă de lucru
afacere: Micul Șmecher
actualizat: 2026-10-03
---

# De continuat — SOUL (pașii următori)

> Lista curentă, rescrisă pe 2026-10-03. Oricine (om sau Claude) poate relua de aici doar din note: harta completă e în [[SOUL — Harta memoriei]], deciziile în [[Jurnal decizii]], starea în [[Micul Șmecher]]. Căile `micul-smecher/...` sunt în vault. Tot ce e marcat **[neverificat]** nu e confirmat în repo sau pe hardware. Nicio parolă, cheie sau token nu se scrie în vault.

## Regulile lui Andu (valabile pentru tot)
- Numele: **SOUL** (un cuvânt). Sistemul: **SoulOS**. **Engleza e limba implicită** a produsului; notele interne rămân în română.
- Forma finală: **MĂRGĂRITAR**, mărimea M (≈ 90 × 101 × 31,5 mm), aluminiu, 5 culori (Argint, Grafit, Albastru noapte, Jar, Șampanie). Pe față doar sticla neagră.
- **Fără Founders 00**: pe site doar listă de așteptare, nicio rezervare/plată înainte de grant și CE.
- **Fără AI inclus plătit de noi**: fiecare om își conectează propriul AI (cheia lui de Anthropic/OpenAI, conectorul din aplicația Claude, „Sign in with ChatGPT” după aprobarea OpenAI) sau folosește modul offline.
- Abonamentul **Claude Pro/Max nu poate fi folosit de un dispozitiv terț** (regula Anthropic, verificată în `docs/08-OWN-CLAUDE.md` §1) — nu construim niciodată login claude.ai în SOUL.
- Prima serie = 10–25 bucăți (test de vânzare), fără matrițe.

## A. Ce face Andu (fondatorul), în ordine
- [ ] 1. **Cumpără placa** Waveshare ESP32-S3-Touch-LCD-2.8C (varianta cu touch) de pe **Alibaba (~140 lei)** [preț de la fondator, neverificat; `prototip/COMANDA.md` dă ~190 lei Waveshare/AliExpress] + **bateria LiPo 803450** 1500 mAh, cu PCM și mufă MX1.25, de pe **eMAG** (~35 lei; nu mai mare de 8,6 × 34,5 × 50,5 mm). Lista completă: [[micul-smecher/prototip/COMANDA|COMANDA]].
- [ ] 2. **Printează P0**: cele 6 STL-uri din `micul-smecher/prototip/stl/plastic/` (PETG/PLA, 3 pereți, 20 %), la printeaza3d.ro sau capib.ro. Corp ≈ 112 × 125 × 31,6 mm după STL [de măsurat cu șublerul pe print; `docs/00-START-HERE.md` mai dă 112 × 128 × 34]. Planșe: `micul-smecher/blueprints/final/`.
- [ ] 3. **Flash firmware 1.2.0** + testul BRINGUP: `firmware/release/SOUL-2.8C-install.bin` la adresa `0x0` din https://espressif.github.io/esptool-js/ → urmezi [[micul-smecher/firmware/BRINGUP|BRINGUP.md]] (15 min) și scrii valorile măsurate în tabelul de la final (axele IMU, touch, ecran, BLE cu Claude Desktop).
- [ ] 4. **Cont pe console.anthropic.com** pentru teste: o cheie numită SOUL cu limită lunară mică (ex. $5). Cheia se pune doar pe dispozitiv / pagina telefonului, **niciodată în vault sau în git**.
- [ ] 5. **Trimite cererile**: emailul către Anthropic (formularul Contact sales) și formularul OpenAI „Sign in with ChatGPT” https://openai.com/form/sign-in-with-chatgpt-interest/ — textele gata în [[SOUL — Cereri parteneriat Anthropic și OpenAI]]. La Anthropic adaugă și cererea pentru canalul SOUL Bridge (docs/08 §7).
- [ ] 6. **Domeniu + găzduire EU + expeditor email**: cumpără domeniul pentru SOUL Cloud (`{BASE}`), hosting Fly.io în regiune EU (configul e în `micul-smecher/ai/fly.toml`), un expeditor de email tranzacțional EU cu SPF/DKIM/DMARC (docs/07 §5 „Founder actions”).
- [ ] 7. **Creează repo-ul GitHub „soul”** (`krea123/soul`) pentru copia partajată — apoi Claude rulează sincronizarea (B.5).
- [ ] 8. **Distribuie artefactele** (sunt private până le partajezi tu din claude.ai): site v2 https://claude.ai/artifact/WZtQ7JpCjpj6M3sfgJugHC · SoulOS v4 https://claude.ai/artifact/BFboeyYNYTUBrzsiB9uEfA · galeria de ochi https://claude.ai/artifact/M8CVFPvTN3FCj6fC9UbA3D · semnătura https://claude.ai/artifact/36i5S4iZkq3t48ZqJZwFt5
- [ ] 9. (opțional) Testează SOUL Bridge pe Mac/PC-ul tău cu contul tău Pro/Max (docs/08 §3.1 și §7) — singurul test pe care Claude nu-l poate face.

## B. Ce face Claude (după ce Andu deblochează)
- [ ] 1. **După placa reală:** corecturile din BRINGUP (rotație, touch, `IMU_MAP`), testul BLE Hardware Buddy cu Claude Desktop real, timpii măsurați în docs/07 (înlocuiește estimările [E]).
- [ ] 2. **SOUL Cloud (din statusul docs/07):** deploy EU după ce există domeniul; test cu **claude.ai real** (redirect-ul OAuth al claude.ai, nu clientul loopback); CIMD (neimplementat); întrebarea despre plan pe `/me/connect-claude`; Sign in with Apple / Google (doar cod pe email azi); notificarea pe telefon (`notify.py` nu există); Postgres, backup, monitorizare; capturi RO pentru fiecare pas Claude/ChatGPT; listare în Claude Connectors Directory.
- [ ] 3. **Sign in with ChatGPT:** azi doar „coming soon” pe `/pair` și `/me/signin-chatgpt`; se construiește abia după aprobarea scrisă a OpenAI (docs/07 §1.10).
- [ ] 4. **SOUL Bridge (docs/08 §7):** endpoint-ul `/bridge` în firmware + ecranul de pairing + brain `bridge`; în cloud `/v1/bridge` (opțional) și `/v1/pt/inbox`; installer semnat, iconiță în tray, pornire automată. Rămâne „experimental” până la acordul Anthropic.
- [ ] 5. **Repo separat:** după ce Andu creează `krea123/soul`, rulează `bash micul-smecher/tools/sync-soul-repo.sh` după fiecare push (vault-ul rămâne sursa).
- [ ] 6. Refă STEP-urile, varianta aluminiu și imaginile P0 (`prototip/step/`, `prototip/img/`) pe MĂRGĂRITAR — azi sunt încă HOPA rev A (vezi `prototip/README.md`); corectează cota P0 din `docs/00-START-HERE.md`.
- [ ] 7. Pachetul zip: `python3 micul-smecher/docs/_tools/build_zip.py` după schimbări mari (sub 95 MB; ultima refacere 2026-10-03, ~90 MB).
- [—] **Trailer v4: oprit de Andu** (WIP salvat în commit `cfe5104`). Valabil rămâne trailerul v3 (`trailer/`). Nu se reia fără cererea lui.

## Gata (istoric scurt)
- [x] Forma MĂRGĂRITAR + randări v9; P0 STL-uri de plastic + planșele `blueprints/final/` (2026-09-26)
- [x] Brand Package v1.0 + brand book 19 pagini; trailer v3; pagina de lansare v2
- [x] Ochii SOUL v2: semnătura, 120 de designuri, 31 de expresii, comportamente cu giroscopul (web + firmware)
- [x] SoulOS v4 (web) + firmware SoulOS 1.2.0 (compilat, testat pe PC și în simulator; neîncărcat pe placă)
- [x] SOUL Cloud (pairing, gateway, conector OAuth MCP, `/pair`, `/me`) testat end-to-end cu falsuri; SOUL Bridge prototip
- [x] Draftele de cereri către Anthropic și OpenAI
- [x] Faza 1–2 din lista veche (randări v4–v8, research, kit de prototip, competitori, software, „inovația Apple”) — vezi [[SOUL — Harta memoriei]]
