# Riscuri și provocări

<!-- Secțiune obligatorie pe Indiegogo. TRADUCERE pentru citit; se publică varianta în engleză (../04-risks.md). Blocurile f vin din facts.json prin tools/build_copy.py. -->

SOUL e un produs în dezvoltare, făcut de o firmă mică. Să-l susții nu înseamnă să cumperi dintr-un magazin: ne ajuți să construim primul lot, iar unele lucruri pot merge prost. Iată ce știm că poate merge prost și ce facem în privința asta.

**1. Lotul e încă în fața noastră.**
Primul nostru prototip funcțional e mărimea mai mare, M. SOUL pe care îl susții e S (63 × 71 mm, AMOLED rotund de 1,75″).
[[G1: „SoulOS rulează pe placa S reală, cu voce, din <data>.”]]
[[G2: „Un SOUL S din aluminiu a fost asamblat și filmat funcționând dintr-o singură dublă pe <data>.”]]
Între câteva bucăți făcute de mână și un lot de câteva sute mai e muncă: adâncimea finală, bateria finală, testarea fiecărei bucăți. Ce facem: nu am lansat pe randări. Pagina a apărut doar după ce un S real a mers în fața camerei, iar specificațiile spun clar ce e final și ce încă se decide.

**2. Certificarea.**
<!--f:ce_risk-->SOUL a trecut testele radio, EMC, de siguranță electrică și EN 18031 la [[CE: numele laboratorului]]; declarația UE de conformitate e semnată din [[CE: data semnării declarației UE]]. Ce rămâne: fiecare unitate din lot e testată la final (semnal radio, încărcare, ecran) și orice schimbare de componentă se re-evaluează înainte să plece.<!--/f-->

**3. Data de livrare poate aluneca.**
Estimarea noastră pentru lotul 1 e <!--f:delivery-->mai 2028 (UE)<!--/f-->. <!--f:delivery_risk-->CE trebuie să treacă înainte de lansare; dacă întârzie, se mută lansarea, nu data ta de livrare. Ce mai poate muta data: frezarea și anodizarea lotului și coletele din perioada sărbătorilor. Am păstrat cam 10 săptămâni de rezervă.<!--/f--> Cele mai multe campanii hardware livrează cu întârziere; am planificat pentru asta, dar nu o putem exclude.
Ce facem: un update la două săptămâni, săptămânal cât livrăm, și în aceeași săptămână pentru orice întârziere, cu motivul și noua dată. Dacă ratăm luna estimată, poți anula și primești toți banii înapoi (vezi *Rambursări și anulare*). Susținătorii primesc SOUL înaintea oricărei comenzi din magazin.

**4. Culorile sunt greu de potrivit.**
Culorile anodizate variază între loturi, iar cele calde ca Jar cel mai mult. De aceea campania oferă <!--f:colours_n-->trei<!--/f--> culori, nu cinci. Ce facem: o mostră de referință aprobată pentru fiecare culoare, o baie pentru fiecare culoare și verificare sub lumină standard de zi. Mici diferențe între bucăți sunt normale la aluminiul anodizat.

**5. Costurile pot fi mai mari decât credem.**
Până ne trimit furnizorii oferte scrise, orice cost pe bucată e o estimare, iar obiectivul include o marjă de siguranță de 15 % pentru asta.
[[G3: „Ofertele scrise de la <parteneri> sunt la <x> % de modelul nostru.”]]
Dacă costurile cresc, le suportăm noi; nu-ți cerem mai mulți bani pentru recompensă. Transportul e tariful fix pe zonă de pe pagină: dacă firma de curierat cere mai mult, diferența o plătim noi.

**6. Unele piese au un singur furnizor.**
<!--f:supply_risk-->Placa din SOUL S vine de la un singur furnizor (Waveshare ESP32-S3-Touch-AMOLED-1.75). Ce facem: cerem o ofertă scrisă de volum înainte de lansare și cumpărăm toate plăcile pentru lot imediat după prima plată. O placă proprie (cu modul radio pre-certificat) e un proiect pentru un lot următor, nu pentru acesta. [[D8: electronics route not decided yet; this paragraph follows facts.json decisions.D8]]<!--/f-->

**7. Furnizorii de AI își pot schimba regulile.**
SOUL se conectează la propriul tău Claude sau la propria ta cheie API OpenAI; nu include AI. Anthropic și OpenAI își pot schimba oricând API-urile, prețurile sau regulile. Suportul pentru cheia OpenAI e încă în dezvoltare, iar „Sign in with ChatGPT” depinde de aprobarea OpenAI, pe care nu o controlăm, deci nu-l promitem. Le plătești direct ce folosești.
Ce facem: SOUL merge offline, fără niciun AI (ochi, stări, notițe, mementouri, alarme, concentrare) și poate schimba AI-ul fără să piardă SOUL Memory. Dacă dispărem vreodată, publicăm firmware-ul, ca SOUL să nu devină niciodată o cărămidă.

**8. Vocea depinde de un serviciu de vorbire.**
<!--f:voice-->Un detaliu onest: ca să-ți transforme vocea în text, SOUL are nevoie de un serviciu de vorbire. Azi SoulOS îl folosește pe cel de la OpenAI, cu propria ta cheie OpenAI. Vocea pentru cei care folosesc doar Claude e în dezvoltare. Scrisul pe tastatura rotundă merge mereu, cu orice AI și offline.<!--/f-->

**9. Suntem o firmă mică.**
ARTEMIS DIGITAL e o firmă mică din București, iar asta e prima noastră campanie. Ce facem: parteneri specializați pentru frezare, anodizare, asamblare și testare [[G3: îi numim]], o listă limitată de țări de livrare și recompense limitate la cât poate livra lotul 1 (<!--f:batch1-->270<!--/f--> de SOUL). Ce trece de lotul 1 e „Campaign Price · batch 2”, cu luna lui, mai târzie (<!--f:delivery_b2-->august 2028<!--/f-->), afișată pe recompensă înainte să susții: nu mutăm niciodată o susținere făcută pe o dată pe una mai târzie.

**10. Dacă nu putem livra.**
Dacă ceva face livrarea imposibilă, dăm banii înapoi fiecărui susținător și publicăm unde s-au dus banii. Politica completă e la *Rambursări și anulare*.

Nu e o jucărie. SOUL e pentru persoane de <!--f:age-->18<!--/f--> ani și peste. Conține piese mici și o baterie cu litiu.
