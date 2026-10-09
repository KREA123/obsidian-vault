/* SOUL landing v3 — vanilla JS, progressive enhancement.
   Every block is optional: if the eye engine (eyes/eyes.js) is missing, the page still reads and the form still works. */
(() => {
"use strict";
const CFG = window.SOUL_CONFIG || {};
const SE = window.SoulEyes;
const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
const HOVER = matchMedia("(hover: hover) and (pointer: fine)").matches;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
};
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const pick = a => a[(Math.random() * a.length) | 0];
const nowS = () => performance.now() / 1000;

/* ================================================================== i18n */
const RO = {
  "skip": "Sari la conținut",
  "ann": "Prelansare · <b>încă fără certificare CE</b> · doar listă de așteptare, nu se plătește nimic.", "ann.why": "De ce?",
  "nav.object": "obiectul", "nav.colours": "culori", "nav.born": "născut", "nav.ai": "AI-ul tău", "nav.os": "SoulOS", "nav.privacy": "intimitate", "nav.faq": "întrebări", "nav.cta": "listă", "nav.sound": "Efecte sonore", "nav.soundL": "sunet",
  "hero.alt": "Randare de concept: SOUL din aluminiu argintiu, din față, o pietricică moale cu fața dintr-o singură sticlă neagră rotundă și doi ochi vii care se uită la tine.",
  "hero.hint": "psst. mișcă mouse-ul.",
  "hero.sayK": "SOUL · mărimea M · MĂRGĂRITAR", "hero.say": "cât palma. din aluminiu. viu.",
  "hero.h1": "AI-ul tău are creier.<br><em>dă-i un suflet.</em>",
  "hero.lead": "O piatră de aluminiu cât palma, cu doi ochi vii. Clipește, te urmărește cu privirea, ațipește când pleci. Și vorbește cu AI-ul pe care îl ai deja.",
  "hero.cta": "intră pe listă", "price.from": "de la",
  "marq.label": "SOUL, pe scurt",
  "m1": "fără cameră", "m2": "ascultă doar cât ții sticla", "m3": "Claude-ul sau ChatGPT-ul tău", "m4": "viu și offline", "m5": "se naște cu unul din 120 de ochi", "m6": "memoria stă pe dispozitiv", "m7": "proiectat în România",
  "alive.eyebrow": "viu, offline", "alive.h1": "se uită", "alive.h2": "înapoi.",
  "alive.lead": "Fără aplicație, fără cont, fără internet. Tot ce vezi pe sticlă rulează pe piatră și merge mai departe chiar dacă Wi-Fi-ul nu mai revine niciodată.",
  "alive.c1t": "clipește.", "alive.c1p": "La întâmplare, niciodată după ceas. Uneori de două ori, când e curios.",
  "alive.c2t": "te urmărește.", "alive.c2p": "Mouse-ul tău, aici. Degetul tău, pe birou. Știe mereu unde ai plecat.",
  "alive.c3t": "are toane.", "alive.c3p": "Vesel, somnoros, bănuitor, <i>șmecher</i>. Atinge-l și vezi ce-ți iese.",
  "fig.render": "randare de concept",
  "obj.alt": "Randare de concept: SOUL din profil, o pietricică subțire de aluminiu, adâncă de 31,5 mm, cu fața de sticlă neagră ușor înclinată în sus și fanta difuzorului în cusătura laterală.",
  "obj.eyebrow": "obiectul · MĂRGĂRITAR", "obj.h2": "o piatră pe care<br>vrei s-o ții în mână.",
  "obj.lead": "Forma lui se numește MĂRGĂRITAR: o pietricică cu umeri moi la creștet, din aluminiu, finisată ca o piatră de râu. O singură sticlă neagră rotundă pe față. Fără logo, fără butoane, fără găuri.",
  "obj.k1": "mărimea M", "obj.k2": "sticla", "obj.v2": "2,8″ rotundă, neagră", "obj.k3": "corp", "obj.v3": "aluminiu 6061", "obj.k4": "finisaj", "obj.v4": "sablat, anodizat",
  "col.eyebrow": "cinci aluminiuri", "col.h2": "tu alegi corpul.<br>ochii se aleg singuri.", "col.legend": "Culoare",
  "col.same": "Toate culorile costă la fel. Aluminiu 6061 sablat și anodizat, cu fața din sticlă neagră.",
  "col.alt": "Randare de concept: cinci SOUL-uri în șir, din aluminiu Grafit, Jar, Argint, Albastru noapte și Șampanie, fiecare cu perechea lui de ochi vii.",
  "col.fam": "Grafit, Jar, Argint, Albastru noapte, Șampanie. Cinci corpuri, cinci perechi de ochi diferite. Atinge orice sticlă.",
  "born.eyebrow": "născut, nu fabricat", "born.h1": "se naște cu unul din", "born.h2": "perechi de ochi.",
  "born.lead": "La prima pornire, fiecare SOUL se naște din ID-ul unic al cipului său. Ochii pe care îi primește sunt ochii pe care îi păstrează. Nu îi alege nimeni. Nici măcar noi.",
  "born.cvaria": "Ochii unui SOUL nou-născut", "born.name": "nume", "born.chip": "ID cip", "born.date": "născut",
  "born.roll": "naște-l pe al tău", "born.share": "copiază linkul", "born.chipL": "ID-ul cipului (12 caractere hexazecimale)", "born.chipGo": "caută un cip",
  "born.sample": "O naștere de probă. Scrie orice ID de cip și vezi exact cu ce ochi s-ar naște: același calcul rulează pe SOUL-ul adevărat.",
  "born.oddsCap": "Șansele fiecărei rarități la naștere", "born.th1": "raritate", "born.th2": "șansă", "born.th3": "modele", "born.th4": "o pereche anume",
  "born.oddsNote": "Sunt șansele reale din codul nașterii. În interiorul unei rarități, fiecare model e la fel de probabil. Raritatea schimbă doar ochii: fiecare SOUL face exact aceleași lucruri.",
  "born.gridT": "colecția", "born.filter": "Filtrează după raritate",
  "ai.eyebrow": "AI-ul tău, întrupat", "ai.h2": "adu-ți propriul AI.<br>primește un corp.",
  "ai.lead": "SOUL se conectează la AI-ul pe care îl folosești deja, pe contul tău. Nu vindem AI și nu îl includem. Sau îl ții offline: tot viu e.",
  "ai.c.k": "contul tău", "ai.c.t": "Claude-ul tău.", "ai.c.p": "Conectezi propriul cont Anthropic sau propria cheie API și vorbești cu el ținând sticla.",
  "ai.c.l1": "cont propriu sau cheie API", "ai.c.l2": "adaugi SOUL ca conector în aplicația Claude: îi ceri lui Claude să-i pună un plan, un memento sau o notiță",
  "ai.g.k": "cheia ta, de acum", "ai.g.t": "ChatGPT-ul tău.", "ai.g.p": "Pui propria cheie API OpenAI și merge. Plătești direct la OpenAI, nu nouă.",
  "ai.g.l1": "cheie API proprie: merge de acum", "ai.g.l2": "„Sign in with ChatGPT”: în așteptarea aprobării OpenAI",
  "ai.o.k": "fără cont", "ai.o.t": "Offline.", "ai.o.p": "Fără AI, fără înregistrare, niciodată. Ochii, toanele, notițele, mementourile, alarmele și focusul trăiesc pe piatră.",
  "ai.o.l1": "nimic nu pleacă de pe dispozitiv", "ai.o.l2": "scrii pe tastatura lui rotundă",
  "ai.m.t": "SOUL Memory stă pe dispozitiv.", "ai.m.p": "Ce ține minte despre tine rămâne în piatră, în cuvinte simple pe care le poți citi și șterge. Când vorbești, merge cu tine la AI-ul pe care l-ai conectat, așa că poți schimba AI-ul fără s-o iei de la capăt.",
  "ai.m.k": "schimbi AI-ul, păstrezi sufletul",
  "ai.note": "SOUL e în dezvoltare, iar aceste conexiuni sunt în lucru. Claude e marcă Anthropic; ChatGPT e marcă OpenAI. SOUL e independent și nu e afiliat cu niciuna și nici susținut de ele.",
  "hold.alt": "Randare de concept: SOUL argintiu pe o palmă deschisă. Acoperă palma ca o piatră mare și netedă, iar ochii lui se uită în sus, la tine.",
  "hold.hint": "ține apăsat pe sticlă", "hold.eyebrow": "ține sticla · demo scriptat", "hold.h2": "ține sticla.<br>te ascultă.",
  "hold.which": "Care AI", "hold.off": "offline",
  "hold.idle": "Ține apăsat pe sticlă (sau pe buton) și SOUL ascultă. Dai drumul și îți răspunde.",
  "hold.btn": "ține ca să vorbești", "hold.micOff": "microfon oprit",
  "hold.note": "Un demo scriptat, nu un AI live. Pe SOUL-ul adevărat microfonul e pornit doar cât timp ții degetul pe sticlă. Merge și cu Space sau Enter.",
  "os.eyebrow": "SoulOS", "os.h2": "un mic sistem de operare.<br>pe un cerc.",
  "os.lead": "Panouri de sticlă care plutesc peste fața lui, o tastatură rotundă, notițe, mementouri, alarme, hărți și aplicații mici. Merge pe hotspotul telefonului. Iar când se odihnește, e doar ochi pe negru pur.",
  "os.alt0": "Randare de concept: SOUL pe un birou de lemn, cu tastatura SoulOS pe ecranul rotund: cuvântul Hello deasupra unei tastaturi QWERTY rotunde.",
  "os.sbK": "repaus", "os.sb": "Fără ceas, fără lumină, fără notificări care se holbează la tine. În repaus, SOUL arată doar ochii, pe negru pur.",
  "os.row": "Ecrane SoulOS",
  "os.a1": "Tastatura SoulOS pe ecranul rotund: Hello scris deasupra unei tastaturi QWERTY rotunde.", "os.a2": "SoulOS după un mesaj către Claude: memento pus pentru ora 17:00.",
  "os.a3": "Alegerea modului AI în SoulOS.", "os.a4": "Alarmă SoulOS pusă rotind un cadran pe margine, aici la 7.",
  "os.a5": "Orbita din SoulOS: numele aplicațiilor stau pe marginea de jos ca un zâmbet.", "os.a6": "Azi în SoulOS: vremea, câte un lucru pe rând.",
  "os.c1t": "o tastatură adevărată", "os.c1": "QWERTY rotund, cu sugestii, diacritice și anulare.",
  "os.c2t": "îi scrii AI-ului tău", "os.c2": "„Amintește-mi la 5 să sun la bancă” devine un memento adevărat.",
  "os.c3t": "moduri AI", "os.c3": "Claude-ul tău, ChatGPT-ul tău sau deloc AI.",
  "os.c4t": "alarme pe cadran", "os.c4": "Rotești marginea până la oră. Se trezește el întâi, apoi te trezește pe tine.",
  "os.c5t": "orbita", "os.c5": "Aplicațiile stau pe margine ca un zâmbet. Le învârți cu degetul.",
  "os.c6t": "azi", "os.c6": "Glisezi în sus și îți spune câte un lucru pe rând.",
  "os.cta": "încearcă SoulOS", "os.ctap": "Rulează chiar aici, în browser: aceeași interfață ca pe piatră.",
  "night.alt": "Randare de concept, noaptea: SOUL în oul lui OU deschis, în întuneric, cu ochi somnoroși, luminat doar de strălucirea caldă a oului.",
  "night.hint": "atinge-l ca să-l trezești. n-o să-i placă.", "night.eyebrow": "OU · oul lui de încărcare", "night.h2": "noaptea,<br>doarme în oul lui.",
  "night.l1t": "se încarcă pe dedesubt", "night.l1": "Contacte aurii în picior. Îl pui în OU și se încarcă. Niciun cablu în piatră.",
  "night.l2t": "o lampă de veghe care nu te fixează", "night.l2": "Lumina caldă vine din ou, nu din ecran.",
  "night.l3t": "ochi închiși, microfon oprit", "night.l3": "Când doarme în OU nu ascultă. Te aude doar cât timp ții degetul pe sticlă.",
  "pr.eyebrow": "intimitate · în scris", "pr.h2": "promisiuni, nu setări.",
  "pr1t": "fără cameră. deloc.", "pr1p": "SOUL nu are nicio cameră. Ochii sunt doar ca să se uite înapoi.",
  "pr2t": "ascultă doar cât ții sticla.", "pr2p": "Fără cuvânt de trezire, fără microfon mereu pornit. Ridici degetul și se oprește.",
  "pr3t": "memorie pe care o citești.", "pr3p": "SOUL Memory stă pe dispozitiv, în cuvinte simple, la o atingere de ștergere.",
  "pr4t": "doar la AI-ul ales de tine.", "pr4p": "Cuvintele tale merg la AI-ul pe care l-ai conectat, pe contul tău. Offline, nimic nu pleacă de pe piatră. Fără reclame și nu îți vindem niciodată datele.",
  "pr5t": "spune mereu că e un AI.", "pr5p": "Nu se dă drept om, fără serii de zile, fără șantaj emoțional, fără bosumflări pentru atenție.",
  "pr6t": "nu devine niciodată o cărămidă.", "pr6p": "Personalitatea lui rulează pe dispozitiv. Dacă dispărem vreodată, publicăm firmware-ul. 16+, nu e o jucărie.",
  "sp.eyebrow": "mărimea M · specificații", "sp.h2": "partea plictisitoare.",
  "sp.k1": "ecran", "sp.v1": "rotund, 2,8″, 480 × 480, sub sticlă neagră", "sp.k2": "dimensiuni",
  "sp.k3": "corp", "sp.v3": "aluminiu 6061, sablat și anodizat", "sp.k4": "culori", "sp.v4": "Argint, Grafit, Albastru noapte, Jar, Șampanie",
  "sp.k5": "ochi", "sp.v5": "unul din 120 de modele, decis la naștere", "sp.k6": "creier", "sp.v6": "ESP32-S3, Bluetooth LE și Wi-Fi",
  "sp.k7": "AI", "sp.v7": "Claude-ul tău, ChatGPT-ul tău sau offline", "sp.k8": "voce", "sp.v8": "ții sticla ca să vorbești; difuzor în cusătura laterală",
  "sp.k9": "cameră", "sp.v9": "niciuna", "sp.k10": "încărcare", "sp.v10": "în OU, oul lui, prin contactele din picior",
  "sp.k11": "preț", "sp.vat": "cu TVA", "sp.k12": "stadiu", "sp.v12": "prelansare · încă fără certificare CE",
  "box.k": "planificat", "box.t": "ce e în cutie", "box.1": "SOUL, mărimea M", "box.1p": "în culoarea aleasă de tine, cu ochii aleși de el", "box.2": "OU, oul lui de încărcare", "box.2p": "unde se încarcă și doarme",
  "box.note": "Lista finală, autonomia bateriei și accesoriile le publicăm înainte să se deschidă rezervările.",
  "sp.note": "Toate imaginile produsului sunt randări de concept, nu fotografii. Specificațiile descriu designul aflat în dezvoltare și se pot schimba înainte de producție.",
  "faq.eyebrow": "întrebări", "faq.h2": "întrebări bune.",
  "q1": "Îl pot cumpăra acum?", "a1": "Încă nu. SOUL are Bluetooth și Wi-Fi, deci trebuie să treacă testele CE (Directiva UE privind echipamentele radio) într-un laborator acreditat înainte să-l poată vinde cineva. Încă nu are certificare CE. Până atunci există doar o listă de așteptare: fără plată, fără precomenzi, fără avansuri.",
  "q2": "Am nevoie de abonament?", "a2": "Nu la noi. SOUL e viu offline, fără cont. Pentru AI îți conectezi propriul Claude sau ChatGPT, pe contul sau cheia ta API, și îi plătești direct pe ei. Nu vindem și nu includem AI.",
  "q3": "Cu ce AI merge?", "a3": "Claude: propriul cont Anthropic sau propria cheie API, plus un conector pentru aplicația Claude. ChatGPT: propria cheie API OpenAI merge de acum; „Sign in with ChatGPT” așteaptă aprobarea OpenAI. Sau deloc AI. SOUL e în dezvoltare, iar aceste conexiuni sunt în lucru.",
  "q4": "Ce e SOUL Memory?", "a4": "Lucrurile pe care SOUL le ține minte despre tine: nume, planuri, preferințe. Stau pe dispozitiv, în cuvinte simple pe care le poți citi și șterge. Când vorbești, merg cu tine la AI-ul conectat, așa că schimbarea AI-ului nu înseamnă s-o iei de la capăt.",
  "q5": "Ascultă tot timpul? Are cameră?", "a5": "Nu și nu. Ascultă doar cât timp ții degetul pe sticlă. Nu are cuvânt de trezire și nu are cameră.",
  "q6": "Pot să-i aleg ochii?", "a6": "Nu, și tocmai asta e distracția. Tu alegi culoarea corpului. Ochii se decid o singură dată, la prima pornire, din ID-ul unic al cipului: unul din 120 de modele, unele mult mai rare decât altele. Șansele sunt publicate mai sus.",
  "q7": "Merge și departe de casă?", "a7": "Da. Offline e mereu viu. Pentru AI are nevoie de Wi-Fi și poate merge pe hotspotul telefonului tău.",
  "q8": "Cât ține bateria?", "a8": "Publicăm autonomia măsurată înainte să cerem cuiva să plătească. Se încarcă în OU, oul lui.",
  "q9": "E o jucărie?", "a9": "Nu. SOUL e făcut pentru adulți și adolescenți de peste 16 ani. Conține piese mici și o baterie cu litiu.",
  "q10": "Cine îl face?", "a10": "ARTEMIS DIGITAL S.R.L., din București, România. Proiectat în România. Anunțăm partenerii de producție înainte să cerem cuiva să plătească.",
  "res.alt": "SOUL în culoarea aleasă, cu ochii urmărindu-te cum completezi formularul.",
  "res.eyebrow": "listă de așteptare · de la 249 €", "res.h2": "fii acolo când deschide ochii.",
  "res.lead": "Lasă-ne emailul. Îți scriem când se deschid rezervările, înaintea tuturor. Fără plată, fără precomandă.",
  "res.email": "email", "res.lang": "emailuri în", "res.colour": "culoarea preferată",
  "res.consent": "Sunt de acord să primesc emailuri despre SOUL de la ARTEMIS DIGITAL S.R.L. și mă pot dezabona oricând. Citește <a href=\"#legal\">Politica de confidențialitate</a>.",
  "res.submit": "intră pe listă", "res.fine": "Aici nu se plătește nimic. Un email când se deschid rezervările și câte o noutate până atunci.",
  "res.th": "ești pe listă.", "res.tp": "Tocmai ți-a zâmbit. Îți scriem înaintea tuturor.", "res.tc": "culoare", "res.tl": "limbă",
  "res.demo": "Mod de previzualizare: pagina asta încă nu trimite emailul nicăieri. Versiunea de magazin o va face.",
  "f.privacy": "Politica de confidențialitate", "f.terms": "Termeni", "f.cookies": "Cookie-uri", "f.os": "Încearcă SoulOS", "f.anpc": "Litigii consumatori (ANPC · SAL)", "f.odr": "Soluționarea online a litigiilor (UE)",
  "f.company": "Companie", "f.city": "București, România", "f.addr": "Adresă:", "f.cui": "CUI:", "f.reg": "Nr. Reg. Com.:", "f.contact": "Contact:",
  "f.status": "Stadiul produsului", "f.statusp": "SOUL e un produs în dezvoltare. Încă nu are certificare CE și nu e oferit spre vânzare. Paginile legale (confidențialitate, termeni, cookie-uri, datele producătorului conform GPSR) sunt provizorii și vor fi publicate înainte să se deschidă rezervările.",
  "f.tm": "Claude este o marcă comercială a Anthropic. ChatGPT este o marcă comercială a OpenAI. SOUL este independent și nu este afiliat cu Anthropic sau OpenAI și nici susținut de acestea.",
  "f.made": "© 2026 ARTEMIS DIGITAL S.R.L. Ține sticla.", "f.ro": "Proiectat în România."
};
const COLS = [
  { k: "silver", hex: "#CBCDCF", en: "Silver", ro: "Argint", den: "The classic. Cool and bright, like a river stone in daylight.", dro: "Clasicul. Rece și luminos, ca o piatră de râu în plină zi." },
  { k: "graphite", hex: "#55575B", en: "Graphite", ro: "Grafit", den: "Dark and quiet. The cream eyes look warmest against it.", dro: "Închis și liniștit. Ochii crem par cei mai calzi pe el." },
  { k: "midnight", hex: "#26324C", en: "Midnight", ro: "Albastru noapte", den: "A deep blue that reads almost black in the evening.", dro: "Un albastru adânc care seara pare aproape negru." },
  { k: "ember", hex: "#D2622C", en: "Ember", ro: "Jar", den: "Warm orange, the colour of a coal that's still glowing.", dro: "Portocaliu cald, culoarea unui cărbune care încă arde." },
  { k: "champagne", hex: "#D8C3A2", en: "Champagne", ro: "Șampanie", den: "Soft gold. At home on a wooden desk.", dro: "Auriu moale. Ca acasă pe un birou de lemn." }
];
const DYN = {
  en: {
    email: "Enter an email address like name@example.com.", consent: "Tick the box so we can write to you.",
    net: "We couldn't reach the list. Check your connection and try again.", sending: "Sending…",
    rar: { common: "Common", uncommon: "Uncommon", rare: "Rare", epic: "Epic", legendary: "Legendary", mythic: "Mythic" },
    featured: "featured", all: "all 120",
    oneIn: n => "1 in " + n.toLocaleString("en-GB"),
    date: d => d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }).replace("Sept", "Sep"),
    hintTouch: "tap the glass.", hint: "psst. move your cursor.",
    cta: c => "waitlist in " + c, from: "from", wink: "tap for a wink",
    chipBad: "A chip ID has 12 hex characters (0–9, A–F), like 34:85:18:6A:C2:9F.",
    copied: "link copied", copy: "copy link",
    langName: { en: "English", ro: "Română" },
    short: "hold a little longer…",
    via: { claude: "via your Claude", chatgpt: "via your ChatGPT", offline: "offline · on the device" }, mem: " · SOUL Memory",
    scripts: [
      { you: "remind me to call mum on sunday at eleven.", ai: "done. sunday at 11:00: call mum. I'll remind you at 10:45 too." },
      { you: "what did I want to get Ana for her birthday?", ai: "the blue notebook from the shop near your office. her birthday is on the 14th.", mem: true },
      { you: "wake me at seven. gently.", ai: "alarm at 7:00. I'll wake up first, then wake you, slowly." }
    ],
    offline: "offline, I can't understand speech: voice needs the AI you connect. type it on my keyboard instead. reminders, alarms and notes work without any AI.",
    micOn: "listening", micOff: "mic off", thinking: "thinking…"
  },
  ro: {
    email: "Scrie o adresă de email, de exemplu nume@exemplu.ro.", consent: "Bifează căsuța ca să-ți putem scrie.",
    net: "Nu am putut ajunge la listă. Verifică conexiunea și încearcă din nou.", sending: "Se trimite…",
    rar: { common: "Comun", uncommon: "Neobișnuit", rare: "Rar", epic: "Epic", legendary: "Legendar", mythic: "Mitic" },
    featured: "recomandate", all: "toate 120",
    oneIn: n => "1 din " + n.toLocaleString("ro-RO"),
    date: d => { const p = n => String(n).padStart(2, "0"); return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}`; },
    hintTouch: "atinge sticla.", hint: "psst. mișcă mouse-ul.",
    cta: c => "pe listă în " + c, from: "de la", wink: "atinge pentru un ochi făcut",
    chipBad: "Un ID de cip are 12 caractere hexazecimale (0–9, A–F), de exemplu 34:85:18:6A:C2:9F.",
    copied: "link copiat", copy: "copiază linkul",
    langName: { en: "English", ro: "Română" },
    short: "mai ține puțin…",
    via: { claude: "prin Claude-ul tău", chatgpt: "prin ChatGPT-ul tău", offline: "offline · pe dispozitiv" }, mem: " · SOUL Memory",
    scripts: [
      { you: "amintește-mi s-o sun pe mama duminică la unsprezece.", ai: "gata. duminică la 11:00: o suni pe mama. îți amintesc și la 10:45." },
      { you: "ce voiam să-i iau Anei de ziua ei?", ai: "carnetul albastru de la magazinul de lângă birou. ziua ei e pe 14.", mem: true },
      { you: "trezește-mă la șapte. cu blândețe.", ai: "alarmă la 7:00. mă trezesc eu întâi, apoi te trezesc pe tine, încet." }
    ],
    offline: "offline nu pot înțelege vorbirea: vocea are nevoie de AI-ul pe care îl conectezi. scrie-mi pe tastatură. mementourile, alarmele și notițele merg fără AI.",
    micOn: "ascultă", micOff: "microfon oprit", thinking: "se gândește…"
  }
};
const EN = {};
$$("[data-i18n]").forEach(el => { EN[el.dataset.i18n] = el.innerHTML; });
$$("[data-i18n-attr]").forEach(el => el.dataset.i18nAttr.split(",").forEach(pair => { const [a, k] = pair.split(":"); EN[k] = el.getAttribute(a) || ""; }));
let LANG = "en";
const D = () => DYN[LANG];
const colName = k => { const c = COLS.find(x => x.k === k) || COLS[0]; return c[LANG]; };
function money(v) {
  const cur = CFG.CURRENCY || "EUR", sym = { EUR: "€", RON: "lei", USD: "$", GBP: "£" }[cur] || cur;
  const n = Number(v).toLocaleString(LANG === "ro" ? "ro-RO" : "en-IE", { maximumFractionDigits: 2 });
  return LANG === "ro" || sym.length > 1 ? n + " " + sym : sym + n;
}
let COUNT = 120;
function fillConfig() {
  const P = CFG.PRICES || {};
  $$("[data-price]").forEach(el => { const v = P[el.dataset.price]; if (v != null) el.textContent = money(v); });
  $$("[data-cfg='email']").forEach(el => { if (CFG.CONTACT_EMAIL) el.textContent = CFG.CONTACT_EMAIL; });
  $$("[data-count]").forEach(el => { el.textContent = COUNT; });
}
const langHooks = [];
function applyLang(lang, save) {
  LANG = lang === "ro" ? "ro" : "en";
  document.documentElement.lang = LANG;
  $$("[data-i18n]").forEach(el => {
    const k = el.dataset.i18n, v = LANG === "ro" ? (RO[k] != null ? RO[k] : EN[k]) : EN[k];
    if (v != null && el.innerHTML !== v) el.innerHTML = v;
  });
  $$("[data-i18n-attr]").forEach(el => el.dataset.i18nAttr.split(",").forEach(pair => {
    const [a, k] = pair.split(":"), v = LANG === "ro" ? (RO[k] != null ? RO[k] : EN[k]) : EN[k];
    if (v != null) el.setAttribute(a, v);
  }));
  $$(".lang button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lang === LANG)));
  fillConfig();
  langHooks.forEach(f => { try { f(); } catch (e) {} });
  if (save) store.set("soul-lang", LANG);
}

/* structured data for search (built from the English FAQ) */
try {
  const strip = h => h.replace(/<[^>]+>/g, "");
  const faq = [];
  for (let i = 1; EN["q" + i]; i++) faq.push({ "@type": "Question", name: strip(EN["q" + i]), acceptedAnswer: { "@type": "Answer", text: strip(EN["a" + i]) } });
  const ld = [{ "@context": "https://schema.org", "@type": "Organization", name: "SOUL", legalName: "ARTEMIS DIGITAL S.R.L.", address: { "@type": "PostalAddress", addressLocality: "Bucharest", addressCountry: "RO" } },
              { "@context": "https://schema.org", "@type": "FAQPage", mainEntity: faq }];
  const s = document.createElement("script"); s.type = "application/ld+json"; s.textContent = JSON.stringify(ld); document.head.appendChild(s);
} catch (e) {}

/* ================================================================== sound (off by default) */
let SOUND = store.get("soul-sound") === "1", AC = null;
function tone(f, d, type, g, when) {
  if (!SOUND) return;
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    const t = AC.currentTime + (when || 0), o = AC.createOscillator(), v = AC.createGain();
    o.type = type || "sine"; o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * 1.5, t + d * .6);
    v.gain.setValueAtTime(0, t); v.gain.linearRampToValueAtTime(g || .05, t + .012); v.gain.exponentialRampToValueAtTime(.0001, t + d);
    o.connect(v).connect(AC.destination); o.start(t); o.stop(t + d + .02);
  } catch (e) {}
}
const sfx = {
  boop: () => tone(520 + Math.random() * 160, .14, "sine", .06),
  tick: () => tone(1200 + Math.random() * 300, .03, "square", .012),
  reveal: () => { [523, 659, 784, 1047].forEach((f, i) => tone(f, .32, "triangle", .045, i * .07)); },
  wink: () => { tone(880, .07, "sine", .05); tone(1320, .09, "sine", .04, .07); }
};
const sndBtn = $("#snd");
const paintSnd = () => sndBtn && sndBtn.setAttribute("aria-pressed", String(SOUND));
paintSnd();
if (sndBtn) sndBtn.addEventListener("click", () => { SOUND = !SOUND; store.set("soul-sound", SOUND ? "1" : "0"); paintSnd(); sfx.wink(); });

/* ================================================================== the eye collection */
const DATA = window.SOUL_DESIGNS || { designs: [] };
const DESIGNS = DATA.designs && DATA.designs.length ? DATA.designs : [{ id: "original", n: 1, num: "#001", name: "Original", rarity: "common" }];
COUNT = DESIGNS.length;
const byId = id => DESIGNS.find(d => d.id === id) || DESIGNS[0];
const RAR = {}; (SE ? SE.RARITIES : []).forEach(r => { RAR[r.key] = r; });
const rarColor = k => (RAR[k] && RAR[k].color) || "#C9C4B8";
const numOf = d => d.num || "#" + String(d.n).padStart(3, "0");

/* where the glass sits in each picture: centre (fraction of the image) and the 2×2 map of the unit disc, in image px */
const GLASS = {"hand":{"w":1400,"h":1200,"glass":[{"c":[0.50417,0.48276],"m":[216.88,10.21,10.21,162.25]}]},"night":{"w":960,"h":1200,"glass":[{"c":[0.49863,0.4907],"m":[140.12,-2.42,-2.42,152.05]}]},"family":{"w":2000,"h":1125,"glass":[{"c":[0.15108,0.49004],"m":[117.63,0,0,117.63]},{"c":[0.31614,0.4937],"m":[119.36,0,0,119.36]},{"c":[0.50151,0.50236],"m":[121.31,0,0,121.31]},{"c":[0.68943,0.49376],"m":[118.72,0,0,118.72]},{"c":[0.85907,0.48349],"m":[115.39,0,0,115.39]}]},"front":{"w":1956,"h":2236,"glass":[{"c":[0.5,0.46868],"m":[671.93,0,0,669.08]}]},"col":{"w":1223,"h":1469,"glass":[{"c":[0.55014,0.46756],"m":[390.82,-18.17,22.56,432.22]}]}};

const LIVE = [];   // { inst, cv, role, follow, shot }
function mountGlass(shot) {
  const key = shot.dataset.glass, g = GLASS[key];
  if (!g || !SE) return [];
  const ids = (shot.dataset.design || "original").split(",");
  const out = [];
  g.glass.forEach((gl, i) => {
    const [m11, m21, m12, m22] = gl.m;
    const R = Math.max(Math.hypot(m11, m21), Math.hypot(m12, m22));
    const cx = gl.c[0] * g.w, cy = gl.c[1] * g.h;
    const pos = `left:${(cx - R) / g.w * 100}%;top:${(cy - R) / g.h * 100}%;width:${2 * R / g.w * 100}%;height:${2 * R / g.h * 100}%;transform:matrix(${m11 / R},${m21 / R},${m12 / R},${m22 / R},0,0)`;
    const cv = document.createElement("canvas");
    cv.className = "live"; cv.setAttribute("style", pos); cv.setAttribute("aria-hidden", "true");
    shot.appendChild(cv);
    if (key === "front" || key === "col") { const s = document.createElement("span"); s.className = "sheen"; s.setAttribute("style", pos); shot.appendChild(s); }
    const inst = SE.createEyes(cv, byId(ids[i % ids.length]), { glass: false, fit: 1, interactive: false, seed: (Math.random() * 1e9) | 0 });
    const rec = { inst, cv, role: shot.dataset.role, follow: true, shot, i };
    LIVE.push(rec); out.push(rec);
  });
  return out;
}

/* everyone looks at the pointer (or the last touch) */
const PTR = { x: innerWidth / 2, y: innerHeight * .4, t: -1e9, active: false };
addEventListener("pointermove", e => { PTR.x = e.clientX; PTR.y = e.clientY; PTR.t = nowS(); PTR.active = true; }, { passive: true });
addEventListener("pointerdown", e => { PTR.x = e.clientX; PTR.y = e.clientY; PTR.t = nowS(); PTR.active = true; }, { passive: true });
document.addEventListener("pointerleave", () => { PTR.active = false; });
function lookLoop() {
  if (!document.hidden) {
    const fresh = PTR.active && nowS() - PTR.t < (HOVER ? 6 : 2.5);
    for (const r of LIVE) {
      if (!r.inst._visible) continue;
      if (!r.follow || !fresh) { if (r.looking) { r.inst.lookAt(null); r.looking = false; } continue; }
      const b = r.cv.getBoundingClientRect();
      const k = Math.max(220, b.width * 1.6);
      r.inst.lookAt(clamp((PTR.x - (b.left + b.width / 2)) / k, -1, 1), clamp((PTR.y - (b.top + b.height / 2)) / k, -1, 1));
      r.looking = true;
    }
  }
  setTimeout(() => requestAnimationFrame(lookLoop), 40);
}
/* the engine already skips canvases that are off-screen; this also pauses everything while the tab is hidden */
document.addEventListener("visibilitychange", () => { LIVE.forEach(r => r.inst.pause(document.hidden)); });

const TAPS = ["wink", "laugh", "happy", "smirk", "surprised", "love", "excited", "shy", "suspicious", "smug", "sneeze"];
function tapReact(r, name) {
  const n = name || pick(TAPS);
  if (n === "smirk" || n === "suspicious" || n === "smug") { r.follow = false; setTimeout(() => { r.follow = true; }, 2600); }
  r.inst.react(n, SE.MOODS[n] ? 2.2 : undefined);
  (n === "wink" ? sfx.wink : sfx.boop)();
}

$$(".shot[data-glass]").forEach(s => mountGlass(s));
const byRole = role => LIVE.filter(r => r.role === role);
LIVE.forEach(r => {
  if (["hand", "night", "moods", "reserve"].includes(r.role)) return;
  r.cv.addEventListener("click", () => tapReact(r));
});

/* ================================================================== hero: wakes up, then scroll parts the letters */
const hero = byRole("hero")[0];
if (hero) {
  hero.inst.setExpression("sleepy");
  setTimeout(() => { hero.inst.setExpression("neutral"); hero.inst.react("wake"); sfx.boop(); }, RM ? 0 : 650);
  let idleT = nowS(), asleep = false;
  const poke = () => { idleT = nowS(); if (asleep) { asleep = false; hero.inst.setExpression("neutral"); hero.inst.react("wake"); } };
  ["pointermove", "pointerdown", "keydown", "scroll"].forEach(ev => addEventListener(ev, poke, { passive: true }));
  setInterval(() => { if (!asleep && nowS() - idleT > 22) { asleep = true; hero.inst.setExpression("sleepy"); } }, 1000);
}
const hint = $("#hint");
langHooks.push(() => { if (hint) hint.textContent = HOVER ? D().hint : D().hintTouch; });

const heroSec = $(".hero"), pin = $(".hero-pin"), dev = $("#hero-dev"), wS = $("#wm-s"), wU = $("#wm-u"), wL = $("#wm-l"), nav = $("#nav");
const PIN = !RM && innerHeight >= 520;
if (!PIN) document.documentElement.classList.add("no-pin");
let lastY = scrollY, lastT = performance.now(), surprisedAt = 0, greeted = false;
function onScroll() {
  const y = scrollY;
  nav.classList.toggle("scrolled", y > 40);
  if (PIN && pin) {
    const r = pin.getBoundingClientRect(), span = Math.max(1, pin.offsetHeight - (innerHeight - nav.offsetHeight));
    const p = clamp(-(r.top - nav.offsetHeight) / span, 0, 1);
    const e = p * p * (3 - 2 * p);
    heroSec.style.setProperty("--p", p.toFixed(4));
    const mobile = innerWidth <= 720;
    dev.style.setProperty("--sc", (1 + e * (mobile ? .12 : .2)).toFixed(4));
    dev.style.setProperty("--dx", mobile ? "0%" : (e * 11.71).toFixed(3) + "%");
    dev.style.setProperty("--dy", (-e * (mobile ? 30 : 46)).toFixed(1) + "px");
    dev.style.setProperty("--rot", (Math.sin(e * Math.PI) * -5).toFixed(3) + "deg");
    wS.setAttribute("transform", `translate(${(-70 * e).toFixed(2)} 0)`);
    wU.setAttribute("transform", `translate(${(60 * e).toFixed(2)} 0)`);
    wL.setAttribute("transform", `translate(${(110 * e).toFixed(2)} 0)`);
    const op = (1 - e * .92).toFixed(3);
    wS.style.opacity = op; wU.style.opacity = op; wL.style.opacity = op;
    if (hero && p > .55 && !greeted) { greeted = true; hero.inst.react("love", 1.6); sfx.wink(); }
    if (p < .2) greeted = false;
  }
  const t = performance.now(), v = (y - lastY) / Math.max(1, t - lastT);
  lastY = y; lastT = t;
  if (hero && Math.abs(v) > 3.2 && t - surprisedAt > 4000 && y < innerHeight * 1.5) { surprisedAt = t; hero.inst.react("shocked"); }
}
let ticking = false;
addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; onScroll(); }); } }, { passive: true });
addEventListener("resize", onScroll, { passive: true });
onScroll();

let lastMood = 0;
$$("[data-react]").forEach(el => el.addEventListener("pointerenter", () => {
  const t = performance.now(); if (t - lastMood < 1200) return; lastMood = t;
  const n = el.dataset.react;
  LIVE.filter(r => r.inst._visible).forEach((r, i) => setTimeout(() => {
    if (n === "smirk") { r.follow = false; setTimeout(() => { r.follow = true; }, 2400); }
    r.inst.react(n, 1.8);
  }, i * 60));
}));

/* ================================================================== alive */
const inl = $("canvas[data-inline]");
if (inl && SE) {
  const inst = SE.createEyes(inl, byId("original"), { fit: .98, bezel: false, sheen: false, interactive: false });
  const rec = { inst, cv: inl, role: "inline", follow: true };
  LIVE.push(rec);
  inl.addEventListener("click", () => tapReact(rec, "wink"));
}
const blinkCard = byRole("blink")[0];
if (blinkCard) { blinkCard.follow = false; setInterval(() => { if (blinkCard.inst._visible && !document.hidden && Math.random() < .5) blinkCard.inst.blink(Math.random() < .35 ? 2 : 1); }, 1400); }
const moodCard = byRole("moods")[0];
if (moodCard) {
  const seq = ["happy", "sleepy", "suspicious", "smirk", "love", "surprised", "excited", "confused"];
  let i = 0;
  moodCard.inst.setExpression("smirk"); moodCard.follow = false;
  moodCard.cv.addEventListener("click", () => {
    i = (i + 1) % seq.length; const n = seq[i];
    moodCard.follow = n === "happy" || n === "surprised";
    moodCard.inst.setExpression(n); sfx.boop();
  });
}

/* ================================================================== the object: dimension lines draw in */
const sideFig = $("#side-fig");

/* ================================================================== configurator (+ waitlist colour, kept in sync) */
let COLOUR = "silver";
const cfgRec = byRole("cfg")[0], resRec = byRole("reserve")[0];
const cfgImg = $("#cfg-img"), cfgShot = $("#cfg-shot"), cfgStage = $("#cfg-stage"), resImg = $("#res-img");
const srcset = k => `media/v3/col-${k}-520.webp 520w, media/v3/col-${k}-900.webp 900w`;
function buildSwatches(box, name) {
  if (!box) return;
  COLS.forEach(c => {
    const i = document.createElement("input");
    i.type = "radio"; i.name = name; i.value = c.k; i.className = "sw"; i.style.setProperty("--c", c.hex);
    i.checked = c.k === COLOUR;
    i.addEventListener("change", () => { if (i.checked) setColour(c.k, name); });
    box.appendChild(i);
  });
  if (name === "wl-col") { const s = document.createElement("span"); s.className = "swname"; s.id = "wl-swname"; box.appendChild(s); }
}
buildSwatches($("#cfg-sw"), "cfg-col");
buildSwatches($("#wl-sw"), "wl-col");
let preloaded = false;
function preloadCols() {
  if (preloaded || !cfgImg) return; preloaded = true;
  COLS.forEach(c => { const im = new Image(); im.sizes = cfgImg.sizes; im.srcset = srcset(c.k); im.decode && im.decode().catch(() => {}); });
}
function paintColour() {
  const c = COLS.find(x => x.k === COLOUR) || COLS[0];
  const n = c[LANG];
  const nm = $("#cfg-name"); if (nm) nm.textContent = n;
  const ds = $("#cfg-desc"); if (ds) ds.textContent = LANG === "ro" ? c.dro : c.den;
  const ct = $("#cfg-cta-t"); if (ct) ct.textContent = D().cta(n);
  const sn = $("#wl-swname"); if (sn) sn.textContent = n;
  $$(".sw").forEach(i => { const cc = COLS.find(x => x.k === i.value); i.setAttribute("aria-label", cc[LANG]); i.checked = i.value === COLOUR; });
  if (cfgImg) cfgImg.alt = (LANG === "ro" ? "Randare de concept: SOUL din aluminiu " : "Concept render of SOUL in ") + n + (LANG === "ro" ? ", din față, cu ochi vii." : " aluminium, front view, with live eyes.");
  syncTags();
}
langHooks.push(paintColour);
function setColour(k, from) {
  if (!COLS.some(c => c.k === k)) return;
  const changed = k !== COLOUR; COLOUR = k;
  preloadCols();
  if (changed) {
    if (cfgImg) cfgImg.srcset = srcset(k), cfgImg.src = `media/v3/col-${k}-900.webp`;
    if (resImg) resImg.srcset = srcset(k), resImg.src = `media/v3/col-${k}-520.webp`;
    if (cfgStage) cfgStage.style.setProperty("--tint", (COLS.find(c => c.k === k) || COLS[0]).hex);
    if (cfgShot && !RM) { cfgShot.classList.remove("swap"); void cfgShot.offsetWidth; cfgShot.classList.add("swap"); }
    if (cfgRec) cfgRec.inst.react(pick(["excited", "happy", "love", "wink"]), 1.4);
    if (resRec && from === "wl-col") { resRec.inst.setExpression("neutral"); resRec.inst.react("excited", 1.4); }
    sfx.boop();
  }
  paintColour();
}
if (cfgStage && "IntersectionObserver" in window) {
  const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { preloadCols(); io.disconnect(); } }, { rootMargin: "600px 0px" });
  io.observe(cfgStage);
}
const cfgCta = $("#cfg-cta");
if (cfgCta) cfgCta.addEventListener("click", () => { setColour(COLOUR, "cfg"); setTimeout(() => { const e = $("#wl-email"); if (e) e.focus({ preventScroll: true }); }, RM ? 0 : 700); });

/* ================================================================== born: odds, collection, roll, chip lookup */
const counts = {}; DESIGNS.forEach(d => { counts[d.rarity] = (counts[d.rarity] || 0) + 1; });
const ob = $("#odds-body");
function paintOdds() {
  if (!ob || !SE) return;
  const maxRate = Math.max(...SE.RARITIES.map(r => r.rate));
  ob.innerHTML = SE.RARITIES.map(r => {
    const n = counts[r.key] || 0, each = n ? Math.round(n / r.rate) : 0;
    return `<tr><td><span class="rar" style="--c:${r.color}">${D().rar[r.key]}</span></td><td class="num">${(r.rate * 100).toLocaleString(LANG === "ro" ? "ro-RO" : "en-GB")}%</td><td class="num">${n}</td><td class="num">${each ? D().oneIn(each) : "–"}</td><td aria-hidden="true"><span class="bar" style="--c:${r.color};width:${Math.max(1.5, r.rate / maxRate * 100)}%"></span></td></tr>`;
  }).join("");
}
langHooks.push(paintOdds);

const grid = $("#egrid"), filtersBox = $("#filters");
const featured = (() => {
  const want = { mythic: 2, legendary: 3, epic: 4, rare: 5, uncommon: 5, common: 5 }, out = [];
  Object.keys(want).forEach(k => DESIGNS.filter(d => d.rarity === k).slice(0, want[k]).forEach(d => out.push(d)));
  let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; }
  return out;
})();
const gridInst = [];
let FILTER = "featured";
function cell(d) {
  const b = document.createElement("button");
  b.type = "button"; b.className = "ecell";
  b.innerHTML = `<canvas aria-hidden="true"></canvas><b>${d.name}</b><small style="--c:${rarColor(d.rarity)}" data-rar="${d.rarity}">${numOf(d)}</small>`;
  grid.appendChild(b);
  const inst = SE.createEyes(b.querySelector("canvas"), d, { fit: .92, interactive: false, seed: d.n * 977 });
  const rec = { inst, cv: b.querySelector("canvas"), role: "grid", follow: true };
  LIVE.push(rec); gridInst.push(rec);
  b.setAttribute("aria-label", `${d.name}, ${D().rar[d.rarity]}`);
  b.addEventListener("click", () => { showBirth(d, null); $(".roll").scrollIntoView({ behavior: RM ? "auto" : "smooth", block: "center" }); });
  b.addEventListener("pointerenter", () => inst.react(pick(["wink", "happy", "surprised", "smirk"]), 1.4));
}
function paintGrid() {
  if (!grid || !SE) return;
  gridInst.splice(0).forEach(r => { r.inst.destroy(); const k = LIVE.indexOf(r); if (k >= 0) LIVE.splice(k, 1); });
  grid.innerHTML = "";
  const list = FILTER === "featured" ? featured : FILTER === "all" ? DESIGNS.slice().sort((a, b) => a.n - b.n) : DESIGNS.filter(d => d.rarity === FILTER).sort((a, b) => a.n - b.n);
  list.forEach(cell);
}
function paintFilters() {
  if (!filtersBox || !SE) return;
  const keys = ["featured", ...SE.RARITIES.map(r => r.key).reverse(), "all"];
  filtersBox.innerHTML = "";
  keys.forEach(k => {
    const b = document.createElement("button"); b.type = "button";
    b.textContent = k === "featured" ? D().featured : k === "all" ? D().all : D().rar[k] + " · " + (counts[k] || 0);
    b.setAttribute("aria-pressed", String(k === FILTER));
    b.addEventListener("click", () => { FILTER = k; paintFilters(); paintGrid(); });
    filtersBox.appendChild(b);
  });
}
langHooks.push(() => { paintFilters(); $$("#egrid small[data-rar]").forEach(s => s.parentElement.setAttribute("aria-label", `${s.previousElementSibling.textContent}, ${D().rar[s.dataset.rar]}`)); });
/* build the collection only when it comes near the screen */
if (grid && SE) {
  const go = () => { paintGrid(); };
  if ("IntersectionObserver" in window) { const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { go(); io.disconnect(); } }, { rootMargin: "800px 0px" }); io.observe(grid); } else go();
}

const NAMES = ["Mira", "Luma", "Nova", "Kai", "Juno", "Tomi", "Nara", "Ivo", "Sia", "Pip", "Ada", "Luca", "Eli", "Ema", "Bobo", "Zia", "Dor", "Ilinca", "Toma", "Vali"];
const rollCv = $("#roll-cv");
const roller = SE && rollCv ? SE.createEyes(rollCv, byId("original"), { fit: .9, interactive: false }) : null;
const rollRec = roller ? { inst: roller, cv: rollCv, role: "roll", follow: true } : null;
if (rollRec) { LIVE.push(rollRec); rollCv.addEventListener("click", () => tapReact(rollRec)); }
const fmtChip = hex => hex.toUpperCase().match(/.{2}/g).join(":");
const cleanChip = s => String(s || "").replace(/[^0-9a-fA-F]/g, "");
function randChip() { const b = [0x34, 0x85, 0x18]; for (let i = 0; i < 3; i++) b.push((Math.random() * 256) | 0); return b.map(x => x.toString(16).padStart(2, "0")).join(""); }
let BIRTH = null;
function paintBirth() {
  if (!BIRTH) return;
  const d = BIRTH.design, n = counts[d.rarity] || 1, rate = RAR[d.rarity] ? RAR[d.rarity].rate : .5;
  $("#rc-num").textContent = `${numOf(d)} / ${COUNT}`;
  $("#rc-name").textContent = d.name;
  const rr = $("#rc-rar"); rr.textContent = D().rar[d.rarity]; rr.style.setProperty("--c", rarColor(d.rarity));
  $("#rc-odds").textContent = D().oneIn(Math.round(n / rate));
  $("#rc-pet").textContent = BIRTH.pet;
  $("#rc-chip").textContent = BIRTH.chip ? fmtChip(BIRTH.chip) : "–";
  $("#rc-date").textContent = D().date(BIRTH.date);
}
langHooks.push(paintBirth);
function petFor(chip) { return chip && SE ? NAMES[SE.hashStr(chip.toLowerCase()) % NAMES.length] : "Mira"; }
function showBirth(design, chip) {
  BIRTH = { design, chip, pet: petFor(chip), date: new Date() };
  if (roller) roller.setDesign(design, { instant: !chip });
  paintBirth();
}
function birthFromChip(chip) { const r = SE.rollFromChipId(DESIGNS, chip); return r && r.design ? r.design : DESIGNS[0]; }
const burst = $("#burst"), bctx = burst ? burst.getContext("2d") : null;
function confetti(color) {
  if (!bctx || RM) return;
  const dpr = Math.min(2, devicePixelRatio || 1), W = burst.width = burst.clientWidth * dpr, H = burst.height = burst.clientHeight * dpr;
  const parts = Array.from({ length: 46 }, () => { const a = Math.random() * Math.PI * 2, s = (2 + Math.random() * 7) * dpr; return { x: W / 2, y: H / 2, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 2 * dpr, r: (2 + Math.random() * 4) * dpr, c: Math.random() < .55 ? color : pick(["#FFF0C8", "#2440FF", "#FF5A1F"]) }; });
  const t0 = performance.now();
  (function f(t) {
    const k = (t - t0) / 1100; bctx.clearRect(0, 0, W, H); if (k > 1) return;
    parts.forEach(p => { p.x += p.vx; p.y += p.vy; p.vy += .22 * dpr; p.vx *= .985; bctx.globalAlpha = 1 - k; bctx.fillStyle = p.c; bctx.beginPath(); bctx.arc(p.x, p.y, p.r, 0, 6.283); bctx.fill(); });
    requestAnimationFrame(f);
  })(t0);
}
const rollBtn = $("#roll-btn");
function birthAnim(chip, done) {
  const design = birthFromChip(chip);
  const spins = RM ? 0 : 16;
  let i = 0;
  if (rollBtn) rollBtn.disabled = true;
  roller.react("startled");
  (function spin() {
    if (i < spins) {
      const d = DESIGNS[(Math.random() * DESIGNS.length) | 0];
      roller.setDesign(d, { instant: true });
      $("#rc-name").textContent = d.name; $("#rc-num").textContent = `${numOf(d)} / ${COUNT}`;
      sfx.tick(); i++;
      setTimeout(spin, 45 + i * i * 1.6);
      return;
    }
    showBirth(design, chip);
    roller.setExpression("neutral"); roller.react("hello");
    setTimeout(() => { roller.react(["legendary", "mythic", "epic"].includes(design.rarity) ? "excited" : "happy", 2); }, 900);
    confetti(rarColor(design.rarity)); sfx.reveal();
    if (rollBtn) rollBtn.disabled = false;
    try { history.replaceState(null, "", "#born=" + chip.toLowerCase()); } catch (e) {}
    if (done) done();
  })();
}
if (roller) {
  showBirth(byId("original"), null);
  rollBtn.addEventListener("click", () => birthAnim(randChip()));
  const cf = $("#chipform"), ci = $("#chip-in"), help = $("#chip-help");
  cf.addEventListener("submit", e => {
    e.preventDefault();
    const hex = cleanChip(ci.value);
    if (hex.length !== 12) { ci.setAttribute("aria-invalid", "true"); help.textContent = D().chipBad; roller.react("confused", 1.6); return; }
    ci.removeAttribute("aria-invalid"); help.innerHTML = LANG === "ro" ? (RO["born.sample"] || EN["born.sample"]) : EN["born.sample"];
    ci.value = fmtChip(hex);
    birthAnim(hex);
  });
  const share = $("#share-btn");
  share.addEventListener("click", async () => {
    let chip = BIRTH && BIRTH.chip;
    if (!chip) { chip = randChip(); birthAnim(chip); }
    const url = location.href.split("#")[0] + "#born=" + chip.toLowerCase();
    try { await navigator.clipboard.writeText(url); share.firstElementChild.textContent = D().copied; }
    catch (e) { ci.value = url; ci.select(); }
    setTimeout(() => { share.firstElementChild.textContent = D().copy; }, 2200);
  });
  const m = /^#born=([0-9a-f:]{12,17})$/i.exec(location.hash);
  if (m && cleanChip(m[1]).length === 12) {
    const hex = cleanChip(m[1]);
    ci.value = fmtChip(hex);
    showBirth(birthFromChip(hex), hex);
    addEventListener("load", () => setTimeout(() => $("#born").scrollIntoView({ behavior: "auto" }), 60));
  }
}

/* ================================================================== hold the glass (scripted) */
const hand = byRole("hand")[0];
const holdBtn = $("#hold-btn"), term = $("#term"), mic = $("#mic");
let PROV = "claude", holding = false, busy = false, tHold = 0, wordT = null, step = 0, shown = 0, fillRaf = 0;
$$("#prov-seg button").forEach(b => b.addEventListener("click", () => {
  PROV = b.dataset.prov;
  $$("#prov-seg button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  if (hand) hand.inst.react(PROV === "offline" ? "sleepy" : "wink", 1.2);
}));
function micState(on) {
  if (!mic) return;
  mic.classList.toggle("on", on);
  mic.lastElementChild.textContent = on ? D().micOn : D().micOff;
}
langHooks.push(() => micState(holding));
function bubble(cls, text, small) {
  const p = document.createElement("p"); p.className = "bub " + cls; p.textContent = text;
  if (small) { const s = document.createElement("small"); s.textContent = small; p.appendChild(s); }
  term.appendChild(p); return p;
}
function setFill(v) { if (holdBtn) holdBtn.style.setProperty("--h", v.toFixed(3)); }
function holdStart(e) {
  if (holding || busy || !term) return;
  if (e && e.cancelable) e.preventDefault();
  holding = true; tHold = nowS(); shown = 0;
  const sc = D().scripts[step % D().scripts.length], words = sc.you.split(" ");
  term.innerHTML = ""; const you = bubble("you", "…");
  micState(true);
  if (hand) { hand.follow = false; hand.inst.lookAt(0, -.1); hand.inst.setExpression("listening"); hand.cv.classList.add("listening"); }
  sfx.tick();
  wordT = setInterval(() => { if (shown < words.length) { shown++; you.textContent = words.slice(0, shown).join(" "); } }, RM ? 60 : 150);
  const f = () => { if (!holding) return; setFill(clamp((nowS() - tHold) / 1.6, 0, 1)); fillRaf = requestAnimationFrame(f); };
  f();
}
function holdEnd() {
  if (!holding) return;
  holding = false; clearInterval(wordT); cancelAnimationFrame(fillRaf); setFill(0); micState(false);
  if (hand) hand.cv.classList.remove("listening");
  const sc = D().scripts[step % D().scripts.length];
  if (nowS() - tHold < .55) {
    term.innerHTML = ""; bubble("idle", D().short);
    if (hand) { hand.inst.setExpression("neutral"); hand.inst.react("confused", 1.2); hand.follow = true; }
    return;
  }
  busy = true;
  term.lastElementChild.textContent = sc.you;
  const think = bubble("soul", D().thinking);
  if (hand) hand.inst.setExpression(PROV === "offline" ? "sad" : "thinking");
  setTimeout(() => {
    const ans = PROV === "offline" ? D().offline : sc.ai;
    const label = D().via[PROV] + (sc.mem && PROV !== "offline" ? D().mem : "");
    think.textContent = ""; let i = 0;
    const s = document.createElement("small"); s.textContent = label;
    const typer = setInterval(() => {
      i = Math.min(ans.length, i + (RM ? ans.length : 3));
      think.textContent = ans.slice(0, i);
      if (i >= ans.length) {
        clearInterval(typer); think.appendChild(s); busy = false;
        if (hand) { hand.inst.setExpression("neutral"); hand.inst.react(PROV === "offline" ? "shy" : "happy", 1.6); hand.follow = true; }
        sfx.reveal();
        if (PROV !== "offline") step++;
      }
    }, 24);
  }, RM ? 200 : 1000);
}
if (holdBtn && term) {
  holdBtn.addEventListener("pointerdown", e => { holdStart(e); try { holdBtn.setPointerCapture(e.pointerId); } catch (x) {} });
  ["pointerup", "pointercancel", "lostpointercapture"].forEach(ev => holdBtn.addEventListener(ev, holdEnd));
  holdBtn.addEventListener("keydown", e => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); holdStart(); } });
  holdBtn.addEventListener("keyup", e => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); holdEnd(); } });
  holdBtn.addEventListener("click", e => e.preventDefault());
  holdBtn.addEventListener("contextmenu", e => e.preventDefault());
  addEventListener("blur", holdEnd);
}
if (hand) {
  hand.cv.addEventListener("pointerdown", e => { holdStart(e); try { hand.cv.setPointerCapture(e.pointerId); } catch (x) {} });
  ["pointerup", "pointercancel", "lostpointercapture"].forEach(ev => hand.cv.addEventListener(ev, holdEnd));
  hand.cv.addEventListener("contextmenu", e => e.preventDefault());
}

/* ================================================================== SoulOS standby: eyes on pure black */
const sb = $("#standby-cv");
if (sb && SE) {
  const inst = SE.createEyes(sb, byId("original"), { fit: .82, bezel: false, sheen: false, background: "#000", interactive: false, randomMood: true });
  const rec = { inst, cv: sb, role: "standby", follow: true };
  LIVE.push(rec);
  sb.addEventListener("click", () => tapReact(rec));
}

/* ================================================================== night */
const night = byRole("night")[0];
if (night) {
  night.follow = false; night.inst.setExpression("sleepy");
  let to;
  night.cv.addEventListener("click", () => {
    clearTimeout(to); night.inst.setExpression("neutral"); night.inst.react("wake"); night.follow = true; sfx.boop();
    to = setTimeout(() => { night.inst.setExpression("bored"); setTimeout(() => { night.follow = false; night.inst.setExpression("sleepy"); }, 1800); }, 3200);
  });
}

/* ================================================================== waitlist
   Demo mode: validates, stores locally, shows the success state.
   Shopify: set data-native="true" on the form and render it with {% form 'customer' %}; this script then only validates. */
const form = $("#waitlist"), msg = $("#wl-msg"), email = $("#wl-email"), wlLang = $("#wl-lang"), tags = $("#wl-tags");
let langTouched = false;
function syncTags() { if (tags) tags.value = ["waitlist", "colour-" + COLOUR, "lang-" + (wlLang ? wlLang.value : LANG)].join(","); }
if (wlLang) {
  wlLang.addEventListener("change", () => { langTouched = true; syncTags(); });
  langHooks.push(() => { if (!langTouched) wlLang.value = LANG; syncTags(); });
}
if (resRec) { resRec.inst.setExpression("sleepy"); resRec.follow = false; resRec.cv.addEventListener("click", () => tapReact(resRec, "wink")); }
const wakeRes = () => { if (resRec && resRec.inst.expression === "sleepy") { resRec.inst.setExpression("neutral"); resRec.inst.react("wake"); } };
if (email && resRec) {
  email.addEventListener("focus", () => { wakeRes(); resRec.follow = false; resRec.inst.lookAt(.45, .1); });
  email.addEventListener("input", () => { resRec.follow = false; const k = clamp(email.value.length / 26, 0, 1); resRec.inst.lookAt(-.2 + k * .9, .22); });
  email.addEventListener("blur", () => { resRec.follow = true; });
}
if (form) form.addEventListener("submit", async e => {
  const d = D(), em = email.value.trim(), consent = $("#wl-consent").checked;
  msg.textContent = "";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(em)) { e.preventDefault(); msg.textContent = d.email; email.setAttribute("aria-invalid", "true"); email.focus(); if (resRec) resRec.inst.react("confused", 1.6); return; }
  email.removeAttribute("aria-invalid");
  if (!consent) { e.preventDefault(); msg.textContent = d.consent; $("#wl-consent").focus(); if (resRec) resRec.inst.react("suspicious", 1.6); return; }
  syncTags();
  if (form.dataset.native === "true") return;          // Shopify posts the customer form itself
  e.preventDefault();
  if ($("#wl-web").value) { done(); return; }           // honeypot: pretend success
  const data = { email: em, colour: COLOUR, language: wlLang ? wlLang.value : LANG, consent: true, tags: tags ? tags.value : "", ts: new Date().toISOString(), source: "landing-v3" };
  const btn = $("#wl-submit");
  if (CFG.WAITLIST_ENDPOINT) {
    btn.disabled = true; const old = btn.innerHTML; btn.textContent = d.sending;
    try {
      const r = await fetch(CFG.WAITLIST_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(data) });
      if (!r.ok) throw new Error(String(r.status));
    } catch (err) { msg.textContent = d.net; btn.disabled = false; btn.innerHTML = old; if (resRec) resRec.inst.react("sad", 2); return; }
  } else {
    try { const k = "soul-waitlist"; const arr = JSON.parse(store.get(k) || "[]"); arr.push(data); store.set(k, JSON.stringify(arr)); } catch (err) {}
  }
  done();
  function done() {
    form.hidden = true; const th = $("#wl-thanks"); th.hidden = false;
    $("#th-col").textContent = colName(COLOUR); $("#th-lang").textContent = d.langName[wlLang ? wlLang.value : LANG];
    th.focus({ preventScroll: true });
    if (resRec) { resRec.follow = true; resRec.inst.setExpression("neutral"); resRec.inst.react("laugh"); setTimeout(() => resRec.inst.setExpression("love"), 1900); setTimeout(() => resRec.inst.setExpression("happy"), 5200); }
    LIVE.filter(r => r.inst._visible && r !== resRec).forEach(r => r.inst.react("happy", 2));
    sfx.reveal();
  }
});

/* ================================================================== reveals, nav state, dock */
if ("IntersectionObserver" in window) {
  if (!RM) {
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.remove("pre"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px" });
    $$(".rv").forEach(el => { const b = el.getBoundingClientRect(); if (b.top > innerHeight) { el.classList.add("pre"); io.observe(el); } });
    const seen = new WeakSet();
    const io2 = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting || seen.has(e.target)) return; seen.add(e.target);
      const r = LIVE.find(x => x.cv === e.target);
      if (r && ["blink", "follow", "family", "cfg"].includes(r.role)) setTimeout(() => r.inst.react(pick(["hello", "wink", "happy"]), 1.4), 150 + Math.random() * 500);
    }), { threshold: .6 });
    LIVE.forEach(r => io2.observe(r.cv));
  }
  if (sideFig) { const io3 = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { sideFig.classList.add("in"); io3.disconnect(); } }, { threshold: .4 }); io3.observe(sideFig); }
  const links = $$(".nav-links a"), secs = links.map(a => $(a.getAttribute("href"))).filter(Boolean);
  const io4 = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    links.forEach(a => a.setAttribute("aria-current", String(a.getAttribute("href") === "#" + e.target.id)));
  }), { rootMargin: "-45% 0px -50% 0px" });
  secs.forEach(s => io4.observe(s));
  const dock = $("#dock"), res = $("#reserve"), foot = $("#legal");
  if (dock && res) {
    let resIn = false, footIn = false;
    const upd = () => { const on = scrollY > innerHeight * 1.2 && !resIn && !footIn; dock.classList.toggle("on", on); dock.setAttribute("aria-hidden", String(!on)); dock.querySelector("a").tabIndex = on ? 0 : -1; };
    new IntersectionObserver(es => { es.forEach(e => { if (e.target === res) resIn = e.isIntersecting; else footIn = e.isIntersecting; }); upd(); }).observe(res);
    new IntersectionObserver(es => { footIn = es[0].isIntersecting; upd(); }).observe(foot);
    addEventListener("scroll", upd, { passive: true });
  }
}

/* ================================================================== language */
$$(".lang button").forEach(b => b.addEventListener("click", () => applyLang(b.dataset.lang, true)));
const saved = store.get("soul-lang");
applyLang(location.hash === "#ro" ? "ro" : saved === "ro" ? "ro" : "en", false);
requestAnimationFrame(lookLoop);
})();
