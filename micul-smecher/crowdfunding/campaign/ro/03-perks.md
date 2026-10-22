# Recompense (Indiegogo „Products → Rewards / Add-ons”) · traducere

Scara activă vine din `facts.json → campaign.ladder` și `pricing.ladders` (decizia D3). Varianta pentru formularul Indiegogo, coloană cu coloană, e `../perks.csv` (generat de `tools/build_copy.py`). Nu edita blocurile f de mână.

## Cum le introduci

- **Câmpul de preț:** prețul din campanie merge în **Regular price**, iar **Discount price** rămâne gol. Prețul planificat după campanie nu apare niciodată ca preț vechi tăiat, ca insignă „−x %” sau „economisești €x”: SOUL nu s-a vândut niciodată la prețul ăla, deci ar fi un preț de referință pe care nu-l putem susține (regulile UE de afișare a prețurilor, Directiva Omnibus). Prețul planificat se spune în cuvinte în descriere și nicăieri altundeva.
- **Cotele de TVA: le pui pe toate pe 0 %, în orice caz.** Indiegogo tratează prețurile ca **nete** și completează singur cotele de TVA din UE (HC/478, HC/597). Dacă rămân, susținătorii plătesc TVA peste prețul afișat. ARTEMIS nu e plătitoare de TVA azi, deci nu are voie să încaseze TVA deloc; dacă se înregistrează (D2), TVA-ul e inclus în preț și îl plătim prin OSS. Oricum ar fi, susținătorul plătește exact prețul afișat. Verifici în **Tester mode**: totalul de la plată trebuie să fie exact prețul recompensei (plus transportul în Pledge Manager), fără rând de taxe.
- **Culoarea** e o **opțiune** pe produsul SOUL (HC/526), <!--f:colours_n-->trei<!--/f--> valori (<!--f:colours-->Argint, Grafit și Jar<!--/f-->), fără diferență de preț, fără limită pe culoare la lansare.
- **Ochii** nu sunt niciodată opțiune, recompensă, extra sau stretch goal.
- **Loturi (D12).** Lotul 1 are <!--f:batch1-->270<!--/f--> de SOUL, lotul pentru care e făcut calendarul de livrare. First Light, Campaign Price și Two Souls au limite care **umplu exact lotul 1**. „Campaign Price · batch 2” are același preț și o lună de livrare mai târzie, ca nimeni să nu fie mutat de pe o dată pe alta.
- **Livrarea estimată:** o lună pe recompensă: <!--f:delivery_field-->mai 2028 (EU: May 2028 (estimate)); Campaign Price · batch 2: august 2028 (Batch 2, EU: August 2028 (estimate))<!--/f-->.
- **Disponibilitate pe țări** (HC/528): doar RO, DE, AT, FR, BE, NL, IT, ES, PL, SE pe recompensele cu dispozitiv (UK: decizia D13; SUA/Canada: D14). Soul Supporter: oriunde.
- **Pin:** First Light cât ține, apoi Two Souls. Un singur pin odată.
- **Stretch Pay:** oprit în campanie. **Stable Pledge:** îl pornești la G3 doar dacă ai ofertele de curierat și depozit în scris (e ireversibil, HC/471).
- Ultimul rând din descrierea fiecărei recompense cu dispozitiv e „Render (CGI), not a photo.”, pentru că imaginea e o randare.

## Recompensele

<!--f:rewards_md-->
### Soul Supporter · €10
Fără dispozitiv, doar din suflet. Numele tău în registrul de nașteri SOUL (opțional), pachetul digital de wallpapere cu ochi și fiecare update.
- **Fără limită** · **Livrare:** digital, în prima lună după campanie; registrul se publică atunci când pleacă primii SOUL

### First Light · €249 · 150 bucăți · 1 de susținător · lotul 1
Primii 150 SOUL, la cel mai mic preț din campanie, fiecare cu **numărul lui First Light (001–150) gravat cu laserul pe picior**. Un SOUL S (63 × 71 mm, AMOLED rotund de 1,75″) în culoarea aleasă (Argint, Grafit și Jar), născut cu ochii aleși de el, și OU, oul lui de încărcare.
Merge cu propriul Claude sau cu propria cheie API OpenAI (în dezvoltare), ori offline. SOUL nu include AI. A trecut testele radio, EMC, de siguranță și EN 18031 la [[CE: numele laboratorului]]; declarația UE de conformitate e semnată ([[CE: data semnării declarației UE]]). Prețul planificat după campanie: €299. Prețul e final (nu se adaugă TVA).
*Render (CGI), nu fotografie.*
- **Conține:** 1 × SOUL S (opțiune de culoare), 1 × OU, cablu USB-C, ghid · **Livrare estimată:** mai 2028 (UE)

### Campaign Price · €269 · 100 bucăți · lotul 1
Un SOUL S în culoarea aleasă, cu ochii aleși de el, și OU. Restul textului ca la First Light, fără gravură.
- **Conține:** 1 × SOUL S, 1 × OU, cablu USB-C, ghid · **Livrare estimată:** mai 2028 (UE)

### Two Souls · €498 (€249 bucata) · 10 seturi · lotul 1
Doi SOUL S la prețul First Light pe bucată, oricare două culori, fiecare cu OU-ul lui. Unul pentru tine, unul pentru cineva drag. Fiecare se naște cu ochii lui, deci rareori se potrivesc.
- **Conține:** 2 × SOUL S, 2 × OU, 2 × cablu USB-C, ghid · un singur colet · **Livrare estimată:** mai 2028 (UE)

### Campaign Price · lotul 2 · €269 · fără limită
Același SOUL S și OU, din lotul 2, pentru cine vine după ce lotul 1 s-a terminat. **Livrare estimată: august 2028.**
- **Conține:** 1 × SOUL S, 1 × OU, cablu USB-C, ghid · **Livrare estimată:** august 2028

### Extra: încă un ou OU · €35
Al doilea ou de încărcare, pentru birou sau noptieră. Vine în același colet cu SOUL, fără transport în plus.

### Late Pledge (după campanie) · €299
După campanie: Late Pledge la €299, din 30 noiembrie 2027, livrat cu lotul 2 (estimat august 2028).
<!--/f-->

## Transportul (toate recompensele cu dispozitiv)

Pe colet, **fix** și afișat înainte să susțină cineva; se plătește după campanie, în Pledge Manager. Tarifele acoperă deja comisioanele Indiegogo pe transport.

<!--f:shipping_table-->
| Zona | Țări | Pe colet (fix) |
|---|---|---|
| RO | România | €6 |
| UE 1 | Germania, Austria, Polonia, Olanda, Belgia | €12 |
| UE 2 | Franța, Italia, Spania, Suedia | €15 |
| Încă un SOUL în același colet | – | +€4 |
<!--/f-->

<!--f:shipping_note-->Transportul se plătește după campanie, în Pledge Manager, la tarifele fixe de mai sus. Tarifele sunt fixe: dacă firma de curierat cere mai mult, diferența o plătim noi.<!--/f-->

Nu sunt în campania asta: Marea Britanie, SUA, Canada, Elveția, Norvegia, Australia și restul lumii. Au nevoie întâi de certificări, înregistrări sau de reguli de TVA proprii; le deschidem în Late Pledge doar când sunt gata.

SOUL conține o baterie cu litiu, deci pleacă pe drum sau prin curier ca „baterie cu litiu în echipament” (UN3481), cu bateria puțin încărcată. Îl încarci în OU când ajunge.

## De ce scara asta (intern, nu se publică)

- Un preț de lansare limitat, un preț de campanie, apoi un Late Pledge clar mai sus: trepte puține și largi, nu trei recompense la €10–20 una de alta ca în prima variantă.
- **First Light** înseamnă mai mult decât €20: are numărul First Light (001–150) gravat cu laserul pe picior. Marcajul laser e deja în costul pe bucată, deci nu costă în plus [estimare]. Nu e o raritate și nu schimbă nimic altceva.
- **Two Souls** costă prețul First Light pe bucată (€249), ca recompensa-cadou să atragă; contribuția e aceeași ca la First Light. Limitat la 10 seturi în lotul 1.
- **Prețul pe bucată nu scade**: contribuția la First Light e mică (vezi ultimul rând). Prețul se justifică prin obiectul din aluminiu frezat: filmări macro ale finisajului sablat sunt pe lista de cadre G2.
- Raritatea nu intră niciodată în preț.
- <!--f:internal_contrib-->Contribution per device after unit cost at the goal batch (270 units, €136 each) [estimate, tools/goal_model.py]: First Light €49 · Campaign Price €64 · Two Souls €49 per device · Late Pledge €87.<!--/f-->
