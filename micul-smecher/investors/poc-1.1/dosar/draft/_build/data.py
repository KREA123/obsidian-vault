# -*- coding: utf-8 -*-
"""Facts copied from dosar/03-NUCLEU-PROIECT.md (single source of truth). Change there first."""

APPLICANT = 'ARTEMIS DIGITAL S.R.L.'
ACRONIM = 'SOUL-PoC'
TITLU = ('SOUL — dispozitiv AI tangibil, local-first, cu interfață circulară și carcasă reparabilă din aluminiu: '
         'validarea modelului conceptual de la TRL 3 la TRL 5')
TITLU_EN = ('SOUL — a tangible, local-first AI interaction device with a circular interface and a repairable '
            'aluminium enclosure: proof of concept from TRL 3 to TRL 5')
RIS3 = ('1. Tehnologia Informației și Comunicațiilor (TIC); 2. Sisteme și Componente Inteligente '
        '[[Cl: subdomeniile exacte din RIS3 BI 2021–2027, după descărcarea strategiei de pe adrbi.ro]]')
TOTAL = '191.308 €'

OBJ_GENERAL = ('validarea modelului conceptual SOUL (dispozitiv AI tangibil, local-first, cu interfață circulară și '
               'carcasă reparabilă) de la TRL 3 la TRL 5, în 24 de luni, la București.')

# code, objective, indicator, deadline, activities, result
OBJECTIVES = [
    ('O1', 'Realizarea și validarea în laborator (TRL 4) a modelului integrat SOUL M (afișaj 2,8″ + touch + audio + baterie + AI hibrid)',
     'fps median ≥ 30 · precizie touch ≥ 97 % · WPM ≥ 15 (N = 6) · succes offline ≥ 90 % · latență vocală p50 ≤ 1,8 s · 8/8 protocoale rulate',
     'L14', 'A1, A2, A3 (CDI I.3)', 'R1 Raport TRL 4'),
    ('O2', 'Proiectarea și realizarea a 15 prototipuri pre-serie cu PCB propriu și carcasă CNC din aluminiu cu baterie înlocuibilă',
     '15/15 unități funcționale · atenuare RSSI ≤ 6 dB · înlocuirea bateriei ≤ 5 min · autonomie ≥ 24 h (profil tipic)',
     'L17', 'A4 (CDI I.3/I.4)', 'R2 (partea 1)'),
    ('O3', 'Validarea în mediu relevant (TRL 5) cu ≥ 12 utilizatori timp de 4 săptămâni + pre-testare EMC/RF',
     'WPM ≥ 20 și UER ≤ 3 % · latență p50 ≤ 1,5 s / p90 ≤ 2,5 s · succes offline ≥ 90 % · ≥ 99 % sesiuni fără crash · SUS ≥ 75 · 0 depășiri la pre-scan (marjă ≥ 3 dB)',
     'L22', 'A5 (CDI I.3)', 'R2 Raport TRL 5'),
    ('O4', 'Protejarea și valorificarea rezultatelor',
     'cerere de design EUIPO (≤ L5) · cerere de marcă (≤ L6) · 1 articol OA peer-review trimis (≤ L20) · ≥ 2 acorduri de pilot/distribuție + plan de comercializare (L24)',
     'L24', 'A6, A7 (CDI I.2/I.4 + conex II.1)', 'R3, R4, R5'),
]

RESULTS = [
    ('R1', 'Model de laborator SOUL M validat la TRL 4 + Raport de validare TRL 4', 'L14'),
    ('R2', '15 prototipuri SOUL M pre-serie validate la TRL 5 în mediu relevant + Raport TRL 5 + raport de pre-testare EMC/RF', 'L22'),
    ('R3', '2 cereri de protecție IP depuse (desen/model industrial UE; marcă UE) + raport de brevetabilitate', 'L18'),
    ('R4', '1 articol științific trimis la o revistă open-access peer-review + 1 comunicare la o conferință', 'L20–L24'),
    ('R5', 'Plan de valorificare comercială + ≥ 2 acorduri de pilot/distribuție semnate', 'L24'),
]

# code, name, type, months, subactivities, deliverables
ACTIVITIES = [
    ('A0', 'Pregătirea CF, a Planului de afaceri, a Raportului științific + validarea de către expert', 'Conex II.2, precontractuală',
     'înainte de depunere', '–', 'CF, Anexa 3, Anexa 16 semnată'),
    ('A1', 'Specificații, protocoale experimentale, setup de laborator', 'CDI I.3 (+ I.1 echipamente)', 'L1–L3',
     '1.1 specificația sistemului M; 1.2 protocoalele P1–P10 cu praguri; 1.3 achiziția aparatelor de măsură și a PC-ului; 1.4 bancul de test (cutie ecranată, analizor de consum)',
     'L1.1 Specificație; L1.2 Protocoale; M1 Banc de test validat (L3)'),
    ('A2', 'Modelul de laborator M integrat: port RGB/ST7701, GT911, audio I2S (2 mic + amplificator), baterie 2500–3000 mAh, carcasă SLA la scara M, flux vocal (xiaozhi-esp32 adaptat + server UE suflet_ai), scalarea tastaturii la 480 px',
     'CDI I.3 + materiale', 'L2–L8',
     '2.1 firmware afișaj/touch; 2.2 subsistem audio + AEC; 2.3 alimentare/PMU; 2.4 carcasă SLA; 2.5 server vocal UE; 2.6 integrare',
     'L2.1 Model de laborator funcțional; IE1 (L6): raport intermediar CDI'),
    ('A3', 'Validarea TRL 4 în laborator (protocoalele P1–P8) + analiza rezultatelor + raportul de etapă TRL 4', 'CDI I.3', 'L6–L14',
     '3.1 teste de componente; 3.2 teste de sistem; 3.3 studiu de tastare N = 6; 3.4 analiză + decizie de poartă',
     'R1 Raport TRL 4 (L14) = IE2; decizia go/no-go TRL 5'),
    ('A4', 'Prototipul pre-serie: PCB propriu (ESP32-S3-WROOM-1, ST7701, GT911, ES8311/ES7210, PMU, IMU, RTC, pini de încărcare), antenă prin fereastră polimerică, carcasă CNC Al 6061 rev A (3 seturi) și rev B (5 + 15 seturi), baterie înlocuibilă, capsula OU; securitatea EN 18031 (secure boot, OTA semnat)',
     'CDI I.3/I.4 + servicii', 'L9–L17',
     '4.1 schema și layout rev A (L9–L11); 4.2 fabricare + test rev A (L11–L13); 4.3 antenă + RF (serviciu extern); 4.4 după poarta L14: rev B + lotul de 15 carcase; 4.5 asamblare și QC',
     'L4.1 PCB rev A testat; M3 15 prototipuri (L17)'),
    ('A5', 'Validarea TRL 5 în mediu relevant: 15 unități la 12–15 utilizatori din BI (case, birouri, un living lab), 4 săptămâni, telemetrie opt-in; protocoalele P1–P10; 2 workshop-uri de testare; pre-testare EMC/RF (2 sesiuni)',
     'CDI I.3 + servicii de testare', 'L16–L22',
     '5.1 recrutarea panelului (≥ 40 % femei, ≥ 2 persoane cu deficiențe de vedere/motorii); 5.2 teren; 5.3 pre-scan; 5.4 analiza + raportul TRL 5',
     'R2 Raport TRL 5 (L22) = IE3'),
    ('A6', 'Protecția IP și valorificarea: căutare de anteriorități (L1–L3), design UE (≤ L5), marcă UE (≤ L6), evaluarea brevetabilității/modelului de utilitate (L12–L18); customer discovery (≥ 30 de interviuri), transformarea scrisorilor de intenție în acorduri, planul de comercializare',
     'CDI I.2/I.4 + conex II.1', 'L1–L24', '–', 'R3 (L18), R5 (L24)'),
    ('A7', 'Diseminare: manuscris (după depunerea IP), trimitere la o revistă OA peer-review (≤ L20), preprint în repozitoriu OA (Zenodo), prezentare la o conferință/târg, demo public',
     'Conex II.1', 'L14–L24', '–', 'R4'),
    ('A8', 'Management, audit financiar, comunicare și vizibilitate', 'Conex II.3, II.4, II.5', 'L1–L24', '–',
     'rapoarte de progres, raport de audit, afiș/panou, comunicate'),
]

GANTT = [
    ('A1 Specificații, protocoale, setup laborator', range(1, 4)),
    ('A2 Model de laborator M integrat', range(2, 9)),
    ('A3 Validare TRL 4 + raport TRL 4', range(6, 15)),
    ('A4 PCB propriu + carcasă Al, pre-serie', range(9, 18)),
    ('A5 Validare TRL 5 în mediu relevant + pre-scan', range(16, 23)),
    ('A6 Protecție IP + valorificare', range(1, 25)),
    ('A7 Diseminare', range(14, 25)),
    ('A8 Management, audit, vizibilitate', range(1, 25)),
]
DEPENDENCIES = ('Dependențe: A2 depinde de M1 (L3). A3 depinde de L2.1. Rev B și lotul de 15 din A4 depind de poarta IE2 (L14). '
                'A5 depinde de M3 (L17). Manuscrisul din A7 se trimite după depunerea cererilor IP (A6).')

MILESTONES = [
    ('M1', 'Banc de test validat', 'A1', 'L3', 'aparatele recepționate și calibrate; protocoalele P1–P10 aprobate de coordonator', 'management/CDI'),
    ('IE1', 'Raport intermediar CDI: modelul de laborator rulează integrat', 'A2', 'L6 (≤ 6 luni)', 'afișaj + touch + audio + AI funcționale; primele măsurători P1, P2, P5', 'calitativ CDI (obligatoriu)'),
    ('IE2', 'Raportul de etapă TRL 4 + obiectivele TRL 5', 'A3', 'L14 (≤ 2/3 = L16)', 'pragurile O1 atinse sau abaterile motivate; decizia go/no-go; dacă e no-go → Anexa 17 (eșec de cercetare)', 'calitativ CDI (obligatoriu)'),
    ('M3', '15 prototipuri pre-serie', 'A4', 'L17', 'QC trecut 15/15', 'CDI'),
    ('IE3', 'Raportul TRL 5', 'A5', 'L22', 'pragurile O3 atinse', 'calitativ CDI'),
    ('IE-M1..M3', 'Achiziții (L4, L15), progres financiar (≥ 30 % la L10, ≥ 70 % la L18), cerere IP depusă (L6)', 'A6, A8', 'L4–L18', '–', 'management'),
]

HYP = [
    ('H1', 'Randare', 'Dacă motorul de randare SDF anti-aliased rulează pe ESP32-S3 cu framebuffer în PSRAM și bounce-buffers pe magistrala RGB a panoului ST7701 480×480, atunci animația ochilor menține median ≥ 30 fps (p5 ≥ 24) cu Wi-Fi și BLE active, fără artefacte de drift.',
     'Poate un MCU de ~10 € să randeze procedural, fluid, o interfață expresivă pe un panou RGB fără memorie proprie, în paralel cu radioul?'),
    ('H2', 'Tastare/touch', 'Dacă tastatura QWERTY circulară (pas ≈ 0,0944·D → 6,7 mm pe Ø70, taste de margine „stăpâne” pe bordură) este combinată cu decodare probabilistică și diacritice RO automate, atunci utilizatorii ating ≥ 20 WPM cu UER ≤ 3 % și ≥ 97 % precizie touch.',
     'Este introducerea de text direct pe un ecran rotund de 2,8″ suficient de rapidă și precisă pentru notițe și comenzi reale, în română și engleză?'),
    ('H3', 'AI hibrid și voce', 'Dacă acțiunile utilizatorului sunt descrise printr-un singur set de scheme JSON executate în trei moduri (fără AI / Claude / ChatGPT) cu parser local RO/EN și degradare controlată, iar vocea circulă prin Opus/WebSocket către servere UE, atunci ≥ 90 % din comenzi se execută corect fără internet, latența vocală p50 ≤ 1,5 s (p90 ≤ 2,5 s) și 100 % din căderile de rețea/cheie sunt tratate fără blocare.',
     'Poate un dispozitiv să rămână util offline și rapid online, independent de un singur furnizor de AI?'),
    ('H4', 'RF prin aluminiu', 'Dacă antena BLE/Wi-Fi 2,4 GHz radiază printr-o fereastră polimerică în talpa unei carcase CNC din Al 6061, atunci atenuarea față de placa neîncasetată este ≤ 6 dB, legătura BLE rămâne stabilă ≥ 10 m în interior (PDR ≥ 99 %, reconectare ≤ 3 s) și pre-scanul EMC/RF nu are depășiri (marjă ≥ 3 dB).',
     'Se poate folosi o carcasă monomaterial din aluminiu (premium, reciclabilă) fără a compromite legătura radio?'),
    ('H5', 'Energie și reparabilitate', 'Dacă managementul luminii de fundal, somnul radioului și bateria de 2500–3000 mAh sunt integrate într-o arhitectură cu baterie înlocuibilă de utilizator (conector MX1.25, Torx, fără adeziv), atunci autonomia în profil tipic este ≥ 24 h (standby ≥ 7 zile), iar utilizatori neexperți înlocuiesc bateria în ≤ 5 min cu 100 % reușită și SUS ≥ 75.',
     'Poate un obiect premium, cu ecran IPS mare, să aibă o zi întreagă de autonomie și baterie schimbabilă de utilizator (Reg. (UE) 2023/1542 art. 11)?'),
]

# code, protocol, hyp, method, baseline, trl4, trl5
PROTOCOLS = [
    ('P1', 'fps la animația ochilor', 'H1', 'contor de cadre în firmware, log serial/telemetrie; 60 min; Wi-Fi + BLE active; 24 de reacții', 'X2', 'median ≥ 30 fps, p5 ≥ 24', 'median ≥ 30, p5 ≥ 24 pe 15 unități; 0 artefacte de drift raportate'),
    ('P2', 'Precizia touch', 'H2', 'grilă de ținte de 6,7 mm pe tot discul (inclusiv bordura), 200 de atingeri/persoană', 'X3', '≥ 97 % (N = 6)', '≥ 97 % (N ≥ 12)'),
    ('P3', 'Viteza și acuratețea tastării', 'H2', 'set de fraze MacKenzie–Soukoreff (EN) + set RO; 15 min de acomodare; WPM, UER, CER', 'X4', '≥ 15 WPM, UER ≤ 5 % (N = 6)', '≥ 20 WPM, UER ≤ 3 % (N ≥ 12)'),
    ('P4', 'Diacritice RO automate', 'H2', 'corpus de 300 de cuvinte RO', '–', '≥ 90 % corecte', '≥ 95 % corecte'),
    ('P5', 'Succesul offline', 'H3', 'corpus de 200 de comenzi RO/EN (alarme, mementouri, notițe, cronometre, liste), fără internet', 'X5', '≥ 90 %', '≥ 90 % pe comenzile reale din teren'),
    ('P6', 'Latența vocală end-to-end', 'H3', 'de la sfârșitul rostirii la primul sunet; 100 de ture; Wi-Fi casnic; servere UE', 'X6 (text)', 'p50 ≤ 1,8 s, p90 ≤ 3 s', 'p50 ≤ 1,5 s, p90 ≤ 2,5 s'),
    ('P7', 'Degradarea controlată', 'H3', 'se taie rețeaua sau cheia API în 50 de scenarii', '–', '100 % fără blocare; răspuns local', '100 %; ≥ 99 % sesiuni fără crash (telemetrie)'),
    ('P8', 'RF prin carcasă', 'H4', 'RSSI în cutia ecranată și la 1/3/5/10 m: placă goală vs. SLA vs. Al rev A/B; pachete pierdute BLE', 'X7', 'atenuare ≤ 8 dB (rev A)', '≤ 6 dB (rev B); legătură stabilă ≥ 10 m în interior; PDR ≥ 99 %; reconectare ≤ 3 s'),
    ('P9', 'Autonomie și consum', 'H5', 'analizor de consum; profil tipic definit (ecran activ 25 % din timp, 30 de interacțiuni vocale, BLE conectat); standby', 'X8', 'modelul de consum validat ± 15 %', '≥ 24 h în profil tipic; ≥ 7 zile standby'),
    ('P10', 'Reparabilitate + utilizabilitate', 'H5', 'cronometrarea înlocuirii bateriei (Torx) de către utilizatori neexperți; chestionar SUS; test de accesibilitate (voce, modul „taste mari”, contrast)', '–', 'procedura documentată; ≤ 10 min (N = 3)', '≤ 5 min, 100 % reușită (N ≥ 10); SUS ≥ 75'),
    ('P11', 'Pre-scan EMC/RF (EN 300 328, EN 301 489-1/-17)', '–', 'laborator acreditat, 2 sesiuni (rev A, rev B)', '–', '–', '0 depășiri, marjă ≥ 3 dB (rev B)'),
]

RELEVANT_ENV = ('Mediul relevant la TRL 5 (Anexa 18): configurația e „similară aplicației finale în aproape toate aspectele” '
                '(PCB propriu, carcasă finală din aluminiu, baterie finală, firmware + server UE) și rulează în condițiile reale de '
                'utilizare (locuințe și birouri din BI, rețele Wi-Fi casnice, zgomot ambiental, utilizatori reali), completate cu '
                'reproducerea controlată în laborator (cutie ecranată, atenuare calibrată). Diferențele față de produsul final (fără '
                'certificare CE, fără ambalaj, fără producție în serie) se analizează explicit în raportul TRL 5.')
ETHICS = ('Etică și date: consimțământ informat, telemetrie opt-in, pseudonimizare, ștergerea datelor la final, fără înregistrarea '
          'audio brută (GDPR). Informare AI Act art. 50 la prima pornire.')

DELIVERABLES = [
    ('L1.1', 'Specificația sistemului SOUL M', 'A1', 'L2', 'coordonator tehnic'),
    ('L1.2', 'Protocoalele experimentale P1–P11 cu praguri', 'A1', 'L3', 'coordonator tehnic'),
    ('L2.1', 'Modelul de laborator integrat + raportul IE1', 'A2', 'L6', 'inginer embedded'),
    ('R1', 'Raportul de validare TRL 4', 'A3', 'L14', 'coordonator tehnic'),
    ('L4.1', 'Documentația PCB rev A/B (scheme, Gerber, BOM) + CAD-ul carcasei rev B', 'A4', 'L12 / L16', 'inginer embedded'),
    ('L4.2', '15 prototipuri pre-serie + fișele QC', 'A4', 'L17', 'echipa'),
    ('L5.1', 'Rapoartele de pre-testare EMC/RF', 'A5', 'L18 / L21', 'laborator + coordonator'),
    ('R2', 'Raportul de validare TRL 5 (+ setul de date anonimizat)', 'A5', 'L22', 'coordonator tehnic'),
    ('R3', 'Cererile IP (design UE, marcă UE) + raportul de brevetabilitate', 'A6', 'L5 / L6 / L18', 'Andu + consilier PI'),
    ('R4', 'Manuscris trimis OA peer-review + preprint + prezentare la conferință', 'A7', 'L20 / L24', 'coordonator + student'),
    ('R5', 'Planul de valorificare + ≥ 2 acorduri', 'A6', 'L24', 'Andu'),
]

# nr, line, category, activity, eur
BUDGET = [
    ('I', 'ACTIVITATEA DE BAZĂ (CDI)', None, None, None),
    ('1', 'Salariu coordonator tehnic/științific (1.200 h × 34 €)', 'Cheltuieli salariale CDI (I.3)', 'A1–A5, A7', '40.800'),
    ('2', 'Salariu inginer embedded/firmware (1.680 h × 25 €)', 'Cheltuieli salariale CDI (I.3)', 'A2–A5', '42.000'),
    ('3', 'Salariu student cercetare (1.200 h × 12 €)', 'Cheltuieli salariale CDI (I.3)', 'A3, A5, A7', '14.400'),
    ('4', 'CAM 2,25 % pe liniile 1–3', 'Cheltuieli salariale CDI', '–', '2.187'),
    ('5', 'Osciloscop digital 4 canale ≥ 200 MHz (1.500 + TVA)', 'Active corporale – dezvoltare experimentală (subgr. 2.2)', 'A1–A5', '1.815'),
    ('6', 'Analizor de spectru ≥ 3 GHz (3.500 + TVA)', 'Active corporale (2.2)', 'A3, A4, A5', '4.235'),
    ('7', 'Analizor de consum / source-measure (1.000 + TVA)', 'Active corporale (2.2)', 'A3, A5', '1.210'),
    ('8', 'Cutie ecranată RF ≥ 60 dB (900 + TVA)', 'Active corporale (2.2)', 'A3, A5', '1.089'),
    ('9', 'Stație de lucru PC (2.000 + TVA)', 'Active corporale (grupa 3, echipamente informatice)', 'A2–A5', '2.420'),
    ('10', 'Imprimantă 3D SLA (3.900 + TVA)', 'Active corporale (2.1)', 'A2, A4', '4.719'),
    ('11', 'Materiale: 8 plăci 2.8C, 20 de panouri de 2,8″, 25 de seturi audio, 30 de celule Li-ion, componente, rășină, obiecte de inventar (3.725 + TVA)', 'Materiale, consumabile, obiecte de inventar', 'A2, A4', '4.507'),
    ('12', 'CNC + anodizare carcase Al 6061 (3 + 5 + 15 seturi) (5.550 + TVA)', 'Servicii (echivalente) pentru dezvoltare experimentală', 'A4', '6.716'),
    ('13', 'Fabricare + asamblare PCB propriu rev A/B (3.000 + TVA)', 'Servicii pentru dezvoltare experimentală', 'A4', '3.630'),
    ('14', 'Pre-testare EMC/RF, 2 sesiuni (4.000 + TVA)', 'Servicii de sprijinire a inovării (testare)', 'A5', '4.840'),
    ('15', 'Evaluare preliminară EN 18031 (2.500 + TVA)', 'Consultanță în inovare (utilizarea standardelor)', 'A4', '3.025'),
    ('16', 'Servicii CDI externalizate: proiectarea/validarea antenei prin carcasa din aluminiu (4.500 + TVA)', 'Servicii CDI externalizate (I.3)', 'A4', '5.445'),
    ('17', '2 workshop-uri/sesiuni de testare cu utilizatori', 'Workshop-uri colaborative (validare TRL 4–5)', 'A5', '2.500'),
    ('18', 'SaaS: API AI (LLM/STT/TTS), găzduire UE, CAD (≈ 4.132 + TVA)', 'Servicii SaaS pentru CDI', 'A2–A5', '5.000'),
    ('19', 'Taxe EUIPO: marcă UE (3 clase ≈ 1.050) + desen industrial multiplu (≈ 940)', 'Obținerea/protejarea activelor necorporale', 'A6', '1.990'),
    ('20', 'Consilier în proprietate industrială: anterioritate, depunere, brevetabilitate (1.250 + TVA)', 'Consultanță în inovare (protecția activelor necorporale)', 'A6', '1.512'),
    ('', 'Subtotal activitate de bază', '', '', '154.040'),
    ('II.1', 'DISEMINARE (conex, în afara plafonului de 10 %)', None, None, None),
    ('21', 'Taxă de publicare open-access peer-review (APC ≈ 2.800 + TVA)', 'Publicarea rezultatelor', 'A7', '3.388'),
    ('22', 'Conferință/târg internațional: taxă, transport, cazare, diurnă, max. 2 persoane', 'Participare la conferințe/târguri', 'A7', '2.900'),
    ('23', 'Customer discovery / focus-grupuri (1.240 + TVA)', 'Promovare pentru validare comercială', 'A6', '1.500'),
    ('', 'Subtotal II.1', '', '', '7.788'),
    ('II.2–II.5', 'PLAFON CUMULAT 10 % DIN TOTAL', None, None, None),
    ('24', 'II.2 Consultanță pentru CF + validarea Raportului științific de către expert', 'Consultanță pentru CF (precontractuală)', 'A0', '4.500'),
    ('25', 'II.3 Salariu manager de proiect (480 h × 18 €) + CAM', 'Management', 'A8', '8.834'),
    ('26', 'II.4 Audit financiar (2.000 + TVA)', 'Audit', 'A8', '2.420'),
    ('27', 'II.5 Comunicare și vizibilitate (1.000 + TVA)', 'Informare și publicitate', 'A8', '1.210'),
    ('', 'Subtotal II.2–II.5', '', '', '16.964'),
    ('', 'TOTAL COSTURI DIRECTE', '', '', '178.793'),
    ('28', 'Costuri indirecte 7 % × costuri directe (chirie, utilități, personal suport)', 'Rată forfetară', '–', '12.515'),
    ('', 'TOTAL ELIGIBIL = NERAMBURSABIL (100 %)', '', '', '191.308'),
]
BUDGET_CHECKS = [
    ('50.000 € ≤ nerambursabil ≤ 200.000 €', '191.308 € (rezervă de curs ~4,3 %)', 'îndeplinit'),
    ('Activitatea de bază ≥ 50 % din eligibil', '154.040 / 191.308 = 80,5 %', 'îndeplinit'),
    ('II.2 + II.3 + II.4 + II.5 ≤ 10 % din eligibilul total', '16.964 / 191.308 = 8,9 % (plafon 19.131 €)', 'îndeplinit'),
    ('Indirecte = exact 7 % din directe', '12.515 €', 'îndeplinit'),
    ('De minimis: 191.308 € + ajutoarele anterioare ≤ 300.000 €', 'spațiu necesar ≥ 108.692 € liber', '[[Ct: de verificat în RegAS]]'),
    ('Salarii ≤ HG 1188/2022 Anexa 2', '34 ≤ 35 · 25 ≤ 35 · 12 ≤ 15 · 18 ≤ 50 €/h', 'îndeplinit'),
    ('Eșec de cercetare: max. 50 % decontat; activele pentru TRL 5 cad', 'liniile 12 (lotul de 15), 13 (rev B), 14 se angajează după IE2', 'îndeplinit'),
]

# risk, desc, prob, impact, measures
RISKS = [
    ('R1', 'Eșec de cercetare: H1/H3/H4 nu se validează (fps < 30 pe RGB, atenuare RF > 6 dB, latență > prag)', 'Medie', 'Mare',
     'poarta IE2 la L14 (≤ 2/3); alternative tehnice pregătite (randare parțială, bounce-buffers, fereastră radio mai mare, antenă externă în talpă, server mai aproape/model mai mic); dacă tot nu merge → Anexa 17, se decontează max. 50 % și nu cumpărăm activele pentru TRL 5 înainte de poartă'),
    ('R2', 'Recrutarea coordonatorului/inginerului întârzie', 'Medie', 'Mare',
     'declarații de disponibilitate semnate înainte de depunere; detașare de la o organizație de cercetare ca variantă'),
    ('R3', 'Lanțul de aprovizionare (panouri, module, CNC)', 'Medie', 'Mediu', '2 furnizori pe linie; stoc tampon la L2'),
    ('R4', 'Ghidul final schimbă plafoanele (Anexa 20) sau calendarul', 'Medie', 'Mediu', 'buget modular; rezervă de curs 4 %'),
    ('R5', 'Curs valutar: plafonul de minimis/200 k€ depășit la semnare', 'Redusă', 'Mediu', '191 k€ în loc de 200 k€'),
    ('R6', 'ARTEMIS devine plătitoare de TVA → TVA neeligibilă', 'Medie', 'Mediu', 'monitorizare lunară a CA; notificarea AM-ului; reducerea TVA din buget'),
    ('R7', 'Cash-flow până la rambursare', 'Medie', 'Mare', 'prefinanțare (§12.1), cereri de plată (§12.2), linie de credit FNGCIMM'),
    ('R8', 'Dependența de API-uri terțe (Claude/OpenAI/STT/TTS)', 'Redusă', 'Mediu', 'modul offline; mai mulți furnizori; server UE propriu'),
    ('R9', 'Conformitate (AI Act art. 50, GDPR, EN 18031)', 'Redusă', 'Mediu', 'informare AI la pornire; DPA; evaluarea EN 18031 (linia 15)'),
    ('R10', 'Conflict cu planul Founders 00 (vânzarea a 25 buc. cu CE în primăvara 2027): dacă SOUL M e vândut/certificat înainte de contract, proiectul pare „demarat/finalizat” și TRL > 5', 'Mare, dacă nu se decide', 'Eliminatoriu',
     'nu certificăm CE și nu vindem SOUL M înainte de contract; waitlist-ul rămâne (e dovadă de piață); Founders 00 devine pasul post-PoC [[A: decizie de confirmat de Andu]]'),
    ('R11', 'Schimbări de acționariat (ex. un investitor angel intră în ARTEMIS)', 'Medie', 'Eliminatoriu (condiții artificiale, §5.1.2)',
     'investiția se face într-un vehicul separat sau după durabilitate, cu avizul AM; fără transfer de IP în durabilitate'),
    ('R12', 'Conflict de marcă „SOUL”', 'Mare', 'Mediu', 'căutare TMview acum; marcă figurativă/compusă ca rezervă; designul protejează forma oricum'),
]

POSTPOC = [
    ('Founders 00 (pilot)', 'TRL 6 → 7', 'An 1 (S1)', '25 de unități numerotate, PCB rev C, certificare CE/RED + EN 18031 (5–12 k€ + 0–9 k€), înregistrări ANMAP, GPSR; vânzare în RO; feedback',
     'venituri din precomenzi (25 × 349 €), fonduri proprii, EUIPO SME Fund (IP), EDIH (testare)'),
    ('Batch 1 / CE complet', 'TRL 7 → 8', 'An 1 (S2) – An 2', '300 de unități, scule (matrițe parțiale), aplicația de telefon, 3–5 piețe UE (EPR, reprezentant autorizat)',
     'PR BI 1.2 (produse noi în IMM) sau Eurostars Call 12/13, pre-seed/angel într-un vehicul care nu afectează PoC-ul, crowdfunding (Indiegogo/Gamefound — Kickstarter nu e disponibil din RO)'),
    ('SOUL Standard', 'TRL 9', 'An 2 – An 3', '1–10 k unități/an, PCB cu modul certificat, cost < 60 €/buc., canale: online direct + retail de design + B2B (echipe care folosesc Claude Code)',
     'venituri, EIC Accelerator (la TRL 6–8), credit garantat FNGCIMM pentru stoc'),
    ('Platforma', 'TRL 9', 'An 3 – An 5', 'abonament opțional (voce/memorie), accesorii, SoulOS pentru parteneri, licențierea designului/firmware-ului',
     'venituri recurente, licențe'),
]

IPPLAN = [
    ('0', 'Căutare TMview + DesignView pentru „SOUL” (clasele 9, 42, 14, 28) — risc mare de conflict (SOUL Electronics etc.)', 'acum, înainte de depunere', '0 €'),
    ('0b', 'Dacă marca verbală e liberă: poate fi depusă înainte de proiect prin EUIPO SME Fund (voucher 75 %, până la 04.12.2026). Atunci nu mai apare în bugetul PoC (fără dublă finanțare, §5.2.1 V), iar linia 19 se folosește pentru marca figurativă/clase suplimentare și design', 'T−8 săpt.', 'în afara proiectului'),
    ('1', 'Consilier PI: anterioritate + strategie (design / model de utilitate OSIM / brevet)', 'L1–L3', 'linia 20'),
    ('2', 'Desen/model industrial UE multiplu: corpul SOUL M + capsula OU (+ eventual interfața grafică a ochilor). Grație de 12 luni de la prima divulgare publică: dacă randările v6/M sunt publice din sept. 2026, cererea se depune până în sept. 2027; dacă termenul cade înainte de contract, o depunem după depunerea CF, ca activitate precontractuală, la risc propriu', '≤ L5', 'linia 19'),
    ('3', 'Marcă UE (verbală sau figurativă, 3 clase)', '≤ L6', 'linia 19'),
    ('4', 'Evaluarea brevetabilității/modelului de utilitate: carcasa cu fereastră radio polimerică + mecanismul bateriei înlocuibile + contactele OU; metoda de decodare a tastaturii circulare', 'L12–L18', 'linia 20; depunerea OSIM, dacă merită, în perioada de durabilitate'),
    ('5', 'Publicare (articol OA, preprint Zenodo) doar după depunerea cererilor de la pașii 2–3', 'trimitere ≤ L20', 'linia 21'),
    ('6', 'Secret comercial: parametrii decodorului, datele de antrenare, tuning-ul antenei', 'continuu', '–'),
    ('7', 'Cesiunea drepturilor Andu → ARTEMIS (codul și designul pre-proiect) + registrul licențelor open-source (MIT/OFL)', 'înainte de depunere', '0 €'),
]

CIRCULAR = [
    ('Prelungirea duratei de viață / reparabilitate', 'baterie înlocuibilă de utilizator (conector MX1.25, spumă, nu adeziv; Reg. 2023/1542 art. 11); închidere cu șuruburi Torx standard; module înlocuibile (panou, placă, difuzor)', 'P10: înlocuire ≤ 5 min; ghid de reparare publicat'),
    ('Design pentru dezasamblare și reciclare', 'carcasă monomaterial Al 6061 (reciclabil nelimitat), fără adezivi structurali; talpă polimerică detașabilă; marcarea materialelor', 'raport de dezasamblare: ≥ 90 % din masă separabilă pe fracții'),
    ('Actualizare software (OTA) în loc de înlocuire hardware', 'funcții noi livrate prin OTA semnat; hardware-ul nu se învechește la schimbarea modelului AI (BYO-AI)', 'OTA semnat demonstrat la TRL 5'),
    ('Independența de server (evită „bricking”-ul de tip Humane)', 'modul offline complet + serverul AI publicabil/escrow', 'P5, P7'),
    ('Reducerea resurselor pe unitatea de output', 'un singur obiect pentru notițe/alarme/remindere/aprobări Claude; capsula OU fără baterie; ambalaj din pulpă/carton', 'BOM + fișa materialelor'),
    ('Piese de schimb', 'angajament: baterii și piese de schimb 5 ani', 'Plan de afaceri §6'),
]

NOVELTY = [
    ('N1', 'Randare SDF anti-aliased a „ochilor” parametrici pe MCU, pe un panou RGB 480×480 fără memorie proprie (framebuffer în PSRAM)', 'competitorii folosesc animații pre-randate (sprite-uri) sau SoC-uri scumpe', '≥ 30 fps cu Wi-Fi + BLE active; 24 de reacții procedurale; personalitate derivată din ID-ul cipului'),
    ('N2', 'Round QWERTY cu tastele de la margine „stăpâne” pe bordură, decodare probabilistică, diacritice RO automate', 'smartwatch-uri: 10–30 WPM în literatură; fără suport RO', '≥ 20 WPM, UER ≤ 3 %, diacritice automate'),
    ('N3', 'Arhitectură „un singur set de acțiuni, trei moduri” (fără AI / Claude / ChatGPT), fallback local, conector MCP, cheie proprie criptată', 'dispozitivele au un singur furnizor, au cloud obligatoriu sau merg doar offline', '≥ 90 % succes offline; continuitate 100 % la căderea rețelei'),
    ('N4', 'Carcasă CNC din aluminiu cu antenă prin fereastră polimerică în talpă + încărcare prin pini în capsula OU', 'carcasele metalice blochează RF; obiectele premium nu au AI', 'atenuare ≤ 6 dB; legătură BLE ≥ 10 m'),
    ('N5', 'Reparabilitate de la proiectare: baterie schimbabilă de utilizator (Torx), fără adeziv pe celulă, componente modulare, OTA', 'multe gadgeturi au baterii lipite/nedemontabile', 'înlocuire ≤ 5 min de către utilizatori neexperți'),
]

# existing evidence (TRL 3); numbers verified 25.09.2026 on commit b84f714
EVIDENCE = [
    ('D1', 'Rezultat experimental (teste automate) + cod sursă', 'Firmware „Suflet” + modulele SoulOS v1 (Canvas SDF, Face, Brain, Personality, Gestures, ClaudeLink, Keyboard, TextField, Predictor, TimePicker, Alarms, Shell); 61/61 teste Unity trec pe PC (`pio test -e native`, 25.09.2026; 55 în v1 + 6 pentru geometria 480 px a lui SOUL M); compilează pentru amoled143 / amoled175 / lcd28 (SOUL M) / sim', '2026-09', 'depozit git, `firmware/` (README); commit b84f714; raport de testare anexat [[A: export log + hash la data depunerii]]'),
    ('D2', 'Simulator / model software', 'Simulator pe PC care rulează aceleași fișiere ca placa și produce cadrele reale ale motorului (10 clipuri: idle, boop, purr, dizzy, sleep…) + cadre cu tastatura și time-picker-ul, inclusiv la 480 px', '2026-09', '`firmware/sim`, `media/` (clipuri MP4/GIF anexate)'),
    ('D3', 'Rezultat experimental (teste automate) + cod sursă', 'Serviciul AI `suflet_ai` v0.2: 3 moduri (fără AI / Claude / ChatGPT), 8 acțiuni cu scheme JSON stricte, parser local RO/EN, conector MCP, cheie proprie criptată; 49/49 teste pytest trec (25.09.2026)', '2026-09', '`ai/` (README, tests/)'),
    ('D4', 'Prototip interactiv (software)', 'Prototipul web SoulOS: tastatura rotundă interactivă, testabilă cu utilizatori la scara 70 mm', '2026-09', '`os/index.html`, `os/research/04`, `os/ARCHITECTURE.md`'),
    ('D5', 'Studiu analitic', 'Geometria tastaturii pe diametre (pas = 0,0944·D → 6,7 mm pe Ø70) și analiza panoului: justificarea analitică a alegerii 2,8″ IPS 480×480', '2026-09', '`research/12` §1–2'),
    ('D6', 'Prototip virtual (CAD)', 'CAD parametric (CadQuery), STL/STEP pentru P0, randări v6/v7/M ale corpului de ~90 × 103 × 31 mm din aluminiu', '2026-09', '`prototip/`, `cad/`, `renders/`'),
    ('D7', 'Documentare cronologică', 'Istoricul git cu commit-uri datate (primul commit SOUL: 24.09.2026)', '2026-09', 'depozitul vault (export `git log` anexat)'),
    ('D8', 'Raport de laborator TRL 3 pe hardware (ÎN CURS — de finalizat înainte de depunere)', 'Experimentele X1–X8 pe placa Waveshare ESP32-S3-Touch-LCD-2.8C (cumpărată din fonduri proprii, în afara bugetului): port, fps, precizie touch, tastare pilot, parser offline, latență AI, RSSI prin aluminiu, consum', '[[A+Cl: T−6 … T−2 săpt.]]', '„Raport de laborator TRL 3 — SOUL M (2.8C)”, datat și semnat, cu loguri, fotografii, video cu marcaj de timp și hash git [[de anexat]]'),
]

XTESTS = [
    ('X1', 'Port pe 2.8C: driver RGB ST7701 (Arduino_GFX `Arduino_RGB_Display`), framebuffer în PSRAM, touch GT911', 'build `lcd28` (codul există, compilează; neflash-uit)', 'firmware rulând pe placă; video'),
    ('X2', 'fps la ochi', 'contor de cadre pe serial, 10 min, cu Wi-Fi oprit/pornit', 'median/p5 fps (baseline pentru H1)'),
    ('X3', 'Precizia touch', 'test „grilă de ținte” 6,7 mm, 200 de atingeri, 3 persoane', '% atingeri corecte, eroare medie în mm'),
    ('X4', 'Tastare pilot pe prototipul web (desktop/tabletă la scara 70 mm) și pe placă', 'fraze standard (MacKenzie), N = 5', 'WPM, rata de eroare (baseline pentru H2)'),
    ('X5', 'Parserul offline pe un corpus de 200 de comenzi RO/EN', 'pytest + script de corpus', '% comenzi corecte (baseline pentru H3)'),
    ('X6', 'Latența unui tur AI (text) cu Claude/OpenAI', '50 de tururi, cronometrare', 'p50/p90 în secunde'),
    ('X7', 'Împerecherea BLE cu Claude Desktop Hardware Buddy + RSSI prin plăci de aluminiu (tablă 1,5 mm)', 'telefon cu nRF Connect, 1/3/5 m', 'atenuare orientativă în dB'),
    ('X8', 'Consumul plăcii (ecran aprins/stins)', 'multimetru USB', 'mA (baseline pentru H5)'),
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
    'Profesioniștii care lucrează zilnic cu asistenți AI (dezvoltatori care folosesc Claude Code/Cowork, creatori, freelanceri): nevoia de aprobări și notițe rapide, fără telefon.',
    'Utilizatorii care vor un asistent privat, cu funcționare offline, fără abonament obligatoriu.',
    'Persoanele cu nevoi de accesibilitate (control vocal, taste mari).',
    'Ecosistemul regional: laboratoare universitare (UPB), ateliere CNC/PCB, laboratoare de testare.',
]
