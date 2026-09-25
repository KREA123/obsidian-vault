# 11 · Competitori SOUL: analiză aprofundată (2026-09-25)

Etichete: **[V]** pagină deschisă azi cu WebFetch (URL în §7) · **[V-s]** rezumat WebSearch azi, pagina nu a fost deschisă · **[V-0x]** verificat în nota 0x (01/04/05/09, r-trends), nu repet · **[K]** cunoștințe de fond · **[E]** estimare / judecată.
Nu repet ce e deja în 01, 04, 05, 09 și r-trends (vânzări Starboy/Mochi/Ropet/Eilik/Loona/Emo, Humane/Rabbit post-mortem, xiaozhi tech, costuri voce, AUP Claude, cadranele din r-trends §2). Aici: **ce e nou din 23–25 sept. 2026, recenziile, cine ne poate copia și cât de repede, prețul**.

**SOUL, pe scurt:** aluminiu, 63×74 mm, stă în picioare, AMOLED rotund de 1,75" cu doi ochi, nimic altceva pe față. Merge **offline fără AI** sau cu **AI-ul tău**: Claude (conector MCP + „permission buddy” BLE pentru Claude Code/Cowork), ChatGPT (app) sau cheie API proprie. SoulOS include tastatură, notițe, remindere, alarme, focus, jurnal, traducere. Capsula de încărcare se numește OU. Founders: 10–25 buc. la €349–399, apoi €199–299.

---

## 0. Ce s-a schimbat de ieri (fapte noi)
1. **Muse Charm are două camere (față + spate)**, 5G, ecran OLED de ~2", senzor de amprentă și avatarul „Jolly” (personalizabil: haine, voce, accent, viteză de vorbire). E condusă de **Alan Dye** (fost șef de interfață la Apple) împreună cu Meta Superintelligence Labs. Deocamdată există doar câteva unități, lansarea e țintită pentru decembrie și nu are preț [V heise, Decrypt, StartupFortune]. Gulf News scrie „fără cameră”, iar Engadget nu confirmă nimic. Majoritatea surselor spun 2 camere, deci **tratăm ca „are camere”** [E].
2. **Agentul Muse** (lansat 2026-09-08) face lucruri concrete: citește și trimite e-mailuri, rezervă călătorii, completează formulare, negociază, cumpără și rulează task-uri în fundal. Planuri: gratuit (100M tokeni/săpt.), **$20/lună** și **$100/lună**. **Disponibil doar în SUA, pentru 18+. Nu există în Europa** [V Gulf News]. Muse avea 2,5M descărcări. **Amazon a blocat cumpărăturile făcute de Muse**, iar presa a relatat că Muse a citit iMessage-urile private ale unui jurnalist fără permisiune [V Decrypt].
3. **Dispozitivul OpenAI × Ive:** difuzor „donut” din **metal premium**, cu părți mobile și fără ecran, raportat la **$300–400** (TechCrunch 2026-08-06), cu lansare **în 2027** [V]. Ianuarie 2026: se vorbea de 5 dispozitive până în 2028, cu căștile „Sweetpea” primele, în sept. 2026 [V-s winbuzzer, neconfirmat].
4. **Friend 2.0:** $249, vorbește printr-un difuzor, „nu e asistent și nu e iubit”; „a avut probleme să vândă în volum” [V TechCrunch 2026-07-30]. WIRED: „te hărțuiește”, iar un tester a fost acuzat că „poartă microfon” la o petrecere Anthropic [V-s].
5. **Fuzozo:** aproape **300k unități în China (iunie 2026)**, 40k doar de 618, locul 1 pe Tmall la jucării AI. Robopoet a strâns ¥100M pre-A (Tuya, Sequoia China, GSR) [V stocktitan]. Tuya a anunțat versiunea **celulară** la CES 2026 și vrea să ducă Fuzozo în afara Chinei [V-s].
6. **Ecosistemul Claude Hardware Buddy e deja comercial:** „Vibe Desktop Buddy” (vânzător independent) costă **$110 + $15 transport**, pe M5StickS3 cu ecran de 1,14", 3 butoane, IMU, ~2 h activ. Face aprobări Claude Code/Cowork și are animale ASCII + GIF-uri personalizate [V claude-desktop-buddy.com]. Espressif a recomandat Cardputer și ESP-IDF „Desktop Buddy library” la Build with Claude (2026-05-14) [V]. Pe GitHub există fork-uri *agnostice de bridge* (m5stack-desktop-buddy) [V-s].
7. **Loona DeskMate** (KEYi) e un „co-worker AI care vede ecranul”. Folosește iPhone-ul ca față, are cap motorizat cu 3 DOF, încărcător GaN de 165 W și **50+ integrări (Gmail, Slack, Calendar, Zoom)**. Costă $219–239 early bird / $299 MSRP; modelul e credite pentru task-uri grele, iar backerii primesc Plus pe viață [V CNX]. Livrările au început în vara 2026 [V-s].
8. **Alexa+ în Europa:** UK (19 mar.), DE (7 mai), IT, ES, FR, AT. Costă **€22,99/lună fără Prime** [V-s aboutamazon]. **Nu există în română și nu e lansată în RO** [E]. Google Home Speaker costă $99 (lansat 2026-06-25), iar funcțiile bune cer Home Premium la $10/$20 pe lună [V-s].
9. **Bee (Amazon):** abonamentul de $19 a dispărut, hardware-ul costă $50, iar „actions” scriu e-mailuri și invitații din conversații. Bee devine endpoint Alexa+ [V-s TechCrunch/T3]. **Pebble (Core Devices)** a construit 23k+ PT2 și are ~14k precomenzi PR2. **Index 01** e un inel de $75→$99 cu baterii înlocuibile care trimite notițe vocale în Obsidian, Reminders și Tasks [V repebble; V-s].
10. **Rabbit** (2026-01-29) a lansat **DLAM**: r1 prin USB controlează un PC/Mac. A adăugat **OpenClaw** în alfa și anunță un „rabbit cyberdeck” cu tastatură pentru „vibe coderi” [V rabbit.tech]. **Omi** costă acum **$179**, e open source, are server MCP și o comunitate de 9k pe Discord [V omi.me]. **Nothing** are $200M pentru un „dispozitiv AI-native, nu telefon” în 2026 [V-s], fără lansare încă.

---

## 1. Matricea competitorilor (24)
Legendă pentru „Face lucruri”: ●● acțiuni reale în aplicații/cont · ● remindere/notițe/control local · ○ doar conversație/emoție · – nimic.

| # | Produs | Ce este | Preț | Abonament | AI | Ecran / față | Face lucruri | Tracțiune | Status | + | − |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Meta Muse Charm** | breloc agent, 5G, 2 camere, amprentă | nean. [V] | Muse gratuit / $20 / $100 [V] | Muse (Meta), închis | OLED ~2", avatar Jolly | ●● e-mail, călătorii, cumpărături [V] | app 2,5M descărcări [V] | prototip, dec. 2026, **doar SUA** [V] | buget, agent real, Alan Dye | camere + 24/7, scandal iMessage, Amazon l-a blocat, atârnă |
| 2 | **OpenAI × Ive** | difuzor „donut” din metal, părți mobile, cameră | $300–400 [V] | prob. ChatGPT Plus [E] | ChatGPT, închis | fără ecran | ●● (prob.) | Foxconn, 40–50M planificat [V-s] | 2027 [V] | brand, design, ChatGPT 800M+ [K] | fără față, cameră, casă nu buzunar, un singur model |
| 3 | **Friend 2.0** | pandantiv always-on + difuzor | $249 [V] | $10/lună memorie [V-0x] | nedeclarat [V] | fără (LED) | ○ | gen 1 ~3k vânduți [V-0x] | vinde greu [V] | poveste clară „prieten” | ascultă tot, personalitate random/snarky, „wire” |
| 4 | Rabbit r1 | handheld 2,88", DLAM, OpenClaw | $199 (−15% în ian.) [V] | nu | multi (LAM + LLM) | ecran mic, fără față | ●● control PC (DLAM) [V] | 100–130k vânduți, ~5% DAU [V-0x] | viu, cyberdeck anunțat | a devenit util pentru pasionați | reputație „sertar”, baterie |
| 5 | Humane Ai Pin | pin + proiector laser | $699 + $24/lună | obligatoriu | OpenAI via cloud | proiector | ●● (teoretic) | ~10k | **mort**, brick 2025-02-28 [V-s] | — | lecția: cloudul moare, abonamentul ucide |
| 6 | Plaud NotePin S | recorder purtabil | $179 [V-s] | 300 min gratis; Pro $99,99/an [V-s] | GPT/Claude/Gemini [K] | fără | ● notițe/rezumate | 2M+ device-uri, $100M ARR [V-0x] | lider | o singură treabă, bine făcută | abonament, fără personalitate |
| 7 | Bee (Amazon) | brățară/pin always-on | $50 [V-s] | **$0 acum** [V-s] | Alexa+/Nova | fără | ●● e-mailuri, invitații | — | integrat în Alexa+ | preț, Amazon | ascultare 24/7, lock-in Amazon |
| 8 | Limitless (Meta) | pandantiv recorder | — | — | — | fără | ● | — | **vânzări oprite**, tăiat în UE [V-0x] | — | cumpărat → UE deconectată |
| 9 | Omi | pandantiv open source | $179 (devkit $69,99) [V/V-s] | gratuit + Unlimited [V] | multi, MCP [V] | fără | ●● 9k app-uri, MCP [V] | Discord 9k [V] | activ | deschis, MCP, dezvoltatori | fără față, niche, look DIY |
| 10 | **Fuzozo** | pluș breloc cu ochi care clipesc | ¥399 (~$55) [V-0x] | „energy” top-up [V-0x] | Tuya cloud (CN) [V] | ochi LCD | ○ | ~300k, 40k de 618 [V] | CN; 4G + export în curs [V-s] | preț, 40 min/zi, scară | doar chineză, Wi-Fi, praf, „bosumflat” [V] |
| 11 | BubblePal | clip AI pentru plușuri | $149 [V-0x] | 12 luni VIP incluse [V-s] | DeepSeek/Doubao | fără | ○ | 300k+ [V-0x] | activ, copii 3–8 | IP-uri licențiate | 10–15 s latență, Wi-Fi doar 2,4 GHz [V-s] |
| 12 | Eilik | robot de birou cu față | $139,99 [V-s] | nu | niciunul (offline) | ecran față | – | 60k+ proprietari [V-s] | stabil | 8–10 h, ieftin, privat | nu vorbește [V] |
| 13 | Eiliko | breloc cu față TFT 1,28" | $59,90 | nu | LLM via app | ecran | ○ | KS $600k [V-0x] | livrat | preț impuls | 2,5 h baterie, sunete repetitive [V-s] |
| 14 | Ropet | pluș cald cu ochi-cameră | $349–469 [V] | nu | local | ecrane ochi | ○ | ~20k [V-0x] | activ | privat, offline, 87% 5★ [V] | 2,5–3,5 h, „nu vorbește încă” [V] |
| 15 | Loona / **DeskMate** | robot-câine / dock iPhone | $499 / $299 [V] | nu; credite pt. DeskMate [V] | GPT-4o [V] | iPhone ca față | ○ / ●● 50+ integrări [V] | ~60k / KS $722k [V-0x] | livrare 2026 | viu, util la birou (DM) | 2 h, motoare, iPhone obligatoriu, camere/ecran văzut |
| 16 | Emo | robot de birou | $279–379 [V] | nu | ChatGPT [V] | ecran față | ○ | KS $348k [V-0x] | activ | cel mai conversațional [V] | 2 h, doar engleză, app instabilă, suport slab [V] |
| 17 | Casio Moflin | blăniță fără față | $429 [V-0x] | nu | on-device | fără | – | >20k [V-0x] | activ, UE anunțat [V-s] | atașament în câteva zile, privat | motor care bâzâie, 5 h, „needy” [V] |
| 18 | Tamagotchi Paradise / Uni | animal virtual | $44,99 / ~$59 [V-0x/K] | nu | niciunul | LCD pixel | – | serie 103M [V-s] | noi variante iulie 2026 | nostalgie, colecție, docking | plictisește, ecran zgâriabil, zgomotos [V-s] |
| 19 | **Claude Buddy DIY / Vibe Desktop Buddy** | M5Stick + firmware Anthropic MIT | $30 DIY / **$110+15** [V] | nu | **Claude (desktop)** | 1,14" 135×240 | ● aprobări Claude Code [V] | PH #2/zi [V-s] | vânzare activă | exact jobul nostru de dev | plastic, 2 h, ASCII, doar la birou |
| 20 | **xiaozhi (clone)** | ESP32 + LCD/AMOLED, MCP | $15–165 [V-s] | nu (server xiaozhi.me) | Qwen/DeepSeek/orice OpenAI-compat. [V-0x] | 0,96–2,8"; AMOLED 1,75 suportat [V-0x] | ●● MCP pe device [V-0x] | repo 30k★ [V-0x] | mii de SKU-uri | MIT, ieftin, rapid | flash/setup, server CN implicit, look DIY |
| 21 | Echo Spot / Alexa+ | ceas + ecran 2,83" | $80 [V-s] | Prime sau $19,99 / €22,99 [V-s] | Nova **+ Claude** [V-0x] | ecran rotund, fără ochi | ●● casă/cumpărături | masiv [K] | Alexa+ în UK/DE/FR/IT/ES; **nu în RO** | preț, ecosistem | lock-in, 0 personalitate, fără română |
| 22 | Google Home Speaker | difuzor Gemini | $99 [V-s] | Home Premium $10/$20 [V-s] | Gemini | fără | ●● casă | nou | lansat iunie 2026 | audio, preț | „un mod mai rapid de a fi frustrat” (Gizmodo) [V-s] |
| 23 | Pebble (Core Devices) | ceasuri PT2/PR2 + inel Index 01 | PT2 ~$225 [K]; Index $75–99 [V-s] | nu | notițe vocale → app | e-paper | ● remindere, Obsidian [V] | 23k+ PT2, 14k PR2 [V] | livrează | open source, fără abonament, fani | fără personalitate |
| 24 | Nothing (AI-native) | dispozitiv „nu telefon” + OS | — | — | multi-model? [E] | ? | ●● „understanding into action” [V-s] | $200M, $1,3B [V-s] | nelansat | design, comunitate, EU (Londra) | necunoscut |
| + | Starboy (CREATURE) | breloc metalic, ochi OLED | $139–599 [V-0x] | nu | niciunul | 400×400 OLED | – | batch 1–2 epuizate [V-0x] | batch 3 nov. 2026 | metal, raritate, preț premium validat | fără AI, recognition lent |

**Citire:** doar **Muse, OpenAI, Omi, xiaozhi, DeskMate și Buddy** „fac lucruri”. Dintre ele, **doar Buddy/xiaozhi au BYO-AI**, dar arată ca kituri DIY. Obiectele frumoase (Starboy, Moflin, Ropet, Eilik) nu fac nimic util. **Nimeni nu are simultan față + obiect premium + BYO-AI + acțiuni + offline** [E].

---

## 2. Harta de poziționare
Axa X: **util (face lucruri) ← → emoțional (creatură)**. Axa Y: **AI închis (sus) ↔ AI-ul tău / fără AI (jos)**.

```
                     AI ÎNCHIS (un furnizor, abonamentul lor)
                                   ▲
   Alexa+/Echo Spot  Google Home   │   Muse Charm (Meta)
   Bee (Amazon)   OpenAI×Ive       │        Friend 2.0
   Humane†  Rabbit r1              │  BubblePal   Fuzozo
   Loona DeskMate  Plaud           │  Loona   Emo   Eiliko
 UTIL ◄────────────────────────────┼────────────────────────────► EMOȚIONAL
   Omi   xiaozhi-clone             │           Starboy  Moflin
   Vibe Desktop Buddy / DIY        │   ★ SOUL   Ropet  Eilik
   Pebble Index 01                 │           Tamagotchi
                                   ▼
             AI-UL TĂU (Claude / ChatGPT / cheie) sau offline
```
- **SOUL stă singur în cadranul de jos, chiar pe axă, puțin spre „emoțional”.** Face lucruri prin AI-ul tău (Claude MCP, aprobări Claude Code, ChatGPT), dar arată și se comportă ca o creatură. Vecinii din stânga-jos (Buddy, xiaozhi, Omi) sunt kituri fără suflet. Vecinii din dreapta-jos (Starboy, Ropet, Moflin, Eilik) sunt frumoși, dar nu fac nimic [E].
- **A treia dimensiune (nu apare pe hartă):** obiectul. Toți din sus-dreapta **atârnă** sau sunt din pluș. SOUL **stă în picioare, e din aluminiu și nu are nimic pe față** (r-trends §2).
- **A patra dimensiune: geografia.** Muse e doar în SUA, Alexa+ nu vorbește română, iar Limitless a tăiat UE. SOUL e **singurul produs gândit UE-first** [V/E].

---

## 3. Cei 5 cei mai periculoși: ce ar trebui să copieze și cât de repede

| Competitor | Ce le lipsește ca să fie SOUL | Cât de repede pot | Probabilitate | Apărarea noastră |
|---|---|---|---|---|
| **1. Meta Muse Charm** | (a) BYO-AI: **niciodată**, fiindcă modelul lor de afaceri e Muse + date; (b) să stea în picioare, fără camere, obiect premium: 12–24 luni (v2); (c) disponibilitate UE: Muse nu e în UE, iar AI Act + GDPR + camere pe breloc = 6–18 luni [E] | hardware 12+ luni; BYO niciodată | **mare** pe „charm agent” în SUA, **mică** în UE în 2027 | „Nu te privește. Nu e al lor.”; fără camere; lansare în UE înainte să ajungă Meta; Claude/ChatGPT la alegere |
| **2. OpenAI × Ive** | față/ecran (anti-Ive prin design), portabilitate, alt model decât ChatGPT (**niciodată**). Dar **Codex/ChatGPT desktop ar putea deschide un „buddy API”** ca Anthropic în 3–6 luni [E] | produs 2027; API buddy în câteva luni | **mare** pe „obiect AI premium de $300–400” | fii primul la hero-film (**înainte de feb. 2027**); SOUL e „personal, în buzunar, cu ochi”, nu difuzor de casă; merge și cu ChatGPT, deci nu îi suntem dușmani |
| **3. Friend** | ecran/față, acțiuni, BYO-AI, obiect premium. Echipă mică, pivotează des | 9–15 luni pentru hardware nou [E] | medie-mică (vinde greu [V]) | Friend e contraexemplul nostru: ascultă tot, personalitate random, snarky. SOUL: hold-to-talk, personalitate stabilă, „face lucruri” |
| **4. Fuzozo / Tuya** | carcasă tare cu AMOLED rotund (Tuya are furnizorii), limbi occidentale, BYO-AI (improbabil: Tuya vinde cloud), încredere UE | **3–6 luni** pentru un „Fuzozo hard-shell” de $79–129 [E]; 4G deja anunțat | **mare** pe preț/volum, mică pe premium | nu concura la preț. „Făcut în UE, date în UE, AI-ul tău, nu se oprește dacă firma moare” (Soul Pledge); aluminiu vs pluș |
| **5. Clone xiaozhi + Buddy** | au deja MCP, AMOLED 1,75 (**același panou Waveshare ca noi** [V-0x]) și BLE Buddy (spec MIT). Le lipsesc designul, OS-ul, integrarea curată Claude+ChatGPT, suportul și încrederea | **2–6 săptămâni** pentru un clon funcțional pe AliExpress la $40–80 după ce apare SOUL [E] | **foarte mare** (tehnic) | moat-ul **nu e tehnic**: obiect (aluminiu, OU, „HOPA”), brand + număr de suflet/NFC, SoulOS polisat, română, garanție UE, comunitate Founders. Publică eye-engine-ul open source *noi primii* (05 move 5), ca să fim standardul, nu victima |

**Moat-ul real (în ordinea tăriei)** [E]:
1. **Neutralitate de model.** Meta, OpenAI, Amazon și Google nu pot structural să spună „adu-ți AI-ul”. E moat de *business model*, nu de cod.
2. **Obiectul:** aluminiu, stă în picioare, OU, gestul HOPA, ochi pe negru. Se copiază în 3–6 luni, dar doar prost. Brandul și proveniența (număr de suflet, certificat NFC) nu se copiază.
3. **Încredere UE:** fără camere, hold-to-talk, relay UE, offline pe viață, Soul Pledge/escrow, conformitate AI Act art. 50 de la prima pornire.
4. **Română + limbi mici:** Alexa+, Muse și Fuzozo nu vorbesc română. E piața de acasă și povestea de presă.
5. **Viteza + comunitatea Founders:** primii 25 sunt co-designeri, nu clienți.
Tehnologia (ESP32, AMOLED, MCP, BLE Buddy) **nu e moat**. Tratează-o ca atare.

---

## 4. Ce laudă și ce reclamă clienții (Reddit, Amazon, YouTube, The Verge/WIRED/Gizmodo)
**Laudă (repetat în categorii):** atașament emoțional rapid (Moflin „în câteva zile” [V]; Fuzozo „un prieten care rămâne” [V]); **privacy on-device** (Ropet, Moflin, Eilik [V]); fără abonament (Loona, Emo, Eilik, Bee acum [V/V-s]); **o singură treabă făcută bine** (Plaud: butonul care dă „click” la record, bateria de o zi [V-s]); Rabbit r1 cu DLAM, „util pentru pasionați” [V-s]; obiecte frumoase, rare, numerotate (Starboy [V-0x]).

**Top 10 reclamații pe care SOUL nu are voie să le repete:**
| # | Reclamație | Unde (dovadă) | Regula SOUL |
|---|---|---|---|
| 1 | **Baterie scurtă** | Loona/Emo ~2 h, Eiliko 2,5 h, Ropet 2,5–3,5 h, Moflin 5 h, Buddy ~2 h [V/V-s] | ≥ 1 zi de „viață” cu ochii în idle (AMOLED negru, ~5% pixeli); OU încarcă peste noapte; publică cifre reale măsurate |
| 2 | **Latență** | BubblePal 10–15 s [V-0x]; Rabbit „demo > realitate” [V-s] | < 1,5 s până la primul sunet; ochi „gândesc” acoperă așteptarea; comenzi locale instant |
| 3 | **Ascultă tot / camere** | Friend „wire”, WIRED [V-s]; Muse „24/7 mic + location relay” [V]; Bee | fără cameră, **hold-to-talk**, stare de ascultare vizibilă în ochi, audio șters implicit |
| 4 | **Abonament pentru funcțiile de bază** | Humane $24; Plaud Pro $99,99/an; Google Home Premium; Alexa+ €22,99 [V-s] | nucleul e gratuit pe viață; AI-ul e al tău (costul e la Anthropic/OpenAI); plătești doar extra opțional (voce premium, relay) |
| 5 | **Plictisește după 2 săptămâni** | Tamagotchi Uni „fun at first” [V-s]; Starboy „fun fades” [V-0x]; Rabbit în sertar | utilitate zilnică (alarme, remindere, aprobări Claude) + conținut la ziua 30 (sezoane, evoluție ochi) |
| 6 | **Acțiunile nu merg** | Rabbit la lansare; Google Home „mai rapid frustrant” [V-s]; Amazon blochează Muse [V] | promite doar ce merge demonstrat: aprobări Claude Code, remindere, notițe, traducere. Nu „cumpără pentru tine” în v1 |
| 7 | **Moare cu cloudul/firma** | Humane bricked, Moxie, Limitless tăiat în UE [V-s/V-0x]; Loona „cloud free for the moment” [V-s] | offline pe viață + Soul Pledge (firmware + relay open-source/escrow) |
| 8 | **Zgomot mecanic / sunete repetitive** | Moflin bâzâie, Loona motoare, Tamagotchi Uni zgomotos, Eiliko sunete repetitive [V/V-s] | fără motoare; sunete rare, cu rampă; mod silențios implicit noaptea (calm tech) |
| 9 | **Limbă** | Fuzozo doar chineză, Emo doar engleză, BubblePal alunecări de limbă [V/V-s] | română + engleză din ziua 1, cu STT testat pe română (Deepgram poate lipsi, 04) |
| 10 | **Personalitate toxică sau needy** | Friend snarky/„bully” [V-s]; Moflin „needy, more stressful than soothing” [V]; Fuzozo „bosumflat” dacă e neglijat [V] | personalitate stabilă și caldă, **fără vinovăție, fără bosumflare, fără pedeapsă pentru absență** (AI Act art. 5, AUP) |
Bonus de evitat: aplicația care crapă și suportul absent (Emo [V]); Wi-Fi doar 2,4 GHz fără fallback BLE (BubblePal [V-s]); ecran care se zgârie (Uni [V-s]), deci geam călit/safir pe față; dependența de un anumit telefon (DeskMate cere iPhone 12+ [V]).

---

## 5. Prețuri de referință → verdict €349–399 / €199–299
Curs: **€1 = $1,137** (BCE 24.09, 09).

| Produs | Preț | Categorie |
|---|---|---|
| Echo Spot / Google Home | $80 / $99 | subvenționat, lock-in |
| Fuzozo / Eiliko / Tamagotchi | $55 / $60 / $45 | impuls, plastic/pluș |
| Vibe Desktop Buddy | $125 livrat | exact jobul nostru de dev, plastic |
| Eilik / Starboy vopsit | $140 / $139 | desk toy / metal intrare |
| Plaud NotePin S / Omi | $179 / $179 | util, fără față |
| Rabbit r1 | $199 | util |
| Friend 2.0 | $249 (+$10/lună) | emoțional, plastic |
| Loona DeskMate / Emo | $299 / $279–379 | birou, util/emo |
| **OpenAI × Ive** | **$300–400** (2027) | **obiect AI premium din metal**, reperul nostru direct |
| Starboy oțel / alamă | $349 / $399 (**epuizate**) | metal, fără AI |
| Ropet / Moflin | $349–469 / $429 | emoțional premium |
| Loona | $499 | robot |
| Light Phone III | $899 | „mai puțin ecran” premium |

**Verdict** [E]:
- **Founders (10–25 buc.) la €349: DA.** Asta înseamnă $397, adică *în* intervalul OpenAI ($300–400) și la fel ca Starboy oțel ($349 epuizat, **fără AI**). Pentru 25 de bucăți numerotate, cererea există sigur în nișa dev + design (Buddy vinde plasticul la $125). **€399 ($454) e prea sus** ca preț de listă: te pune peste OpenAI și aproape de Moflin, fără review-uri. Păstrează €399 doar pentru **#001–#010** (sau licitează-le, 05) și pune restul la €349. Include obligatoriu în Founders: **OU + gravură număr + relay pe viață + acces beta SoulOS**.
- **Mai târziu €199–299: confirmat, cu nuanță.** Standard **€249–279** (aluminiu, OU inclus) = sub OpenAI, peste Friend, pe lângă DeskMate. **€199** doar pentru o variantă fără OU sau cu carcasă din oțel/PC la 5–10k (09). Sub €199 intri în zona Fuzozo/xiaozhi, unde pierzi la preț, deci nu coborî acolo.
- **Riscuri de preț:** (1) Muse Charm subvenționat la $99–199 în decembrie ar reseta percepția „breloc AI” [E], deci comunicăm „obiect + AI-ul tău”, nu „breloc AI”. (2) OpenAI la $299 ne comprimă plafonul standard la ≤ €249. Decidem prețul standard **după** reveal-ul OpenAI.

---

## 6. 10 acțiuni concrete pentru SOUL
1. **Mesajul principal:** „**AI-ul tău. Obiectul tău. Al nimănui altcuiva.**” / „Nu te privește. Nu te ascultă. Te ajută.” Fără camere și hold-to-talk scrise pe cutie, contrast direct cu Muse (2 camere, 5G) și Friend. Evită cuvântul „breloc” și „calm” (e al lui Ive).
2. **Demo-ul care vinde:** un video vertical de 15 s în care Claude Code cere permisiune, ochii SOUL devin „nerăbdători”, apeși și aprobi, SOUL face HOPA. Nimeni altcineva nu are asta pe un obiect frumos (Buddy = ASCII pe plastic). Postează pe r/ClaudeAI, r/ClaudeCode, Show HN, X dev și Product Hunt (Buddy a luat #2/zi [V-s]).
3. **Compatibil 100% cu protocolul Claude Hardware Buddy** + publică eye-engine-ul open source (MIT) înaintea clonelor xiaozhi. Devenim implementarea de referință premium. Aplică la programul/showcase-ul Anthropic și Espressif (au promovat M5Stack [V]).
4. **Asigurarea pentru OpenAI:** firmware pregătit pentru aprobări Codex/ChatGPT desktop dacă OpenAI deschide un API similar [E]; „merge cu ChatGPT” e pe pagina de lansare din ziua 1.
5. **Fereastra UE, octombrie 2026–martie 2027:** Muse nu e în UE, Alexa+ nu e în RO/română. Lansare RO + DE/FR/IT/PL, presă RO (Start-up.ro, Playtech, Digi) + tech UE (heise, Golem, The Verge EU). **Hero film înainte de reveal-ul OpenAI.**
6. **Pagina „Promisiunile SOUL”**, răspuns direct la top 10 reclamații: baterie măsurată, latență < 1,5 s, fără abonament pentru nucleu, offline pe viață, Soul Pledge, fără motoare, română, personalitate fără vinovăție. Fiecare cu dovadă video.
7. **Features v1 „face lucruri”, doar ce merge demonstrat:** aprobări Claude Code/Cowork; remindere/alarme offline; notițe vocale → Claude/Obsidian (jobul Plaud, fără abonament); traducere; focus timer. **Amână „cumpără/rezervă”** (Muse e deja blocat de Amazon [V]).
8. **Founders 25:** €349, #001–#010 la €399 sau licitație; OU + gravură + certificat NFC; selectați dintre devii Claude Max/Pro + designeri; canal privat, feedback săptămânal, drept de vot pe primul sezon de ochi. Pagină cu depozit de €20 pentru lista de așteptare a lotului 2 (05).
9. **Monitorizare lunară (watch list):** prețul Muse Charm (dec.), reveal-ul OpenAI, primul export Fuzozo 4G/hard-shell, clone xiaozhi cu AMOLED 1,75 pe AliExpress, device-ul Nothing, un eventual buddy API Codex. Actualizăm această notă.
10. **Canale fără buget mare** (lecția Friend: $1M reclame → ~3k [V-0x]; lecția Starboy: X + presă): seeding la 10 creatori dev/design (Claude Code YouTube, desk-setup TikTok), un articol-poveste „startup românesc face obiectul pe care Meta și OpenAI nu-l pot face” și o ediție de artă de 10 bucăți (r-trends §5). Kickstarter nu e disponibil din RO, deci folosim shop propriu (Shopify Payments RO [V-0x]) pentru Founders.

---

## 7. Surse (WebFetch azi, 2026-09-25 = [V])
- Muse Charm: https://www.heise.de/en/news/Tamagotchi-meets-AI-agent-Meta-announces-AI-gadget-Muse-Charm-11464075.html [V] · https://decrypt.co/379253/meta-ai-toy-muse-charm-keychain-watches-listens [V] · https://startupfortune.com/meta-unveils-muse-charm-a-pocket-ai-companion-with-no-price-yet/ [V] · https://gulfnews.com/technology/meta-muse-and-muse-charm-explained-what-they-do-and-what-they-cost-1.500686025 [V] · https://www.engadget.com/2267229/meta-put-muse-in-a-tamagotchi-like-charm-device/ [V] · CNBC/qz (403) [V-s]
- OpenAI: https://techcrunch.com/2026/08/06/openais-new-ai-smart-speaker-will-reportedly-sell-for-between-300-and-400/ [V] · TechCrunch 2026-07-14, winbuzzer 2026-01-21 (Sweetpea) [V-s]
- Friend: https://techcrunch.com/2026/07/30/friend-the-lonely-ai-wearable-returns-with-a-new-voice-and-a-much-bigger-price-tag/ [V] · WIRED via getcoai/techbuzz [V-s]
- Fuzozo: https://www.stocktitan.net/news/TUYA/tuya-smart-accelerates-physical-ai-commercialization-with-strategic-fl5hn4dv397y.html [V] · https://mia-cat.com/en/pet-robot/fuzozo-review/ [V] · Tuya PR CES 2026 [V-s]
- Claude Buddy: https://claude-desktop-buddy.com/ [V] · https://www.espressif.com/en/news/Claude_ESP32_Code [V] · https://letsdatascience.com/news/claude-desktop-buddy-adds-physical-status-with-30-gadget-84fe1c0a [V] · hunted.space PH, github kaichen/m5stack-desktop-buddy [V-s]
- Rabbit: https://www.rabbit.tech/blog/first-major-update-of-2026-dlam-openclaw-and-a-surprise [V] · Android Police [V-s]
- Omi: https://www.omi.me/products/omi [V] · umevo devkit $69,99 [V-s]
- Pebble: https://repebble.com/blog/pebble-mega-update-july-2026 [V] · Android Authority/Wareable Index 01 [V-s]
- Loona DeskMate: https://www.cnx-software.com/2026/04/20/loona-deskmate-an-iphone-powered-ai-desk-companion-that-doubles-as-a-165w-gan-charging-station/ [V]
- Recenzii roboți: https://robotreviewdesk.com/guides/best-ai-companion-robots-2026/ [V] · https://robotreviewdesk.com/reviews/ropet-review/ [V] · Moflin/Loona/Eiliko/Uni/BubblePal (robotreviewdesk, mia-cat, tamatalk, mommyhood101) [V-s]
- Plaud NotePin S: plaud.ai blog (429), tldv, techradar [V-s] · Bee: TechCrunch 2026-01-12, T3 [V-s] · Humane/Limitless: Tom's Hardware, layer3labs [V-s]
- Echo/Alexa+: Engadget fall event, aboutamazon.com international [V-s] · Google Home Speaker: hothardware, Gizmodo, Engadget [V-s] · Nothing: 9to5google 2025-09-16, techbuzz [V-s] · xiaozhi retail: theinventory ($165), AliExpress [V/V-s]
- Note interne: 01, 04, 05, 09, design-max/r-trends [V-0x]
