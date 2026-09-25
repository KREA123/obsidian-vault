# -*- coding: utf-8 -*-
import sys, copy
from docx import Document
from docxlib import *
from data import *
import proj

SRC = 'a3.docx'
OUT = sys.argv[1]
d = Document(SRC)
B = list(d.element.body.iterchildren())
NUM = 1  # bullet numbering in this template
RATE = 5.09


def lei(eur):
    return f"{eur * RATE:,.0f}".replace(',', '.')


def fill(i, items):
    """Replace paragraph B[i] with a sequence of items (str paragraphs, '- ' bullets, ('table', el))."""
    p = B[i]
    proto = copy.deepcopy(p)
    first = True
    cur = p
    for it in items:
        if isinstance(it, str):
            if it.startswith('- '):
                el = clone_par(proto, it[2:], numid=NUM)
            else:
                el = clone_par(proto, it)
            if first:
                p.addprevious(el); delete(p); first = False
            else:
                cur.addnext(el)
            cur = el
        else:  # table element
            if isinstance(it, tuple):
                it = it[1]
            if first:
                p.addprevious(it); delete(p); first = False
            else:
                spacer = clone_par(proto, '')
                cur.addnext(spacer); cur = spacer
                cur.addnext(it)
            cur = it
            sp = clone_par(proto, '')
            cur.addnext(sp); cur = sp
    return cur


TPROTO = B[54]  # objectives table: header row 0, data row 1


def T(header, data, widths, **kw):
    return build_table(TPROTO, header, data, widths, **kw)


def drop(*idx):
    for i in idx:
        delete(B[i])


# ------------------------------------------------------------------ header / cover
for p in d.sections[0].header.paragraphs:
    for r in p.runs:
        if 'Denumire' in r.text:
            r.text = '  |  ARTEMIS DIGITAL S.R.L. — SOUL-PoC'
        elif r.text.strip() in ('[', 'solicitant]', ' solicitant]'):
            r.text = ''

hdr = rows(B[6])
vals = [APPLICANT, '[[A/Ct: CUI]]', TITLU + ' (acronim SOUL-PoC)', RIS3,
        'TRL 3 — atestat prin Raportul științific (Anexa 16), dovezile D1–D8',
        'TRL 5 (validare în mediu relevant, L22); TRL 4 = rezultat intermediar (poarta IE2, L14)', '[[ZZ/LL/AAAA]]']
for tr, v in zip(hdr, vals):
    set_cell(tcs(tr)[1], v)

# TOC: drop the guide entries
for sdt_p in list(B[27].iter(W('p'))):
    t = ptext(sdt_p)
    if 'GHID DE UTILIZARE' in t or 'Cum sa folositi' in t:
        delete(sdt_p)

# remove usage guide section 29..40
drop(*range(29, 41))

# ------------------------------------------------------------------ I
drop(42, 45, 46)
fill(48, [
    f'Finanțarea nerambursabilă solicitată, de **{TOTAL}** (100 % din valoarea eligibilă, ajutor de minimis), este folosită exclusiv pentru a valida modelul conceptual **SOUL** de la **TRL 3** (dovadă experimentală a conceptului pe componente separate, atestată în Raportul științific) la **TRL 5** (sistem integrat validat în mediu relevant), în **24 de luni**, la sediul ARTEMIS DIGITAL S.R.L. din București.',
    'SOUL este un **dispozitiv tangibil de interacțiune om–mașină / asistent personal AI**: un obiect de ~90 × 103 × 31 mm din aluminiu, cu afișaj rotund IPS de 2,8″ (480×480), care arată doi ochi expresivi, are o tastatură circulară și execută acțiuni utile (notițe, alarme, mementouri, liste, aprobări pentru Claude Code/Cowork) **offline** sau cu asistentul AI ales de utilizator (Claude, ChatGPT sau cheie proprie).',
    'Problema adresată este europeană și tehnică: dispozitivele AI dedicate lansate în 2023–2025 au eșuat din cauza **dependenței de cloud** (Humane AI Pin a fost oprit de la distanță la 28.02.2025; Moxie s-a oprit odată cu serverul, în dec. 2024), a **latenței** (BubblePal: 10–15 s), a **interfeței** (introducerea de text pe ecrane mici și rotunde rămâne o problemă deschisă de cercetare HCI) și a **închiderii ecosistemului** (un singur furnizor, abonament obligatoriu). În paralel, Reg. (UE) 2023/1542 art. 11 impune din **18.02.2027** baterii portabile înlocuibile de utilizator, Dir. (UE) 2024/1799 introduce dreptul la reparare, iar Reg. delegat (UE) 2022/30 + EN 18031 impun securitate cibernetică echipamentelor radio (surse în Secțiunea III).',
    'Proiectul demonstrează experimental ipoteza de cercetare: **dacă** un dispozitiv de 90 × 103 × 31 mm integrează (i) randare SDF optimizată pe ESP32-S3, (ii) o tastatură QWERTY circulară cu decodare probabilistică, (iii) o arhitectură AI hibridă local-first cu degradare controlată și (iv) o carcasă din aluminiu cu fereastră radio polimerică și baterie înlocuibilă, **atunci** sistemul atinge simultan, în mediu relevant, ≥ 30 fps, ≥ 20 cuvinte/min, latență vocală p50 ≤ 1,5 s, ≥ 90 % comenzi corecte fără internet, atenuare RF prin carcasă ≤ 6 dB și ≥ 24 h de autonomie.',
    'Banii acoperă: echipa CDI (coordonator tehnic/științific, inginer embedded, student), aparatura de măsură strict necesară (osciloscop, analizor de spectru, analizor de consum, cutie ecranată RF, PC, imprimantă SLA), prototiparea în două iterații (PCB propriu rev A/B, carcase CNC din Al 6061), 15 prototipuri pre-serie, pre-testarea EMC/RF, evaluarea preliminară EN 18031, protecția IP (design și marcă UE), publicarea open-access și managementul.',
    'La final, ARTEMIS va deține un rezultat validat la TRL 5 (15 prototipuri testate de ≥ 12 utilizatori timp de 4 săptămâni), două cereri de protecție IP, un articol trimis la o revistă open-access peer-review și ≥ 2 acorduri de pilot/distribuție, adică punctul de pornire pentru certificarea CE și seria pilot (Secțiunea VI).',
])

drop(51)
fill(53, [f'**Obiectiv general:** {OBJ_GENERAL} Obiectivele specifice O1–O4 sunt identice cu cele din Cererea de finanțare și din Raportul științific (Anexa 16, §1.4).'])
t = B[54]
rs = rows(t)
for tr, o in zip(rs[1:4], OBJECTIVES[:3]):
    fill_row(tr, list(o))
add_row_after(rs[3], list(OBJECTIVES[3]))
t.addnext(copy.deepcopy(B[55]))
nxt = t.getnext()
write_runs(nxt, 'Rezultate așteptate (max. 5, corelate cu CF): ' + ' · '.join(f'**{c}** — {n} ({m})' for c, n, m in RESULTS) + '.', plain=True)

drop(57)
fill(58, [
    'Managementul proiectului este asigurat de o echipă de 4 persoane, cu responsabilități separate:',
    '- **Manager de proiect — Andu, administratorul ARTEMIS** (20 h/lună, activitate conexă II.3): planificare, achiziții conform Ordinului MFE 1284/2016, raportare către AM PR BI, cereri de plată/rambursare, relația cu partenerii, valorificarea comercială (A6) și vizibilitatea (A8).',
    '- **Coordonator tehnic/științific** [[Nume Prenume — de nominalizat înainte de depunere]] (50 h/lună): arhitectura sistemului, protocoalele P1–P11, rapoartele TRL 4 și TRL 5, articolul științific; propune decizia de poartă.',
    '- **Inginer embedded/firmware** [[Nume Prenume]] și **student cercetare** [[Nume Prenume]]: execută activitățile A2–A5 și A7.',
    '**Structura decizională.** Comitetul de coordonare (manager + coordonator tehnic) se reunește lunar și aprobă planul pe luna următoare. Deciziile tehnice se iau de coordonatorul tehnic; deciziile cu impact asupra bugetului, calendarului sau rezultatelor se iau de manager, cu notificarea AM PR BI când sunt necesare acte adiționale.',
    '**Poarta de decizie IE2 (L14).** La luna 14 (înainte de 2/3 din durată, L16) Raportul de etapă TRL 4 compară măsurătorile P1–P8 cu pragurile O1. Decizia go/no-go condiționează angajarea cheltuielilor specifice TRL 5 (liniile 12 — lotul de 15 carcase, 13 — rev B, 14 — pre-scan). În caz de no-go se aplică procedura de eșec de cercetare (Anexa 17).',
    '**Gestiunea riscurilor.** Registrul de riscuri (R1–R12, §6.4) se revizuiește lunar; fiecare risc are un responsabil și un indicator de declanșare.',
    '**Monitorizare și raportare.** Indicatorii de etapă IE1 (L6), IE2 (L14), IE3 (L22) și indicatorii de management IE-M1..M3 (achiziții L4/L15; progres financiar ≥ 30 % la L10 și ≥ 70 % la L18; cerere IP depusă la L6) intră în Planul de monitorizare (Anexa 13). Pontaje lunare pe proiect, contabilitate analitică separată, arhivă electronică (git + dosar partajat) pentru toate datele experimentale.',
    '**Experiență cu finanțare europeană:** ARTEMIS nu a implementat până acum proiecte cu finanțare europeană [[A: confirmă]]. Compensăm prin audit financiar (linia 26), prin consultanță pentru pregătirea dosarului (linia 24) și prin calendarul de raportare de mai sus.',
])

drop(61, 62)
fill(63, [
    '**Problema.** Asistenții AI generativi sunt captivi în telefon și în ecranul computerului, iar dispozitivele AI dedicate încercate până acum au eșuat din motive tehnice și de arhitectură: dependență de cloud („bricking” la închiderea serverului), latență mare, interfață nepotrivită pentru text pe ecrane mici, un singur furnizor de AI și baterii nereparabile.',
    '**Soluția.** SOUL M: afișaj rotund IPS 2,8″ 480×480 pe ESP32-S3 (framebuffer în PSRAM), touch capacitiv GT911, IMU, 2 microfoane MEMS, amplificator, PMU, baterie Li-ion 2500–3000 mAh înlocuibilă, antenă BLE/Wi-Fi care radiază printr-o fereastră polimerică din talpa unei carcase CNC din Al 6061, încărcare prin pini în capsula „OU”. Firmware-ul SoulOS randează procedural ochii (SDF anti-aliased), rulează tastatura circulară și execută un singur set de acțiuni în trei moduri: fără AI, cu Claude, cu ChatGPT.',
    '**Tipul de inovare: inovare de produs** — un bun fizic nou (hardware + carcasă), cu firmware încorporat și un serviciu software asociat (serverul AI UE). Nu este o simplă integrare de componente: cele cinci elemente de diferențiere N1–N5 (tabelul de mai jos) cer dezvoltare experimentală și validare prin măsurători.',
    ('table', T(['Cod', 'Element nou', 'Stadiul actual / competitori', 'Contribuția SOUL-PoC (măsurabilă)'],
                [list(n) for n in NOVELTY], [700, 3200, 2800, 2938])),
    '**De unde pornim (TRL 3).** Există firmware testat (61/61 teste Unity), simulator, serviciul AI (49/49 teste), prototipul web al tastaturii, analiza geometrică și CAD-ul; înainte de depunere rulăm experimentele X1–X8 pe placa de dezvoltare SOUL M (dovezile D1–D8, §4.2).',
    '**Ce demonstrează proiectul.** TRL 4 (L14): modelul integrat funcționează în laborator la pragurile O1. TRL 5 (L22): 15 prototipuri cu PCB propriu și carcasă finală din aluminiu sunt folosite 4 săptămâni de ≥ 12 utilizatori din București-Ilfov, în locuințe și birouri reale, la pragurile O3.',
])

# ------------------------------------------------------------------ II
drop(67)
t = B[70]
comp = [APPLICANT, '[[A/Ct: CUI]] / [[J40/…/…]]', 'Societate cu răspundere limitată (Legea 31/1990)',
        '[[ZZ/LL/AAAA — din certificatul constatator]]', '[[Adresa completă]], București, [[sector]]',
        'Sediul social (spațiu de birou + laborator electronic) [[A: confirmă; dacă e alt spațiu, adresa punctului de lucru din BI]]',
        '[[Ct: cod CAEN principal + denumire]]',
        '[[Ct: codul CAEN pentru cercetare-dezvoltare în științe naturale și inginerie, autorizat la locul de implementare]]',
        '[[Ct: valoare în RON]]', '[[A: Asociat 1 – X %; …]]', '[[Nume Prenume]] („Andu”), administrator',
        'Microîntreprindere [[Ct: de confirmat prin Anexa 7, inclusiv întreprinderile partenere/legate]]', '[[Ct: număr]]']
for tr, v in zip(rows(t), comp):
    set_cell(tcs(tr)[1], v)

drop(73)
fill(74, [
    'ARTEMIS DIGITAL S.R.L. este o firmă din București care operează brandul **KREA** (servicii digitale: dezvoltare web/IT și marketing digital) și magazinul online **MundiShop** (comerț electronic) [[A: completați 2–3 fraze cu cifre: ani de activitate, clienți, echipă]]. Activitatea curentă aparține domeniului RIS3 **TIC**: dezvoltare software, integrare de servicii cloud, automatizări și analiză de date.',
    'Din septembrie 2026 firma desfășoară o activitate proprie de cercetare-dezvoltare: **SOUL**, un dispozitiv de interacțiune om–mașină care leagă TIC (firmware embedded, AI hibrid, securitate cibernetică) de **Sisteme și Componente Inteligente** (sistem ciber-fizic cu afișaj, senzori, radio, energie). Proiectul PoC transformă această direcție într-o linie de produs proprie: trecerea de la servicii pentru clienți la un produs cu proprietate intelectuală, vândut în UE. Experiența de comerț electronic (MundiShop) și de marketing digital (KREA) este direct utilă la validarea comercială (A6) și la lansarea post-PoC.',
])

drop(77)
fill(78, [
    'Da. Rezultatele CD obținute până la depunere (septembrie 2026, documentate în depozitul git cu commit-uri datate) sunt cedate de autorul lor (Andu) către ARTEMIS prin contract de cesiune, cu titlu gratuit, înainte de depunere [[A: semnează cesiunea — model în dosar]]. Componentele open-source folosite (claude-desktop-buddy — MIT; fontul Nunito — OFL; xiaozhi-esp32 — MIT) sunt listate cu licențele lor.',
    ('table', T(['Cod', 'Rezultat CD existent', 'Unde / dovadă'],
                [[e[0], e[2], e[4]] for e in EVIDENCE], [700, 5938, 3000])),
])

drop(81)
t = B[82]
delete(rows(t)[1])
set_cell(tcs(rows(t)[1])[0], 'Nu este cazul — ARTEMIS nu are proiecte anterioare cu finanțare europeană sau națională [[A: confirmă]]. Experiența CDI este demonstrată prin rezultatele SOUL din §2.3 și dovezile D1–D8 din Raportul științific.')

drop(85)
fill(86, [
    'Colaborările planificate acoperă tot ce nu deține ARTEMIS: expertiză RF, laboratoare acreditate, utilizatori-pilot și canale de valorificare. Fiecare se confirmă prin documente anexate la CF:',
    '- **Organizație de cercetare parteneră** [[UPB ETTI / IMT București / ICI — de confirmat]]: expertiză RF/antene, acces la camera anecoică, recrutarea studentului; scrisoare de intenție/acord de colaborare [[de obținut]].',
    '- **Laborator EMC/RF acreditat** [[denumire — ex. laborator RO + alternativă UE]]: pre-scan EN 300 328 / EN 301 489 (2 sesiuni); ofertă + scrisoare de disponibilitate [[de obținut]].',
    '- **Ateliere CNC și fabricanți PCB** (RO/UE și internaționali): prototipare rev A/B și lotul de 15; oferte [[de obținut, 2 pe linie]].',
    '- **Utilizatori-pilot și parteneri comerciali**: ≥ 2 scrisori de intenție cu toate cele 7 elemente cerute de grilă (un retailer/distribuitor, o firmă de software care folosește Claude Code, un living lab/laborator universitar) [[de obținut, datate ≤ 6 luni înainte de depunere]].',
    '- **Asociație a persoanelor cu dizabilități** [[denumire]]: recrutarea a ≥ 2 participanți cu deficiențe de vedere/motorii și testul public de accesibilitate (măsura suplimentară de egalitate de șanse).',
    '- **Expert științific independent** [[Nume Prenume, afiliere]]: validarea Raportului științific.',
])

# ------------------------------------------------------------------ III
drop(90, 93, 94)
fill(95, [
    'SOUL se adresează intersecției a trei piețe în creștere, cu date verificabile (link și dată pentru fiecare cifră):',
    '- **Adopția AI generativ în UE.** În 2025, **32,7 %** din persoanele de 16–74 ani din UE au folosit instrumente de AI generativ (25,1 % în scop personal, **15,1 % la muncă**); România are cel mai mic nivel (**17,8 %**), deci cea mai mare marjă de creștere (Eurostat, 16.12.2025: https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20251216-3).',
    '- **Dispozitive personale purtabile/de birou.** IDC: **45,6 milioane** de dispozitive purtate la încheietură livrate doar în T1 2025 (+10,5 % an/an), din care 34,8 M smartwatch-uri (https://www.emsnow.com/idc-global-wrist-worn-device-shipments-grew-10-5-in-q1-2025/). Este piața de referință pentru interfețele rotunde mici.',
    '- **Hardware AI dedicat.** Plaud a livrat **peste 2 milioane** de dispozitive AI de notițe, iar abonamentele sale depășesc **100 M$ ARR**, cu ~50 % dintre cumpărători plătitori (TechCrunch, 16.06.2026: https://techcrunch.com/2026/06/16/plaud-says-its-software-business-topped-100m-in-arr-after-shipping-over-2m-ai-notetakers/). Fuzozo (China) a vândut ~300.000 de unități (https://www.stocktitan.net/news/TUYA/tuya-smart-accelerates-physical-ai-commercialization-with-strategic-fl5hn4dv397y.html). Campaniile de crowdfunding pentru dispozitive AI de birou strâng 0,3–0,8 M$ (Loona DeskMate 721.816 $: https://www.kicktraq.com/projects/keyitechnology/loona-deskmate-the-worlds-first-screen-aware-ai-co-worker/; Eiliko ~600.000 $: https://www.kicktraq.com/projects/energize-lab/eiliko/).',
    '- **Obiect AI premium, validat ca preț.** OpenAI × Jony Ive pregătesc pentru 2027 un dispozitiv din metal premium la **300–400 $** (TechCrunch, 06.08.2026: https://techcrunch.com/2026/08/06/openais-new-ai-smart-speaker-will-reportedly-sell-for-between-300-and-400/); obiectele metalice fără AI se vând la 139–599 $ (STARBOY: https://gizmodo.com/can-we-interest-you-in-a-400-ai-keychain-that-behaves-like-a-real-pet-2000732919).',
    '**Tendințe.** (1) Utilizatorii cer confidențialitate și funcționare offline după eșecurile Humane (https://www.axios.com/2025/02/18/humane-ai-pin-shut-down-hp) și Moxie (https://www.theregister.com/2024/12/16/moxie_cloud_services_lessons/). (2) Marile platforme închid ecosistemul: Meta Muse Charm e disponibil doar în SUA (https://www.heise.de/en/news/Tamagotchi-meets-AI-agent-Meta-announces-AI-gadget-Muse-Charm-11464075.html), Alexa+ nu există în română. (3) Reglementarea UE (baterii înlocuibile din 18.02.2027, dreptul la reparare, securitatea radio, AI Act art. 50) favorizează produsele proiectate de la început pentru reparabilitate și transparență.',
    '**Dimensiunea pieței adresabile [E — estimare proprie, de rafinat în A6]:** 15,1 % × ~335 M persoane de 16–74 ani din UE ≈ **50 M** de utilizatori profesionali de AI generativ (piața totală); nișa „dispozitiv dedicat premium, BYO-AI, UE-first” la 0,1–0,5 % din aceștia ≈ **50–250 mii** de unități, adică **12–60 M€** la un preț mediu de ~250 € (piața adresabilă). Ținta SOUL în anul 5 post-proiect: **7.000 de unități/an** (≈ 3–14 % din piața adresabilă).',
    'Benchmark-ul complet al celor 24 de competitori (preț, abonament, AI, tracțiune, status, cu surse) este anexat (research 11).',
])

drop(98)
t = B[99]
seg = [
    ['Segment 1 (B2C/B2B mic, UE): profesioniști care lucrează zilnic cu asistenți AI', 'dezvoltatori care folosesc Claude Code/Cowork, creatori, freelanceri; 25–45 ani; vor aprobări și notițe rapide fără telefon, cu AI-ul pe care îl plătesc deja', '[E] ~50 M utilizatori AI la muncă în UE (Eurostat); țintă An 1–5: 175 → 7.000 buc./an'],
    ['Segment 2 (B2C premium, UE): utilizatori care vor un asistent privat, offline, fără abonament', 'cumpărători de obiecte de design și gadgeturi premium (referință: STARBOY, Moflin, Ropet), sensibili la confidențialitate', '[E] preț acceptat 250–400 €; ~30 % din vânzări'],
    ['Segment 3 (B2B): echipe/firme care folosesc Claude Code și cadouri corporate', 'firme de software din UE, 10–200 de dezvoltatori; pilot cu 3–5 persoane, apoi achiziție de echipă', '[E] 20–50 de firme în An 3–5; licențiere B2B 20–60 k€/an'],
    ['Segment 4 (acces și incluziune): persoane cu nevoi de accesibilitate', 'control vocal, modul „taste mari”, contrast ridicat; parteneriate cu asociații', '[E] nișă de validare și canal instituțional; nu e inclus în proiecție'],
]
fill_table_rows(t, 1, seg)
rs = rows(t)
set_cell(tcs(rs[-1])[0], seg[-1][0])
after = t
gp = copy.deepcopy(B[100]); t.addnext(gp)
write_runs(gp, '**Grupul țintă al proiectului** (corelat cu CF): ' + ' '.join(f'({i}) {g}' for i, g in enumerate(TARGET_GROUPS, 1)))

drop(102)
t = B[103]
compet = [
    ['Meta Muse Charm (agent AI purtabil)', 'SUA', 'breloc cu 2 camere, 5G, agent Muse (e-mail, rezervări, cumpărături); abonament 0/20/100 $/lună; doar SUA', 'fără camere, hold-to-talk; AI la alegere; disponibil în UE și în română; funcționează offline'],
    ['OpenAI × Jony Ive (difuzor AI din metal, 2027)', 'SUA', 'obiect premium din metal, fără ecran, 300–400 $, doar ChatGPT', 'față expresivă + tastatură; portabil; merge cu Claude și ChatGPT; baterie înlocuibilă'],
    ['Plaud NotePin S (recorder AI)', 'SUA / China', 'o singură funcție (notițe), 179 $ + abonament Pro 99,99 $/an', 'fără abonament obligatoriu; acțiuni multiple (alarme, liste, aprobări); offline'],
    ['Rabbit r1 (handheld AI)', 'SUA', 'ecran 2,88″, 199 $, cloud propriu; ~5 % utilizatori zilnici', 'funcții locale utile zilnic; obiect de birou premium; AI la alegere'],
    ['Humane AI Pin (închis 28.02.2025)', 'SUA', '699 $ + 24 $/lună obligatoriu; oprit de server', 'nu depinde de serverul producătorului (offline + server publicabil/escrow)'],
    ['Fuzozo (Robopoet/Tuya)', 'China', 'pluș cu ochi LCD, ~55 $, cloud Tuya, doar chineză', 'obiect din aluminiu, date în UE, română/engleză, acțiuni utile'],
    ['Loona DeskMate (KEYi)', 'China', 'dock motorizat cu iPhone ca față, 219–299 $, 50+ integrări, cere iPhone', 'dispozitiv autonom, fără telefon obligatoriu, fără motoare, autonomie ≥ 24 h'],
    ['Vibe Desktop Buddy / clone xiaozhi-esp32', 'SUA / China', 'kituri pe M5Stick/ESP32, 110 $ + transport, ecran 1,14″, ~2 h baterie, aspect DIY', 'aceeași funcție de aprobări Claude pe un obiect premium; ecran 2,8″ cu tastatură; OS finisat; garanție UE'],
    ['Amazon Echo Spot / Alexa+', 'SUA', 'ecran rotund 2,83″, 80 $ + Alexa+ 22,99 €/lună fără Prime; nu există în română', 'fără lock-in; română; confidențialitate; portabil'],
]
fill_table_rows(t, 1, compet)
src = copy.deepcopy(B[104]); t.addnext(src)
write_runs(src, 'Surse: ' + ' · '.join(u for _, u in MARKET_SOURCES[2:14]) + '. **Concluzie:** niciun produs analizat nu combină față expresivă + obiect premium reparabil + AI la alegerea utilizatorului + acțiuni utile + funcționare offline (research 11 §1, anexat).')

drop(106)
fill(107, [
    'Principalele bariere de intrare și modul de depășire:',
    '- **Conformitate radio și securitate cibernetică (RED 2014/53/UE, Reg. delegat 2022/30, EN 18031-1/-2/-3, EN 300 328, EN 301 489).** Depășire: arhitectura EN 18031 (secure boot, OTA semnat, BLE LE Secure Connections) intră în proiect (A4, linia 15), iar pre-scanul EMC/RF (linia 14) reduce riscul certificării CE din An 1 post-proiect.',
    '- **Baterii (Reg. 2023/1542), DEEE/EPR, GPSR, RoHS.** Depășire: bateria înlocuibilă de utilizator este cerință de proiectare (P10); înregistrările ANMAP/EPR și dosarul GPSR se fac la Founders 00.',
    '- **AI Act art. 50 și GDPR.** Depășire: informare „sunt un AI” la prima pornire, telemetrie opt-in, fără înregistrare audio brută, servere în UE.',
    '- **Proprietate intelectuală și mărci existente** (risc de conflict „SOUL”). Depășire: căutare TMview/DesignView înainte de depunere, design UE ≤ L5, marcă UE ≤ L6, marcă figurativă/compusă ca rezervă (§6.2).',
    '- **Capital pentru scule și stoc; concurența marilor platforme.** Depășire: producție în loturi mici (25 → 300 → 1–10 k), precomenzi, finanțări europene (PR BI 1.2, Eurostars, EIC) și poziționare pe neutralitatea de model, pe care platformele închise nu o pot oferi.',
    '- **Brevete existente pe tastaturi circulare** (literatura C-QWERTY, COMPASS). Depășire: căutare de anteriorități prin consilierul PI (L1–L3) înainte de a fixa metoda de decodare.',
])

drop(110)
t = B[111]
mk = [
    'Preț premium, justificat de material, reparabilitate și neutralitatea de model: **349 €** pentru Founders 00 (25 de unități numerotate), apoi **279–299 €** (Batch 1) și **239–259 €** (SOUL Standard, preț net mediu). Reperele: OpenAI × Ive 300–400 $, STARBOY oțel 349 $, Loona DeskMate 299 $. Nucleul funcțional e gratuit pe viață; se plătesc opțional vocea/memoria (~4 €/lună) și accesoriile.',
    'Vânzare directă online (magazin propriu Shopify, experiența MundiShop) — ~70 % din volum; crowdfunding Indiegogo/Gamefound pentru Batch 1 (Kickstarter nu acceptă creatori din România); retail de design/electronice premium prin distribuitori (scrisori de intenție la depunere); B2B pentru echipe care folosesc Claude Code.',
    'Demo-ul „Claude Code cere permisiunea → SOUL aprobă” pe comunitățile de dezvoltatori (r/ClaudeAI, Show HN, Product Hunt); presă tech RO + UE; conferința/târgul din proiect (A7, linia 22); articolul open-access și preprintul (A7); seeding la 10 creatori dev/design; lista de așteptare existentă.',
    'Până la L24: ≥ 30 de interviuri de customer discovery; ≥ 2 acorduri de pilot/distribuție semnate; ≥ 500 de înscrieri pe lista de așteptare [E]. An 1 post-proiect: 25 de unități Founders vândute + 150 Batch 1; An 2: 850 de unități; An 5: 7.000 de unități/an.',
]
for tr, v in zip(rows(t), mk):
    set_cell(tcs(tr)[1], v)

drop(114)
t = B[115]
sw = rows(t)
set_cell(tcs(sw[1])[0], '\n'.join([
    'S1. Dovezi TRL 3 verificabile: 61/61 teste firmware, 49/49 teste AI, simulator, prototip web, CAD (Raport științific §II).',
    'S2. Combinație unică: față expresivă + obiect din aluminiu reparabil + AI la alegere + acțiuni utile + offline (research 11).',
    'S3. Neutralitate de model (Claude/ChatGPT/cheie proprie) — platformele închise nu o pot copia fără să-și schimbe modelul de afaceri.',
    'S4. Română + engleză din ziua 1; servere UE; conformitate proiectată (baterie înlocuibilă, EN 18031, AI Act).',
    'S5. Cost de dezvoltare redus: ESP32-S3 + panou 2,8″ (~40 $ placa de dezvoltare).']))
set_cell(tcs(sw[1])[1], '\n'.join([
    'W1. Nicio vânzare încă; nicio dovadă de piață plătitoare (doar listă de așteptare).',
    'W2. Echipă mică; coordonatorul și inginerul se nominalizează înainte de depunere.',
    'W3. Ecranul IPS nu are negru real (lumina de fundal) și consumă de ~5–10× mai mult decât AMOLED.',
    'W4. Primul proiect cu finanțare europeană al firmei.',
    'W5. Dependență de furnizori asiatici pentru panou și module.']))
set_cell(tcs(sw[3])[0], '\n'.join([
    'O1. Adopția AI crește rapid (32,7 % în UE; 17,8 % în RO — cea mai mare marjă).',
    'O2. Eșecurile Humane/Moxie au creat cerere pentru dispozitive care nu „mor” cu serverul.',
    'O3. Marile platforme lipsesc din UE/română (Muse doar SUA, Alexa+ fără română).',
    'O4. Reglementarea UE (baterii înlocuibile, drept la reparare) avantajează produsele proiectate astfel de la început.',
    'O5. Ecosistemul Claude Hardware Buddy (protocol MIT) și MCP creează un public de dezvoltatori gata să cumpere.']))
set_cell(tcs(sw[3])[1], '\n'.join([
    'T1. OpenAI × Ive (2027) și Meta Muse pot redefini categoria „obiect AI premium”.',
    'T2. Clone xiaozhi/ESP32 ieftine pot apărea în 2–6 săptămâni după lansare.',
    'T3. Conflict de marcă „SOUL”.',
    'T4. Schimbarea API-urilor/prețurilor furnizorilor de AI.',
    'T5. Eșec de cercetare pe H1/H3/H4 (RF prin aluminiu, latență) — tratat prin poarta IE2.']))

# ------------------------------------------------------------------ IV
drop(118, 121)
t = B[122]
for tr in rows(t)[1:]:
    name = ptext(tcs(tr)[1])
    if 'Tehnologia' in name or 'Sisteme' in name:
        set_cell(tcs(tr)[2], '☒ DA', bold=True, align='center')
    else:
        set_cell(tcs(tr)[2], '☐', align='center')
fill(125, [
    '**Domeniul 1 — Tehnologia Informației și Comunicațiilor (TIC).** Proiectul dezvoltă și validează: firmware embedded (C++17) pentru randare SDF în timp real; tastatură circulară cu decodare probabilistică; arhitectură AI hibridă local-first (parser offline RO/EN + modele de limbaj la alegerea utilizatorului prin tool-calling, conector MCP); flux vocal în timp real (Opus/WebSocket, servere UE); securitate cibernetică conform EN 18031 (BLE LE Secure Connections, OTA semnat, secure boot). **Obiective și activități:** O1, O3; A2, A3, A5. **Rezultate:** firmware SoulOS, serviciul AI, protocoalele și datele de validare (R1, R2, R4).',
    '**Domeniul 2 — Sisteme și Componente Inteligente.** Proiectul realizează un sistem ciber-fizic integrat: ESP32-S3, afișaj rotund IPS 480×480, touch capacitiv, IMU, microfoane MEMS, PMU, baterie înlocuibilă și antenă BLE/Wi-Fi integrată într-o carcasă CNC din aluminiu cu fereastră radio polimerică. **Obiective și activități:** O2, O3; A4, A5. **Rezultate:** PCB propriu, arhitectura electromecanică, măsurătorile RF/energie/EMC (R2, R3).',
    '**Elemente concrete:** tehnologiile vizate (embedded, HCI, AI hibrid, RF, energie), sectoarele de aplicare (electronice de consum, instrumente pentru dezvoltatori, accesibilitate), profilul echipei (inginer embedded/electronist ≥ 5 ani, inginer firmware, student ETTI/ACS) și piața-țintă (UE, Secțiunea III). Subdomeniile RIS3 BI 2021–2027: [[Cl: citare exactă din strategia RIS3 BI (adrbi.ro), după descărcare]]. Aceeași încadrare apare în CF și în Raportul științific (§1.3).',
])

drop(128)
fill(129, [
    'Rezultatul de cercetare existent constă în **modelul conceptual SOUL demonstrat pe componente separate**, în laborator și în simulare (TRL 3 conform Anexei 18: „validare analitică și/sau experimentală a funcțiilor critice”). Dovezile (detaliate în Raportul științific, §2.3):',
    '- **D1** firmware „Suflet”/SoulOS v1: randare SDF, ochi parametrici, dispoziție, personalitate, gesturi, legătura Claude Hardware Buddy, tastatură circulară, predicție, alarme; **61/61 teste Unity** trec; build-uri pentru trei plăci, inclusiv SOUL M (`lcd28`).',
    '- **D2** simulator pe PC care produce cadrele reale ale motorului (10 clipuri + tastatură și time-picker la 480 px).',
    '- **D3** serviciul AI `suflet_ai` v0.2: 3 moduri, 8 acțiuni cu scheme JSON stricte, parser local RO/EN, conector MCP; **49/49 teste** trec.',
    '- **D4–D6** prototipul web al tastaturii rotunde, analiza geometrică (pas = 0,0944·D → 6,7 mm pe Ø70), CAD parametric și randări ale corpului M. **D7** istoricul git datat.',
    '- **D8 (în curs, înainte de depunere):** Raportul de laborator TRL 3 pe placa Waveshare ESP32-S3-Touch-LCD-2.8C (cumpărată din fonduri proprii, în afara bugetului) cu experimentele **X1–X8**: port RGB/touch, fps, precizie touch, tastare pilot, parser offline pe 200 de comenzi, latență AI, RSSI prin aluminiu, consum.',
    '**Limitele actuale (declarate):** nimic nu rulează încă integrat pe hardware-ul final; firmware-ul a fost scris inițial pentru AMOLED CO5300 și este portat pe ST7701 (RGB) + GT911; nu există încă audio integrat, PCB propriu, carcasă metalică sau teste cu utilizatori. **De aceea este necesară continuarea până la TRL 4–5:** integrarea, validarea la pragurile O1/O3 și testarea în mediu relevant nu se pot face fără echipa, aparatura și prototiparea din proiect.',
])

drop(132, 133)
gantt_rows = [[n] + ['■' if m in rng else '' for m in range(1, 25)] for n, rng in GANTT]
fill(134, [
    '**Arhitectura sistemului SOUL M** (specificația completă — livrabilul L1.1):',
    '- **Mecanică:** corp ~90 × 103 × 31 mm, CNC din Al 6061 anodizat (design v6), geam frontal, talpă polimerică detașabilă care servește ca fereastră radio, închidere cu șuruburi Torx, capsula de încărcare „OU” cu pini pogo.',
    '- **Electronică:** ESP32-S3 (WROOM-1, 8 MB PSRAM, 16 MB flash), panou rotund IPS 2,8″ 480×480 (ST7701, interfață RGB565 paralelă, framebuffer 460 KB în PSRAM, bounce-buffers), touch GT911 (I²C), IMU QMI8658, RTC PCF85063A, codec ES8311 + ES7210 cu 2 microfoane MEMS și AEC, amplificator, PMU, celulă Li-ion 2500–3000 mAh pe conector MX1.25, PCB propriu (A4).',
    '- **Firmware SoulOS (C++17, Arduino/ESP-IDF, PlatformIO):** Canvas (randare SDF anti-aliased), Face/Brain/Personality (24 de reacții procedurale, personalitate derivată din ID-ul cipului), Gestures, Keyboard/TextField/Predictor (Round QWERTY cu decodare probabilistică, diacritice RO automate, modul „taste mari” T9 cu taste de 10,3 × 7,7 mm), TimePicker, Alarms, Shell, ClaudeLink (protocolul Claude Hardware Buddy prin BLE securizat), OTA semnat, secure boot.',
    '- **Serviciul AI (Python, servere UE):** un singur set de acțiuni cu scheme JSON (alarme, mementouri, notițe, liste, cronometre, aprobări) executat în trei moduri — fără AI (parser local RO/EN), Claude (SDK Anthropic, tool-calling, conector MCP), ChatGPT —, cheie proprie criptată, degradare controlată la căderea rețelei; flux vocal Opus/WebSocket (xiaozhi-esp32 adaptat, MIT).',
    '**Standarde aplicate:** EN 18031-1/-2/-3, EN 300 328, EN 301 489-1/-17, Reg. (UE) 2023/1542 art. 11, AI Act art. 50, GDPR, RoHS. **Metodologii:** protocoalele P1–P11 (Raportul științific §3.3), metodologia MacKenzie–Soukoreff pentru tastare, SUS pentru utilizabilitate.',
    '**Economie circulară aplicată direct produsului** (Grila 1.5):',
    ('table', T(['Principiu', 'Cum se regăsește în SOUL M', 'Cum se verifică în proiect'], [list(c) for c in CIRCULAR], [2400, 4638, 2600])),
    '**Etapele de realizare în perioada de implementare** (identice cu CF și Raportul științific):',
    ('table', T(['Cod', 'Activitate', 'Tip (ghid)', 'Luni', 'Livrabile / milestone'],
                [[a[0], a[1], a[2], a[3], a[5]] for a in ACTIVITIES], [700, 4138, 1500, 1100, 2200])),
    '**Diagrama Gantt (L1…L24):**',
    ('table', T(['Activitate'] + [str(m) for m in range(1, 25)], gantt_rows, [2426] + [301] * 24, size=14, compact=True,
                center_cols=tuple(range(1, 25)))),
    DEPENDENCIES,
    '**Milestone-uri și indicatori de etapă** (Anexa 13):',
    ('table', T(['Cod', 'Milestone', 'Luna', 'Criteriu de îndeplinire', 'Tip'],
                [[m[0], m[1], m[3], m[4], m[5]] for m in MILESTONES], [900, 2800, 1300, 3238, 1400])),
])

drop(137, 138)
t = B[139]
loc = ['[[Adresa completă a sediului social]], București, [[sector]]',
       'Spațiu de birou + laborator electronic (bancul de test, aparatele de măsură, stația de lipit, imprimanta SLA)',
       '[[A: suprafața în mp]]',
       '[[A: proprietate / chirie / comodat]] — contractul acoperă implementarea + 3 ani de durabilitate, cu clauza că proprietarul nu are drepturi asupra bunurilor din proiect (se anexează la contractare)',
       'Energie electrică (prize dedicate pentru bancul de test), internet fibră, ventilație, depozitare pentru prototipuri; testele EMC/RF se fac la laboratorul acreditat partener',
       'Nu este cazul (activitate de birou/laborator electronic de joasă tensiune; fără lucrări de construcții)']
for tr, v in zip(rows(t), loc):
    set_cell(tcs(tr)[1], v)

drop(142)
t = B[144]
eq = [
    ['Osciloscop digital 4 canale', '≥ 200 MHz, ≥ 1 GSa/s, decodare I²C/SPI/UART/I²S; RoHS', '1', '7.635', '7.635', 'semnalele RGB, I²C, I²S, alimentarea (A1–A5); verificare H1, H5'],
    ['Analizor de spectru', '≥ 3 GHz (acoperă 2,4 GHz BLE/Wi-Fi), tracking generator opțional', '1', '17.815', '17.815', 'măsurătorile RF prin carcasă (P8) și pregătirea pre-scanului (P11); H4'],
    ['Analizor de consum / source-measure', 'măsurare curent nA–A, eșantionare ≥ 100 kS/s, profilare energie', '1', '5.090', '5.090', 'modelul de consum și autonomia (P9); H5'],
    ['Cutie ecranată RF', 'atenuare ≥ 60 dB la 2,4 GHz, treceri pentru USB/RF', '1', '4.581', '4.581', 'măsurători RSSI reproductibile, controlul interferențelor (P8)'],
    ['Stație de lucru PC', 'CPU ≥ 8 nuclee, 32 GB RAM, SSD 1 TB; ecodesign/ErP', '1', '10.180', '10.180', 'compilare firmware, simulare, analiza datelor, CAD (A2–A5)'],
    ['Imprimantă 3D SLA', 'rezoluție XY ≤ 50 µm, volum ≥ 14 × 8 × 15 cm', '1', '19.851', '19.851', 'carcase SLA la scara M (A2), dispozitive de test și fixare (A4)'],
]
rs = rows(t)
fill_row(rs[1], eq[0]); fill_row(rs[2], eq[1])
last = rs[2]
for e in eq[2:]:
    last = add_row_after(last, e)
fill_row(rs[3], ['TOTAL echipamente', '', '', '', '65.152', '12.800 € fără TVA (15.488 € cu TVA 21 %, liniile 5–10)'], bold=True)
note = copy.deepcopy(B[145]); t.addnext(note)
write_runs(note, 'Valorile sunt estimări [E] la cursul orientativ de 5,09 lei/€, până la primirea a câte 2 oferte pe linie; cursul se înlocuiește cu InforEuro din ghidul final. Toate echipamentele sunt noi (nu second-hand) și se achiziționează conform Ordinului MFE 1284/2016, după depunere.')

drop(147)
t = B[148]
rs = rows(t)
intang = [
    ['Cerere de marcă UE (3 clase) — taxă EUIPO', 'Marcă (protecție IP)', '5.345', 'protecția numelui produsului (A6, R3); fără TVA'],
    ['Cerere de desen/model industrial UE multiplu (corp SOUL M + capsula OU) — taxe EUIPO', 'Desen/model industrial', '4.785', 'protecția formei produsului înainte de publicare (A6, R3)'],
    ['KiCad, PlatformIO, CadQuery, Git (open-source)', 'Software, licențe gratuite', '0', 'proiectare PCB, firmware, CAD parametric'],
    ['Abonamente SaaS pentru CDI: API AI (LLM/STT/TTS), găzduire UE, CAD — linia 18', 'Servicii SaaS (nu se capitalizează)', '21.032', 'rularea serverului AI și a fluxului vocal pentru testele P5–P7 (A2–A5)'],
]
fill_row(rs[1], intang[0])
last = rs[1]
for e in intang[1:]:
    last = add_row_after(last, e)
fill_row(rs[2], ['TOTAL active necorporale', '', '10.129', '1.990 € (taxe oficiale, fără TVA, linia 19); consilierul PI este serviciu (linia 20: 6.363 lei fără TVA)'], bold=True)

drop(151)
t = B[152]
rs = rows(t)
mat = [
    ['Plăci de dezvoltare Waveshare ESP32-S3-Touch-LCD-2.8C', '8 buc.', '1.527', 'modele de laborator și bancuri paralele de test (A2, A3)'],
    ['Panouri IPS rotunde 2,8″ 480×480 (ST7701)', '20 buc.', '1.120', 'prototipuri rev A/B și lotul de 15 (A4)'],
    ['Seturi audio (2 microfoane MEMS I²S + amplificator + difuzor)', '25 seturi', '1.527', 'subsistemul vocal, AEC, P6 (A2, A4)'],
    ['Celule Li-ion 2500–3000 mAh cu conector MX1.25', '30 buc.', '1.222', 'autonomie și înlocuire baterie (P9, P10)'],
    ['Componente electronice (conectori, pini pogo, IMU, RTC, pasive, cabluri, șuruburi Torx, spume)', 'lot', '8.144', 'asamblarea prototipurilor și a capsulelor OU (A4)'],
    ['Rășină SLA și consumabile de imprimare', 'lot', '3.563', 'carcase SLA la scara M și fixturi de test (A2, A4)'],
    ['Obiecte de inventar (unelte, stație de lipit, dispozitive de fixare)', 'lot', '1.858', 'asamblare și QC (A4)'],
]
fill_row(rs[1], mat[0])
last = rs[1]
for e in mat[1:]:
    last = add_row_after(last, e)
fill_row(rs[2], ['TOTAL materiale/consumabile', '', '18.960', '3.725 € fără TVA (4.507 € cu TVA, linia 11); defalcare orientativă [E]'], bold=True)
bud_rows = []
for nr, line, cat, act, eur in BUDGET:
    if cat is None:
        bud_rows.append([f'**{nr}**', f'**{line}**', '', '', ''])
    elif nr == '':
        bud_rows.append(['', f'**{line}**', '', '', f'**{eur}**'])
    else:
        bud_rows.append([nr, line, cat, act, eur])
fill(153, [
    '**Sinteza bugetului proiectului** (identică cu secțiunea Buget din CF; € cu TVA 21 % inclusă — ARTEMIS e neplătitoare de TVA; salarii brute + CAM 2,25 %; prețuri [E] până la primirea ofertelor):',
    ('table', T(['Nr.', 'Linie bugetară', 'Categorie / tip activitate', 'Activitate', '€'], bud_rows, [700, 4100, 2700, 1100, 1038], size=17)),
    '**Verificarea pragurilor:**',
    ('table', T(['Prag', 'Valoare', 'Stare'], [list(c) for c in BUDGET_CHECKS], [3800, 3838, 2000])),
    'Justificarea valorii: salariile acoperă ~3.900 de ore de CD pe 24 de luni, minimul realist pentru a porta, integra, proiecta un PCB, face două iterații de carcasă și rula două campanii de validare; tarifele sunt sub plafoanele HG 1188/2022. Echipamentele sunt strict cele de măsură fără de care nu se pot verifica H1–H5. Prototiparea se face în două iterații (A → B) plus un lot de 15 unități (N ≥ 12 utilizatori + rezervă). Pre-testarea EMC/RF și EN 18031 reduc riscul fazei următoare (CE) fără să intre în certificarea finală (TRL 7–8, necerută în proiect).',
])

# ------------------------------------------------------------------ V
drop(155)
drop(159)
fill(160, [
    'Politica de resurse umane a ARTEMIS se bazează pe recrutare nediscriminatorie și pe dezvoltarea competențelor CDI în echipă mică:',
    '- **Recrutare:** anunțuri neutre ca gen, criterii obiective din fișele de post (studii, ani de experiență, publicații), interviu tehnic structurat; contracte individuale de muncă part-time pe proiect; varianta de detașare de la o organizație de cercetare pentru coordonator.',
    '- **Menținere și dezvoltare:** program flexibil și muncă hibridă; salarizare pe grilă transparentă; participarea la o conferință internațională (A7); co-autorat la articol; acces la bancul de test și la aparatura din proiect.',
    '- **Timp de lucru:** pontaje lunare pe proiect; respectarea Codului muncii (max. 48 h/săpt. pe toate contractele); plafonul HG 1188/2022 aplicat tuturor veniturilor din proiecte ale fiecărei persoane. Scutirea de impozit pe venit pentru personalul CD (Cod fiscal art. 60 pct. 3) se aplică doar cu documentația cerută [[Ct: verifică]].',
    '- **Principii orizontale (măsuri minime):** politica internă de egalitate de șanse și nediscriminare (decizia administratorului, anexată [[A: semnează]]); accesibilitatea produsului (control vocal, modul „taste mari”, text scalabil, paletă sigură pentru daltonism, fără dependență exclusivă de gesturi fine).',
    '- **Tineri (Grila 4.3a):** un student ≤ 24 ani, înmatriculat în învățământul superior (UPB ETTI/ACS), angajat cu CIM pe activitățile CD A3, A5, A7 [[de nominalizat; adeverință de student 2026–2027]].',
    '- **Măsuri suplimentare de egalitate de șanse (Grila 4.3b):** (1) panelul de validare TRL 5 are ≥ 40 % femei, ≥ 3 persoane peste 55 de ani și ≥ 2 persoane cu deficiențe de vedere sau motorii, recrutate printr-o asociație de profil; (2) test de accesibilitate al interfeței (voce, „taste mari” 10,3 × 7,7 mm, contrast ridicat, feedback haptic/sonor, dimensiunea textului) împreună cu asociația, cu raport public.',
    '- **DNSH:** echipamentele respectă ecodesign-ul (Dir. 2009/125/CE) și RoHS (cerințe în specificațiile de achiziție); rebuturile de prototip (DEEE, baterii) se predau unui colector autorizat, cu proces-verbal (OUG 5/2015).',
])

drop(163, 164)
t = B[166]
rs = rows(t)
team = [
    ['1', '[[Nume Prenume]]\nCoordonator tehnic/științific (HG 1188 Anexa 2, cat. 2 „responsabil tehnic proiect”, plafon 35 €/h)',
     'inginer embedded/electronist, ≥ 5 ani în TIC/sisteme embedded (ideal doctor) [[CV Europass + diplome]]', 'A1–A5, A7', '173,06\n(34 €/h)', '50', '24', '1.200', '207.672\n(40.800 €)'],
    ['2', '[[Nume Prenume]]\nInginer embedded/firmware (cat. 2 „personal de specialitate”, plafon 35 €/h)',
     'studii superioare în domeniu, ≥ 2 ani experiență sau ≥ 1 publicație WoS/Scopus [[CV]]', 'A2–A5', '127,25\n(25 €/h)', '80', '21', '1.680', '213.780\n(42.000 €)'],
    ['3', '[[Nume Prenume]]\nStudent cercetare (cat. 4 „student”, plafon 15 €/h)',
     '≤ 24 ani, înmatriculat UPB ETTI/ACS; teste cu utilizatori, analiza datelor, corpusuri RO [[adeverință]]', 'A3, A5, A7', '61,08\n(12 €/h)', '60', '20', '1.200', '73.296\n(14.400 €)'],
]
for tr, v in zip(rs[1:4], team):
    fill_row(tr, v)
set_cell(tcs(rs[4])[1], '494.748 lei (97.200 €)', bold=True)
set_cell(tcs(rs[5])[1], '11.132 lei (2.187 €)', bold=True)
set_cell(tcs(rs[6])[1], '505.880 lei (99.387 €)', bold=True)
nt = copy.deepcopy(B[167]); t.addnext(nt)
write_runs(nt, 'Tarifele sunt brute, în €/oră, convertite orientativ la 5,09 lei/€ [E]; conversia finală se face la cursul BNR de la data contractului (HG 1188/2022, Anexa 2: plafoanele în €/oră includ toate taxele angajatului). CAM (2,25 %) nu intră în plafon și este eligibilă (ghid §5.3.2).')

drop(171)
t = B[172]
rs = rows(t)
fill_row(rs[1], ['1', '[[Nume Prenume]] („Andu”)\nManager de proiect (cat. 1 „manager de proiect”, plafon 50 €/h)',
                 'coordonare, achiziții (Ordinul MFE 1284/2016), raportare, relația cu AM PR BI, valorificare comercială', '91,62\n(18 €/h)', '20', '24', '480', '43.978\n(8.640 €)'])
fill_row(rs[2], ['2', 'Nu este cazul', 'gestiunea financiară și cererile de rambursare sunt asigurate de contabilul firmei, din costurile indirecte (7 %)', '–', '–', '–', '–', '–'])
set_cell(tcs(rs[3])[1], '43.978 lei (8.640 €)', bold=True)
set_cell(tcs(rs[4])[1], '987 lei (194 €)', bold=True)
set_cell(tcs(rs[5])[1], '44.965 lei (8.834 €, linia 25)', bold=True)
nt = copy.deepcopy(B[173]); t.addnext(nt)
write_runs(nt, '[[Ct: confirmă posibilitatea CIM pentru administrator; alternativ, serviciu extern de management cu atribuții separate]].')

drop(175)
fill(176, [
    'În perioada de durabilitate (3 ani după plata finală) resursele umane cresc odată cu traseul TRL 6 → 9 (Secțiunea VI) și sunt finanțate din venituri, precomenzi și, după durabilitate, dintr-o rundă de investiții:',
    '- **An 1:** păstrăm inginerul embedded ca 1 normă întreagă (PCB rev C, certificare CE/RED + EN 18031, Founders 00); managerul de proiect devine responsabil de producție și vânzări.',
    '- **An 2:** angajăm 1 persoană suport/QA (asistență clienți, testare loturi, garanții) și 1 inginer hardware (0,5 → 1 normă în An 2–3) pentru Batch 1 și sculele de producție.',
    '- **An 3–5:** echipa ajunge la 5–6 persoane în activitatea inovatoare (firmware, hardware, suport, vânzări B2B); calificări: studii superioare în electronică/calculatoare, experiență embedded/RF; studentul din proiect are prioritate la angajare.',
    'Costurile sunt incluse în proiecția din §6.3 (liniile „cheltuieli CDI” și „cheltuieli comercializare”).',
])

# ------------------------------------------------------------------ VI
drop(179, 182)
t = B[183]
rs = rows(t)
pp = [[p[0] + ' — ' + p[3], p[1], p[2], p[4]] for p in POSTPOC]
for tr, v in zip(rs[1:4], pp[:3]):
    fill_row(tr, v)
add_row_after(rs[3], pp[3])
nt = copy.deepcopy(B[184]); t.addnext(nt)
write_runs(nt, '**Punctul de pornire** este rezultatul validat la TRL 5 (R2: 15 prototipuri, raportul TRL 5, pre-scanul EMC/RF) și protecția IP (R3). **Cerințele pentru TRL 6–9:** PCB rev C cu modul radio certificat, certificare CE/RED + EN 18031, dosar GPSR, înregistrări EPR/ANMAP, scule de producție, aplicația de telefon, lanț de aprovizionare cu 2 furnizori pe componentele critice. **Modelul de valorificare:** comercializare directă a hardware-ului (349 € Founders → 199–299 € Standard) + serviciu opțional (voce/memorie) + licențiere B2B a designului/firmware-ului. Orice investiție de capital se face într-un vehicul separat sau după perioada de durabilitate, fără transfer de IP în durabilitate. Calendarul acoperă **5 ani** post-finalizare (An 1 ≈ 2029–2030).')

drop(186)
fill(187, [
    'Strategia de IP urmează regula **„întâi protecția, apoi publicarea”** (file first, publish later): cererile de design și marcă se depun până la L5–L6, iar articolul științific se trimite abia după (≤ L20). Protecția acoperă forma produsului (design UE), numele (marcă UE), eventualele soluții tehnice brevetabile (evaluate la L12–L18) și know-how-ul (secret comercial).',
    ('table', T(['Pas', 'Ce', 'Când', 'Cost / linie'], [list(r) for r in IPPLAN], [700, 5538, 1900, 1500])),
    '**Dovada demersurilor în implementare (Grila 2.1d):** numărul și data cererilor EUIPO (design ≤ L5, marcă ≤ L6), raportul de brevetabilitate (L18). **Publicarea open-access (Grila 1.4):** revista țintă [[Cl: revista aleasă, ex. MDPI Electronics sau Sensors / IEEE Access, cu captura paginii de APC]]; APC bugetat în linia 21; preprint în Zenodo. **Licențe open-source:** codul terț (MIT/OFL) rămâne sub licențele sale; motorul ochilor poate fi publicat open-source după depunerea cererilor IP, ca strategie de standardizare.',
])

drop(190)
P = proj.out


def L(x):
    return f"{round(x * RATE / 1000) * 1000:,.0f}".replace(',', '.')


def row(key):
    return [L(P[y][key]) for y in range(1, 6)]


t = B[192]
rs = rows(t)
opex_dep = [L(P[y]['opex'] + P[y]['dep']) for y in range(1, 6)]
vals = [
    row('rev'), row('rev'), ['[[Ct]]'] * 5, opex_dep, row('rd'), row('com'), row('ebitda'), row('net'), row('capex'),
    ['precomenzi Founders; fonduri proprii; EUIPO SME Fund; EDIH', 'PR BI 1.2 / Eurostars; crowdfunding; pre-seed în vehicul separat', 'venituri; EIC Accelerator; credit FNGCIMM', 'venituri; credit pentru stoc; rundă de capital (după durabilitate)', 'venituri recurente; licențe'],
    ['2', '4', '4', '5', '6'],
]
for tr, v in zip(rs[1:], vals):
    fill_row(tr, [None] + v)
set_cell(tcs(rs[1])[0], 'Venituri din exploatare (total) — activitatea SOUL*')
nt = copy.deepcopy(B[193]); t.addnext(nt)
write_runs(nt, '* Proiecția acoperă activitatea SOUL (valori în lei, rotunjite la mia de lei, curs orientativ 5,09 lei/€); activitatea curentă a firmei (KREA, MundiShop) se adaugă de contabil [[Ct]]. Cheltuielile de exploatare includ costul bunurilor vândute, cheltuielile CDI, de comercializare, generale și amortizarea. Toate valorile sunt **estimări [E]**.')
assump = [
    '**Ipoteza 1 — volume și prețuri [E]:** An 1: 25 Founders × 349 € + 150 Batch 1 × 299 €; An 2: 150 × 299 € + 700 Standard × 279 €; An 3: 2.000 × 259 €; An 4: 4.000 × 249 €; An 5: 7.000 × 239 € (preț net mediu, după marja distribuitorilor). Reperele de preț sunt în §3.3 (OpenAI × Ive 300–400 $, STARBOY 349 $, Loona DeskMate 299 $).',
    '**Ipoteza 2 — cota de piață [E]:** 7.000 de unități în An 5 ≈ 3–14 % din piața adresabilă estimată în §3.1 (50–250 mii de unități în nișa „dispozitiv AI dedicat premium, BYO-AI, UE-first”), adică ≈ 0,014 % din cei ~50 M de utilizatori profesionali de AI generativ din UE.',
    '**Ipoteza 3 — clienți [E]:** An 1: 175 de clienți (25 din lista de așteptare + 150 din crowdfunding/magazin); conversie listă → cumpărător 2–10 % (referințe de crowdfunding, research 01); 20–50 de clienți B2B în An 3–5.',
    '**Ipoteza 4 — costuri unitare [E]:** COGS 190 € (Founders, loturi mici CNC) → 150 € (Batch 1) → 110 € → 80 € → 65 € → 60 € (An 5, PCB cu modul certificat, carcasă la volum); logistică, plăți și garanții 8 % din venitul hardware; CAC 20–30 €/unitate + costuri fixe de marketing și suport.',
    '**Ipoteza 5 — venituri recurente [E]:** serviciu opțional voce/memorie 4 €/lună, adoptat de 15 % din baza instalată din An 2 (cost direct 50 % din venit: API AI + voce, 1–4 $/utilizator/lună, research 04); accesorii și piese de schimb 5 % din venitul hardware; licențiere B2B 20/40/60 k€ în An 3/4/5.',
    '**Ipoteza 6 — CDI și echipă [E]:** An 1: inginer 1 normă + certificare CE/RED + EN 18031 (5–12 k€ + 0–9 k€); An 2: + suport/QA + inginer hardware 0,5 normă; An 3–5: 4–6 persoane. CapEx: scule și fixturi de producție (5/40/60/30/30 k€). Impozit pe profit 16 % cu reportarea pierderilor [[Ct: confirmă regimul fiscal]].',
    '**Scenariu prudent (−50 % unități, −10 % preț):** EBITDA negativ în An 1–3 și pozitiv din An 4 (≈ 0,4 M lei), ≈ 1,3 M lei în An 5; pierderile din An 1–3 se acoperă din precomenzi, finanțări nerambursabile (PR BI 1.2/Eurostars) și, după durabilitate, capital.',
]
fill(195, assump)
drop(196, 197)

drop(200)
t = B[201]
rs = rows(t)
rk = [[r[0], r[1], r[2], r[3], r[4]] for r in RISKS]
for tr, v in zip(rs[1:5], rk[:4]):
    fill_row(tr, v)
last = rs[4]
for v in rk[4:]:
    last = add_row_after(last, v)
write_runs(B[203], 'Legenda: probabilitatea și impactul sunt exprimate explicit (Mare / Medie / Redusă). Riscurile R1–R12 sunt identice cu secțiunea Riscuri din CF; R1 este riscul de eșec de cercetare prevăzut în ghid (§5.2.2, §5.7.1; Anexa 17).')

# declaration
write_runs(B[211], f'Subsemnatul/a, [[Nume Prenume]], în calitate de reprezentant legal al {APPLICANT}, declar pe propria răspundere că informațiile din prezentul Plan de Afaceri sunt corecte, complete și reflectă fidel capacitatea și intenția organizației noastre de a implementa proiectul propus în cadrul Apelului PR BI P1/1.1/1/2026.')
sig = tcs(rows(B[213])[0])
set_cell(sig[1], 'Data: [[ZZ/LL/AAAA]]\nFuncție: Administrator\nDenumire organizație: ARTEMIS DIGITAL S.R.L.')

for i, w in [(54, [700, 2500, 2500, 900, 1400, 1638]), (166, [450, 1700, 1500, 900, 1000, 700, 700, 900, 1788]),
             (172, [450, 1900, 2300, 1000, 800, 800, 800, 1588]), (201, [600, 3000, 1100, 1300, 3638]),
             (144, [1900, 2000, 900, 1300, 1300, 2238])]:
    set_widths(B[i], w)
# update fields (TOC) on open
st = d.settings.element
uf = OxmlElement('w:updateFields'); uf.set(W('val'), 'true')
after_tags = ['hdrShapeDefaults','footnotePr','endnotePr','compat','docVars','rsids','mathPr','attachedSchema','themeFontLang','clrSchemeMapping','doNotIncludeSubdocsInStats','doNotAutoCompressPictures','forceUpgrade','captions','readModeInkLockDown','smartTagType','schemaLibrary','shapeDefaults','doNotEmbedSmartTags','decimalSymbol','listSeparator']
for ch in st:
    if ch.tag.split('}')[1] in after_tags:
        ch.addprevious(uf); break
else:
    st.append(uf)

finalize(d)
d.save(OUT)
print('saved', OUT)
