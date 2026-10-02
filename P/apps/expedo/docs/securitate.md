# Securitate și protecția datelor — Expedo

Publicat de **ARTEMIS DIGITAL SRL** · contact: office@krea.ro · actualizat: 2 octombrie 2026

Documentul are trei părți: ce date ținem și cum le protejăm (pe scurt), procedura pentru incidente și răspunsurile la chestionarul Shopify „Protected customer data”. Paginile publice care spun același lucru comercianților și clienților: `/confidentialitate` (`/privacy`) și `/termeni` (`/terms`, cu acordul de prelucrare a datelor).

## 1. Ce date ținem și unde

| Unde | Ce conține | Cum e protejat |
|---|---|---|
| `orders.data` | comanda din Shopify: nume, adrese, telefon, e-mail, firmă/CUI, produse, sume, notă, atribute checkout | criptat (AES-256-GCM, `enc1:`) |
| `orders.overrides` | corecturile manuale (adresă, telefon, observații AWB) | criptat |
| `orders.issues`, `orders.last_error` | probleme de validare (pot cita telefonul), erori de la curieri | criptat |
| `orders.phone_hash`, `email_hash`, `search_terms` | coduri pentru căutare și istoricul de refuzuri | HMAC cu cheie, pe magazin; nu se pot inversa fără `APP_SECRET` |
| `orders` (restul coloanelor) | numărul comenzii (#1024), sume, curier, AWB, factură, statusuri, date | în clar — nu sunt date ale clientului |
| `events.message`, `events.data` | istoricul comenzii (mesajele de eroare pot cita adresa) | criptat |
| `cache` | nomenclatoare curieri; la curierul de probă, coletele „create” (cu destinatar) | criptat |
| `stores.access_token`, `integrations.credentials` | token Shopify, parolele curierilor și ale facturării | criptat (existent dinainte) |
| `access_log` | cine a văzut / exportat date: ID utilizator Shopify sau „admin”, acțiune, nr. comandă | fără date ale clienților |
| `jobs` | sarcini în fundal (doar ID-uri) | se șterg după 7 zile |

- Cheia de criptare și cheia pentru coduri sunt derivate din `APP_SECRET` (două chei diferite). `APP_SECRET` stă în variabilele de mediu ale serverului, nu în baza de date.
- Rândurile scrise de versiunile vechi (în clar) se criptează automat la prima pornire a versiunii noi (`encryptPlaintextRows` în `src/db.js`).
- Căutarea: numărul comenzii, AWB-ul și factura se caută ca înainte (parțial). Numele, telefonul și e-mailul se caută doar exact (cuvinte întregi din nume, telefonul în orice format, e-mailul fără diferență de majuscule), prin coduri.
- Transfer: HTTPS spre Shopify, curieri și facturare; HTTPS la găzduire (Render). Serverul: Render, regiunea Frankfurt (`render.yaml`).

**Păstrare (`src/core/privacy.js`):** zilnic, pentru comenzile terminate (livrate, returnate, anulate, expediate în afara Expedo) mai vechi decât setarea magazinului „Păstrează datele clienților” (90 / 180 / 365 / 730 zile, implicit 180, socotite de la livrare / retur / anulare), se șterg: numele, adresele, telefonul, e-mailul, firma, nota, atributele, etichetele, corecturile de adresă, problemele, erorile, codurile de căutare; din istoric se șterg erorile și modificările manuale, iar detaliile celorlalte evenimente. Rămân: numărul comenzii, sumele, produsele, curierul, AWB-ul, factura, statusurile. Comenzile în lucru sau în procesare chiar atunci nu se ating niciodată. Jurnalul de acces se păstrează 365 de zile.

**Webhook-uri GDPR:**
- `customers/data_request` — se notează în jurnalul de acces (actor „shopify”) și în Activitate (avertisment); comerciantul apasă „Descarcă datele clientului” și primește un JSON cu tot ce avem. Comenzile se găsesc după ID-urile trimise de Shopify și după e-mail (nu după telefon: oamenii împart telefoane și n-avem voie să dăm comanda altcuiva).
- `customers/redact` — aceeași căutare; datele clientului se șterg imediat (aceeași funcție ca la păstrare), rămâne doar partea contabilă.
- `shop/redact` — se șterge tot: magazin, comenzi, integrări, evenimente, sarcini, cache, jurnal de acces.

## 2. Procedura pentru incidente de securitate

Un incident = orice acces, pierdere sau modificare neautorizată a datelor (sau suspiciunea serioasă a unuia): server compromis, `APP_SECRET` / parolă de admin / token scurs, bază de date copiată, bug care arată comenzile unui magazin altui magazin.

Responsabil: administratorul ARTEMIS DIGITAL SRL (office@krea.ro). Fiecare pas se notează cu ora, în registrul de incidente (un document intern), chiar dacă incidentul se dovedește minor.

1. **Detectare** (ora 0 = când aflăm)
   - Surse: alerte și jurnale Render, `/healthz`, Activitate → Acces la date (acțiuni neobișnuite, actori necunoscuți), sesizări de la comercianți, Shopify sau curieri, rapoarte de securitate pe office@krea.ro.
   - Deschide intrarea în registru: ce s-a observat, când, de unde.
2. **Izolare** (imediat, în primele ore)
   - Dacă serverul e compromis: suspendă serviciul în Render; păstrează o copie a discului și a jurnalelor pentru analiză (nu le șterge).
   - Schimbă ce s-ar fi putut scurge: `ADMIN_PASSWORD`, `SESSION_SECRET` (deloghează pe toți), `SHOPIFY_API_SECRET` (Partner Dashboard → rotate), parolele contului Render / GitHub / Shopify Partner.
   - Dacă e posibil ca baza de date să fi fost copiată **împreună cu** `APP_SECRET`: datele trebuie tratate ca expuse. Comercianții își schimbă parolele de curier și facturare (sunt în aceeași bază). Atenție: schimbarea `APP_SECRET` face datele existente ilizibile — nu există încă un script de recriptare (vezi „Rămase deschise”).
   - Dacă e un bug în aplicație: oprește funcția afectată sau revino la versiunea anterioară.
3. **Evaluare** (în primele 24–48 de ore)
   - Ce magazine, ce comenzi, ce câmpuri, ce perioadă. Surse: `access_log`, `events`, jurnalele Render, istoricul Git.
   - Erau datele criptate și cheia a rămas sigură? Dacă da, riscul pentru clienți e mic (rămâne obligația de notificare dacă nu putem exclude accesul la cheie).
   - Concluzie scrisă: e o încălcare a securității datelor cu caracter personal? Ce risc are pentru clienți (scăzut / ridicat)?
4. **Notificare** (în cel mult **72 de ore** de la ora 0)
   - **Comercianții afectați** — e-mail la adresa magazinului din Shopify: ce s-a întâmplat, ce date și câte comenzi, ce am făcut, ce trebuie să facă ei (ex. schimbă parolele de curier), un contact. Ei sunt operatorii: ei decid notificarea ANSPDCP și a clienților lor; le dăm toate informațiile necesare.
   - **Shopify** — prin Partner Dashboard (suport) / contactul de securitate și confidențialitate Shopify, cu aceleași informații.
   - **ANSPDCP** (dataprotection.ro) — doar pentru datele la care ARTEMIS DIGITAL SRL e operator (date despre magazine și utilizatori), dacă incidentul are risc pentru ei.
   - Dacă nu avem toate informațiile în 72 de ore, trimitem ce avem și completăm pe parcurs.
5. **Remediere**
   - Repară cauza (cod, configurare, acces), cu test automat care prinde problema pe viitor.
   - Repornește serviciul doar după verificare; urmărește jurnalele câteva zile.
6. **Analiză după incident** (în 2 săptămâni)
   - Ce s-a întâmplat, cronologia, de ce nu am prins mai devreme, ce schimbăm. Se trece în registru și se trimite comercianților afectați un rezumat.
   - Actualizează acest document, paginile publice și răspunsurile de mai jos dacă s-a schimbat ceva.

## 3. Cerințele Shopify „Protected customer data” → implementare

Expedo cere nivelul 2 (nume, adresă, telefon, e-mail). Răspunsurile sunt cele pe care le putem da cinstit azi; „De confirmat” = ține de conturile și organizarea ARTEMIS DIGITAL SRL, nu de cod.

### Nivelul 1

| # | Cerința Shopify | Răspuns | Cum |
|---|---|---|---|
| 1 | Prelucrezi doar datele minime necesare? | **Da** | Scopuri: `read_orders`, `write_orders`, fulfillment orders. Fără `read_customers`. Numele, adresa, telefonul și e-mailul sunt necesare pentru AWB și factură; nota și atributele checkout pentru easybox / CUI. |
| 2 | Spui comercianților ce date prelucrezi și de ce? | **Da** | `/confidentialitate`, `/privacy`; link în aplicație (subsol, Setări → Date clienți). |
| 3 | Folosești datele doar pentru acele scopuri? | **Da** | Doar AWB, factură, expediere, urmărire, ramburs, istoric de refuzuri în același magazin. Fără marketing, vânzare, AI, schimb între magazine. |
| 4 | Respecți deciziile de consimțământ ale clienților? | **Da / nu se aplică** | Nu trimitem marketing și nu folosim datele pentru nimic care cere consimțământ. |
| 5 | Respecți refuzul clienților de a le fi vândute datele? | **Da** | Nu vindem date. |
| 6 | Decizii automate cu efect juridic sau similar? | **Nu luăm astfel de decizii** | Istoricul de refuzuri doar avertizează; o regulă făcută de comerciant poate pune comanda „în așteptare” pentru verificare. Nicio comandă nu e refuzată automat; decide un om. |
| 7 | Ai acorduri de confidențialitate și protecția datelor cu comercianții? | **Da** | Termenii (`/termeni`) includ acordul de prelucrare (art. 28 GDPR), acceptat la instalare. |
| 8 | Aplici perioade de păstrare? | **Da** | Setare per magazin 90/180/365/730 zile (implicit 180), sarcina zilnică `privacy_cleanup`; jurnal de acces 365 zile; `shop/redact` șterge tot. |
| 9 | Criptezi datele la stocare și la transfer? | **Da** | AES-256-GCM pe câmpurile cu date ale clienților (tabelul din secțiunea 1); HTTPS la transfer. În clar rămân doar date fără clienți (nr. comandă, sume, AWB, factură, statusuri). |

### Nivelul 2

| # | Cerința Shopify | Răspuns | Cum |
|---|---|---|---|
| 10 | Criptezi copiile de siguranță? | **Da (la nivel de aplicație)** | Datele clienților sunt criptate înainte să ajungă pe disc, deci orice copie a bazei are doar text criptat; cheia nu e pe disc. Criptarea copiilor de disc ale Render ține de Render. |
| 11 | Ții separat datele de test de cele reale? | **Da** | Magazinul demo are comenzi inventate; testele automate folosesc baze în memorie cu date inventate; testele cap-coadă rulează pe un magazin de dezvoltare cu comenzi de test. Modul de probă rulează pe comenzile reale ale comerciantului, dar nu trimite nimic la curieri / facturare. |
| 12 | Ai o strategie de prevenire a pierderii datelor? | **Parțial** | Criptare, separare pe magazine, păstrare limitată, jurnal de acces, exporturile (CSV ramburs) nu conțin date ale clienților, exportul de date al unui client e notat. Nu avem instrumente DLP dedicate. |
| 13 | Limitezi accesul personalului la date? | **Da** | La server și la baza de date are acces doar administratorul ARTEMIS DIGITAL SRL. În magazin, accesul îl dă comerciantul prin permisiunile Shopify (Expedo nu are roluri proprii: cine deschide aplicația vede comenzile magazinului). |
| 14 | Ceri parole puternice pentru conturile personalului? | **Parțial — de confirmat** | Utilizatorii magazinului intră prin Shopify (regulile Shopify, inclusiv 2FA). Parola de admin pentru panoul separat (`ADMIN_PASSWORD`) nu e verificată de aplicație — folosiți minim 16 caractere aleatorii (aplicația avertizează la pornire dacă e mai scurtă de 12). De confirmat: 2FA pe conturile Render, GitHub și Shopify Partner. |
| 15 | Ții un jurnal al accesului la date? | **Da** | `access_log`: deschidere comandă, factură PDF, etichete, listă de picking, export ramburs, export date client, cereri GDPR; cine (utilizatorul Shopify din sesiune sau „admin”) și când. Vizibil în Activitate → Acces la date (filtre), păstrat 365 de zile. |
| 16 | Ai o procedură pentru incidente de securitate? | **Da** | Secțiunea 2 a acestui document. |

## 4. Rămase deschise

- **Datele firmei** pe paginile publice: CUI-ul și sediul ARTEMIS DIGITAL SRL se pun în variabila `PUBLISHER_DETAILS`.
- **Rotirea `APP_SECRET`**: nu există încă un script care să recripteze datele cu o cheie nouă; până atunci cheia nu se poate schimba fără să pierdem datele criptate.
- **Lista de comenzi** (nume client, oraș) nu se notează în jurnalul de acces; se notează doar deschiderea unei comenzi și exporturile.
- **Render**: de verificat la deploy că serviciul e în regiunea Frankfurt (`region` din `render.yaml` se aplică doar la crearea serviciului) și că acordul de prelucrare Render e acceptat.
- Pe paginile publice, Render e trecut ca furnizor de găzduire; dacă se schimbă găzduirea, se schimbă și acolo (`src/legal.js`), cu anunț la comercianți cu 30 de zile înainte.
