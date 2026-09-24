---
tip: plan
afacere: Micul Șmecher
status: activ
actualizat: 2026-09-24
---
# Planul de bani — Micul Șmecher

> Cifrele pe bucată sunt calculate (TVA 21% scos din preț, comisioane de plată 2,9% + €0,30). Costurile de piese sunt la prețuri de dev-kit, cantități mici — scad la producție. Ce e estimare scrie „estimare”.

## Adevărul, întâi
- **Bani mulți ACUM nu există în hardware.** Cel mai rapid ban real vine din **pre-comenzi**, iar pre-comenzile vin după **un clip cu prototipul real**. Drumul cel mai scurt: ~2–3 săptămâni până la clip, ~4–6 săptămâni până la primele încasări.
- Comparabilele arată ce e realist pentru o campanie bună: Mirumi ~478.000 $, Eiliko ~600.000 $, Sweekar ~644.000 $ (2025–2026). Asta e **cifră de afaceri**, nu profit — o parte merge în producție.
- **1.000.000 € profit** din acest produs în 12 luni înseamnă ~18.000 de bucăți la ~€55 profit pe bucată. Se poate doar cu un hit viral (Fuzozo a vândut ~300.000 în China). Probabilitate mică; plafonul e însă mare, iar **valoarea firmei** (nu doar profitul) e unde stă milionul: Nothing a strâns 8 M$ de la comunitate, Plaud are peste 100 M$ venit software pe an.

## Cele 3 faze (fiecare o plătește pe următoarea)

### Faza A — Founders Desk Edition „works with Claude” (săptămânile 1–8)
Companion de birou alimentat prin USB (fără baterie → fără riscul și birocrația bateriei), pe placa Waveshare 1.43, carcasă printată mată, numerotat 001–300. Funcționează azi cu Claude Code / Cowork + toată viața offline.

| Preț (cu TVA) | Net fără TVA | Cost/bucată | Comisioane | **Rămâne/bucată** |
|---|---|---|---|---|
| €99 | €81,8 | €45,7 | €3,2 | **€32,9** (40%) |
| **€119 (recomandat)** | €98,3 | €45,7 | €3,8 | **€48,9** (50%) |
| €129 | €106,6 | €45,7 | €4,0 | **€56,9** (53%) |

Cost/bucată €45,7 = placă €26 + carcasă SLA €9 + suport și cablu €3 + cutie și certificat €3 + asamblare €2,5 + rebuturi 5%. Transportul se plătește separat de client.

| Scenariu la €119 | Încasat | Rămâne după piese | Minus teste CE (~€8.000) |
|---|---|---|---|
| 100 bucăți | €11.900 | €4.890 | −€3.110 |
| **300 bucăți** | €35.700 | €14.669 | €6.669 |
| 1.000 bucăți | €119.000 | €48.896 | €40.896 |

**Concluzie:** la 100 de bucăți nu merită dacă plătim teste CE complete; de la 300 în sus, da. De clarificat cu un consultant (1–2 h, ~€200) dacă un kit pentru dezvoltatori pe placa Waveshare (care are marcajul ei) poate porni cu un dosar mai simplu — vezi [[Conformitate și riscuri Micul Șmecher]].
**Poarta A:** ≥ 100 de rezervări plătite în 14 zile de la clip. Dacă nu → oprim și ajustăm mesajul/prețul, nu băgăm bani în producție.

### Faza B — Voice Edition (lunile 2–5): AI-ul personal în mână
Placa Waveshare 1.75 (2 microfoane + difuzor), baterie, amuletă de geantă, „ții degetul și vorbești”. Rezervare cu **€10 returnabili** → campanie de pre-comenzi (Indiegogo sau Gamefound acceptă România; **Kickstarter nu** — doar cu firmă în PL/GR/SI; sau direct pe Shopify ca Starboy).

Pe dev-kit (bucăți făcute manual) costul e mare: €73/bucată (placă €33, baterie €4,5, carcasă €12, cutie €4, asamblare €4, **AI inclus 6 luni ~€12**, rebuturi). La €149 rămân ~€45; la €179 ~€69. **La producția cu PCB propriu** costul coboară la ~€35–45 → ~€75/bucată la €149 (estimare).

| Campanie (comparabile) | Bucăți (~1,35/susținător) | Net fără TVA | Platformă + plăți (~8%) |
|---|---|---|---|
| €250.000 | ~1.690 | €206.600 | €20.000 |
| €450.000 | ~3.040 | €371.900 | €36.000 |
| €650.000 | ~4.390 | €537.200 | €52.000 |

Costul listei de așteptare (benchmark Prelaunch/LaunchBoom): email €1–3, 2–10% cumpără; **rezervare de €1–10: €5–25 per rezervare, 10–50% cumpără.** Țintă: ~2.000 de rezervări → 500–1.000 de susținători din prima zi.
**Poarta B:** ≥ 2.000 de rezervări cu depozit înainte de lansarea campaniei.

### Faza C — Producție (lunile 5–14)
PCB propriu cu modul ESP32-S3-WROOM (refolosim parte din dovezile radio Espressif), baterie înlocuibilă cu șurubelnița (obligatoriu în UE din 18.02.2027), carcasă turnată, certificare completă. Buget total 1.000 de bucăți: **€0,36–0,75 M** all-in (estimare din cercetare); se plătește din campanie + finanțare. **Nu comandăm nicio matriță fără comenzi plătite.**

## Abonamentul (bani recurenți)
- **Viu fără abonament, pentru totdeauna.** Vocea AI: 6 luni incluse, apoi opțional ~€4,99/lună sau pachete de minute.
- Costul real al vocii: ~1–4 $/utilizator/lună (STT+TTS) + LLM ~1–3 $ (de măsurat). Marja brută pe abonament: ~40–60%.
- Reper: la Plaud ~50% dintre proprietari plătesc. La 5.000 de utilizatori × 30% × €4,99 ≈ **€7.500/lună recurent** (estimare).

## Finanțarea (fără să pui banii tăi)
1. **Startup Nation 2026 — 250.000 lei (~€49.000) nerambursabili**, sesiunea a doua „în această toamnă” (StartupCafe, 14.09.2026). Cere **firmă nouă** → înființăm SRL-ul SUFLET acum. ⚠️ De verificat condițiile exacte în ghid.
2. Pre-comenzile Fazei A (€15–35k).
3. Business angels + pre-seed €1–2 M: Early Game Ventures (RO, conduce pre-seed, €0,5–2 M), Credo Ventures (1–5 M$), HAX (550k $ pentru hardware). Argumentul: prototip real + clip + listă cu depozite + „works with Claude”.
4. Rundă de comunitate pe **SeedBlink** (fondată de români) după ce lista trece de 20.000.
5. EIC Accelerator (până la €2,5 M grant) — pentru scalare, termen 4.11.2026 (prea devreme pentru noi; următorul ciclu).

## Filtrul celor 5 întrebări ([[Scopul — 1 milion €]])
1. **Cât profit pe lună dacă merge?** Faza A: €5–15k total în ~2 luni (~€2,5–7,5k/lună). Faza B: campanie €250–650k venit; profit după producție ~25–35% (estimare) → €60–200k pe ciclu. Abonament: €7,5k/lună la 5.000 de utilizatori.
2. **Cât de sigur?** Nesigur. Avem dovezi de piață (Starboy stoc epuizat la 139–599 $, Eiliko/Mirumi/Sweekar 0,5–0,65 M$, Fuzozo 300k bucăți), dar **zero date proprii**. Primele date: rezervările din Poarta A.
3. **Cât costă?** Prototip ~€120. Faza A: ~€2–4k (piese pentru primele 50 + domeniu + marcă) înainte de încasări; teste CE €5–12k din încasări. Timp Andu: ~6–10 h/săptămână (asamblare, filmare, postări).
4. **Se poate înmulți?** Da: global, recurent (abonament), colecționabil (ediții, rarități), iar „works with Claude” are un public de milioane.
5. **Ce putem pierde?** ~€120 pe prototip + ~€2–4k dacă Faza A nu atinge poarta. Pierdere acceptabilă. Riscul mare (matrițe, stoc) începe abia după comenzi plătite.

**Verdict JARVIS:** merită, **ca experiment cu porți**, în paralel cu [[Expandly]] (care rămâne pe drumul spre App Store înainte de Black Friday). Nu mutăm bani din MundiShop.

## Pre-mortem — de ce ar putea eșua
- Clipul nu prinde → nicio rezervare. *Contra:* 10 clipuri diferite, testate organic înainte de reclame.
- Anthropic schimbă/închide API-ul Hardware Buddy (e „developer mode”, neoficial). *Contra:* viața offline + vocea nu depind de el; cerem parteneriat.
- Meta lansează Muse Charm ieftin și ia piața de masă. *Contra:* nișă premium, design, confidențialitate, orice AI, dezvoltatori.
- Livrări întârziate (75% din campaniile hardware întârzie). *Contra:* promitem o dată cu 3 luni după planul intern.
- Costul vocii scapă de sub control la utilizatorii intensivi. *Contra:* minute incluse + pachete.

## Legat de
[[Micul Șmecher]] · [[Viziunea — momentul iPhone]] · [[Produs și dezvoltare Micul Șmecher]] · [[Roadmap 1 milion €]]
