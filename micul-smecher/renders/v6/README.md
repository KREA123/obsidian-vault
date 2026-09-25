# SOUL v6: aluminiu (randări / concept CGI)

**Toate imaginile și clipul din acest folder sunt randări / concept (CGI).** Nu sunt fotografii ale unui produs real. Oriunde le folosești, etichetează-le „randare / concept (CGI)".

Designul ales este **HOPA**, numit acum simplu **SOUL**. v6 păstrează silueta și proporțiile HOPA și schimbă două lucruri:
1. **CMF.** Corpul nu mai e din sticlă sau plastic perlat. E din **aluminiu anodizat, sablat fin cu microbile**.
2. **Baza** (decizia lead-ului din 25.09): **fără balans**. SOUL e un dispozitiv AI pe care îl atingi, îl ții în mână și pe care tastezi, iar un corp care se leagănă sub deget deranjează. Acum stă ferm pe un **picior plat**.

## Fișiere
| Fișier | Ce arată |
|---|---|
| `soul_v6_hero.png` (1600×1200) | Argint natural, 3/4 din stânga; OU (neschimbat) difuz în fundal |
| `soul_v6_family.png` (2000×1125) | Cele 5 culori anodizate: Grafit · Jar · Argint · Albastru noapte · Șampanie |
| `soul_v6_side.png` | Din partea difuzorului (+x): fanta laser pe cusătură, teșitura la sticlă, pana 27 → 15 mm, piciorul retras |
| `soul_v6_back.png` | Spatele: o cupolă curată din aluminiu sablat, fără text sau șuruburi |
| `soul_v6_bottom.png` | Dedesubt: placa din polimer (fereastra de antenă), piciorul oval 30×14, cele 5 contacte aurii, 2 × Torx T5, marcajul laser |
| `soul_v6_ou_night.png` | Noaptea, în capsula OU, cu ochi chihlimbar; lumina vine doar din OU |
| `soul_v6_hand.png` | În palmă, pentru scară |
| `soul_v6_macro.png` | Prim-plan: granulația sablării și teșitura prelucrată CNC, care întâlnește sticla neagră |
| `soul_v6_alive.mp4` + `.gif` (720×720, 5 s) | SOUL stă nemișcat; doar ochii clipesc și privesc stânga și dreapta (buclă) |

Clipul HOPA cu balans a fost **renunțat** odată cu balansul.

## Geometrie (față de v5)
- **Carcasa** este identică cu HOPA de deasupra planului z = 3 mm: fața înclinată la 8°, sticla Ø52, cusătura de centură pe siluetă, coroana.
- **Baza:** sub z = 3 carcasa e tăiată plat. O **placă din polimer mat** închide fundul și servește ca fereastră de antenă, pentru că metalul blochează Bluetooth și Wi-Fi.
- **Piciorul:** oval (superelipsă) de **30 × 14 mm**, înalt de 1,2 mm, cu muchia de jos rotunjită la R0,3. E retras față de conturul bazei (≈33 × 25 mm), așa că de jos se vede o linie de umbră fină și SOUL nu se clatină.
- **Dimensiuni:** ≈ **63 × 72,2 × 27 mm**, cu 1,8 mm mai scund decât v5, din cauza tăierii plate.
- **Contacte:** 5 contacte aurii (un pad central Ø1,8 și 4 pad-uri în arc) pe o monedă FR4, în inelul TPU, montate la nivel în picior. Tot pe picior sunt 2 × Torx T5.
- **Marcaj laser pe placă:** „SOUL · Nº 00417 · PROIECTAT ÎN ROMÂNIA", rândul legal, simbolul CE și coșul barat (`src/tex_v6.py`).
- **Fața** are doar sticla neagră și aluminiul. Nu are inel, logo sau găuri.
- **Teșitură:** o singură teșitură prelucrată la 45°, de 0,45 mm, în jurul locașului sticlei. Ea dă linia de lumină subțire dintre metal și sticlă.
- **Difuzor:** o singură fantă fină tăiată cu laser, 12 × 0,6 mm, în cusătura +x (z 46–58). Microfoanele sunt 2 găuri Ø0,7 în cusătura −x.

## Material (CMF)
- **Aluminiu 6061-T6**, sablat fin și uniform cu microbile de sticlă (≈ 50 µm). Anodizare tip II colorată și sigilată.
- **În randare:** metallic 1, roughness ≈ 0,39 (argint) – 0,46 (grafit), anizotropie 0,15 și un coat subțire (IOR 1,6) care imită oxidul sigilat. Granulația e un bump Voronoi fin (≈ 50 µm), iar tonul anodizării variază cu ±3 % pe suprafață.
- **Teșitura** se taie după sablare și se anodizează odată cu piesa. Iese la fel de colorată, dar satinat-lucioasă, cu urme circulare de sculă.
- **Culori:**

| Culoare | Aluminiu (sRGB) | Placa și piciorul (polimer) |
|---|---|---|
| Argint natural | #CBCDCF | #B4B6B8 |
| Grafit | #55575B | #3C3E41 |
| Albastru noapte | #26324C | #1D2435 |
| Jar | #D2622C | #A44A22 |
| Șampanie | #D8C3A2 | #BDAA8A |

- **Polimerul** (PC/ABS, textură VDI 27) are tonul culorii corpului. E singura parte nemetalică și se vede doar de jos sau din unghiuri joase.

## Fabricație: prima serie de 10–25 bucăți
- **Carcasa:** frezare CNC din bară de 6061, fără matrițe. Recomandăm să fie din **două jumătăți** separate pe cusătura de centură (față și spate). Fiecare se prelucrează în 3+2 axe, iar cusătura e deja în design, deci îmbinarea „nu se vede". Din aceeași prindere se taie locașul sticlei și teșitura de 45°.
- **Finisaj:** sablare, apoi anodizare. Teșitura se retrece după sablare și înainte de anodizare.
- **Placa de bază și piciorul:** din polimer, printate SLA sau MJF și vopsite mat în ton pentru prima serie. La volum mai mare se pot injecta.
- **Varianta mai ieftină la volum:** cele două jumătăți pot trece la ambutisare din tablă, cu aceeași cusătură ca linie de îmbinare. Asta e o ipoteză neverificată cu un furnizor.

## Cum se regenerează
Pipeline-ul v5 (`../v5/src/soul_v5.py`) este încărcat prin `exec`, fără cod duplicat. `src/soul_v6.py` suprascrie doar:
- materialele;
- `body_mesh`: teșitura, fanta fină și tăierea plată;
- `bottom_details`: piciorul și contactele;
- cadrele noi.

Comenzi:
```
cd renders/v6/src
PREVIEW=1 ./render_v6.sh hero          # previzualizare la rezoluție pe jumătate
./render_v6.sh                         # toate cadrele statice (Cycles CPU, o randare pe rând, apoi OIDN și AgX)
./render_v6.sh alive                   # clipul de 5 s (fiecare stare unică a ochilor se randează o singură dată)
```
Plasa corpului se construiește o dată (≈ 2 min) și se păstrează în cache în `/tmp/soul_v6_cache`.
