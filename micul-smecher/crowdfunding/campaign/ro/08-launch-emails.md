# Emailurile din timpul campaniei (4) · traducere

Către lista de așteptare (doar abonați), din platforma noastră de email. Emailurile Indiegogo către susținători sunt separate (update-urile, `09-updates-templates.md`). Subsolul: ca în `07-prelaunch-emails.md`.
**Reguli:** orice cifră despre progresul campaniei (suma strânsă, susținători, % din obiectiv, recompense rămase) se copiază de pe pagina live în momentul trimiterii, scrisă aici `{{LIVE:…}}`. Niciodată rotunjită în sus, niciodată estimată. Fiecare preț, dată și rând despre prețul de după campanie e un bloc f generat din `facts.json`: fără urgență inventată (prețul de după campanie e prețul din Late Pledge, și emailul o spune).

| # | Când | Cui |
|---|---|---|
| 1 | ziua lansării, 09:00 (<!--f:launch_day-->marți, 5 octombrie 2027<!--/f-->); retrimitere scurtă la 13:00 celor care nu l-au deschis | toată lista |
| 2 | lansare + 48 de ore, 09:00 | toată lista minus susținătorii (dacă platforma îi poate exclude; altfel toată lista, cu rândul pentru susținători) |
| 3 | ziua 17, 09:00 (jumătatea campaniei) | toată lista |
| 4 | cu 48 de ore înainte de final + ultima zi, 09:00 (finalul: <!--f:end_day-->marți, 9 noiembrie 2027<!--/f-->) | toată lista minus susținătorii |

---

## Email 1 · Ziua lansării

**Subiect:** SOUL e live. First Light: <!--f:launch_cap-->150<!--/f--> la <!--f:launch_price-->€249<!--/f-->.
**Previzualizare:** Tocmai a deschis ochii pe Indiegogo.

{{img:launch-700}} (imagine 700 × 700 „Live on Indiegogo”, randare etichetată)

Salut,

**SOUL e live pe Indiegogo.** → {{URL:campaign}}

<!--f:ladder_line-->**First Light:** primii 150 susținători, €249, cu numărul First Light gravat pe picior · **Campaign Price:** €269 · **Two Souls:** €498 (€249 bucata) · după campanie: **Late Pledge** €299. Prețul de vânzare planificat după campanie: €299.<!--/f-->

Ce susții:
- SOUL S: 63 × 71 mm de aluminiu sablat și anodizat, un AMOLED rotund de 1,75″, doi ochi vii.
- Născut cu una din 120 de perechi de ochi. Nu le alege nimeni.
- <!--f:ai_line-->Merge cu propriul Claude sau cu propria cheie API OpenAI (în dezvoltare), ori offline. SOUL nu include AI.<!--/f-->
- Fără cameră. Ascultă doar cât ții degetul pe sticlă.
- OU, oul lui de încărcare, în cutie.
- Livrare estimată: <!--f:delivery-->mai 2028 (UE)<!--/f--> (lotul 1).

E **totul sau nimic**: dacă nu atingem obiectivul, nu plătește nimeni. Prima zi decide mult. Dacă SOUL te-a făcut să zâmbești, azi e ziua.

**[Susține SOUL →]** {{URL:campaign}}

Ține degetul pe sticlă,
[de completat: prenumele fondatorului]

P.S. <!--f:ce_short-->A trecut testele radio, EMC, de siguranță și EN 18031 la [[CE: numele laboratorului]]; declarația UE de conformitate e semnată ([[CE: data semnării declarației UE]]).<!--/f--> Tot ce știm că poate merge prost e pe pagină, la „Risks and challenges”.

**Retrimiterea de la 13:00 (doar celor care nu l-au deschis). Subiect:** First Light: au mai rămas {{LIVE:first_light_left}} din <!--f:launch_cap-->150<!--/f-->

---

## Email 2 · 48 de ore

**Subiect (dacă nu am atins obiectivul):** {{LIVE:percent}} % în două zile. Mulțumim.
**Subiect (dacă l-am atins):** Am reușit. SOUL e finanțat.
**Previzualizare:** Ce s-a întâmplat și ce mai e deschis.

Salut,

acum două zile SOUL și-a deschis ochii pe Indiegogo. De atunci **{{LIVE:backers}} de oameni** l-au susținut, cu **€{{LIVE:raised}}** ({{LIVE:percent}} % din obiectiv).

[Dacă e finanțat:] **SOUL e finanțat.** Fiecare recompensă se va face. De acum, fiecare euro merge întâi la stretch goals: la <!--f:stretch_first-->€95.000<!--/f-->, SoulOS în germană, franceză, spaniolă și italiană.
[Dacă nu:] **Suntem la {{LIVE:percent}} %.** E totul sau nimic, deci până trecem de <!--f:goal-->€70.000<!--/f--> nu plătește nimeni și nimic nu e sigur. Zilele următoare decid.

Încă deschise:
- **First Light** (<!--f:launch_price-->€249<!--/f-->): au rămas {{LIVE:first_light_left}} [sau: epuizat, mulțumim]
- **Two Souls** (<!--f:two_price-->€498<!--/f-->): doi SOUL, oricare două culori: cel de făcut cadou
- **Campaign Price** (<!--f:campaign_price-->€269<!--/f-->)

Întrebarea primită cel mai des: „Include AI?” Nu. SOUL se conectează la propriul tău Claude sau la propria ta cheie API OpenAI (în dezvoltare) sau trăiește offline. Le plătești direct, și nu există abonament SOUL.

**[Vezi SOUL →]** {{URL:campaign}}

Ai susținut deja? Mulțumim. Cel mai util lucru acum e un mesaj către un prieten căruia i-ar plăcea.

Ține degetul pe sticlă,
[de completat: prenumele fondatorului]

---

## Email 3 · Jumătatea campaniei (ziua 17)

**Subiect:** La jumătate. Ce am construit de la lansare.
**Previzualizare:** O privire înăuntru și încă {{LIVE:days_left}} zile.

Salut,

suntem la jumătatea campaniei: **{{LIVE:backers}} de susținători, €{{LIVE:raised}}, încă {{LIVE:days_left}} zile.**

Ce am făcut în aceste două săptămâni (doar lucruri reale, cu poze):
- [de completat: un progres real, de ex. „mostra de referință în Jar, aprobată” + o poză reală]
- [de completat: ceva din SoulOS, de ex. „o expresie nouă” + o captură, etichetată]
- [de completat: cea mai interesantă întrebare de la susținători și răspunsul nostru]

Următorul stretch goal: **{{LIVE:next_stretch}}**.

Dacă așteptai să te hotărăști: prețul din campanie e <!--f:campaign_price-->€269<!--/f--> până la final. <!--f:after_campaign-->După campanie: Late Pledge la €299, din 30 noiembrie 2027, livrat cu lotul 2 (estimat august 2028).<!--/f-->

**[Susține SOUL →]** {{URL:campaign}}

Ține degetul pe sticlă,
[de completat: prenumele fondatorului]

---

## Email 4 · Ultimele 48 de ore

**Subiect:** <!--f:urgency_subject-->Încă 48 de ore. Apoi €299, în Late Pledge.<!--/f-->
**Previzualizare:** Campania se termină <!--f:end_day-->marți, 9 noiembrie 2027<!--/f-->.

Salut,

campania SOUL se termină **<!--f:end_day-->marți, 9 noiembrie 2027<!--/f-->** [de completat: ora exactă de pe Indiegogo]. <!--f:after_campaign-->După campanie: Late Pledge la €299, din 30 noiembrie 2027, livrat cu lotul 2 (estimat august 2028).<!--/f-->

Azi: **{{LIVE:backers}} de susținători, €{{LIVE:raised}}** ({{LIVE:percent}} % din <!--f:goal-->€70.000<!--/f-->).

[Dacă nu e finanțat:] Mai avem **€{{LIVE:remaining}}** până la obiectiv. E totul sau nimic: dacă nu ajungem, nu plătește nimeni și nu facem lotul. Dacă voiai să-l susții, acum contează.
[Dacă e finanțat:] SOUL e finanțat. În ultimele 48 de ore țintim următorul stretch goal: {{LIVE:next_stretch}}.

Prețul din campanie: **<!--f:campaign_price-->€269<!--/f-->** (Two Souls <!--f:two_each-->€249<!--/f--> bucata). Livrare estimată: <!--f:delivery-->mai 2028 (UE)<!--/f--> pentru lotul 1, <!--f:delivery_b2-->august 2028<!--/f--> pentru lotul 2.

**[Susține SOUL înainte să se închidă →]** {{URL:campaign}}

Ține degetul pe sticlă,
[de completat: prenumele fondatorului]

**Retrimiterea din ultima zi (09:00, celor care n-au susținut). Subiect:** Ultima zi pentru SOUL pe Indiegogo
Text: două rânduri + buton. „<!--f:last_day-->Campania SOUL se închide în seara asta. Azi €269; după, €299 în Late Pledge.<!--/f--> → {{URL:campaign}}”
