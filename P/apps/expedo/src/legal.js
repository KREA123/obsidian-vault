import { config } from './config.js';
import { RETENTION_DAYS } from './core/settings.js';

// Public pages served without login: privacy policy and terms (with the data processing addendum),
// in Romanian and English. Written to match what the code does; when the code changes (new provider,
// new data, other retention), change these pages too. Sections: [heading, ...blocks]; a block is a
// paragraph (string) or a list (array of strings).

const PUBLISHER = 'ARTEMIS DIGITAL SRL';
const EMAIL = 'office@krea.ro';
const UPDATED = { ro: '2 octombrie 2026', en: '2 October 2026' };
const days = RETENTION_DAYS.join(', ');

const T = {
  ro: {
    privacy: {
      title: 'Politica de confidențialitate',
      intro: `Expedo este o aplicație Shopify pentru procesarea comenzilor (AWB, facturi, urmărire colete, ramburs), publicată de ${PUBLISHER}. Aici scrie ce date prelucrează aplicația, de ce, cui le transmite și cât le păstrează.`,
      sections: [
        ['1. Cine răspunde de date',
          'Pentru datele clienților din comenzi, magazinul care folosește Expedo (comerciantul) este operatorul de date, iar ' + PUBLISHER + ' este persoana împuternicită: prelucrăm datele doar ca să facem ce ne cere comerciantul prin aplicație. Detaliile sunt în Acordul de prelucrare a datelor, din Termeni.',
          `Pentru datele despre magazin și despre utilizatorii lui (domeniul magazinului, ID-ul utilizatorului Shopify din jurnalul de acces), ${PUBLISHER} este operator.`,
          `Contact: ${EMAIL}.`],
        ['2. Ce date prelucrăm',
          ['Din comenzile Shopify: numele, adresa de livrare și de facturare, telefonul și e-mailul clientului, firma și CUI-ul (dacă există), produsele, sumele, metoda de plată, nota clientului și câmpurile completate la checkout (de exemplu ID-ul easybox).',
            'Date create de aplicație: AWB-ul, statusul livrării, seria și numărul facturii, ramburs încasat, istoricul comenzii.',
            'Istoricul de refuzuri: câte colete ale aceluiași client (același telefon sau e-mail, în același magazin) au fost refuzate sau livrate. Se calculează doar în magazinul respectiv; nu se compară clienți între magazine.',
            'Despre magazin: domeniul .myshopify.com, numele magazinului, token-ul de acces Shopify și datele de conectare la curieri și la facturare (toate criptate), setările.',
            'Jurnalul de acces: cine (ID-ul utilizatorului Shopify sau „admin”) a deschis o comandă, a descărcat etichete, factura, lista de picking sau exportul de ramburs, și când.'],
          'Nu cerem și nu prelucrăm date sensibile (sănătate, religie etc.). Nu folosim cookie-uri de urmărire sau reclame: doar un cookie de sesiune pentru autentificare și unul temporar la instalare. Interfața încarcă fonturi de la Google Fonts și, în adminul Shopify, scriptul App Bridge de la Shopify; acestea primesc adresa IP a celui care deschide aplicația, nu date ale clienților.'],
        ['3. De ce le prelucrăm',
          ['generarea AWB-ului la curierul ales de comerciant;',
            'emiterea facturii în programul de facturare ales de comerciant;',
            'marcarea comenzii ca expediată în Shopify, cu AWB-ul și link de urmărire;',
            'urmărirea coletelor și evidența rambursului;',
            'avertizarea comerciantului când un client a mai refuzat colete cu ramburs (aplicația doar avertizează sau, dacă comerciantul a făcut o regulă, pune comanda în așteptare pentru verificare; nu refuză nicio comandă singură);',
            'securitate, depanare și asistență.'],
          'Nu vindem date, nu le folosim pentru reclame sau marketing, nu le folosim pentru antrenarea modelelor de inteligență artificială și nu le dăm altor comercianți.'],
        ['4. Temeiul legal',
          'Comerciantul, ca operator, stabilește temeiul. De obicei: executarea contractului cu clientul (livrarea comenzii, art. 6 alin. 1 lit. b GDPR), obligații legale (facturarea, lit. c) și interesul legitim de a evita pierderile la ramburs (istoricul de refuzuri, lit. f). Pentru datele despre magazin, temeiul nostru este contractul cu comerciantul (Termenii).'],
        ['5. Cui transmitem datele',
          ['Shopify — platforma de la care vin comenzile și în care marcăm expedierea.',
            'Curierii pe care comerciantul îi conectează (Cargus, Sameday, FAN Courier, GLS, DPD): numele, adresa, telefonul, e-mailul destinatarului și suma de ramburs, pentru AWB.',
            'Programul de facturare pe care comerciantul îl conectează (SmartBill, FGO, Oblio): datele de facturare și produsele.',
            'Furnizorul de găzduire, Render Services, Inc.: serverul și discul pe care rulează aplicația și baza de date (regiunea Frankfurt, UE).'],
          'Un curier sau un program de facturare primește date doar dacă comerciantul l-a conectat și l-a ales. În modul de probă nu se trimite nimic curierilor sau programelor de facturare.'],
        ['6. Transferuri în afara UE',
          'Baza de date se află pe un server în UE. Render Services, Inc. este o companie din SUA; prelucrarea se face în baza acordului de prelucrare a datelor oferit de Render, care prevede garanții pentru transferuri (clauzele contractuale standard ale Comisiei Europene). Shopify prelucrează datele conform propriei politici.'],
        ['7. Cât timp păstrăm datele',
          [`Datele clienților dintr-o comandă terminată (livrată, returnată, anulată) se șterg automat după un număr de zile ales de comerciant în Setări → Date clienți (${days}; implicit 180). Rămân numărul comenzii, sumele, produsele, AWB-ul, factura și statusurile, necesare pentru contabilitate și verificarea rambursului.`,
            'Comenzile în lucru (neexpediate sau pe drum) nu se șterg până nu se termină.',
            'Jurnalul de acces se păstrează un an.',
            'La cererea unui client, transmisă prin Shopify, datele lui se șterg imediat din toate comenzile.',
            'La dezinstalare, Shopify ne trimite după 48 de ore cererea de ștergere a magazinului; atunci ștergem toate datele magazinului.',
            'Copiile de siguranță ale discului, dacă furnizorul de găzduire le face, conțin datele tot criptate și expiră după ciclul furnizorului.']],
        ['8. Cum protejăm datele',
          ['conexiuni doar prin HTTPS;',
            'datele clienților, token-urile Shopify și parolele curierilor și programelor de facturare sunt criptate în baza de date (AES-256-GCM); cheia stă separat de baza de date, în configurația serverului;',
            'căutarea după telefon, e-mail sau nume se face prin coduri (HMAC cu cheie secretă), nu prin date în clar;',
            'fiecare magazin vede doar comenzile lui; cererile de la Shopify (webhook-uri, sesiuni) sunt verificate cu semnătură;',
            'jurnalul de acces arată cine a văzut sau a exportat date;',
            `doar administratorul ${PUBLISHER} are acces la server.`]],
        ['9. Drepturile clienților',
          'Orice persoană are dreptul de acces, rectificare, ștergere, restricționare, opoziție și portabilitate, precum și dreptul de a se plânge la Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal (www.dataprotection.ro).',
          `Clienții unui magazin se adresează întâi magazinului (operatorul). Cererile făcute prin Shopify ajung automat la noi: o cerere de date apare în Expedo, iar comerciantul descarcă un fișier cu tot ce avem; o cerere de ștergere se execută imediat. Ne poți scrie și direct la ${EMAIL}.`],
        ['10. Incidente de securitate',
          'Dacă aflăm de un incident care afectează datele, anunțăm comercianții afectați fără întârziere și în cel mult 72 de ore, precum și Shopify, cu ce s-a întâmplat, ce date sunt afectate și ce am făcut.'],
        ['11. Modificări',
          'Dacă schimbăm ce date prelucrăm sau cui le transmitem, actualizăm pagina și anunțăm comercianții prin e-mail.'],
      ],
    },
    terms: {
      title: 'Termeni și condiții',
      intro: `Acești termeni se aplică folosirii aplicației Expedo, publicată de ${PUBLISHER} („noi”), de către magazinele Shopify care o instalează („comerciantul”). Prin instalarea aplicației, comerciantul acceptă termenii.`,
      sections: [
        ['1. Serviciul',
          'Expedo preia comenzile din Shopify, verifică adresele, generează AWB-uri la curierii conectați de comerciant, emite facturi în programul de facturare conectat de comerciant, marchează comenzile ca expediate în Shopify, urmărește coletele și ține evidența rambursului.'],
        ['2. Contractele cu curierii și facturarea',
          'Comerciantul are propriile contracte cu curierii și cu programul de facturare; noi nu suntem parte în ele. AWB-urile și facturile se fac în conturile comerciantului, cu datele de conectare pe care le introduce el. Costurile de transport și de facturare sunt între comerciant și acești furnizori.'],
        ['3. Ce face comerciantul',
          ['introduce date de conectare corecte și verifică primele AWB-uri și facturi (recomandăm câteva zile în modul de probă);',
            'verifică AWB-urile și facturile înainte de a le folosi; aplicația semnalează problemele, dar comerciantul decide;',
            'își informează clienții, în propria politică de confidențialitate, că datele lor merg la curieri și la programul de facturare și, dacă folosește istoricul de refuzuri, despre acesta;',
            'folosește aplicația conform legii și termenilor Shopify.']],
        ['4. Preț',
          'Dacă aplicația are un plan plătit, prețul este cel afișat în Shopify App Store la instalare și se plătește prin facturarea Shopify.'],
        ['5. Disponibilitate și răspundere',
          'Facem tot ce putem ca aplicația să funcționeze continuu, dar nu garantăm că va fi mereu disponibilă sau fără erori. Integrările sunt scrise după documentația oficială a fiecărui furnizor; dacă un furnizor își schimbă sistemul sau nu funcționează, AWB-urile sau facturile se pot întârzia.',
          'În limita permisă de lege, nu răspundem pentru pierderi indirecte (profit nerealizat, comenzi pierdute) și răspunderea noastră totală este limitată la sumele plătite de comerciant pentru aplicație în ultimele 12 luni.'],
        ['6. Încetare',
          'Comerciantul poate dezinstala aplicația oricând. Datele magazinului se șterg când Shopify ne trimite cererea de ștergere (la 48 de ore după dezinstalare). Putem suspenda accesul la aplicație în caz de folosire abuzivă sau ilegală.'],
        ['7. Legea aplicabilă',
          'Se aplică legea română. Litigiile se rezolvă amiabil, iar dacă nu se poate, de instanțele competente de la sediul ' + PUBLISHER + '.'],
        ['8. Contact', `${EMAIL}`],
      ],
      dpa: {
        title: 'Anexă — Acord de prelucrare a datelor (art. 28 GDPR)',
        sections: [
          ['A1. Părți și roluri',
            `Comerciantul este operatorul datelor clienților săi. ${PUBLISHER} este persoana împuternicită și prelucrează datele doar pe baza instrucțiunilor comerciantului. Setările și acțiunile comerciantului în aplicație (curier ales, facturare, reguli, zile de păstrare, butoanele din comenzi) sunt instrucțiunile lui documentate.`],
          ['A2. Obiect, durată, natură și scop',
            'Prelucrarea are loc cât timp aplicația este instalată și până la ștergerea datelor (vezi A8). Natura: preluare din Shopify, stocare criptată, transmitere către curieri, programul de facturare și Shopify, afișare către comerciant. Scopurile: cele din Politica de confidențialitate, secțiunea 3.'],
          ['A3. Persoane vizate și categorii de date',
            ['Persoane vizate: clienții comerciantului (cumpărători, destinatari) și utilizatorii comerciantului care folosesc aplicația.',
              'Date: nume, adresă de livrare și de facturare, telefon, e-mail, firmă și CUI, produse comandate, sume, metoda de plată, nota și câmpurile de la checkout, AWB, status livrare, factură, istoricul de refuzuri; pentru utilizatori, ID-ul Shopify din jurnalul de acces.',
              'Nu sunt prelucrate categorii speciale de date.']],
          ['A4. Confidențialitate',
            'Persoanele autorizate să prelucreze datele s-au angajat să păstreze confidențialitatea. În prezent, acces la server are doar administratorul ' + PUBLISHER + '.'],
          ['A5. Măsuri de securitate (art. 32 GDPR)',
            ['HTTPS pentru toate conexiunile;',
              'criptare AES-256-GCM în baza de date pentru datele clienților, token-urile Shopify și datele de conectare la furnizori; cheia este separată de baza de date;',
              'căutare prin coduri HMAC cu cheie, fără date în clar;',
              'separare strictă între magazine; verificarea semnăturii la webhook-urile și sesiunile Shopify; protecție CSRF;',
              'jurnal de acces la datele clienților, păstrat un an;',
              'ștergere automată după perioada de păstrare aleasă de comerciant;',
              'mod de probă, în care nu se trimit date la curieri și la facturare.']],
          ['A6. Sub-împuterniciți',
            ['Render Services, Inc. — găzduire (server și disc, regiunea Frankfurt, UE);',
              'Shopify — platforma de la care vin comenzile și în care se marchează expedierea;',
              'curierii aleși de comerciant (Cargus, Sameday, FAN Courier, GLS, DPD) — doar cei conectați de el, pentru AWB;',
              'programul de facturare ales de comerciant (SmartBill, FGO, Oblio) — doar cel conectat de el, pentru factură.'],
            'Comerciantul autorizează acești sub-împuterniciți. Anunțăm prin e-mail, cu cel puțin 30 de zile înainte, orice furnizor nou de găzduire sau alt sub-împuternicit pe care îl alegem noi; comerciantul se poate opune dezinstalând aplicația. Curierii și programele de facturare sunt alese și contractate de comerciant.'],
          ['A7. Asistență',
            'Ajutăm comerciantul să răspundă cererilor clienților: cererile de date primite prin Shopify apar în Activitate, cu un fișier de descărcat; cererile de ștergere se execută automat. La cerere, oferim informațiile necesare pentru o evaluare de impact.'],
          ['A8. Ștergerea datelor',
            `La dezinstalare, ștergem toate datele magazinului când Shopify trimite cererea de ștergere (după 48 de ore). Comerciantul poate cere ștergerea mai devreme la ${EMAIL}. Datele clienților din comenzile terminate se șterg oricum după zilele de păstrare alese.`],
          ['A9. Audit',
            'La cererea comerciantului, oferim informațiile necesare pentru a arăta că respectăm acest acord. Un audit se face cu notificare rezonabilă, cel mult o dată pe an, pe costul comerciantului.'],
          ['A10. Încălcarea securității datelor',
            'Anunțăm comerciantul afectat fără întârziere nejustificată și în cel mult 72 de ore de la aflare, cu: ce s-a întâmplat, categoriile și numărul aproximativ de persoane și înregistrări afectate, consecințele probabile și măsurile luate. Anunțăm și Shopify. Comerciantul decide notificarea autorității și a clienților; îl ajutăm cu informațiile necesare.'],
          ['A11. Transferuri',
            'Datele sunt stocate în UE. Pentru accesul furnizorului de găzduire din SUA se aplică garanțiile din acordul său de prelucrare a datelor (clauzele contractuale standard).'],
        ],
      },
    },
  },
  en: {
    privacy: {
      title: 'Privacy policy',
      intro: `Expedo is a Shopify app for processing orders (shipping labels, invoices, parcel tracking, cash on delivery), published by ${PUBLISHER}. This page explains what data the app processes, why, who receives it and how long it is kept.`,
      sections: [
        ['1. Who is responsible',
          `For customer data in orders, the store using Expedo (the merchant) is the controller and ${PUBLISHER} is the processor: we process the data only to do what the merchant asks through the app. See the Data Processing Addendum in the Terms.`,
          `For data about the store and its users (store domain, the Shopify user ID in the access log), ${PUBLISHER} is the controller.`,
          `Contact: ${EMAIL}.`],
        ['2. What data we process',
          ['From Shopify orders: the customer\'s name, shipping and billing address, phone and e-mail, company and tax ID (if any), products, amounts, payment method, customer note and checkout fields (e.g. a parcel locker ID).',
            'Data created by the app: shipping label number (AWB), delivery status, invoice series and number, cash on delivery collected, order history.',
            'Refusal history: how many parcels of the same customer (same phone or e-mail, in the same store) were refused or delivered. Computed within that store only; customers are never compared across stores.',
            'About the store: .myshopify.com domain, store name, Shopify access token and courier / invoicing credentials (all encrypted), settings.',
            'Access log: who (Shopify user ID or "admin") opened an order or downloaded labels, an invoice, a picking list or the cash-on-delivery export, and when.'],
          'We do not ask for or process sensitive data (health, religion etc.). We use no tracking or advertising cookies: only a session cookie for login and a temporary one during install. The interface loads fonts from Google Fonts and, inside the Shopify admin, Shopify\'s App Bridge script; these receive the IP address of whoever opens the app, not customer data.'],
        ['3. Why we process it',
          ['creating the shipping label with the courier chosen by the merchant;',
            'issuing the invoice in the invoicing service chosen by the merchant;',
            'marking the order as fulfilled in Shopify, with tracking number and link;',
            'tracking parcels and cash on delivery;',
            'warning the merchant when a customer refused cash-on-delivery parcels before (the app only warns or, if the merchant created a rule, puts the order on hold for review; it never rejects an order by itself);',
            'security, troubleshooting and support.'],
          'We do not sell data, use it for advertising or marketing, use it to train artificial intelligence models, or share it with other merchants.'],
        ['4. Legal basis',
          'The merchant, as controller, determines the legal basis. Usually: performance of the contract with the customer (delivering the order, GDPR art. 6(1)(b)), legal obligations (invoicing, (c)) and the legitimate interest in avoiding cash-on-delivery losses (refusal history, (f)). For store data, our basis is the contract with the merchant (the Terms).'],
        ['5. Who receives the data',
          ['Shopify — the platform the orders come from and where we mark them fulfilled.',
            'The couriers the merchant connects (Cargus, Sameday, FAN Courier, GLS, DPD): recipient name, address, phone, e-mail and cash-on-delivery amount, for the shipping label.',
            'The invoicing service the merchant connects (SmartBill, FGO, Oblio): billing details and products.',
            'The hosting provider, Render Services, Inc.: the server and disk running the app and its database (Frankfurt region, EU).'],
          'A courier or invoicing service receives data only if the merchant connected and chose it. In test mode nothing is sent to couriers or invoicing services.'],
        ['6. Transfers outside the EU',
          'The database is on a server in the EU. Render Services, Inc. is a US company; processing is covered by Render\'s data processing agreement, which provides safeguards for transfers (the European Commission\'s standard contractual clauses). Shopify processes data under its own policy.'],
        ['7. How long we keep data',
          [`Customer data of a finished order (delivered, returned, cancelled) is deleted automatically after a number of days the merchant chooses in Settings (${days}; default 180). The order number, amounts, products, shipping label number, invoice and statuses remain, as needed for accounting and cash-on-delivery reconciliation.`,
            'Orders still in progress (not shipped or on the way) are not deleted until they finish.',
            'The access log is kept for one year.',
            'When a customer asks through Shopify, their data is deleted from all their orders immediately.',
            'After uninstall, Shopify sends the store deletion request 48 hours later; we then delete all of the store\'s data.',
            'Disk backups, if the hosting provider makes them, contain the data still encrypted and expire on the provider\'s cycle.']],
        ['8. How we protect data',
          ['HTTPS-only connections;',
            'customer data, Shopify tokens and courier / invoicing credentials are encrypted in the database (AES-256-GCM); the key is kept apart from the database, in the server configuration;',
            'search by phone, e-mail or name uses keyed codes (HMAC), not plaintext;',
            'each store only sees its own orders; requests from Shopify (webhooks, sessions) are signature-checked;',
            'the access log shows who viewed or exported data;',
            `only the ${PUBLISHER} administrator has access to the server.`]],
        ['9. Customers\' rights',
          'Everyone has the right of access, rectification, erasure, restriction, objection and portability, and the right to complain to a data protection authority (in Romania: ANSPDCP, www.dataprotection.ro).',
          `A store\'s customers should first contact the store (the controller). Requests made through Shopify reach us automatically: a data request shows up in Expedo and the merchant downloads a file with everything we hold; an erasure request is carried out immediately. You can also write to us at ${EMAIL}.`],
        ['10. Security incidents',
          'If we learn of an incident affecting the data, we notify the affected merchants without undue delay and within 72 hours at most, as well as Shopify, with what happened, which data is affected and what we did.'],
        ['11. Changes',
          'If we change what data we process or who receives it, we update this page and notify merchants by e-mail.'],
      ],
    },
    terms: {
      title: 'Terms of service',
      intro: `These terms apply to the use of the Expedo app, published by ${PUBLISHER} ("we"), by the Shopify stores that install it ("the merchant"). By installing the app, the merchant accepts these terms.`,
      sections: [
        ['1. The service',
          'Expedo imports orders from Shopify, checks addresses, creates shipping labels with the couriers the merchant connects, issues invoices in the invoicing service the merchant connects, marks orders as fulfilled in Shopify, tracks parcels and keeps track of cash on delivery.'],
        ['2. Courier and invoicing contracts',
          'The merchant has its own contracts with couriers and the invoicing service; we are not a party to them. Labels and invoices are created in the merchant\'s accounts, with the credentials the merchant enters. Shipping and invoicing costs are between the merchant and those providers.'],
        ['3. The merchant\'s part',
          ['enters correct credentials and checks the first labels and invoices (we recommend a few days in test mode);',
            'checks labels and invoices before relying on them; the app flags problems, but the merchant decides;',
            'informs its customers, in its own privacy policy, that their data goes to couriers and the invoicing service and, if it uses the refusal history, about that;',
            'uses the app lawfully and in line with Shopify\'s terms.']],
        ['4. Price',
          'If the app has a paid plan, the price is the one shown in the Shopify App Store at install and is paid through Shopify billing.'],
        ['5. Availability and liability',
          'We do our best to keep the app running, but do not guarantee it will always be available or error-free. Integrations follow each provider\'s official documentation; if a provider changes or fails, labels or invoices may be delayed.',
          'To the extent permitted by law, we are not liable for indirect losses (lost profit, lost orders), and our total liability is limited to the amounts the merchant paid for the app in the last 12 months.'],
        ['6. Termination',
          'The merchant can uninstall the app at any time. Store data is deleted when Shopify sends the deletion request (48 hours after uninstall). We may suspend access in case of abusive or unlawful use.'],
        ['7. Governing law',
          `Romanian law applies. Disputes are settled amicably or, failing that, by the competent courts at the registered office of ${PUBLISHER}.`],
        ['8. Contact', `${EMAIL}`],
      ],
      dpa: {
        title: 'Addendum — Data Processing Agreement (GDPR art. 28)',
        sections: [
          ['A1. Parties and roles',
            `The merchant is the controller of its customers' data. ${PUBLISHER} is the processor and processes the data only on the merchant's instructions. The merchant's settings and actions in the app (chosen courier, invoicing, rules, retention days, order buttons) are its documented instructions.`],
          ['A2. Subject, duration, nature and purpose',
            'Processing lasts while the app is installed and until the data is deleted (see A8). Nature: import from Shopify, encrypted storage, transmission to couriers, the invoicing service and Shopify, display to the merchant. Purposes: those in the Privacy policy, section 3.'],
          ['A3. Data subjects and categories of data',
            ['Data subjects: the merchant\'s customers (buyers, recipients) and the merchant\'s users of the app.',
              'Data: name, shipping and billing address, phone, e-mail, company and tax ID, ordered products, amounts, payment method, note and checkout fields, shipping label number, delivery status, invoice, refusal history; for users, the Shopify user ID in the access log.',
              'No special categories of data are processed.']],
          ['A4. Confidentiality',
            `People authorised to process the data are bound by confidentiality. Currently only the ${PUBLISHER} administrator has access to the server.`],
          ['A5. Security measures (GDPR art. 32)',
            ['HTTPS for all connections;',
              'AES-256-GCM encryption in the database for customer data, Shopify tokens and provider credentials; the key is kept apart from the database;',
              'search through keyed HMAC codes, without plaintext;',
              'strict separation between stores; signature checks on Shopify webhooks and sessions; CSRF protection;',
              'access log for customer data, kept for one year;',
              'automatic deletion after the retention period chosen by the merchant;',
              'test mode, in which no data is sent to couriers or invoicing.']],
          ['A6. Sub-processors',
            ['Render Services, Inc. — hosting (server and disk, Frankfurt region, EU);',
              'Shopify — the platform the orders come from and where fulfillment is recorded;',
              'the couriers chosen by the merchant (Cargus, Sameday, FAN Courier, GLS, DPD) — only those it connects, for shipping labels;',
              'the invoicing service chosen by the merchant (SmartBill, FGO, Oblio) — only the one it connects, for invoices.'],
            'The merchant authorises these sub-processors. We give at least 30 days\' notice by e-mail of any new hosting provider or other sub-processor we choose; the merchant may object by uninstalling the app. Couriers and invoicing services are chosen and contracted by the merchant.'],
          ['A7. Assistance',
            'We help the merchant answer customer requests: data requests received through Shopify show up in Activity with a file to download; erasure requests are carried out automatically. On request, we provide the information needed for a data protection impact assessment.'],
          ['A8. Deletion',
            `On uninstall, we delete all of the store's data when Shopify sends the deletion request (after 48 hours). The merchant can ask for earlier deletion at ${EMAIL}. Customer data of finished orders is deleted anyway after the chosen retention days.`],
          ['A9. Audit',
            'On the merchant\'s request, we provide the information needed to show compliance with this agreement. An audit takes place with reasonable notice, at most once a year, at the merchant\'s cost.'],
          ['A10. Personal data breach',
            'We notify the affected merchant without undue delay and within 72 hours of becoming aware, with: what happened, the categories and approximate number of people and records affected, the likely consequences and the measures taken. We also notify Shopify. The merchant decides on notifying the authority and its customers; we help with the information needed.'],
          ['A11. Transfers',
            'Data is stored in the EU. Access by the US hosting provider is covered by the safeguards in its data processing agreement (standard contractual clauses).'],
        ],
      },
    },
  },
};

const PATHS = { privacy: { ro: '/confidentialitate', en: '/privacy' }, terms: { ro: '/termeni', en: '/terms' } };
const UI = {
  ro: { other: 'English', updated: 'Ultima actualizare', publisher: 'Publicat de', links: [['privacy', 'Confidențialitate'], ['terms', 'Termeni']] },
  en: { other: 'Română', updated: 'Last updated', publisher: 'Published by', links: [['privacy', 'Privacy'], ['terms', 'Terms']] },
};

const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const block = (b) => (Array.isArray(b) ? `<ul>${b.map((li) => `<li>${esc(li)}</li>`).join('')}</ul>` : `<p>${esc(b)}</p>`);
const section = ([h, ...blocks]) => `<section><h2>${esc(h)}</h2>${blocks.map(block).join('')}</section>`;

export function legalPage(page, lang) {
  const c = T[lang][page];
  const ui = UI[lang];
  const other = lang === 'ro' ? 'en' : 'ro';
  const details = config.publisherDetails ? ` (${esc(config.publisherDetails)})` : '';
  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(c.title)} — Expedo</title>
<link rel="alternate" hreflang="${other}" href="${PATHS[page][other]}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%231f4bd8'/><path d='M8 11l8-4 8 4v10l-8 4-8-4z' fill='none' stroke='white' stroke-width='2.2' stroke-linejoin='round'/><path d='M8 11l8 4 8-4M16 15v10' fill='none' stroke='white' stroke-width='2.2'/></svg>">
<style>
  :root { --bg: #f6f7f9; --card: #fff; --text: #1a1d23; --muted: #5d6573; --line: #e3e6eb; --accent: #1f4bd8; }
  @media (prefers-color-scheme: dark) { :root { --bg: #111317; --card: #1a1d23; --text: #e8eaee; --muted: #9aa3b2; --line: #2b2f37; --accent: #7d9bff; } }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.6 Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width: 760px; margin: 0 auto; padding: 32px 16px 64px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 28px clamp(16px, 4vw, 36px); }
  header { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
  header .brand { font-weight: 700; font-size: 17px; color: var(--text); text-decoration: none; display: flex; align-items: center; gap: 8px; }
  header nav { margin-left: auto; display: flex; gap: 14px; font-size: 14px; }
  a { color: var(--accent); }
  h1 { font-size: 26px; line-height: 1.25; margin: 0 0 6px; }
  h2 { font-size: 17px; margin: 28px 0 6px; }
  .dpa { margin-top: 36px; padding-top: 8px; border-top: 2px solid var(--line); }
  .dpa > h2:first-child { font-size: 20px; }
  .muted { color: var(--muted); font-size: 13px; }
  ul { padding-left: 20px; margin: 6px 0; } li { margin: 4px 0; } p { margin: 6px 0; }
  footer { margin-top: 18px; text-align: center; }
</style>
</head>
<body>
<main>
  <header>
    <a class="brand" href="${PATHS[page][lang]}"><svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#1f4bd8"/><path d="M8 11l8-4 8 4v10l-8 4-8-4z" fill="none" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/><path d="M8 11l8 4 8-4M16 15v10" fill="none" stroke="#fff" stroke-width="2.2"/></svg>Expedo</a>
    <nav>${ui.links.map(([p, l]) => `<a href="${PATHS[p][lang]}">${esc(l)}</a>`).join('')}<a href="${PATHS[page][other]}" hreflang="${other}">${ui.other}</a></nav>
  </header>
  <article class="card">
    <h1>${esc(c.title)}</h1>
    <p class="muted">${ui.updated}: ${UPDATED[lang]} · ${ui.publisher} ${PUBLISHER}${details} · <a href="mailto:${EMAIL}">${EMAIL}</a></p>
    <p>${esc(c.intro)}</p>
    ${c.sections.map(section).join('')}
    ${c.dpa ? `<div class="dpa" id="dpa"><h2>${esc(c.dpa.title)}</h2>${c.dpa.sections.map(section).join('')}</div>` : ''}
  </article>
  <footer class="muted">© ${PUBLISHER}</footer>
</main>
</body>
</html>`;
}
