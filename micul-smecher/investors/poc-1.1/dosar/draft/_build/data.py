# -*- coding: utf-8 -*-
"""Single source of truth for the generated drafts (Anexa 3, Anexa 16, models). Mirrors dosar/03-NUCLEU-PROIECT.md.
Updated 2026-10-12 to the current facts (Jurnal decizii, SOUL — Harta memoriei, docs/00, 07, 10, firmware/PERF.md, os/DESIGN-ALIVE.md).
2026-10-22: product = size S (decision 2026-10-20; docs/size-s.json, docs/12-SIZE-S.md, firmware/SOUL-S.md). Size M (Waveshare 2.8C) stays
ONLY as the TRL 3 bench prototype (D8, X1–X8).
Change here AND in 03-NUCLEU, then rebuild (see README in this folder)."""

# ---- applicant (certificat ONRC + ANAF, verificat de fondator 12.10.2026)
CUI = '53145290'
REGCOM = 'J2025098748009'
EUID = 'ROONRC.J2025098748009'
DATA_INREG = '17.12.2025'
SEDIU = 'Str. Vlăhița nr. 1, bl. PM18bis, sc. 2, ap. 123, Sector 3, București'
CAEN_PRINCIPAL = '7311 — Activități ale agențiilor de publicitate'
CAEN_DE_ADAUGAT = ('2640 (electronice de larg consum), 6210 (programare), 7210 (cercetare-dezvoltare în științe naturale și inginerie), '
                   '7411 (design industrial), 4740 (comerț cu echipamente TIC) [[Ct: de adăugat la ONRC înainte de depunere; '
                   'lista nu e reverificată pe CAEN Rev.3; 4791 „vânzare online” e de verificat, în Rev.3 se pare că nu mai descrie canalul online]]')
TVA = 'neplătitoare de TVA (ANAF, 12.10.2026)'
DIMS = '~63 × 70,8 × 23 mm'        # SOUL S, the product (docs/size-s.json; 23,0 mm = ținta de adâncime aleasă în docs/12 §2.4)
DIMS_M = '~90 × 101 × 31,5 mm'     # SOUL M = DOAR prototipul de banc TRL 3 (placa 2.8C, D8, X1–X8)
SCREEN_S = 'afișaj rotund AMOLED 1,75″ 466×466'
BATT_S = 'LiPo 750 mAh (603040)'
LIFE_S = '~27 h [estimare] (interval 21–34 h; docs/12 §2.5)'
PRET = 'de la 249 €'
FW = 'SoulOS 1.9.1 „Alive”'   # 1.9.1 = commit fe9fbe4, 22.10.2026; Alive first shipped in 1.9.0 = commit 52689e4, 12.10.2026
FW_TESTS = '245'   # pio test -e native, 1.9.1, 22.10.2026 (firmware/release/README.md) (firmware/SOUL-S.md: both audits run on M and on S)
CLOUD_TESTS = '283'

# ---- AI wording (decision 03.10.2026): only Claude works today; ChatGPT own-key is in development, "Sign in with ChatGPT" awaits OpenAI.
AI_OWN = 'Claude, cu contul sau cheia proprie; în curând și ChatGPT, cu cheie proprie — în lucru'

# ---- RELEASE GATE (TRL 3). Anexa 18: TRL 3 = stadiul experimental, cu măsurători inițiale de laborator; simularea doar completează
# experimentul fizic. Până când D8 (raportul de laborator TRL 3 pe placa 2.8C, X1–X8 filmate) există, TRL 3 se scrie „de atestat după D8”
# și Anexa 16 NU se semnează. Set D8_DONE = True only when the dated, signed TRL 3 lab report + video exist.
D8_DONE = False
TRL3_STATUS = 'atestat prin Raportul științific (Anexa 16), dovezile D1–D8' if D8_DONE else 'de atestat după D8 (raportul de laborator pe placa 2.8C, în curs)'


def release_gate(for_signature):
    """Refuse to build a for-signature Anexa 16 while D8 is still in progress."""
    if for_signature and not D8_DONE:
        raise SystemExit('RELEASE GATE: D8 (raportul de laborator TRL 3, X1–X8 pe placa 2.8C) e „în curs” — '
                         'Anexa 16 nu se poate genera pentru semnare. Setați D8_DONE = True în data.py doar după ce raportul există.')


# ---- public disclosure (GitHub API 12.10.2026: repo KREA123/obsidian-vault, visibility "public", creat 24.09.2026, fără PublicEvent
# => public de la creare). Dates from git (first commit of each path).
REPO_PUBLIC = 'github.com/KREA123/obsidian-vault'
PUBLIC_SINCE = '24.09.2026'
FIRST_PUB = ('randările SOUL din 24.09.2026 (forma MĂRGĂRITAR v9 din 26.09.2026); decodorul tastaturii '
             '(`firmware/lib/Suflet/src/Predictor.cpp`, `Keyboard.cpp`) și conceptul ferestrei radio (`research/10-carcasa-aluminiu.md`) din 25.09.2026; '
             'motorul ochilor din 24.09.2026 și restul firmware-ului din sept.–oct. 2026; acest dosar')
DESIGN_DEADLINE = '24.09.2027'


APPLICANT = 'ARTEMIS DIGITAL S.R.L.'
ACRONIM = 'SOUL-PoC'
TITLU = ('SOUL — dispozitiv AI tangibil, local-first, cu interfață circulară și carcasă reparabilă din aluminiu: '
         'validarea modelului conceptual de la TRL 3 la TRL 5')
TITLU_EN = ('SOUL — a tangible, local-first AI interaction device with a circular interface and a repairable '
            'aluminium enclosure: proof of concept from TRL 3 to TRL 5')
RIS3 = ('1. Tehnologia Informației și Comunicațiilor (TIC); 2. Sisteme și Componente Inteligente '
        '[[Cl: subdomeniile exacte din RIS3 BI 2021–2027, după descărcarea strategiei de pe adrbi.ro]]')
# TOTAL (the eligible total, e.g. '191.240 €') is computed from the budget lines below.

OBJ_GENERAL = ('validarea modelului conceptual SOUL (dispozitiv AI tangibil, local-first, cu interfață circulară și '
               'carcasă reparabilă) de la TRL 3 la TRL 5, în 24 de luni, la București.')

# code, objective, indicator, deadline, activities, result
OBJECTIVES = [
    ('O1', 'Realizarea și validarea în laborator (TRL 4) a modelului integrat SOUL S (afișaj rotund AMOLED 1,75″ 466×466 + touch + IMU + audio cu 2 microfoane și difuzor + baterie LiPo 750 mAh + AI la alegerea proprietarului)',
     'fps median ≥ 30 · precizie touch ≥ 97 % · WPM ≥ 15 (N = 6) · succes offline ≥ 90 % · latența unui tur AI p50 ≤ 1,8 s · 8/8 protocoale rulate',
     'L14', 'A1, A2, A3 (CDI I.3)', 'R1 Raport TRL 4'),
    ('O2', 'Proiectarea și realizarea a 15 prototipuri pre-serie cu PCB propriu și carcasă CNC din aluminiu (forma MĂRGĂRITAR) cu baterie înlocuibilă',
     '15/15 unități funcționale · atenuare RSSI ≤ 6 dB · înlocuirea bateriei ≤ 5 min · autonomie ≥ 24 h (profil tipic)',
     'L17', 'A4 (CDI I.3/I.4)', 'R2 (partea 1)'),
    ('O3', 'Validarea în mediu relevant (TRL 5) cu ≥ 12 utilizatori timp de 4 săptămâni + pre-testare EMC/RF',
     'WPM ≥ 20 și UER ≤ 3 % · latența unui tur AI p50 ≤ 1,5 s / p90 ≤ 2,5 s · succes offline ≥ 90 % · ≥ 99 % sesiuni fără crash · SUS ≥ 75 · 0 depășiri la pre-scan (marjă ≥ 3 dB)',
     'L22', 'A5 (CDI I.3)', 'R2 Raport TRL 5'),
    ('O4', 'Protejarea și valorificarea rezultatelor',
     'cerere de design EUIPO pentru forma MĂRGĂRITAR depusă înainte de ' + DESIGN_DEADLINE + ' (în afara bugetului) · cerere de design pentru elementele noi, nepublicate, din proiect (≤ L18) · cerere de marcă (≤ L6) · 1 articol OA peer-review trimis (≤ L20) · ≥ 2 acorduri de pilot/distribuție + plan de comercializare (L24)',
     'L24', 'A6, A7 (CDI I.2/I.4 + conex II.1)', 'R3, R4, R5'),
]

RESULTS = [
    ('R1', 'Model de laborator SOUL S validat la TRL 4 + Raport de validare TRL 4', 'L14'),
    ('R2', '15 prototipuri SOUL S pre-serie validate la TRL 5 în mediu relevant + Raport TRL 5 + raport de pre-testare EMC/RF', 'L22'),
    ('R3', '2 cereri de protecție IP depuse în proiect (marcă UE; desen/model industrial UE pentru elementele noi din proiect) + raport de brevetabilitate limitat la soluțiile nepublicate', 'L18'),
    ('R4', '1 articol științific trimis la o revistă open-access peer-review + 1 comunicare la o conferință', 'L20–L24'),
    ('R5', 'Plan de valorificare comercială + ≥ 2 acorduri de pilot/distribuție semnate', 'L24'),
]

# code, name, type, months, subactivities, deliverables
ACTIVITIES = [
    ('A0', 'Pregătirea CF, a Planului de afaceri, a Raportului științific + validarea de către expert', 'Conex II.2, precontractuală',
     'înainte de depunere', '–', 'CF, Anexa 3, Anexa 16 semnată'),
    ('A1', 'Specificații, protocoale experimentale, setup de laborator', 'CDI I.3 (+ I.1 echipamente)', 'L1–L3',
     '1.1 specificația sistemului S; 1.2 protocoalele P1–P10 cu praguri; 1.3 achiziția aparatelor de măsură și a PC-ului; 1.4 bancul de test (cutie ecranată, analizor de consum)',
     'L1.1 Specificație; L1.2 Protocoale; M1 Banc de test validat (L3)'),
    ('A2', 'Modelul de laborator S integrat: SoulOS pe ESP32-S3 (placa Waveshare ESP32-S3-Touch-AMOLED-1.75: AMOLED rotund 1,75″ 466×466 CO5300 pe QSPI, touch CST9217, IMU QMI8658, RTC PCF85063, PMU AXP2101), audio pe placă (2 microfoane MEMS, codecuri ES7210 + ES8311, difuzor), baterie LiPo 750 mAh (603040), carcasă SLA la scara S (~63 × 70,8 × 23 mm), comenzi vocale offline EN (ESP-SR), conectarea AI-ului proprietarului (cheie proprie, conectorul Claude prin SOUL Cloud în UE, SOUL Bridge), memoria SOUL Memory pe dispozitiv',
     'CDI I.3 + materiale', 'L2–L8',
     '2.1 firmware afișaj/touch/IMU pe placa AMOLED-1.75; 2.2 subsistem audio ES8311/ES7210 + comenzi vocale offline; 2.3 alimentare, încărcare, consum; 2.4 carcasă SLA; 2.5 SOUL Cloud în UE (pairing, gateway, conector MCP) + SOUL Memory; 2.6 integrare',
     'L2.1 Model de laborator funcțional; IE1 (L6): raport intermediar CDI'),
    ('A3', 'Validarea TRL 4 în laborator (protocoalele P1–P8) + analiza rezultatelor + raportul de etapă TRL 4', 'CDI I.3', 'L6–L14',
     '3.1 teste de componente; 3.2 teste de sistem; 3.3 studiu de tastare N = 6; 3.4 analiză + decizie de poartă',
     'R1 Raport TRL 4 (L14) = IE2; decizia go/no-go TRL 5'),
    ('A4', 'Prototipul pre-serie SOUL S: PCB propriu rotund ~46 mm (ESP32-S3-WROOM-1-N16R8, panou AMOLED 1,75″ 466×466 gol, CO5300/QSPI, touch, QMI8658, RTC, PMU clasa AXP2101, codecuri ES8311 + ES7210, 2 microfoane MEMS, difuzor, încărcare, pini pentru capsula OU) [estimare: arhitectura EVT din docs/12 §1.2], antenă prin fereastră polimerică, carcasă CNC Al 6061 anodizată, forma MĂRGĂRITAR, rev A (3 seturi) și rev B (5 + 15 seturi), baterie înlocuibilă, capsula OU; securitatea EN 18031 (secure boot, OTA semnat)',
     'CDI I.3/I.4 + servicii', 'L9–L17',
     '4.1 schema și layout rev A (L9–L11); 4.2 fabricare + test rev A (L11–L13); 4.3 antenă + RF (serviciu extern); 4.4 după poarta L14: rev B + lotul de 15 carcase; 4.5 asamblare și QC',
     'L4.1 PCB rev A testat; M3 15 prototipuri (L17)'),
    ('A5', 'Validarea TRL 5 în mediu relevant: 15 unități la 12–15 utilizatori din BI (case, birouri, un living lab), 4 săptămâni, telemetrie opt-in; fiecare participant folosește modul offline și propriul AI (cont Anthropic/OpenAI propriu; cine nu are cont primește o cheie de test a proiectului cu limită de cost, doar pe durata testului); protocoalele P1–P10; 2 workshop-uri de testare; pre-testare EMC/RF (2 sesiuni)',
     'CDI I.3 + servicii de testare', 'L16–L22',
     '5.1 recrutarea panelului (≥ 40 % femei, ≥ 2 persoane cu deficiențe de vedere/motorii); 5.2 teren; 5.3 pre-scan; 5.4 analiza + raportul TRL 5',
     'R2 Raport TRL 5 (L22) = IE3'),
    ('A6', 'Protecția IP și valorificarea: căutare de anteriorități (L1–L3), marcă UE (≤ L6), design UE pentru elementele noi din proiect (≤ L18; forma MĂRGĂRITAR, deja publică, se depune înainte de ' + DESIGN_DEADLINE + ', în afara bugetului), evaluarea brevetabilității doar pentru soluțiile nepublicate (L12–L18); customer discovery (≥ 30 de interviuri), transformarea scrisorilor de intenție în acorduri, planul de comercializare',
     'CDI I.2/I.4 + conex II.1', 'L1–L24', '–', 'R3 (L18), R5 (L24)'),
    ('A7', 'Diseminare: manuscris (după depunerea cererilor IP pentru elementele nepublicate), trimitere la o revistă OA peer-review (≤ L20), preprint în repozitoriu OA (Zenodo), prezentare la o conferință/târg, demo public',
     'Conex II.1', 'L14–L24', '–', 'R4'),
    ('A8', 'Management, audit financiar, comunicare și vizibilitate', 'Conex II.3, II.4, II.5', 'L1–L24', '–',
     'rapoarte de progres, raport de audit, afiș/panou, comunicate'),
]

GANTT = [
    ('A1 Specificații, protocoale, setup laborator', range(1, 4)),
    ('A2 Model de laborator S integrat', range(2, 9)),
    ('A3 Validare TRL 4 + raport TRL 4', range(6, 15)),
    ('A4 PCB propriu + carcasă Al, pre-serie', range(9, 18)),
    ('A5 Validare TRL 5 în mediu relevant + pre-scan', range(16, 23)),
    ('A6 Protecție IP + valorificare', range(1, 25)),
    ('A7 Diseminare', range(14, 25)),
    ('A8 Management, audit, vizibilitate', range(1, 25)),
]
DEPENDENCIES = ('Dependențe: A2 depinde de M1 (L3). A3 depinde de L2.1. Rev B și lotul de 15 din A4 depind de poarta IE2 (L14). '
                'A5 depinde de M3 (L17). Manuscrisul din A7 se trimite după depunerea cererilor IP pentru elementele nepublicate (A6).')

MILESTONES = [
    ('M1', 'Banc de test validat', 'A1', 'L3', 'aparatele recepționate și calibrate; protocoalele P1–P10 aprobate de coordonator', 'management/CDI'),
    ('IE1', 'Raport intermediar CDI: modelul de laborator rulează integrat', 'A2', 'L6 (≤ 6 luni)', 'afișaj + touch + audio + AI funcționale; primele măsurători P1, P2, P5', 'calitativ CDI (obligatoriu)'),
    ('IE2', 'Raportul de etapă TRL 4 + obiectivele TRL 5', 'A3', 'L14 (≤ 2/3 = L16)', 'pragurile O1 atinse sau abaterile motivate; decizia go/no-go; dacă e no-go → Anexa 17 (eșec de cercetare)', 'calitativ CDI (obligatoriu)'),
    ('M3', '15 prototipuri pre-serie', 'A4', 'L17', 'QC trecut 15/15', 'CDI'),
    ('IE3', 'Raportul TRL 5', 'A5', 'L22', 'pragurile O3 atinse', 'calitativ CDI'),
    ('IE-M1..M3', 'Achiziții (L4, L15), progres financiar (≥ 30 % la L10, ≥ 70 % la L18), cerere de marcă depusă (L6)', 'A6, A8', 'L4–L18', '–', 'management'),
]

HYP = [
    ('H1', 'Randare', 'Dacă motorul de randare SDF anti-aliased rulează pe ESP32-S3 cu framebuffer în PSRAM și trimite doar regiunile modificate pe QSPI către AMOLED-ul 1,75″ 466×466 (CO5300, cu memorie de cadru proprie), atunci animația ochilor (31 de expresii) menține median ≥ 30 fps (p5 ≥ 24) cu Wi-Fi și BLE active, fără artefacte de drift. Baseline-ul TRL 3 se măsoară pe prototipul M (panou RGB ST7701 480×480, bounce-buffers; X2), iar estimarea pe S e în firmware/PERF.md [estimare].',
     'Poate un MCU de ~10 € să randeze procedural, fluid, o interfață expresivă pe un panou RGB fără memorie proprie, în paralel cu radioul?'),
    ('H2', 'Tastare/touch', 'Dacă tastatura circulară (pe S: 5 rânduri de taste de 5,1 mm, alfabetică, fiecare rând cât încape în cerc — decizia din os/DESIGN-ALIVE.md; reperul de pe prototipul M: QWERTY circular, pas ≈ 0,0944·D → 6,7 mm pe Ø70, taste de margine „stăpâne” pe bordură) este combinată cu decodare probabilistică și diacritice RO automate, atunci utilizatorii ating ≥ 20 WPM cu UER ≤ 3 % și ≥ 97 % precizie touch.',
     'Este introducerea de text direct pe un ecran rotund de 1,75″ suficient de rapidă și precisă pentru notițe și comenzi reale, în română și engleză?'),
    ('H3', 'AI la alegerea proprietarului, offline-first', 'Dacă acțiunile utilizatorului sunt descrise printr-un singur set de scheme JSON, executate offline (parser local RO/EN și comenzi vocale offline EN, ESP-SR) sau de AI-ul conectat de proprietar (Claude, cu cheia lui sau prin conectorul din aplicația Claude; ChatGPT, cu cheia lui), cu degradare controlată și cu o memorie portabilă păstrată pe dispozitiv (SOUL Memory), atunci ≥ 90 % din comenzi se execută corect fără internet, un tur AI are latența p50 ≤ 1,5 s (p90 ≤ 2,5 s), 100 % din căderile de rețea/cheie sunt tratate fără blocare și memoria se păstrează integral la schimbarea AI-ului.',
     'Poate un dispozitiv să rămână util offline și rapid online, independent de un singur furnizor de AI și fără să includă sau să revândă AI?'),
    ('H4', 'RF prin aluminiu', 'Dacă antena BLE/Wi-Fi 2,4 GHz radiază printr-o fereastră polimerică în talpa unei carcase CNC din Al 6061, atunci atenuarea față de placa neîncasetată este ≤ 6 dB, legătura BLE rămâne stabilă ≥ 10 m în interior (PDR ≥ 99 %, reconectare ≤ 3 s) și pre-scanul EMC/RF nu are depășiri (marjă ≥ 3 dB).',
     'Se poate folosi o carcasă monomaterial din aluminiu (premium, reciclabilă) fără a compromite legătura radio?'),
    ('H5', 'Energie și reparabilitate', 'Dacă afișajul AMOLED (negru adevărat, fără lumină de fundal; ochii stau pe negru, iar memoria de cadru a panoului permite somnul ușor al CPU-ului între cadre), somnul radioului și CPU-ului și bateria LiPo de 750 mAh (603040) sunt integrate într-o arhitectură cu baterie înlocuibilă de utilizator (conector MX1.25, Torx, fără adeziv), atunci autonomia în profil tipic este ≥ 24 h (estimarea de pornire: ~27 h [estimare], interval 21–34 h; docs/12 §2.5), iar utilizatori neexperți înlocuiesc bateria în ≤ 5 min cu 100 % reușită și SUS ≥ 75.',
     'Poate un obiect premium de ~63 × 71 × 23 mm, cu ecran AMOLED rotund de 1,75″ și o baterie de 750 mAh, să aibă o zi întreagă de autonomie și baterie schimbabilă de utilizator (Reg. (UE) 2023/1542 art. 11)?'),
]

# code, protocol, hyp, method, baseline, trl4, trl5
PROTOCOLS = [
    ('P1', 'fps la animația ochilor', 'H1', 'contor de cadre în firmware, log serial/telemetrie; 60 min; Wi-Fi + BLE active; toate cele 31 de expresii', 'X2', 'median ≥ 30 fps, p5 ≥ 24', 'median ≥ 30, p5 ≥ 24 pe 15 unități; 0 artefacte de drift raportate'),
    ('P2', 'Precizia touch', 'H2', 'grilă de ținte de 5,1 mm (tasta S) pe tot discul, inclusiv bordura, pe SOUL S; 200 de atingeri/persoană (baseline TRL 3: ținte de 6,7 mm pe prototipul M, X3)', 'X3', '≥ 97 % (N = 6)', '≥ 97 % (N ≥ 12)'),
    ('P3', 'Viteza și acuratețea tastării', 'H2', 'set de fraze MacKenzie–Soukoreff (EN) + set RO; 15 min de acomodare; WPM, UER, CER', 'X4', '≥ 15 WPM, UER ≤ 5 % (N = 6)', '≥ 20 WPM, UER ≤ 3 % (N ≥ 12)'),
    ('P4', 'Diacritice RO automate', 'H2', 'corpus de 300 de cuvinte RO', '–', '≥ 90 % corecte', '≥ 95 % corecte'),
    ('P5', 'Succesul offline (text și voce)', 'H3', 'corpus de 200 de comenzi RO/EN scrise (alarme, mementouri, notițe, cronometre, liste) + 100 de comenzi vocale EN (ESP-SR, pe unitățile cu microfon), fără internet', 'X5', '≥ 90 %', '≥ 90 % pe comenzile reale din teren'),
    ('P6', 'Latența unui tur AI end-to-end', 'H3', 'de la trimiterea întrebării pe SOUL la începutul răspunsului pe ecran; 100 de ture; Wi-Fi casnic; AI-ul proprietarului (Claude/ChatGPT), direct cu cheia proprie sau prin SOUL Cloud (UE)', 'X6', 'p50 ≤ 1,8 s, p90 ≤ 3 s', 'p50 ≤ 1,5 s, p90 ≤ 2,5 s'),
    ('P7', 'Degradarea controlată + portabilitatea memoriei', 'H3', 'se taie rețeaua sau cheia API în 50 de scenarii; se schimbă AI-ul conectat în 10 scenarii (Claude ↔ ChatGPT ↔ offline)', '–', '100 % fără blocare; răspuns local; 100 % din memorie păstrată', '100 %; ≥ 99 % sesiuni fără crash (telemetrie); 100 % din memorie păstrată'),
    ('P8', 'RF prin carcasă', 'H4', 'RSSI în cutia ecranată și la 1/3/5/10 m: placă goală vs. SLA vs. Al rev A/B; pachete pierdute BLE', 'X7', 'atenuare ≤ 8 dB (rev A)', '≤ 6 dB (rev B); legătură stabilă ≥ 10 m în interior; PDR ≥ 99 %; reconectare ≤ 3 s'),
    ('P9', 'Autonomie și consum', 'H5', 'analizor de consum; profil tipic definit (ecran activ ~1 h/zi, ecran stins/somn restul zilei, 50 de întrebări AI, BLE conectat); baterie LiPo 750 mAh (603040) pe S, estimare ~27 h [estimare]; baseline TRL 3: consumul prototipului M (2.8C, 1500 mAh) din X8', 'X8', 'modelul de consum validat ± 15 %', '≥ 24 h în profil tipic'),
    ('P10', 'Reparabilitate + utilizabilitate', 'H5', 'cronometrarea înlocuirii bateriei (Torx) de către utilizatori neexperți; chestionar SUS; test de accesibilitate (voce, modul „taste mari”, contrast)', '–', 'procedura documentată; ≤ 10 min (N = 3)', '≤ 5 min, 100 % reușită (N ≥ 10); SUS ≥ 75'),
    ('P11', 'Pre-scan EMC/RF (EN 300 328, EN 301 489-1/-17)', '–', 'laborator acreditat, 2 sesiuni (rev A, rev B)', '–', '–', '0 depășiri, marjă ≥ 3 dB (rev B)'),
]

RELEVANT_ENV = ('Mediul relevant la TRL 5 (Anexa 18): configurația e „similară aplicației finale în aproape toate aspectele” '
                '(PCB propriu, carcasă finală din aluminiu, baterie finală, firmware SoulOS + SOUL Cloud găzduit în UE) și rulează în condițiile reale de '
                'utilizare (locuințe și birouri din BI, rețele Wi-Fi casnice, zgomot ambiental, utilizatori reali), completate cu '
                'reproducerea controlată în laborator (cutie ecranată, atenuare calibrată). Diferențele față de produsul final (fără '
                'certificare CE, fără ambalaj, fără producție în serie) se analizează explicit în raportul TRL 5.')
ETHICS = ('Etică și date: consimțământ informat, telemetrie opt-in, pseudonimizare, ștergerea datelor la final, fără înregistrarea '
          'audio brută (comenzile vocale offline se recunosc pe dispozitiv), export și ștergere a contului la cerere (GDPR). '
          'Informare AI Act art. 50 la prima pornire. Participanții își folosesc propriul AI; produsul nu include AI.')

DELIVERABLES = [
    ('L1.1', 'Specificația sistemului SOUL S', 'A1', 'L2', 'coordonator tehnic'),
    ('L1.2', 'Protocoalele experimentale P1–P11 cu praguri', 'A1', 'L3', 'coordonator tehnic'),
    ('L2.1', 'Modelul de laborator integrat + raportul IE1', 'A2', 'L6', 'inginer embedded'),
    ('R1', 'Raportul de validare TRL 4', 'A3', 'L14', 'coordonator tehnic'),
    ('L4.1', 'Documentația PCB rev A/B (scheme, Gerber, BOM) + CAD-ul carcasei rev B', 'A4', 'L12 / L16', 'inginer embedded'),
    ('L4.2', '15 prototipuri pre-serie + fișele QC', 'A4', 'L17', 'echipa'),
    ('L5.1', 'Rapoartele de pre-testare EMC/RF', 'A5', 'L18 / L21', 'laborator + coordonator'),
    ('R2', 'Raportul de validare TRL 5 (+ setul de date anonimizat)', 'A5', 'L22', 'coordonator tehnic'),
    ('R3', 'Cererile IP din proiect (marcă UE, design UE pentru elementele noi) + raportul de brevetabilitate', 'A6', 'L6 / L18', 'Andu + consilier PI'),
    ('R4', 'Manuscris trimis OA peer-review + preprint + prezentare la conferință', 'A7', 'L20 / L24', 'coordonator + student'),
    ('R5', 'Planul de valorificare + ≥ 2 acorduri', 'A6', 'L24', 'Andu'),
]

# nr, line, category, activity, eur (int, € cu TVA). Subtotals, indirects, total and checks are COMPUTED below — edit only the lines.
# 12.10.2026: prices aligned to the verified offers note (01 Afaceri/Micul Șmecher/Finanțare — oferte de preț pentru PoC 1.1):
# L5 Rigol DHO924S (rigolshop.eu 719 net; RONEXPRIM 5.102 lei cu TVA) · L6 Siglent SSA3032X Plus (Welectron/Batronix 2.439 net) ·
# L7 Joulescope JS320 (Welectron 878 net; JS220 discontinued) · L14 ZUT Szczecin EMC ≈ 9.800 PLN net/sesiune × 2 + radio EN 300 328 [E] ·
# L19 EUIPO fees (marcă 850+50+150; design 350+125) · L21 Frontiers APC CHF 2.195 · L23 focusgrupuri.ro 850 €/grup × 2.
# Rebalanced from L17 (least justified: only the room has a price, ≈ 250–300 € for 2 days): 2.500 -> 1.500.
PRICED_LINES = '5, 6, 7, 19, 21, 23'  # lines resting on verified public prices (12.10.2026); the rest stay [E] until the offers arrive
JOURNAL = ('Frontiers in Robotics and AI (APC CHF 2.195 ≈ 2.349 € fără TVA, bugetat în linia 21; alternative verificate: '
           'IEEE Access, JMIR Human Factors)')
_SEC_I, _SEC_II1, _SEC_II2 = 'I', 'II.1', 'II.2–II.5'
_LINES = [
    (_SEC_I, '1', 'Salariu coordonator tehnic/științific (1.200 h × 34 €)', 'Cheltuieli salariale CDI (I.3)', 'A1–A5, A7', 40800),
    (_SEC_I, '2', 'Salariu inginer embedded/firmware (1.680 h × 25 €)', 'Cheltuieli salariale CDI (I.3)', 'A2–A5', 42000),
    (_SEC_I, '3', 'Salariu student cercetare (1.200 h × 12 €)', 'Cheltuieli salariale CDI (I.3)', 'A3, A5, A7', 14400),
    (_SEC_I, '4', 'CAM 2,25 % pe liniile 1–3', 'Cheltuieli salariale CDI', '–', 2187),
    (_SEC_I, '5', 'Osciloscop digital 4 canale ≥ 200 MHz, decodare I²C/SPI/UART (I²S de dorit) (830 + TVA)', 'Active corporale – dezvoltare experimentală (subgr. 2.2)', 'A1–A5', 1004),
    (_SEC_I, '6', 'Analizor de spectru ≥ 3 GHz, cu tracking generator (2.440 + TVA)', 'Active corporale (2.2)', 'A3, A4, A5', 2952),
    (_SEC_I, '7', 'Analizor de consum (Joulescope JS320 sau echivalent) (880 + TVA)', 'Active corporale (2.2)', 'A3, A5', 1065),
    (_SEC_I, '8', 'Cutie ecranată RF ≥ 60 dB (900 + TVA)', 'Active corporale (2.2)', 'A3, A5', 1089),
    (_SEC_I, '9', 'Stație de lucru PC (2.000 + TVA)', 'Active corporale (grupa 3, echipamente informatice)', 'A2–A5', 2420),
    (_SEC_I, '10', 'Imprimantă 3D SLA (3.900 + TVA)', 'Active corporale (2.1)', 'A2, A4', 4719),
    (_SEC_I, '11', 'Materiale: 8 plăci de dezvoltare Waveshare ESP32-S3-Touch-AMOLED-1.75, 20 de panouri AMOLED 1,75″ goale, 25 de seturi audio (2 microfoane MEMS + difuzor), 30 de celule LiPo 603040 de 750 mAh, componente, rășină, obiecte de inventar (3.725 + TVA)', 'Materiale, consumabile, obiecte de inventar', 'A2, A4', 4507),
    (_SEC_I, '12', 'CNC + anodizare carcase Al 6061 (3 + 5 + 15 seturi) (5.550 + TVA)', 'Servicii (echivalente) pentru dezvoltare experimentală', 'A4', 6716),
    (_SEC_I, '13', 'Fabricare + asamblare PCB propriu rev A/B (3.000 + TVA)', 'Servicii pentru dezvoltare experimentală', 'A4', 3630),
    (_SEC_I, '14', 'Pre-testare EMC/RF, 2 sesiuni: EMC EN 301 489-1/-17 (≈ 4.610) + radio EN 300 328 (≈ 2.390, [E]) (7.000 + TVA)', 'Servicii de sprijinire a inovării (testare)', 'A5', 8470),
    (_SEC_I, '15', 'Evaluare preliminară EN 18031 (2.500 + TVA)', 'Consultanță în inovare (utilizarea standardelor)', 'A4', 3025),
    (_SEC_I, '16', 'Servicii CDI externalizate: proiectarea/validarea antenei prin carcasa din aluminiu (4.500 + TVA)', 'Servicii CDI externalizate (I.3)', 'A4', 5445),
    (_SEC_I, '17', '2 workshop-uri/sesiuni de testare cu utilizatori: sală, materiale de test, gustare (1.240 + TVA)', 'Workshop-uri colaborative (validare TRL 4–5)', 'A5', 1500),
    (_SEC_I, '18a', 'SaaS: API AI pentru teste (chei de test cu limită de cost, doar în validare) + CAD (≈ 3.140 + TVA)', 'Servicii SaaS pentru CDI (modelare, testare, simulare, analiza datelor)', 'A2–A5', 3800),
    (_SEC_I, '18b', 'Infrastructură cloud de test în UE: servere virtuale pentru instanța de test SOUL Cloud, folosite exclusiv la testarea prototipurilor în L2–L22, oprite la final (≈ 992 + TVA)', 'Servicii SaaS pentru CDI — infrastructură de testare [[de confirmat la helpdesk și pe Anexa 20; alternativ: servicii pentru dezvoltare experimentală]]', 'A2–A5', 1200),
    (_SEC_I, '19', 'Taxe EUIPO: marcă UE, 3 clase (850 + 50 + 150 = 1.050) + desen industrial multiplu, 2 designuri (350 + 125 = 475)', 'Obținerea/protejarea activelor necorporale', 'A6', 1525),
    (_SEC_I, '20', 'Consilier în proprietate industrială: anterioritate, depunere, brevetabilitate (1.250 + TVA)', 'Consultanță în inovare (protecția activelor necorporale)', 'A6', 1512),
    (_SEC_II1, '21', 'Taxă de publicare open-access peer-review (APC ≈ 2.349 + TVA)', 'Publicarea rezultatelor', 'A7', 2842),
    (_SEC_II1, '22', 'Conferință/târg internațional: taxă, transport, cazare, diurnă, max. 2 persoane', 'Participare la conferințe/târguri', 'A7', 2900),
    (_SEC_II1, '23', 'Customer discovery / focus-grupuri, 2 grupuri (1.700 + TVA)', 'Promovare pentru validare comercială', 'A6', 2057),
    (_SEC_II2, '24', 'II.2 Consultanță pentru CF + validarea Raportului științific de către expert', 'Consultanță pentru CF (precontractuală)', 'A0', 4500),
    (_SEC_II2, '25', 'II.3 Salariu manager de proiect (480 h × 18 €) + CAM', 'Management', 'A8', 8834),
    (_SEC_II2, '26', 'II.4 Audit financiar (2.000 + TVA)', 'Audit', 'A8', 2420),
    (_SEC_II2, '27', 'II.5 Comunicare și vizibilitate (1.000 + TVA)', 'Informare și publicitate', 'A8', 1210),
]


def feur(n):
    """12345 -> '12.345' (RO thousands separator)."""
    return f'{n:,.0f}'.replace(',', '.')


def pct(a, b):
    return f'{100 * a / b:.1f}'.replace('.', ',')


LINE_EUR = {nr: v for _, nr, _, _, _, v in _LINES}
SUB_I = sum(v for s, *_, v in _LINES if s == _SEC_I)
SUB_II1 = sum(v for s, *_, v in _LINES if s == _SEC_II1)
SUB_II2 = sum(v for s, *_, v in _LINES if s == _SEC_II2)
DIRECT = SUB_I + SUB_II1 + SUB_II2
INDIRECT = round(0.07 * DIRECT)
ELIGIBIL = DIRECT + INDIRECT
EQUIP = sum(LINE_EUR[k] for k in ('5', '6', '7', '8', '9', '10'))
CD_HOURS = 1200 + 1680 + 1200  # lines 1–3 (coordonator + inginer + student) = 4.080 h CD
EUIPO_TM, EUIPO_DS = 1050, 475  # line 19 split: EU trade mark (3 classes) + multiple design (2 designs), € fără TVA
assert EUIPO_TM + EUIPO_DS == LINE_EUR['19']
# budget shares (03-NUCLEU „Proporții”), one decimal so they add up to 100 %
_SHARE_GROUPS = [
    ('personal CDI', ('1', '2', '3', '4')),
    ('echipamente', ('5', '6', '7', '8', '9', '10')),
    ('materiale + servicii de prototipare/testare/SaaS', ('11', '12', '13', '14', '15', '16', '17', '18a', '18b')),
    ('IP + publicare + diseminare', ('19', '20', '21', '22', '23')),
    ('conexe II.2–II.5', ('24', '25', '26', '27')),
]
SHARES = [(n, sum(LINE_EUR[k] for k in ks)) for n, ks in _SHARE_GROUPS] + [('indirecte', INDIRECT)]
assert sum(v for _, v in SHARES) == ELIGIBIL
TOTAL = feur(ELIGIBIL) + ' €'
assert ELIGIBIL <= 200000 and SUB_I >= 0.5 * ELIGIBIL and SUB_II2 <= 0.10 * ELIGIBIL

_HEAD = {_SEC_I: ('I', 'ACTIVITATEA DE BAZĂ (CDI)'), _SEC_II1: ('II.1', 'DISEMINARE (conex, în afara plafonului de 10 %)'),
         _SEC_II2: ('II.2–II.5', 'PLAFON CUMULAT 10 % DIN TOTAL')}
_SUBNAME = {_SEC_I: ('Subtotal activitate de bază', SUB_I), _SEC_II1: ('Subtotal II.1', SUB_II1), _SEC_II2: ('Subtotal II.2–II.5', SUB_II2)}
BUDGET = []
for _sec in (_SEC_I, _SEC_II1, _SEC_II2):
    BUDGET.append(_HEAD[_sec] + (None, None, None))
    BUDGET += [(nr, line, cat, act, feur(v)) for s, nr, line, cat, act, v in _LINES if s == _sec]
    BUDGET.append(('', _SUBNAME[_sec][0], '', '', feur(_SUBNAME[_sec][1])))
BUDGET += [
    ('', 'TOTAL COSTURI DIRECTE', '', '', feur(DIRECT)),
    ('28', 'Costuri indirecte 7 % × costuri directe (chirie, utilități, personal suport)', 'Rată forfetară', '–', feur(INDIRECT)),
    ('', 'TOTAL ELIGIBIL = NERAMBURSABIL (100 %)', '', '', feur(ELIGIBIL)),
]
BUDGET_CHECKS = [
    ('50.000 € ≤ nerambursabil ≤ 200.000 €', f'{TOTAL} (rezervă de curs ~{pct(200000 - ELIGIBIL, 200000)} %)', 'îndeplinit'),
    ('Activitatea de bază ≥ 50 % din eligibil', f'{feur(SUB_I)} / {feur(ELIGIBIL)} = {pct(SUB_I, ELIGIBIL)} %', 'îndeplinit'),
    ('II.2 + II.3 + II.4 + II.5 ≤ 10 % din eligibilul total', f'{feur(SUB_II2)} / {feur(ELIGIBIL)} = {pct(SUB_II2, ELIGIBIL)} % (plafon {feur(int(0.10 * ELIGIBIL))} €)', 'îndeplinit'),
    ('Indirecte = exact 7 % din directe', f'{feur(INDIRECT)} €', 'îndeplinit'),
    (f'De minimis: {TOTAL} + ajutoarele anterioare ≤ 300.000 €', f'spațiu necesar ≥ {feur(300000 - ELIGIBIL)} € liber', '[[Ct: de verificat în RegAS]]'),
    ('Salarii ≤ HG 1188/2022 Anexa 2', '34 ≤ 35 · 25 ≤ 35 · 12 ≤ 15 · 18 ≤ 50 €/h', 'îndeplinit'),
    ('Eșec de cercetare: max. 50 % decontat; activele pentru TRL 5 cad', 'liniile 12 (lotul de 15), 13 (rev B), 14 se angajează după IE2', 'îndeplinit'),
]

# risk, desc, prob, impact, measures
RISKS = [
    ('R1', 'Eșec de cercetare: H1/H3/H4/H5 nu se validează (fps < 30 pe QSPI, atenuare RF > 6 dB, latență > prag, autonomie < 24 h cu 750 mAh)', 'Medie', 'Mare',
     'poarta IE2 la L14 (≤ 2/3); alternative tehnice pregătite (randare parțială, bounce-buffers, fereastră radio mai mare, antenă externă în talpă, alt model AI ales de proprietar, mai mult somn al ecranului/celulă mai mare dacă încape); dacă tot nu merge → Anexa 17, se decontează max. 50 % și nu cumpărăm activele pentru TRL 5 înainte de poartă'),
    ('R2', 'Recrutarea coordonatorului/inginerului întârzie', 'Medie', 'Mare',
     'declarații de disponibilitate semnate înainte de depunere; detașare de la o organizație de cercetare ca variantă'),
    ('R3', 'Lanțul de aprovizionare (panouri, module, CNC)', 'Medie', 'Mediu', '2 furnizori pe linie; stoc tampon la L2'),
    ('R4', 'Ghidul final schimbă plafoanele (Anexa 20) sau calendarul', 'Medie', 'Mediu', 'buget modular; rezervă de curs 4 %'),
    ('R5', 'Curs valutar: plafonul de minimis/200 k€ depășit la semnare', 'Redusă', 'Mediu', '191 k€ în loc de 200 k€'),
    ('R6', 'ARTEMIS devine plătitoare de TVA (plafonul de 395.000 lei poate fi depășit din activitatea curentă KREA/MundiShop sau, după proiect, din vânzările SOUL) → TVA neeligibilă în proiect; după proiect, vânzările se taxează (OSS pentru vânzările B2C la distanță în UE peste 10.000 €/an)', 'Medie', 'Mediu', 'monitorizare lunară a CA; notificarea AM-ului; reducerea TVA din buget; proiecția post-PoC e calculată deja fără TVA (prețul de listă de 249 € include TVA, ≈ 206 € net); înregistrare OSS înainte de primele vânzări în alte state UE'),
    ('R7', 'Cash-flow până la rambursare', 'Medie', 'Mare', 'prefinanțare (§12.1), cereri de plată (§12.2), linie de credit FNGCIMM'),
    ('R8', 'Dependența de furnizorii de AI și de politicile lor (abonamentele Claude Pro/Max nu pot fi folosite de dispozitive terțe; „Sign in with ChatGPT” cere aprobarea OpenAI)', 'Medie', 'Mediu',
     'modul offline complet; AI-ul proprietarului prin cheia lui API sau prin conectorul din aplicația Claude; mai mulți furnizori; nu promitem funcții care depind de aprobări neobținute; SOUL nu include și nu revinde AI'),
    ('R9', 'Conformitate (AI Act art. 50, GDPR, EN 18031)', 'Redusă', 'Mediu', 'informare AI la pornire; DPA; evaluarea EN 18031 (linia 15)'),
    ('R10', 'Vânzare sau certificare CE înainte de contract: proiectul ar părea „demarat/finalizat” și TRL > 5', 'Redusă (decizia din 26.09.2026)', 'Eliminatoriu',
     'fără ediție Founders; pe site doar listă de așteptare, nicio rezervare sau plată; magazinul Shopify nu se deschide pentru vânzare și SOUL nu se certifică CE înainte de contract; prima serie (10–25 buc.) e pasul post-PoC'),
    ('R11', 'Schimbări de acționariat (ex. un investitor angel intră în ARTEMIS)', 'Medie', 'Eliminatoriu (condiții artificiale, §5.1.2)',
     'investiția se face într-un vehicul separat sau după durabilitate, cu avizul AM; fără transfer de IP în durabilitate'),
    ('R12', 'Conflict de marcă „SOUL”', 'Mare', 'Mediu', 'căutare TMview acum; marcă figurativă/compusă ca rezervă; designul (depus înainte de ' + DESIGN_DEADLINE + ') protejează forma oricum'),
]

POSTPOC = [
    ('Prima serie (10–25 buc.)', 'TRL 6 → 7', 'An 1 (S1)', '10–25 unități, PCB rev C, certificare CE/RED + EN 18031 [E: 5–12 k€ + 0–9 k€], înregistrări ANMAP/EPR, GPSR; vânzare din magazinul propriu, de la 249 €; feedback',
     'venituri din vânzări, fonduri proprii, EUIPO SME Fund (IP), EDIH (testare)'),
    ('Batch 1 / CE complet', 'TRL 7 → 8', 'An 1 (S2) – An 2', '300 de unități, scule (matrițe parțiale), aplicația de telefon, 3–5 piețe UE (EPR, reprezentant autorizat)',
     'PR BI 1.2 (produse noi în IMM) sau Eurostars Call 12/13, pre-seed/angel într-un vehicul care nu afectează PoC-ul, crowdfunding (Indiegogo/Gamefound — Kickstarter nu e disponibil din RO)'),
    ('SOUL Standard', 'TRL 9', 'An 2 – An 3', '1–10 k unități/an, PCB cu modul certificat, cost < 60 €/buc., canale: online direct + retail de design + B2B (echipe care folosesc Claude Code)',
     'venituri, EIC Accelerator (la TRL 6–8), credit garantat FNGCIMM pentru stoc'),
    ('Platforma', 'TRL 9', 'An 3 – An 5', 'accesorii și piese de schimb, SoulOS pentru parteneri, licențierea designului/firmware-ului; eventual servicii SOUL Cloud opționale (backup, sincronizare), fără AI inclus',
     'venituri recurente, licențe'),
]

IPPLAN = [
    ('0', 'Ce e deja public: depozitul ' + REPO_PUBLIC + ' e public din ' + PUBLIC_SINCE + ' (API GitHub, 12.10.2026) și conține ' + FIRST_PUB + '. Tot ce e acolo se tratează ca divulgat la data primului commit. [[A: decide dacă depozitul, inclusiv dosarul, devine privat; nu anulează divulgarea de până acum]]', 'acum', '0 €'),
    ('0a', 'Căutare TMview + DesignView pentru „SOUL” (clasele 9, 42, 14, 28) — risc mare de conflict (SOUL Electronics etc.)', 'acum, înainte de depunere', '0 €'),
    ('0b', 'Desen/model industrial UE pentru forma MĂRGĂRITAR (corpul SOUL: mărimea S, produsul final, randări v10; mărimea M, prototipul, randări v9; + capsula OU și ochii, dacă apar în materialele publice). Grația de 12 luni curge de la prima divulgare (randările din 24.09.2026; MĂRGĂRITAR v9 din 26.09.2026) și expiră pe ~' + DESIGN_DEADLINE + ', înainte de contractul estimat (aug.–oct. 2027). Se depune acum prin EUIPO SME Fund (voucher, până la 04.12.2026) sau imediat după depunerea CF, din fonduri proprii; nu intră în bugetul PoC (fără dublă finanțare, §5.2.1 V)', 'T−8 săpt. … imediat după depunerea CF; în orice caz înainte de ' + DESIGN_DEADLINE, 'în afara proiectului'),
    ('0c', 'Dacă marca verbală e liberă: poate fi depusă înainte de proiect prin același voucher SME Fund. Atunci nu mai apare în bugetul PoC, iar linia 19 se folosește pentru marca figurativă/clase suplimentare și designul elementelor noi', 'T−8 săpt.', 'în afara proiectului'),
    ('1', 'Consilier PI: anterioritate (inclusiv propriile publicări din depozitul public) + strategie (design / model de utilitate OSIM / brevet)', 'L1–L3', 'linia 20'),
    ('2', 'Desen/model industrial UE pentru elementele noi, nepublicate, rezultate în proiect (forma rev B a carcasei și a capsulei OU, dacă diferă de cele publice; interfața grafică finală) — depus înainte de orice publicare a lor', '≤ L18', 'linia 19'),
    ('3', 'Marcă UE (verbală sau figurativă, 3 clase)', '≤ L6', 'linia 19'),
    ('4', 'Evaluarea brevetabilității/modelului de utilitate **doar pentru soluțiile nepublicate** dezvoltate în proiect (implementarea măsurată a ferestrei radio și a antenei, mecanismul bateriei înlocuibile și contactele OU, dacă nu sunt publice). Metoda de decodare a tastaturii și conceptul ferestrei radio sunt publice din 25.09.2026, deci noutatea lor e probabil pierdută: nu le revendicăm', 'L12–L18', 'linia 20; depunerea OSIM, dacă merită, în perioada de durabilitate'),
    ('5', 'Publicare (articol OA, preprint Zenodo) doar după depunerea cererilor pentru elementele nepublicate (pasul 2)', 'trimitere ≤ L20', 'linia 21'),
    ('6', 'Secret comercial **doar pentru ce nu e public**: datele de măsurare RF și tuning-ul antenei din proiect, layout-ul PCB rev A/B, corpusurile și datele de test noi — păstrate în afara depozitului public', 'continuu', '–'),
    ('7', 'Cesiunea drepturilor Andu → ARTEMIS (codul și designul pre-proiect) + registrul licențelor open-source (MIT/OFL); vizibilitatea publică a depozitului nu e o licență (nu are licență open-source declarată, în afară de SOUL Bridge — MIT)', 'înainte de depunere', '0 €'),
]

CIRCULAR = [
    ('Prelungirea duratei de viață / reparabilitate', 'baterie LiPo 750 mAh (603040) înlocuibilă de utilizator (conector MX1.25, spumă, nu adeziv; Reg. 2023/1542 art. 11); închidere cu șuruburi Torx standard; module înlocuibile (panou, placă, difuzor)', 'P10: înlocuire ≤ 5 min; ghid de reparare publicat'),
    ('Design pentru dezasamblare și reciclare', 'carcasă monomaterial Al 6061 (reciclabil nelimitat), fără adezivi structurali; talpă polimerică detașabilă; marcarea materialelor', 'raport de dezasamblare: ≥ 90 % din masă separabilă pe fracții'),
    ('Actualizare software (OTA) în loc de înlocuire hardware', 'funcții noi livrate prin OTA semnat; hardware-ul nu se învechește la schimbarea modelului AI (proprietarul își alege AI-ul; memoria rămâne pe dispozitiv)', 'OTA semnat demonstrat la TRL 5'),
    ('Independența de server (evită „bricking”-ul de tip Humane)', 'modul offline complet; memoria SOUL Memory pe dispozitiv; SOUL Cloud doar transmite mesajele; SOUL Bridge open source (MIT)', 'P5, P7'),
    ('Reducerea resurselor pe unitatea de output', 'un singur obiect pentru notițe/alarme/remindere/aprobări Claude; capsula OU fără baterie; ambalaj din pulpă/carton', 'BOM + fișa materialelor'),
    ('Piese de schimb', 'angajament: baterii și piese de schimb 5 ani', 'Plan de afaceri §6'),
]

NOVELTY = [
    ('N1', 'Randare SDF anti-aliased a „ochilor” parametrici pe MCU, cu framebuffer în PSRAM și push pe regiuni modificate prin QSPI către un AMOLED 466×466 (validată întâi pe panoul RGB 480×480 fără memorie proprie al prototipului M)', 'competitorii folosesc animații pre-randate (sprite-uri) sau SoC-uri scumpe', '≥ 30 fps cu Wi-Fi + BLE active; 120 de designuri de ochi și 31 de expresii; fiecare unitate „se naște” cu o pereche de ochi derivată din ID-ul cipului'),
    ('N2', 'Round QWERTY cu tastele de la margine „stăpâne” pe bordură, decodare probabilistică, diacritice RO automate', 'smartwatch-uri: 10–30 WPM în literatură; fără suport RO', '≥ 20 WPM, UER ≤ 3 %, diacritice automate'),
    ('N3', 'Arhitectură „un singur set de acțiuni, AI-ul proprietarului”: offline / Claude (cheia proprie sau conectorul din aplicația Claude, OAuth 2.1 MCP) / ChatGPT (cheie proprie); memorie portabilă pe dispozitiv (SOUL Memory), dată oricărui AI conectat', 'dispozitivele au un singur furnizor, cloud obligatoriu sau abonament la AI-ul producătorului', '≥ 90 % succes offline; continuitate 100 % la căderea rețelei; 100 % din memorie păstrată la schimbarea AI-ului'),
    ('N4', 'Carcasă CNC din aluminiu cu antenă prin fereastră polimerică în talpă + încărcare prin pini în capsula OU', 'carcasele metalice blochează RF; obiectele premium nu au AI', 'atenuare ≤ 6 dB; legătură BLE ≥ 10 m'),
    ('N5', 'Reparabilitate de la proiectare: baterie schimbabilă de utilizator (Torx), fără adeziv pe celulă, componente modulare, OTA', 'multe gadgeturi au baterii lipite/nedemontabile', 'înlocuire ≤ 5 min de către utilizatori neexperți'),
]

# existing evidence (TRL 3); state verified 12.10.2026 in the vault (git log, firmware/README.md, docs/07, docs/10, firmware/PERF.md)
EVIDENCE = [
    ('D1', 'Rezultat experimental (teste automate) + cod sursă', 'Firmware SoulOS 1.9.1 „Alive” (Alive lansat în 1.9.0 pe 12.10.2026, commit 52689e4; 1.9.1 pe 22.10.2026, compilat fără avertismente; imaginile de instalare `release/SOUL-2.8C-install.bin` pentru M și `release/SOUL-1.75-install.bin` pentru S): motorul ochilor (randare SDF, 120 de designuri, 31 de expresii, fiecare unitate primește o pereche din ID-ul cipului), IMU/giroscop, tastatura circulară, alarme, notițe, hărți/vreme/aplicații, SOUL Memory, comenzi vocale offline EN (ESP-SR), legătura Claude Hardware Buddy (BLE), protocolul SOUL Cloud; 245 de teste native trec pe PC (`pio test -e native`); build-uri `lcd28` (placa 2.8C, prototipul SOUL M), `lcd28_voice`, `amoled175` (placa AMOLED-1.75, SOUL S: profilul de densitate și toate ecranele Alive pe 466 px, 20–22.10.2026) și `sim`', '2026-10', 'depozit git, `firmware/` (README, PERF.md, BRINGUP.md); commit 52689e4 (1.9.0); S: b3aee4c, b9c683d; 1.9.1: fe9fbe4 [[A: export log + hash la data depunerii]]'),
    ('D2', 'Simulator / model software', 'Simulator pe PC care rulează aceeași bibliotecă `lib/Suflet` ca placa și produce cadrele reale (clipuri: idle, boop, purr, dizzy, sleep…, tastatura, ecranele SoulOS la 480 px pe M și 466 px pe S) + banc de performanță (`tools/perf_bench.py`: ≈ 30 fps estimat pe toate scenariile [E], de măsurat pe placă)', '2026-10', '`firmware/sim`, `firmware/PERF.md`, `media/` (clipuri MP4/GIF anexate)'),
    ('D3', 'Rezultat experimental (teste automate) + cod sursă', 'SOUL Cloud: împerechere cu chei de dispozitiv, gateway WebSocket, conector MCP cu OAuth 2.1 (Claude), cheie API proprie criptată, export și ștergere date (GDPR), backup criptat opțional al memoriei; 283 de teste trec; rulat cap-coadă cu simulatorul firmware-ului ca dispozitiv (fără claude.ai real încă). SOUL Bridge: canalul Claude Code de pe computerul proprietarului, open source (MIT). Fără AI inclus (decizia din 03.10.2026)', '2026-10', '`ai/` (README, tests/), `bridge/`, `docs/07-CONNECT-AI.md`, `docs/10-SOUL-MEMORY.md`'),
    ('D4', 'Prototip interactiv (software)', 'SoulOS pe web: ochii ca interfață, tastatura rotundă interactivă testabilă la scara reală, demo public; reproiectarea „Alive” aprobată 12.10.2026', '2026-10', '`os/index.html`, `os/DESIGN-ALIVE.md`, `os/ARCHITECTURE.md`'),
    ('D5', 'Studiu analitic', 'Geometria tastaturii pe diametre (pas = 0,0944·D → 6,7 mm pe Ø70 la M; 4,1 mm la S, de aceea tastatura S cu taste de 5,1 mm) și analiza panoului și a mărimii: justificarea alegerii AMOLED 1,75″ 466×466 pentru produsul S (stiva internă, bateria de 750 mAh, autonomia [estimare], costul), cu IPS 2,8″ 480×480 păstrat pe prototipul M', '2026-09 / 2026-10', '`research/12` §1–2, `docs/12-SIZE-S.md`, `firmware/SOUL-S.md`'),
    ('D6', 'Prototip virtual (CAD)', 'Forma finală MĂRGĂRITAR, mărimea S (~63 × 70,8 × 23 mm, sticlă plată Ø52, aluminiu anodizat, 5 culori; decizia din 20.10.2026): randări v10, planșe tehnice S, STL/STEP-urile prototipului S-P0 printabil; mărimea M (~90 × 101 × 31,5 mm, randări v9) rămâne prototipul de test', '2026-09 / 2026-10', '`renders/v10/`, `renders/v9/`, `blueprints/final/soul_s_*`, `prototip/stl/s/`, `prototip/step/s/`'),
    ('D7', 'Documentare cronologică', 'Istoricul git cu commit-uri datate (primul commit SOUL: 24.09.2026)', '2026-09', 'depozitul vault (export `git log` anexat)'),
    ('D8', 'Raport de laborator TRL 3 pe hardware (ÎN CURS — de finalizat înainte de depunere)', 'Experimentele X1–X8 pe prototipul de banc SOUL M (nu produsul; produsul e mărimea S), placa Waveshare ESP32-S3-Touch-LCD-2.8C (ESP32-S3R8, 8 MB PSRAM, 16 MB flash; comandată din fonduri proprii, în afara bugetului; încă netestată): bring-up, fps, precizie touch, tastare pilot, comenzi offline, latență AI, RSSI prin aluminiu, consum', '[[A+Cl: T−6 … T−2 săpt.]]', '„Raport de laborator TRL 3 — SOUL M (2.8C)”, datat și semnat, cu loguri, fotografii, video cu marcaj de timp pe placa reală și hash git [[de anexat]]'),
]

XTESTS = [
    ('X1', 'Bring-up pe 2.8C: imaginea SoulOS 1.9.1 (`release/SOUL-2.8C-install.bin`) încărcată pe placă; ecran ST7701 RGB, touch GT911, IMU QMI8658, RTC, BLE (pașii din BRINGUP.md)', 'build `lcd28` (compilează fără avertismente; placa e comandată, încă netestată)', 'firmware rulând pe placa reală; video cu marcaj de timp'),
    ('X2', 'fps la ochi', 'linia `[perf]` pe serial (BRINGUP §5), 10 min, cu Wi-Fi oprit/pornit', 'median/p5 fps (baseline pentru H1)'),
    ('X3', 'Precizia touch', 'test „grilă de ținte” 6,7 mm, 200 de atingeri, 3 persoane', '% atingeri corecte, eroare medie în mm'),
    ('X4', 'Tastare pilot pe SoulOS web (la scara reală) și pe placă', 'fraze standard (MacKenzie), N = 5', 'WPM, rata de eroare (baseline pentru H2)'),
    ('X5', 'Comenzile offline: parserul pe un corpus de 200 de comenzi RO/EN + comenzile vocale EN (ESP-SR, build `lcd28_voice`, dacă modulul audio e montat)', 'teste automate + script de corpus; citire cu voce, cameră liniștită', '% comenzi corecte (baseline pentru H3)'),
    ('X6', 'Latența unui tur AI (text) cu cheia proprie Claude (cont de test cu limită de cost); ChatGPT doar dacă integrarea cu cheie proprie e gata', '50 de tururi, cronometrare pe dispozitiv', 'p50/p90 în secunde'),
    ('X7', 'Împerecherea BLE cu Claude Desktop (Hardware Buddy) + RSSI prin plăci de aluminiu (tablă 1,5 mm)', 'telefon cu nRF Connect, 1/3/5 m', 'atenuare orientativă în dB'),
    ('X8', 'Consumul plăcii M (prototipul 2.8C) cu LiPo 1500 mAh (ecran aprins/stins)', 'multimetru USB (BRINGUP §5d)', 'mA (baseline pentru H5; estimarea de pornire: ≈ 177–227 mA treaz, ≈ 35–60 mA cu ecranul stins [E])'),
]

# verified 25.09.2026 via Crossref API / arXiv
REFS = [
    ('1', 'Robust Text Input for Smartwatches: Compensating for Imprecise Tapping and Swiping', 'J. Lai, L. Zhou, K. Wang, D. Zhang', '2025', 'Articol (Int. J. Human–Computer Interaction 41(23):14833–14845), doi:10.1080/10447318.2025.2490709',
     'H2: decodarea care compensează atingerile imprecise pe ecrane mici de ceas — baza pentru decodorul probabilistic al tastaturii circulare'),
    ('2', 'Text entry for the Blind on Smartwatches', 'M. M. Luna, H. A. D. Nascimento, A. Quigley, F. Soares', '2022', 'Articol (Universal Access in the Information Society 22(3):737–755), doi:10.1007/s10209-022-00870-2',
     'H2/P10: accesibilitatea introducerii de text pe ceas — modul „taste mari” și testele cu persoane cu deficiențe de vedere'),
    ('3', 'Text Entry for XR Trove (TEXT): Collecting and Analyzing Techniques for Text Input in XR', 'A. Bhatia, M. H. Mughrabi, D. Abdlkarim, M. Di Luca, M. Gonzalez-Franco, K. Ahuja, H. Seifi', '2025', 'Preprint arXiv:2503.11357, doi:10.48550/arXiv.2503.11357',
     'H2: taxonomia a 176 de tehnici de introducere a textului și atributele care determină performanța (metodologia WPM/UER)'),
    ('4', 'Investigating the rendering capability of embedded devices for graphical-user-interfaces in mobile machines', 'M. Krüger, B. Vogel-Heuser, S. Vollmann', '2023', 'Articol (at – Automatisierungstechnik 71(11):939–952), doi:10.1515/auto-2023-0043',
     'H1: limitele de randare GUI pe dispozitive embedded (fps vs. resurse) — contextul pentru randarea SDF pe ESP32-S3'),
    ('5', 'Moshi: a speech-text foundation model for real-time dialogue', 'A. Défossez, L. Mazaré, M. Orsini, A. Royer, P. Pérez, H. Jégou, E. Grave, N. Zeghidour', '2024', 'Preprint arXiv:2410.00037, doi:10.48550/arXiv.2410.00037',
     'H3: stadiul actual al latenței în dialogul vocal (160–200 ms pentru modele full-duplex vs. secunde în lanțurile ASR→LLM→TTS)'),
    ('6', 'Improving Impressions of Response Delay in AI-based Spoken Dialogue Systems', 'S. Asaka, K. Itoyama, K. Nakadai', '2024', 'Lucrare IEEE RO-MAN 2024, pp. 1416–1421, doi:10.1109/RO-MAN60168.2024.10731216',
     'H3: percepția întârzierii răspunsului la agenți AI încorporați — justifică pragul p50 ≤ 1,5 s și acoperirea așteptării prin expresia ochilor'),
    ('7', 'On-Device Language Models: A Comprehensive Review', 'J. Xu, Z. Li, W. Chen, Q. Wang, X. Gao, Q. Cai, Z. Ling', '2024', 'Preprint arXiv:2409.00088, doi:10.48550/arXiv.2409.00088',
     'H3: compromisurile edge vs. cloud (latență, confidențialitate, cost) — argumentul pentru arhitectura hibridă local-first'),
    ('8', 'Compact Slot Antenna with Extended Bandwidth Integrated on Metal Box for 2.4 GHz IoT Applications', 'Y. Xu, S. Wen, Y. Dong', '2021', 'Lucrare IEEE IWS 2021, doi:10.1109/IWS52775.2021.9499488',
     'H4: antene 2,4 GHz integrate în carcase metalice pentru IoT — principiul ferestrei/fantei radio'),
    ('9', 'Design and Validation of a Compact Dual-Band Bluetooth Antenna for Smartwatch Applications', 'S. K. R. Vuyyuru, M. Räsänen, J. H. S. Bergman, J. Holopainen', '2025', 'Lucrare EuCAP 2025, doi:10.23919/EuCAP63536.2025.10999952',
     'H4: validarea experimentală a antenelor Bluetooth compacte în dispozitive purtabile mici'),
    ('10', 'Disassembly and Repairability of Mechatronic Products: Insight for Engineering Design', 'N. Boix Rodríguez, C. Favi', '2023', 'Articol (Journal of Mechanical Design 146(2)), doi:10.1115/1.4064075',
     'H5/EC: metrici de dezasamblare și reparabilitate pentru produse mecatronice — metodologia P10'),
    ('11', 'The Disassembly Map: A new method to enhance design for product repairability', 'F. De Fazio, C. Bakker, B. Flipsen, R. Balkenende', '2021', 'Articol (Journal of Cleaner Production 320:128552), doi:10.1016/j.jclepro.2021.128552',
     'H5/EC: metoda de proiectare pentru reparabilitate aplicată bateriei înlocuibile și modulelor SOUL'),
]
REFS_BASELINE = [
    'Yi, X., Yu, C., Xu, W., Bi, X., Shi, Y. (2017). COMPASS: Rotational Keyboard on Non-Touch Smartwatches. Proc. CHI 2017, 705–715. doi:10.1145/3025453.3025454 (baseline 10–12,5 WPM; sursă mai veche de 5 ani, folosită doar ca reper).',
    'C-QWERTY: Text Entry on Circular Smart Watches (2019), ResearchGate 337284352 (baseline 20–30 WPM; sursă mai veche de 5 ani, folosită doar ca reper).',
]
NORMS = [
    'Regulamentul (UE) 2023/1542 privind bateriile și deșeurile de baterii, art. 11 (baterii portabile îndepărtabile și înlocuibile de utilizator din 18.02.2027) — https://eur-lex.europa.eu/eli/reg/2023/1542/oj',
    'Directiva (UE) 2024/1799 privind promovarea reparării bunurilor („dreptul la reparare”) — https://eur-lex.europa.eu/eli/dir/2024/1799/oj',
    'Regulamentul (UE) 2024/1689 privind inteligența artificială (AI Act), art. 50 (transparență, aplicabil din 02.08.2026) — https://eur-lex.europa.eu/eli/reg/2024/1689/oj',
    'Regulamentul delegat (UE) 2022/30 (RED art. 3(3) d, e, f — securitate cibernetică) + standardele armonizate EN 18031-1/-2/-3 — https://eur-lex.europa.eu/eli/reg_del/2022/30/oj',
    'ETSI EN 300 328 (echipamente 2,4 GHz); ETSI EN 301 489-1/-17 (EMC pentru echipamente radio).',
]

MARKET_SOURCES = [
    ('Eurostat (16.12.2025): 32,7 % din persoanele de 16–74 ani din UE au folosit instrumente de AI generativ în 2025 (25,1 % în scop personal, 15,1 % la muncă); România: 17,8 % (cel mai mic nivel din UE)', 'https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20251216-3'),
    ('IDC: 45,6 milioane de dispozitive purtate la încheietură livrate în T1 2025 (+10,5 %), din care 34,8 M smartwatch-uri', 'https://www.emsnow.com/idc-global-wrist-worn-device-shipments-grew-10-5-in-q1-2025/'),
    ('TechCrunch (16.06.2026): Plaud a livrat peste 2 milioane de dispozitive AI de notițe; abonamentele depășesc 100 M$ ARR; ~50 % dintre cumpărători plătesc abonament', 'https://techcrunch.com/2026/06/16/plaud-says-its-software-business-topped-100m-in-arr-after-shipping-over-2m-ai-notetakers/'),
    ('Axios (18.02.2025): Humane AI Pin (699 $ + 24 $/lună) oprit de la distanță pe 28.02.2025 după achiziția HP (116 M$)', 'https://www.axios.com/2025/02/18/humane-ai-pin-shut-down-hp'),
    ('The Register (16.12.2024): robotul Moxie (800 $) a încetat să funcționeze odată cu serverele producătorului', 'https://www.theregister.com/2024/12/16/moxie_cloud_services_lessons/'),
    ('TechCrunch (06.08.2026): dispozitivul OpenAI × Jony Ive, difuzor din metal premium, raportat la 300–400 $, lansare 2027', 'https://techcrunch.com/2026/08/06/openais-new-ai-smart-speaker-will-reportedly-sell-for-between-300-and-400/'),
    ('heise (2026): Meta Muse Charm — agent AI cu două camere și 5G, disponibil doar în SUA', 'https://www.heise.de/en/news/Tamagotchi-meets-AI-agent-Meta-announces-AI-gadget-Muse-Charm-11464075.html'),
    ('Stocktitan / Tuya (2026): Fuzozo — aproape 300.000 de unități vândute în China', 'https://www.stocktitan.net/news/TUYA/tuya-smart-accelerates-physical-ai-commercialization-with-strategic-fl5hn4dv397y.html'),
    ('Kicktraq: Loona DeskMate — 721.816 $ de la 3.166 de susținători (2026)', 'https://www.kicktraq.com/projects/keyitechnology/loona-deskmate-the-worlds-first-screen-aware-ai-co-worker/'),
    ('Kicktraq: Eiliko — ~600.000 $ de la 4.707 susținători (2025)', 'https://www.kicktraq.com/projects/energize-lab/eiliko/'),
    ('claude-desktop-buddy.com: „Vibe Desktop Buddy” — dispozitiv de aprobări Claude Code vândut cu 110 $ + transport', 'https://claude-desktop-buddy.com/'),
    ('Gizmodo: STARBOY (CREATURE) — breloc metalic cu ochi OLED, 139–599 $, loturile 1–2 epuizate', 'https://gizmodo.com/can-we-interest-you-in-a-400-ai-keychain-that-behaves-like-a-real-pet-2000732919'),
    ('TechCrunch (30.07.2026): Friend 2.0 — 249 $, „a avut probleme să vândă în volum”', 'https://techcrunch.com/2026/07/30/friend-the-lonely-ai-wearable-returns-with-a-new-voice-and-a-much-bigger-price-tag/'),
    ('CNX Software (20.04.2026): Loona DeskMate — 219–299 $, 50+ integrări, necesită iPhone', 'https://www.cnx-software.com/2026/04/20/loona-deskmate-an-iphone-powered-ai-desk-companion-that-doubles-as-a-165w-gan-charging-station/'),
    ('Kickstarter — Romania nu este țară eligibilă pentru creatori', 'https://help.kickstarter.com/hc/en-us/articles/115005128594-Who-can-use-Kickstarter'),
]

TARGET_GROUPS = [
    'Utilizatorii-pilot din București-Ilfov (≥ 12) care participă la validarea TRL 5.',
    'Profesioniștii care lucrează zilnic cu asistenți AI (dezvoltatori care folosesc Claude Code/Cowork, creatori, freelanceri) și își conectează propriul cont AI: nevoia de aprobări și notițe rapide, fără telefon.',
    'Utilizatorii care vor un asistent privat, cu funcționare offline, fără abonament obligatoriu și fără un AI impus de producător.',
    'Persoanele cu nevoi de accesibilitate (control vocal, taste mari).',
    'Ecosistemul regional: laboratoare universitare (UPB), ateliere CNC/PCB, laboratoare de testare.',
]
