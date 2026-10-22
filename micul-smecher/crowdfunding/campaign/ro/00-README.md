# Traducerea în română (pentru Andu)

Aici e traducerea fiecărui fișier din `campaign/`, cu aceleași nume, ca să citești tot în română. **Pe Indiegogo se postează varianta în engleză**, prin `../story-paste.html` și `../perks.csv`. Comunicatul de presă în română (`10-press-release.md`) e direct pentru presa din România.

**Nu se postează nimic până nu scrii decizia D1 în `03 Decizii/Jurnal decizii.md`** și până nu trec toate porțile scenariului activ. Kitul e construit pe scenariul **after_ce**: campania abia după CE, adică regula ta „nicio plată de la clienți înainte de grant și CE” rămâne în picioare.

## Cifrele din text
Toate prețurile, datele, obiectivul, culorile, luna de livrare, rândurile despre CE și TVA sunt **blocuri f** (un comentariu `f:CHEIE` înainte și `/f` după, invizibile pe pagină). Le rescrie `tools/build_copy.py` din `facts.json`. Nu le edita de mână: schimbi faptul în `facts.json` și rulezi `tools/build_all.sh`.

## Ce înseamnă semnele din text

| Semn | Ce înseamnă | Cine îl închide |
|---|---|---|
| block `f:age` | completat cu 18 (varianta sigură) până decizi D4 | tu |
| `[[CE: …]]` | laboratorul CE și data semnării declarației UE; pagina live e scrisă în starea de după CE | tu, la poarta CE |
| `[[G1: …]]` | adevărat doar după G1 (SoulOS + voce pe placa S reală) | tu, la G1 |
| `[[G2: …]]` | adevărat doar după G2 (SOUL S din aluminiu funcțional, filmat dintr-o dublă) | tu, la G2 |
| `[[G3: …]]` | adevărat doar după G3 (oferte scrise, parteneri semnați, baterie măsurată) | tu, la G3 |
| `[[D8: …]]` | depinde de varianta de electronică (decizia D8) | tu |
| `[de completat: …]` | datele tale (nume, bio, poză, citat) | tu |
| `{{URL:…}}` | linkuri care încă nu există | tu |
| `{{img:…}}`, `{{video:…}}` | imagini și clipuri, vezi `../00-image-map.md` | eu le pregătesc, tu le aprobi |
| `{{LIVE:…}}` | cifre copiate de pe pagina campaniei în momentul trimiterii | cine trimite |

Când trece o poartă, o bifezi în `facts.json → gates` (passed, data, dovada) și rulezi din nou: lista „unde e SOUL azi”, rândurile despre CE și bara de stare trec singure de la „planificat” la „făcut”.

Verificarea automată:
```
python3 -I micul-smecher/crowdfunding/tools/check_copy.py --strict -v
```

## Regulile pe care le respectă textele
- **Mărimea:** se vinde **SOUL S** (63 × 71 mm, 23–26 mm adâncime, încă în lucru, AMOLED rotund de 1,75″, 466 × 466). Prototipul de azi e **M** (90 × 101 mm, 2,8″), mereu etichetat.
- **Randările** au mereu „Render (CGI), not a photo.” Mărimea se arată doar cu desenul la scară reală sau cu randările v10 cu mâna/biroul (când sunt gata), etichetate.
- **AI:** SOUL conectează AI-ul propriu al omului sau merge offline. Nu include, nu vinde AI. **Vocea:** azi transformarea vorbirii în text folosește cheia ta OpenAI; vocea doar cu Claude e în dezvoltare. Nu scriem „ții degetul și vorbești cu Claude” până nu merge.
- **CE:** generat din `facts.json → gates.CE`. Până trece: „fără certificare CE încă”.
- **TVA:** prețurile sunt finale. ARTEMIS nu e plătitoare de TVA azi, deci nu scriem niciodată „cu TVA inclus”. În Indiegogo toate cotele UE se pun pe 0 %, în orice caz.
- **Prețuri:** prețul planificat după campanie apare doar în cuvinte. Fără preț tăiat, fără „−x %”, fără urgență falsă.
- **Ochii** nu se aleg, nu se vând, nu se re-trag, nu costă după raritate. Doi SOUL *rareori* au aceiași ochi (cam 1 din 112); niciodată „nu există doi la fel”.
- **Nimic inventat.** Bateria și autonomia rămân deschise până la măsurare. Greutatea: „~75–95 g (estimare)”.
- **Fără ediție Founders.**
- **Doar tu** faci contul, verificarea identității, banca, accepți termenii și trimiți la review.

## Ce s-a schimbat după review (22.10.2026)
- Scara de recompense: Two Souls €498 (€249 bucata), First Light cu numărul gravat pe picior, recompensele limitate la lotul 1 (270), „Campaign Price · batch 2” cu luna lui.
- Livrare: mai 2028 (UE) pentru lotul 1, august 2028 pentru lotul 2 (D9 aplicat ca variantă sigură). UK scos din campania 1 (D13), SUA/Canada nu mai sunt stretch goal (D14).
- CE: pagina live e scrisă în starea de după CE; „fără certificare CE încă” apare doar în emailurile către lista de așteptare.
- AI: niciodată „cont ChatGPT”; doar propria cheie API OpenAI (în dezvoltare).
- Transport: tarife fixe, nu estimări. Grantul nu apare nicăieri ca sursă de bani.
- Deciziile tale: `../DECIZII-FONDATOR.md`.
