# -*- coding: utf-8 -*-
import sys, copy
from docx import Document
from docxlib import *
from data import *

OUT = sys.argv[1]
d = Document('a16.docx')
B = list(d.element.body.iterchildren())
NUM = 2
PPROTO = copy.deepcopy(B[25])  # plain body paragraph
TPROTO = B[59]                  # header r0 + data r1, 5 cols


def T(header, data, widths, **kw):
    return build_table(TPROTO, header, data, widths, **kw)


def para(text, bullet=False):
    return clone_par(PPROTO, text, numid=NUM if bullet else None)


def put(anchor, items, replace=True):
    """Insert items before anchor element; delete anchor if replace."""
    for it in items:
        if isinstance(it, str):
            el = para(it[2:], True) if it.startswith('- ') else para(it)
            anchor.addprevious(el)
        else:
            anchor.addprevious(it)
            anchor.addprevious(para(''))
    if replace:
        delete(anchor)


def after(el, items):
    """Insert items right after el (in order)."""
    nxt = el.getnext()
    marker = para('')
    el.addnext(marker)
    put(marker, items)


def drop_rows(tbl, *idx):
    rs = rows(tbl)
    for i in sorted(idx, reverse=True):
        delete(rs[i])


def fill_rows(tbl, start, data):
    rs = rows(tbl)
    last = None
    for k, v in enumerate(data):
        if start + k < len(rs):
            fill_row(rs[start + k], v); last = rs[start + k]
        else:
            last = add_row_after(last, v)
    for extra in rows(tbl)[start + len(data):]:
        delete(extra)


# ---------------------------------------------------------------- general data
gen = [TITLU + ' (acronim SOUL-PoC)', APPLICANT, '[[A/Ct: CUI]] / [[J40/…/…]]', 'Nu a fost atribuit (se completează după înregistrarea în MySMIS)',
       RIS3, 'TRL 3 (minim obligatoriu conform Ghidului Solicitantului) — dovezile D1–D8, Secțiunea II',
       'TRL 5 (validare în mediu relevant, L22); TRL 4 = rezultat intermediar (poarta IE2, L14)',
       'Expert independent [[de confirmat: expert independent sau colectiv științific al unei organizații de cercetare; nu este coordonatorul tehnic al proiectului]]']
for tr, v in zip(rows(B[5])[1:], gen):
    set_cell(tcs(tr)[1], v)
fill_row(rows(B[8])[2], ['1', '[[Nume Prenume — expert/coordonator colectiv]]', '[[Universitate/INCD]]', 'TIC; Sisteme și Componente Inteligente (sisteme embedded, RF, HCI)',
                         '[[a) ≥ 5 ani experiență: …; b) ≥ 2 publicații în ultimii 10 ani (DOI): …; c) acreditări/certificări în ultimii 10 ani: …]] — CV Europass și dovezi anexate'])
fill_row(rows(B[8])[3], ['2', '[[Nume Prenume — opțional, membru colectiv]]', '[[Afiliere]]', '[[Domeniu]]', '[[a)/b)/c)]]'])
fill_row(rows(B[8])[4], ['3', '[[Nume Prenume — opțional]]', '[[Afiliere]]', '[[Domeniu]]', '[[a)/b)/c)]]'])

# remove usage guide 11..20
for i in range(11, 21):
    delete(B[i])

# ---------------------------------------------------------------- I
delete(B[22]); delete(B[24])
put(B[25], [
    '**Problema tehnologică.** Asistenții AI generativi sunt accesibili aproape exclusiv prin telefon și computer. Dispozitivele AI dedicate lansate în 2023–2025 au eșuat din motive **tehnice și de arhitectură**, nu din lipsă de cerere: (1) **dependența de cloud** — Humane AI Pin a fost oprit de la distanță la 28.02.2025, iar robotul Moxie a încetat să funcționeze odată cu serverele producătorului (dec. 2024); (2) **latența** — sisteme comerciale cu 10–15 s de așteptare, în timp ce literatura arată că întârzierea răspunsului degradează percepția agentului [6] și că dialogul vocal poate coborî la 160–200 ms în modele full-duplex [5]; (3) **interfața** — introducerea de text pe ecrane mici și rotunde rămâne o problemă deschisă de cercetare HCI (10–30 WPM în literatură; compensarea atingerilor imprecise [1]; accesibilitate [2]; 176 de tehnici catalogate fără un optim pentru discuri mici [3]); (4) **închiderea ecosistemului** — un singur furnizor de AI și abonament obligatoriu; (5) **reparabilitatea și securitatea** — din 18.02.2027 bateriile portabile trebuie să fie înlocuibile de utilizator (Reg. (UE) 2023/1542, art. 11), iar echipamentele radio conectate trebuie să respecte EN 18031 (Reg. delegat (UE) 2022/30).',
    '**Decalajul de cunoaștere.** Nu există o demonstrație publicată a unui sistem care să rezolve **simultan** aceste constrângeri pe un hardware de cost redus (MCU ESP32-S3, fără GPU dedicat), într-o carcasă metalică premium: randarea procedurală fluidă pe un panou RGB fără memorie proprie concurează cu radioul pentru lățimea de bandă PSRAM (H1); tastatura pe un disc de ~70 mm depinde de decodare (H2); independența de cloud cere o arhitectură hibridă verificabilă (H3); aluminiul atenuează semnalul 2,4 GHz (H4); ecranul IPS mare și bateria înlocuibilă concurează pentru volum și energie (H5).',
    '**Ipoteza de cercetare (formulare testabilă):** **dacă** un dispozitiv de 90 × 103 × 31 mm cu afișaj rotund de 2,8″ integrează (i) un motor de randare SDF optimizat pentru un microcontroler ESP32-S3, (ii) o tastatură QWERTY circulară cu decodare probabilistică, (iii) o arhitectură AI hibridă local-first cu degradare controlată și (iv) o carcasă din aluminiu cu fereastră radio polimerică și baterie înlocuibilă, **atunci** sistemul poate atinge simultan, în mediu relevant, **≥ 30 fps** la animație, **≥ 20 cuvinte/min** la tastare, latența vocală **p50 ≤ 1,5 s**, **≥ 90 %** comenzi executate corect fără internet, atenuare RF prin carcasă **≤ 6 dB** și **≥ 24 h** de autonomie în profil tipic.',
    'Ipoteza se descompune în sub-ipotezele H1–H5 (Secțiunea VI), fiecare cu indicatori, metodă de măsurare, baseline (TRL 3) și praguri TRL 4 / TRL 5. Ipoteza este **falsificabilă**: dacă la poarta IE2 (L14) pragurile O1 nu sunt atinse nici după alternativele tehnice prevăzute, se aplică procedura de eșec de cercetare (Anexa 17).',
])

t = B[27]
drop_rows(t, 0)
fill_rows(t, 2, [list(r) for r in REFS])
after(t, ['Sursele [1]–[11] sunt publicate în 2021–2025 (≤ 5 ani) și au fost verificate la 25.09.2026 prin Crossref (DOI) și arXiv. Reperele mai vechi (COMPASS 2017, C-QWERTY 2019) sunt folosite doar ca baseline. Lista completă, cu surse normative și de piață, este în Secțiunea VII. [[E: expertul validează selecția și poate adăuga surse din domeniul său]]'])

delete(B[30])
put(B[31], [
    '**Relevanța economică.** Adopția AI generativ în UE a ajuns la 32,7 % din populația de 16–74 ani în 2025 (15,1 % la muncă; România 17,8 % — cel mai mic nivel din UE, Eurostat). Piața de hardware AI dedicat este validată comercial (Plaud: peste 2 milioane de dispozitive, peste 100 M$ ARR din abonamente; Fuzozo: ~300.000 de unități), dar dominată de produse fie dependente de cloud, fie fără funcții utile, iar marile platforme lipsesc din UE/română (Meta Muse Charm doar în SUA; Alexa+ fără română). Reglementarea UE (baterii înlocuibile, drept la reparare, securitate radio, AI Act art. 50) creează o fereastră pentru produse proiectate de la început în acest sens. Beneficiile estimate pentru solicitant: o linie de produs proprie cu IP protejat (design + marcă UE), cu traseu către 7.000 de unități/an în anul 5 post-proiect [E] (Planul de afaceri, §6.3).',
    '**Încadrarea în RIS3 BI 2021–2027 — două domenii, argumentate pe obiective, activități și rezultate (nu pe CAEN):**',
    '- **Tehnologia Informației și Comunicațiilor (TIC):** firmware embedded (C++17) pentru randare SDF în timp real; tastatură circulară cu decodare probabilistică; arhitectură AI hibridă local-first (parser offline RO/EN + modele de limbaj la alegerea utilizatorului prin tool-calling, conector MCP); flux vocal în timp real (Opus/WebSocket, servere UE); securitate cibernetică EN 18031 (BLE LE Secure Connections, OTA semnat, secure boot). Obiective O1, O3; activități A2, A3, A5; rezultate: firmware SoulOS, serviciul AI, protocoalele și datele de validare (R1, R2, R4).',
    '- **Sisteme și Componente Inteligente:** sistem ciber-fizic integrat — ESP32-S3, afișaj rotund IPS 480×480, touch capacitiv, IMU, microfoane MEMS, PMU, baterie înlocuibilă și antenă BLE/Wi-Fi integrată într-o carcasă CNC din aluminiu cu fereastră radio polimerică. Obiective O2, O3; activități A4, A5; rezultate: PCB propriu, arhitectura electromecanică, măsurătorile RF/energie/EMC (R2, R3).',
    'Subdomeniile RIS3 BI: [[Cl: citare exactă din strategia RIS3 BI 2021–2027 (adrbi.ro), după descărcare]]. Aceeași încadrare apare în Cererea de finanțare și în Planul de afaceri (§4.1).',
])

t = B[33]
drop_rows(t, 0)
fill_rows(t, 1, [[o[0], o[1], o[2], o[3], o[5]] for o in OBJECTIVES])
put(t, [f'**Scopul general:** {OBJ_GENERAL}'], replace=False)
after(t, ['Obiectivele O1–O4 sunt identice cu cele din Cererea de finanțare și din Planul de afaceri (§1.2). Rezultatele așteptate R1–R5: ' + ' · '.join(f'**{c}** — {n} ({m})' for c, n, m in RESULTS) + '.'])

delete(B[36])
put(B[37], [
    '**(i) Principiul de funcționare.** SOUL este un **dispozitiv tangibil de interacțiune om–mașină / asistent personal AI**. Interfața este un afișaj rotund pe care un motor de randare procedurală (câmpuri de distanță cu semn — SDF — cu anti-aliasing analitic) desenează „ochi” parametrici ce exprimă starea sistemului (ascultă, gândește, așteaptă aprobare, doarme); aceeași suprafață găzduiește o tastatură QWERTY circulară. Comenzile utilizatorului (text, voce, gesturi) sunt transformate într-un **singur set de acțiuni** cu scheme JSON stricte, executate în trei moduri: fără AI (parser local RO/EN, pe dispozitiv/serverul propriu), cu Claude sau cu ChatGPT (tool-calling). Dacă rețeaua sau cheia API cad, sistemul revine controlat la modul local.',
    '**(ii) Componente principale și arhitectura sistemului:**',
    '- **Hardware:** ESP32-S3 (WROOM-1, 8 MB PSRAM, 16 MB flash); panou IPS rotund 2,8″ 480×480, controler ST7701, interfață RGB565 paralelă, framebuffer 460 KB în PSRAM, bounce-buffers; touch GT911; IMU QMI8658; RTC PCF85063A; codec ES8311 + ES7210, 2 microfoane MEMS, AEC, amplificator; PMU; celulă Li-ion 2500–3000 mAh pe conector MX1.25 (înlocuibilă).',
    '- **Mecanică:** corp ~90 × 103 × 31 mm, CNC din Al 6061 anodizat; talpă polimerică detașabilă = fereastră radio pentru antena 2,4 GHz; închidere Torx, fără adeziv pe celulă; capsula de încărcare „OU” cu pini pogo.',
    '- **Firmware SoulOS (C++17):** Canvas SDF, Face/Brain/Personality (24 de reacții procedurale, personalitate derivată din ID-ul cipului), Gestures, Keyboard/TextField/Predictor, TimePicker, Alarms, Shell, ClaudeLink (protocolul Claude Hardware Buddy, BLE securizat), OTA semnat, secure boot; geometria UI independentă de rezoluție (466 → 480 px).',
    '- **Serviciul AI (Python, servere UE):** `suflet_ai` — acțiuni cu scheme JSON, parser local RO/EN, conector MCP, cheie proprie criptată; poarta vocală Opus/WebSocket (xiaozhi-esp32, MIT, adaptat la servere UE).',
    '**(iii) Funcționalități-cheie:** notițe, alarme, mementouri, liste, cronometre (offline); aprobări pentru Claude Code/Cowork prin BLE; dialog vocal cu asistentul ales; modul „taste mari” (T9 predictiv, taste de 10,3 × 7,7 mm) și control vocal pentru accesibilitate; informare AI Act art. 50 la prima pornire.',
    '**(iv) Caracterul inovativ — elemente de diferențiere verificabile:**',
    T(['Cod', 'Element nou', 'Stadiul actual / competitori', 'Contribuția SOUL-PoC (măsurabilă)'], [list(n) for n in NOVELTY], [700, 3400, 2900, 3080]),
    '**(v) Tipul de inovare: inovare de produs** — un bun fizic nou (hardware + carcasă) cu firmware încorporat și un serviciu software asociat. Justificare: rezultatul proiectului este un produs care nu există pe piață (niciun competitor din cei 24 analizați nu combină față expresivă + obiect premium reparabil + AI la alegerea utilizatorului + acțiuni utile + funcționare offline) și care cere dezvoltare experimentală (N1–N5), nu doar integrare de componente.',
])

# ---------------------------------------------------------------- II
delete(B[39])
put(B[42], [
    'Nivelul TRL de pornire al proiectului este **TRL 3 — dovadă experimentală a conceptului** (Anexa 18). Justificare: funcțiile critice ale conceptului SOUL sunt validate analitic și experimental **pe componente separate**, în laborator și în simulare: randarea și logica UI (61/61 teste Unity, simulator), tastatura circulară (prototip web interactiv, model geometric), arhitectura AI hibridă (49/49 teste), geometria și CAD-ul corpului, iar înainte de depunere funcțiile critice sunt măsurate pe placa de dezvoltare SOUL M (experimentele X1–X8). **Nu declarăm TRL 4**: componentele nu au fost încă integrate într-un sistem funcțional (audio, baterie, carcasă și AI nu rulează împreună), iar nicio validare de sistem în laborator nu a avut loc.',
])

t = B[44]
drop_rows(t, 0)
trl = [
    'PARCURS. Principiile de bază sunt raportate în literatură: randarea prin câmpuri de distanță cu anti-aliasing analitic (grafică pe calculator) și limitele randării GUI pe dispozitive embedded [4]; introducerea de text pe ecrane rotunde (C-QWERTY, COMPASS — baseline; decodare pentru atingeri imprecise [1]; accesibilitate [2, 3]); compromisurile LLM on-device vs. cloud [7] și latența dialogului vocal [5, 6]; antene 2,4 GHz în carcase metalice [8, 9]; proiectarea pentru dezasamblare și reparabilitate [10, 11].',
    'PARCURS (sept. 2026). Conceptul SOUL a fost formulat și documentat: specificația SoulOS (os/SPEC.md, os/ARCHITECTURE.md), studiile de piață, conformitate și competiție (research 01–11, benchmark de 24 de competitori), modelul geometric al tastaturii (pas = 0,0944·D; taste de 6,7 mm pe Ø70) și alegerea panoului 2,8″ IPS 480×480 (research 12), conceptul de carcasă din aluminiu cu fereastră radio (research 10). Aplicații identificate: aprobări AI, notițe/alarme offline, accesibilitate.',
    'TRL DE PORNIRE — ATINS pentru funcțiile critice pe componente separate. Dovezi (detaliate în §2.3): D1 firmware cu 61/61 teste Unity; D2 simulator cu cadre reale; D3 serviciul AI cu 49/49 teste; D4 prototipul web al tastaturii; D5 modelul analitic al tastaturii; D6 CAD parametric; D7 istoric git datat; D8 raportul de laborator TRL 3 pe hardware (X1–X8) — [[în curs, se finalizează și se anexează înainte de depunere]].',
    'PLANIFICAT (L14). A1–A3: modelul de laborator SOUL M integrat (afișaj + touch + audio + baterie + AI hibrid, carcasă SLA) validat prin protocoalele P1–P8 la pragurile O1: fps median ≥ 30 · precizie touch ≥ 97 % · WPM ≥ 15 (N = 6) · succes offline ≥ 90 % · latență vocală p50 ≤ 1,8 s · 8/8 protocoale rulate. Livrabil: R1 Raport TRL 4 (IE2) + decizia go/no-go.',
    'PLANIFICAT (L22). A4–A5: 15 prototipuri pre-serie cu PCB propriu și carcasă CNC din aluminiu, folosite 4 săptămâni de ≥ 12 utilizatori din BI (locuințe, birouri, living lab) + pre-testare EMC/RF; protocoalele P1–P11 la pragurile O3: WPM ≥ 20 și UER ≤ 3 % · latență p50 ≤ 1,5 s / p90 ≤ 2,5 s · succes offline ≥ 90 % · ≥ 99 % sesiuni fără crash · SUS ≥ 75 · atenuare ≤ 6 dB · ≥ 24 h · 0 depășiri la pre-scan. Livrabil: R2 Raport TRL 5 (IE3).',
]
for tr, v in zip(rows(t)[1:], trl):
    set_cell(tcs(tr)[2], v)

t = B[47]
drop_rows(t, 0, 1)
fill_rows(t, 1, [list(e) for e in EVIDENCE])
after(t, [
    '**Experimentele TRL 3 pe hardware (dovada D8) — de rulat înainte de depunere (T−6 … T−2 săptămâni), toate marcate „în curs”:** placa Waveshare ESP32-S3-Touch-LCD-2.8C (≈ 40 $) + un microfon I²S + un amplificator mic se cumpără din fonduri proprii și **nu intră în buget** (§5.2.1 IV).',
    T(['Cod', 'Experiment', 'Metodă', 'Rezultat de raportat', 'Stare'], [list(x) + ['[[în curs]]'] for x in XTESTS], [650, 3300, 2600, 2330, 1200]),
    'Livrabilul înainte de depunere este „Raport de laborator TRL 3 — SOUL M (2.8C)”, datat și semnat, cu loguri, fotografii, video cu marcaj de timp, hash-ul commit-ului git și rezultatele X1–X8; valorile obținute devin baseline-ul protocoalelor P1–P9 (§3.3). **Contribuția științifică proprie a solicitantului:** motorul de randare SDF pentru MCU, geometria și hit-testing-ul tastaturii circulare cu taste de margine „stăpâne” pe bordură, arhitectura „un set de acțiuni, trei moduri”, conceptul de carcasă cu fereastră radio și baterie înlocuibilă. Drepturile asupra acestor rezultate sunt cedate de autor către ARTEMIS prin contract de cesiune [[A: semnat înainte de depunere]]; componentele open-source (MIT/OFL) sunt listate cu licențele lor.',
])

delete(B[50])
put(B[51], [
    '**Demonstrat până la depunere (TRL 3):** funcțiile critice pe componente separate — randarea SDF și logica UI (teste automate + simulator, inclusiv geometria 480 px), tastatura circulară (hit-testing verificat pe fiecare tastă, prototip web), parserul local și cele trei moduri AI (teste automate), modelul geometric și CAD-ul; pe hardware, prin X1–X8: rularea pe placa 2.8C, fps, precizie touch, tastare pilot, parser pe 200 de comenzi, latența unui tur AI text, atenuarea orientativă prin tablă de aluminiu, consumul plăcii.',
    '**De validat în proiect (TRL 4 → TRL 5):** (1) funcționarea **integrată** a tuturor subsistemelor (afișaj, touch, audio cu AEC, baterie/PMU, AI hibrid, voce) — nedemonstrată azi; (2) performanța la **pragurile O1** în laborator și la **pragurile O3** în mediu relevant; (3) comportamentul RF într-o **carcasă reală din Al 6061** cu fereastră polimerică (nu o tablă de test); (4) autonomia în **profil tipic** cu baterie finală; (5) studiile cu **utilizatori reali** (N = 6 la TRL 4; N ≥ 12, 4 săptămâni la TRL 5) și reparabilitatea (P10); (6) conformitatea preliminară EMC/RF și EN 18031. Nicio afirmație din Secțiunile III–VI nu presupune că aceste rezultate sunt deja obținute.',
])

# ---------------------------------------------------------------- III
delete(B[53])
put(B[55], [
    '**Etapa 1 — setup și protocoale (A1, L1–L3).** Specificația sistemului M (L1.1); protocoalele P1–P11 cu praguri, metode statistice și formulare de consimțământ (L1.2); achiziția și calibrarea aparatelor (osciloscop, analizor de spectru, analizor de consum, cutie ecranată); bancul de test validat (M1, L3).',
    '**Etapa 2 — de la componente la modelul de laborator (A2, L2–L8).** Port RGB/ST7701 cu bounce-buffers și măsurarea fps (P1) la fiecare modificare; integrarea GT911 și calibrarea touch (P2); subsistemul audio I²S cu 2 microfoane și AEC; alimentarea (PMU, baterie 2500–3000 mAh) și modelul de consum (P9); carcasa SLA la scara M; serverul vocal UE; scalarea tastaturii la 480 px. IE1 (L6): modelul rulează integrat, cu primele măsurători P1, P2, P5.',
    '**Etapa 3 — validarea TRL 4 în laborator (A3, L6–L14).** Teste de componente, apoi de sistem, pe protocoalele P1–P8; studiul de tastare cu N = 6 (P3, P4); analiza statistică și **decizia de poartă IE2 (L14)**: pragurile O1 atinse → go TRL 5; neatinse → alternativele tehnice (randare parțială, fereastră radio mai mare, antenă externă în talpă, server mai aproape/model mai mic) și, dacă nici acestea nu reușesc, Anexa 17.',
    '**Etapa 4 — prototipul pre-serie (A4, L9–L17).** PCB propriu rev A (L9–L13) și carcasă Al rev A (3 seturi); proiectarea/validarea antenei prin carcasă (serviciu CDI extern) și P8 pe rev A (≤ 8 dB); **după poarta IE2**: rev B, carcase rev B (5 + 15 seturi), 15 prototipuri, QC 15/15 (M3, L17); arhitectura EN 18031 (secure boot, OTA semnat).',
    '**Etapa 5 — validarea TRL 5 în mediu relevant (A5, L16–L22).** 15 unități la 12–15 utilizatori din BI, 4 săptămâni, telemetrie opt-in; protocoalele P1–P10 în teren și reproducerea controlată în laborator; 2 workshop-uri de testare; 2 sesiuni de pre-scan EMC/RF (P11); raportul TRL 5 (IE3, L22).',
])
put(B[57], [
    '**Integrare.** Integrarea se face incremental, cu un singur depozit git și build-uri reproductibile (PlatformIO), astfel încât orice regresie (fps, consum, RF) să fie legată de un commit. Ordinea: afișaj + touch → audio → alimentare → AI/voce → carcasă. Fiecare pas are un test de acceptanță din P1–P9 rulat automat sau semi-automat (log serial, telemetrie).',
    '**Testare în laborator.** Măsurătorile fizice (RSSI, consum, semnale) se fac în cutia ecranată și cu aparatura din proiect, cu trei configurații de referință (placă goală, carcasă SLA, carcasă Al rev A/B), pentru a izola efectul carcasei. Studiile cu utilizatori folosesc fraze MacKenzie–Soukoreff (EN) și un set echivalent RO, 15 min de acomodare, sesiuni repetate; indicatorii WPM, UER, CER se calculează din logurile de tastare.',
    '**Demonstrare în condiții relevante.** Unitățile rulează firmware-ul și serverul UE finale, pe rețele Wi-Fi casnice reale, cu zgomot ambiental real, la utilizatori reali din BI (panel cu ≥ 40 % femei, ≥ 3 persoane peste 55 de ani, ≥ 2 persoane cu deficiențe de vedere/motorii). Telemetria opt-in înregistrează fps, crash-uri, comenzi offline reușite, latențe, RSSI/PDR, autonomia. Analiza: mediană, p5/p90, intervale de încredere 95 % (bootstrap), comparație cu baseline-ul TRL 3 și cu pragurile O3; abaterile se explică explicit în raportul TRL 5.',
])
t = B[59]
proto_rows = []
for p in PROTOCOLS:
    env = 'TRL 4: laborator ARTEMIS; TRL 5: mediu relevant (BI)' if p[0] != 'P11' else 'laborator EMC/RF acreditat'
    proto_rows.append([p[0], f'{p[1]} ({p[2]})', p[3] + (f'; baseline: {p[4]}' if p[4] != '–' else ''), f'TRL 4: {p[5]}\nTRL 5: {p[6]}', env])
fill_rows(t, 1, proto_rows)
set_widths(t, [650, 1900, 3000, 2530, 1900])
after(t, [RELEVANT_ENV, ETHICS])

# ---------------------------------------------------------------- IV
delete(B[62])
t = B[64]
drop_rows(t, 0)
infra = [
    ['1', 'Laborator electronic ARTEMIS (sediul social, București)', 'banc de lucru, stație de lipit; după contract: osciloscop ≥ 200 MHz, analizor de spectru ≥ 3 GHz, analizor de consum, cutie ecranată ≥ 60 dB, stație PC, imprimantă 3D SLA (liniile 5–10 ale bugetului)', 'propriu (spațiu [[A: proprietate/chirie/comodat]]); aparatele se achiziționează în proiect', 'A1–A5'],
    ['2', 'Placa de dezvoltare Waveshare ESP32-S3-Touch-LCD-2.8C + simulatorul pe PC', 'ESP32-S3R8, IPS 2,8″ 480×480, GT911, IMU, RTC; simulatorul produce cadrele reale ale motorului', 'proprii (achiziționate din fonduri proprii, în afara bugetului)', 'X1–X8, A1–A3'],
    ['3', 'Laborator EMC/RF acreditat [[denumire]]', 'pre-scan EN 300 328 / EN 301 489-1/-17, 2 sesiuni', 'contract de servicii; ofertă + scrisoare de disponibilitate [[de anexat]]', 'A5 (P11)'],
    ['4', 'Organizație de cercetare parteneră [[UPB ETTI / IMT București / ICI — de confirmat]]', 'expertiză RF/antene, acces la camera anecoică, recrutarea studentului', 'acord de colaborare / scrisoare de intenție [[de anexat]]', 'A4, A5'],
    ['5', 'Ateliere CNC și fabricanți PCB (RO/UE/internaționali)', 'CNC Al 6061 + anodizare (3 + 5 + 15 seturi); PCB rev A/B fabricare + asamblare', 'contracte de servicii; câte 2 oferte pe linie [[de anexat]]', 'A4'],
    ['6', 'Software și date', 'Git, PlatformIO, KiCad, CadQuery (open-source); SaaS: API AI (LLM/STT/TTS), găzduire UE, CAD (linia 18); corpusuri proprii RO/EN (200 de comenzi, 300 de cuvinte, fraze de tastare)', 'licențe open-source / SaaS / proprii', 'toate'],
]
fill_rows(t, 1, infra)
t = B[67]
drop_rows(t, 0, 1)
partners = [
    ['1', '[[Universitatea Politehnica București — Facultatea ETTI / IMT / ICI]]', 'Universitate / INCD', 'expertiză RF/antene, acces la laborator/camera anecoică, sprijin pentru recrutarea studentului, eventual serviciul CDI pentru antenă (linia 16)', 'Scrisoare de intenție / acord de colaborare [[anexa nr. …]]'],
    ['2', '[[Laborator EMC/RF acreditat]]', 'Laborator de testare', 'pre-testare EMC/RF (P11)', 'Ofertă + scrisoare de disponibilitate [[anexa nr. …]]'],
    ['3', '[[Living lab / hub de inovare din BI]]', 'Organizație de inovare', 'găzduirea workshop-urilor de testare și a unei părți din panelul TRL 5', 'Scrisoare de intenție [[anexa nr. …]]'],
    ['4', '[[Asociație a persoanelor cu dizabilități]]', 'ONG', 'recrutarea a ≥ 2 participanți cu deficiențe de vedere/motorii; testul de accesibilitate cu raport public', 'Scrisoare de intenție [[anexa nr. …]]'],
    ['5', '[[Firmă de software care folosește Claude Code]] / [[retailer-distribuitor]]', 'IMM', 'pilot cu 3–5 utilizatori în TRL 5 / distribuție după validare', 'Scrisori de intenție cu cele 7 elemente (Grila 4.2) [[anexa nr. …]]'],
]
fill_rows(t, 1, partners)
after(t, ['Resursele umane pentru TRL superior: coordonator tehnic/științific (≥ 5 ani în sisteme embedded) [[Nume]], inginer embedded/firmware (≥ 2 ani) [[Nume]], student cercetare ≤ 24 ani [[Nume]], manager de proiect (Andu); CV-urile și declarațiile de disponibilitate se anexează la CF. Pentru TRL 6–9 (post-proiect): certificare CE/RED + EN 18031 la un laborator notificat, PCB rev C cu modul radio certificat, scule de producție (Planul de afaceri, Secțiunea VI).'])

# ---------------------------------------------------------------- V
delete(B[70])
t = B[73]
trl_of = {'A1': '3 → 3+', 'A2': '3 → 4', 'A3': '4', 'A4': '4 → 5', 'A5': '5', 'A6': '5', 'A7': '5', 'A8': '–'}
ms_of = {'A1': 'M1 banc de test validat (L3)', 'A2': 'IE1 (L6): model integrat funcțional; P1, P2, P5 măsurate', 'A3': 'IE2 (L14): pragurile O1 atinse; go/no-go',
         'A4': 'M3 (L17): 15/15 prototipuri trec QC; P8 ≤ 8 dB pe rev A', 'A5': 'IE3 (L22): pragurile O3 atinse', 'A6': 'cereri EUIPO depuse (≤ L5/L6); ≥ 2 acorduri (L24)',
         'A7': 'manuscris trimis OA peer-review (≤ L20); prezentare (≤ L24)', 'A8': 'rapoarte de progres, audit, vizibilitate'}
fill_rows(t, 1, [[a[0], a[1], trl_of[a[0]], a[3], a[5], ms_of[a[0]]] for a in ACTIVITIES[1:]])
set_widths(t, [650, 3700, 850, 1000, 2000, 1880])
after(t, ['A0 (pregătirea CF, a Planului de afaceri și a acestui raport + validarea de către expert) este activitate precontractuală (conex II.2). Tipurile de activitate (CDI I.1–I.4 / conex II.1–II.5) și bugetul fiecărei activități sunt identice cu CF.'])

delete(B[76])
gantt_rows = [[n] + ['■' if m in rng else '' for m in range(1, 25)] for n, rng in GANTT]
put(B[77], [T(['Activitate'] + [str(m) for m in range(1, 25)], gantt_rows, [2640] + [310] * 24, size=14, compact=True,
              center_cols=tuple(range(1, 25))), DEPENDENCIES])

t = B[79]
fill_rows(t, 1, [[m[0], m[1], m[2], m[3], m[4]] for m in MILESTONES])
t = B[82]
drop_rows(t, 0)
fill_rows(t, 1, [list(x[:4]) + [x[4] + (' [[Nume]]' if x[4] in ('coordonator tehnic', 'inginer embedded') else '')] for x in DELIVERABLES])

# ---------------------------------------------------------------- VI
delete(B[85])
t = B[87]
drop_rows(t, 0)
fill_rows(t, 1, [[h[0], f'**{h[1]}.** {h[2]}', h[3]] for h in HYP])
t = B[90]
ind = [
    ['I1', 'H1', 'fps median al animației ochilor (Wi-Fi + BLE active, 60 min)', 'fps', 'TRL 4/5: median ≥ 30, p5 ≥ 24', 'P1: contor de cadre în firmware, log serial/telemetrie'],
    ['I2', 'H2', 'Precizia touch pe ținte de 6,7 mm', '%', 'TRL 4: ≥ 97 (N = 6); TRL 5: ≥ 97 (N ≥ 12)', 'P2: grilă de ținte, 200 de atingeri/persoană'],
    ['I3', 'H2', 'Viteza de tastare', 'WPM', 'TRL 4: ≥ 15; TRL 5: ≥ 20', 'P3: fraze MacKenzie–Soukoreff (EN) + set RO'],
    ['I4', 'H2', 'Rata de eroare necorectată (UER)', '%', 'TRL 4: ≤ 5; TRL 5: ≤ 3', 'P3: loguri de tastare'],
    ['I5', 'H2', 'Diacritice RO corecte automat', '%', 'TRL 4: ≥ 90; TRL 5: ≥ 95', 'P4: corpus de 300 de cuvinte RO'],
    ['I6', 'H3', 'Comenzi executate corect fără internet', '%', 'TRL 4/5: ≥ 90', 'P5: corpus de 200 de comenzi RO/EN; comenzile reale din teren'],
    ['I7', 'H3', 'Latența vocală end-to-end (p50 / p90)', 's', 'TRL 4: ≤ 1,8 / ≤ 3; TRL 5: ≤ 1,5 / ≤ 2,5', 'P6: 100 de ture, Wi-Fi casnic, servere UE'],
    ['I8', 'H3', 'Scenarii de cădere fără blocare / sesiuni fără crash', '%', '100 / ≥ 99', 'P7: 50 de scenarii; telemetrie TRL 5'],
    ['I9', 'H4', 'Atenuarea RSSI prin carcasă', 'dB', 'TRL 4: ≤ 8 (rev A); TRL 5: ≤ 6 (rev B)', 'P8: cutie ecranată + 1/3/5/10 m, 3 configurații'],
    ['I10', 'H4', 'PDR BLE la 10 m în interior / timp de reconectare', '% / s', '≥ 99 / ≤ 3', 'P8: pachete pierdute, reconectări'],
    ['I11', 'H4', 'Depășiri la pre-scan EMC/RF / marjă', 'nr. / dB', '0 / ≥ 3 (rev B)', 'P11: laborator acreditat, EN 300 328, EN 301 489-1/-17'],
    ['I12', 'H5', 'Autonomie în profil tipic / standby', 'h / zile', 'TRL 4: model validat ± 15 %; TRL 5: ≥ 24 h / ≥ 7 zile', 'P9: analizor de consum, profil tipic definit'],
    ['I13', 'H5', 'Timp de înlocuire a bateriei de către utilizatori neexperți', 'min', 'TRL 4: ≤ 10 (N = 3); TRL 5: ≤ 5, 100 % reușită (N ≥ 10)', 'P10: cronometrare'],
    ['I14', 'H5', 'Scorul de utilizabilitate SUS', 'puncte (0–100)', 'TRL 5: ≥ 75', 'P10: chestionar SUS'],
]
fill_rows(t, 2, ind)
t = B[93]
drop_rows(t, 0)
res = [
    ['R1', 'Model de laborator SOUL M validat la TRL 4 + Raport de validare TRL 4 (L14)', 'TRL 3: funcții pe componente separate; baseline fps/touch/WPM/offline/latență din X2–X6 [[în curs]]', 'TRL 4: pragurile O1 (fps ≥ 30, touch ≥ 97 %, WPM ≥ 15, offline ≥ 90 %, p50 ≤ 1,8 s, 8/8 protocoale)'],
    ['R2', '15 prototipuri SOUL M pre-serie validate la TRL 5 + Raport TRL 5 + raport de pre-testare EMC/RF (L22)', '0 prototipuri cu PCB propriu și carcasă Al; atenuare orientativă prin tablă din X7 [[în curs]]', 'TRL 5: 15/15 funcționale; WPM ≥ 20, UER ≤ 3 %; p50 ≤ 1,5 s; offline ≥ 90 %; ≥ 99 % sesiuni fără crash; ≤ 6 dB; ≥ 24 h; SUS ≥ 75; 0 depășiri'],
    ['R3', '2 cereri de protecție IP depuse (desen/model industrial UE; marcă UE) + raport de brevetabilitate (L18)', '0 cereri depuse', '2 cereri EUIPO (design ≤ L5, marcă ≤ L6) + 1 raport de brevetabilitate'],
    ['R4', 'Publicație științifică open-access peer-review + comunicare la conferință (L20–L24)', '—', '≥ 1 manuscris trimis la o revistă OA peer-review (≤ L20) + preprint Zenodo + 1 comunicare la o conferință'],
    ['R5', 'Plan de valorificare + ≥ 2 acorduri de pilot/distribuție (L24)', 'scrisori de intenție la depunere', 'plan de comercializare + ≥ 2 acorduri semnate'],
]
fill_rows(t, 1, res)

delete(B[96])
put(B[97], [
    '**Impact tehnologic:** o arhitectură de referință, verificată prin măsurători publicate, pentru dispozitive AI tangibile local-first pe MCU de cost redus (randare procedurală, text pe ecrane rotunde, degradare controlată, RF prin carcasă metalică) — transferabilă către alte produse din IoT de consum și accesibilitate.',
    '**Impact asupra pieței:** un produs UE-first, cu IP protejat, pe un segment validat comercial (Plaud, Fuzozo, campaniile de crowdfunding) dar lipsit de soluții independente de cloud; traseu către certificarea CE în An 1 și 7.000 de unități/an în An 5 post-proiect [E] (Planul de afaceri, §6).',
    '**Contribuția la RIS3 BI:** consolidează în București competențe în sisteme embedded, HCI, RF și securitate cibernetică (TIC) și în sisteme ciber-fizice (Sisteme și Componente Inteligente); implică un student ETTI/ACS, o organizație de cercetare, laboratoare și ateliere regionale și un panel de utilizatori din BI.',
    '**Contribuția la obiectivele UE și la reducerea dependențelor strategice:** asistentul nu e legat de un singur furnizor extra-UE (BYO-AI, parser local, servere UE, server publicabil/escrow); datele rămân în UE (GDPR); produsul aplică de la proiectare Reg. (UE) 2023/1542 (baterie înlocuibilă), Dir. (UE) 2024/1799 (reparabilitate), EN 18031 (securitate) și AI Act art. 50 (transparență).',
    '**Diseminare (Grila 1.4):** articol trimis la o revistă open-access peer-review indexată [[Cl: revista țintă — ex. MDPI Electronics / Sensors sau IEEE Access; captura paginii de APC]] (APC bugetat, linia 21) după depunerea cererilor IP (regula „întâi protecția, apoi publicarea”: design ≤ L5, marcă ≤ L6, trimitere ≤ L20); preprint și setul de date anonimizat în Zenodo (repozitoriu OA); o comunicare la o conferință/târg internațional (linia 22); demo public.',
])

# ---------------------------------------------------------------- VII
t = B[100]
for tr in rows(t):
    if ptext(tr).strip().startswith('✏'):
        delete(tr)
refs_txt = [f'[{r[0]}] {r[2]} ({r[3]}). {r[1]}. {r[4]}.' for r in REFS]
put(B[102], ['**Publicații științifice recente (≤ 5 ani; DOI verificate la 25.09.2026):**'] + refs_txt +
    ['**Repere mai vechi (baseline, nu sunt socotite „recente”):**'] + ['- ' + x for x in REFS_BASELINE] +
    ['**Acte normative și standarde:**'] + ['- ' + x for x in NORMS] +
    ['**Surse de piață și context (link, dată):**'] + [f'- {a} — {u}' for a, u in MARKET_SOURCES[:8]])
put(B[104], [
    '- D1 — depozitul git, `micul-smecher/firmware/` (README, test/test_suflet: 61 de teste Unity), commit b84f714 din 25.09.2026 [[A: export + hash la data depunerii]].',
    '- D2 — `firmware/sim` + `media/` (clipurile simulatorului, MP4/GIF).',
    '- D3 — `micul-smecher/ai/` (README, tests/: 49 de teste pytest).',
    '- D4 — `os/index.html`, `os/SPEC.md`, `os/ARCHITECTURE.md`, `os/research/04` (prototipul web SoulOS).',
    '- D5 — `research/12-ecran-mai-mare.md` §1–2 (geometria tastaturii, alegerea panoului).',
    '- D6 — `prototip/`, `cad/`, `renders/` (CAD CadQuery, STL/STEP, randări).',
    '- D7 — export `git log` cu datele commit-urilor (primul commit SOUL: 24.09.2026).',
    '- D8 — „Raport de laborator TRL 3 — SOUL M (2.8C)”, X1–X8 [[în curs; se anexează înainte de depunere]].',
    '- Benchmark-ul celor 24 de competitori (research 11) și studiile research 01, 04 (anexe).',
])

# ---------------------------------------------------------------- VIII
t = B[114]
fill_row(rows(t)[1], ['1', '[[Nume Prenume — expert/coordonator colectiv]]', 'Expert independent [[sau membru colectiv]]', None, None])
fill_row(rows(t)[2], ['2', '[[Nume Prenume — dacă e cazul]]', '[[Calitate]]', None, None])
fill_row(rows(t)[3], ['3', '[[Nume Prenume — dacă e cazul]]', '[[Calitate]]', None, None])
after(t, ['**Solicitant** (elaborează raportul și răspunde de conținut): ARTEMIS DIGITAL S.R.L., prin [[Nume Prenume]], administrator — semnătură: ________________ data: [[ZZ/LL/AAAA]]'])
last_li = B[121]
for txt in ['Raportul de laborator TRL 3 — SOUL M (2.8C) cu rezultatele X1–X8, loguri, fotografii, video cu marcaj de timp și hash git (dovada D8).',
            'Contractul de cesiune a drepturilor autorului către ARTEMIS DIGITAL S.R.L. și declarația privind componentele open-source și licențele lor.']:
    n = clone_par(last_li, txt, keep_num=True)
    last_li.addnext(n); last_li = n

import re as _re
for tbl in d.element.body.iter(W('tbl')):
    pass
for idx, wd in [(27, [450, 2400, 1500, 750, 2200, 2780]), (47, [600, 1800, 3700, 1000, 2980]), (64, [500, 2600, 3200, 2000, 1780]),
                (67, [500, 2500, 1400, 3300, 2380]), (82, [700, 4300, 1300, 1400, 2380]), (44, [1800, 3600, 4680]), (100, [10080]), (87, [600, 5200, 4280]),
                (90, [600, 900, 2600, 1100, 2300, 2580]), (93, [600, 3000, 2900, 3580]), (33, [600, 3000, 2900, 900, 2680]),
                (8, [500, 2300, 2000, 2000, 3280])]:
    tb = B[idx]
    normalize_table(tb, wd)
finalize(d)
d.save(OUT)
print('saved', OUT)
