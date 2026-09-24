---
tip: proiect
afacere: KREA
actualizat: 2026-09-24
---
# Krea-Site — versiunea nouă (v5)

Site-ul refăcut pentru krea.ro, pornind de la ce era live pe 24.09.2026. Vezi și [[Site krea.ro]].

## Cum îl publici
1. Copiază peste folderul tău Krea-Site fișierele `index.html`, `formular.html`, `multumesc.html`, `robots.txt` și `sitemap.xml`.
2. Copiază **conținutul** folderului `assets/` de aici (`og.jpg`, `icon-180.png` și folderul `portofoliu/`) **în** folderul `assets/` pe care îl ai deja. **Nu înlocui tot folderul `assets/`.** Dacă sistemul întreabă „Înlocuiește”/„Replace”, alege Stop sau „Păstrează ambele” și copiază fișierele pe rând. Altfel se șterg clipurile (`assets/videos/`) și pozele (`assets/img*.jpg`, `assets/photos/`).
3. Nu șterge nimic din folderul vechi. `reels_hero.mp4` și `confidentialitate.html` rămân cum sunt.
4. Încarcă folderul pe Netlify ca de obicei. Apoi deschide krea.ro și verifică că se văd pozele și că pornesc clipurile.

## Formularul (/formular și cel de pe prima pagină)
- Doar 4 câmpuri: **Numele afacerii, Domeniu, Email, Telefon**. Am scos „Cu ce se ocupă afacerea?” și „Ce serviciu te interesează?”.
- Trimite tot prin FormSubmit la office@krea.ro, apoi duce la /multumesc.
- Subiectul emailului conține acum numele afacerii: „Lead nou: Clinica X (clinică) — krea.ro/formular 🚀”.
- Câmp nou în email, **sursa**: de unde a venit omul (utm_source, utm_campaign, click TikTok/Meta/Google). Așa vezi ce campanie a adus fiecare lead.
- Mesajele de eroare apar în română, sub fiecare câmp. Pe telefon, tasta „următorul” trece la câmpul următor. Dacă trimiterea eșuează, omul vede un mesaj cu numărul de telefon și nu mai e dus pe /multumesc fără ca lead-ul să fi plecat.

## Pixelul TikTok
- **Neschimbat:** `SubmitForm` și `CompleteRegistration` pe /multumesc, plus `PageView` pe fiecare pagină. Conversiile din formular se numără la fel ca înainte.
- **Nou:** evenimentul `Contact` se trimite la click pe orice buton WhatsApp. Înainte era un singur buton, pe prima pagină. Acum sunt 4 pe prima pagină și 1 pe /formular, așa că vei vedea mai multe evenimente „Contact”.
- **Recomandare, neaplicată** ca să nu schimb ce optimizează campaniile care merg: conversiile de pe /multumesc se trimit la fiecare încărcare a paginii, inclusiv la reîncărcare sau vizită directă. Se pot trimite doar după o trimitere reală a formularului. Spune dacă vrei asta.

## Ce s-a schimbat pe prima pagină
- Fără ecran de încărcare, fără GSAP, fără cursor custom. Titlul și butoanele apar imediat, fără animație, ceea ce contează pentru traficul din reclame.
- Cifrele reale apar sus, imediat după hero: 1,04M lei, 7,47x ROAS, 13,79 lei/comandă, 4,4M+ vizualizări.
- Player video pe tot ecranul, cu sunet, săgeți/swipe între clipuri, funcțional și din tastatură. Pe desktop clipurile pornesc mut la hover. Pe telefon sunt într-un carusel.
- Buton fix jos pe telefon: „Lasă-ne datele” + WhatsApp. Toate butoanele „Te sunăm noi” duc direct la formular.
- Capturi reale pentru PsyHelp și Parcelata în portofoliu.
- SEO: titlu și descriere noi, date structurate (firmă + întrebări frecvente), imagine de share `og.jpg`, `robots.txt`, `sitemap.xml`.
- „Nu suntem plătitori de TVA: la prețurile afișate nu se adaugă TVA” la prețuri.

## Cifre corectate după capturile din Ads Manager
Capturile la care trimite chiar site-ul (`assets/img07-09.jpg`) arătau altceva decât textul:
- **Caz 04:** captura e din TikTok Ads (coloane „CPC (destination)”, „Clicks (destination)”), nu din Meta. Eticheta e acum „Trafic · TikTok”.
- **Caz 05:** s-au cheltuit 473,91 lei, nu 700 (700 era bugetul altei campanii). 3,15 lei e costul la 1.000 de oameni atinși, nu per rezultat.
- **Caz 06:** 6,55 lei e costul pe **apel**, iar 32.059 e numărul de oameni atinși. Nu erau 32.000 de „oameni interesați”. Cheltuiala a fost de 1.133 lei.
- **Clipul din hero** (service auto) nu e clipul cu 2,1M vizualizări: captura cu 2,1M arată alt video. Cifra de 2,1M a rămas doar pe captura ei.
- **PsyHelp** e acum „Clinică de psihiatrie”, cum scrie pe site-ul lor.

## Scoase
- „12 oameni” și „120+ proiecte” (notate în vault ca nereale), cardul „98% recomandă” de lângă ele și banda cu Mario & Luigi (marcă Nintendo).
- Odată cu secțiunile refăcute au dispărut și: „6+ luni alături de fiecare client”, „+200% creștere medie vânzări”, „8x ROAS”, „4.9★ rating Google” (PsyHelp), „100% experiență premium” (WOW), „Locuri limitate luna aceasta”.

## De verificat de tine
- **kx.ro** afișează acum doar o pagină de login, așa că am lăsat cardul KX fără link.
- Cifre pe care nu le-am putut confirma și au rămas cum erau: +180% programări (PsyHelp), 487 parcele (Parcelata), +347% (testimonial KX), „vânzările ni s-au triplat” (testimonial), ratingul 5,0, statisticile automatizărilor (~10x, 0 erori, 90+ Lighthouse, <2s, −60%). Dacă vreuna nu e reală, scoate-o.
