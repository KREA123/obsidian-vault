---
tip: proiect
afacere: KREA
actualizat: 2026-09-24
---
# Krea-Site — versiunea nouă (v5)

Site-ul refăcut pentru krea.ro, pornind de la ce era live pe 24.09.2026. Vezi și [[Site krea.ro]].

## Cum îl publici
1. Copiază peste folderul tău Krea-Site: `index.html`, `formular.html`, `multumesc.html`, `robots.txt`, `sitemap.xml` și folderul `assets/`.
2. **Nu șterge nimic din folderul vechi.** Clipurile (`reels_hero.mp4`, `assets/videos/`), pozele (`assets/img*.jpg`, `assets/photos/`) și `confidentialitate.html` rămân cum sunt. Aici sunt doar fișierele noi din `assets/`: `og.jpg`, `icon-180.png`, `portofoliu/`.
3. Încarcă folderul pe Netlify ca de obicei.

## Formularul (/formular și cel de pe prima pagină)
- Doar 4 câmpuri: **Numele afacerii, Domeniu, Email, Telefon**. Am scos „Cu ce se ocupă afacerea?” și „Ce serviciu te interesează?”.
- Trimite tot prin FormSubmit la office@krea.ro, apoi duce la /multumesc. Pixelul TikTok e neschimbat, deci conversiile se numără la fel.
- Subiectul emailului conține acum numele afacerii: „Lead nou: Clinica X (clinică) — krea.ro/formular 🚀”.
- Câmp nou în email, **sursa**: de unde a venit omul (utm_source, utm_campaign, click TikTok/Meta/Google). Așa vezi ce campanie a adus fiecare lead.
- Mesaje de eroare în română sub fiecare câmp. Dacă trimiterea eșuează, omul vede un mesaj cu numărul de telefon și nu mai e dus pe /multumesc fără ca lead-ul să fi plecat.

## Ce s-a schimbat pe prima pagină
- Fără ecran de încărcare, fără GSAP, fără cursor custom: pagina apare imediat (important pentru traficul din reclame).
- Cifrele reale sus, imediat după hero: 1,04M lei, 7,47x ROAS, 13,79 lei/comandă, 4,4M+ vizualizări.
- Player video pe tot ecranul, cu sunet, săgeți/swipe între clipuri. Pe desktop clipurile pornesc mut la hover, pe telefon sunt într-un carusel.
- Buton fix jos pe telefon: „Lasă-ne datele” + WhatsApp.
- Capturi reale pentru PsyHelp și Parcelata în portofoliu.
- Scoase: „12 oameni” și „120+ proiecte” (notate în vault ca nereale), cardul „98% recomandă” de lângă ele și banda cu Mario & Luigi (marcă Nintendo).
- SEO: titlu și descriere noi, date structurate (firmă + întrebări frecvente), imagine de share `og.jpg`, `robots.txt`, `sitemap.xml`.
- „Nu suntem plătitori de TVA: prețul afișat e prețul final” la prețuri.

## De verificat de tine
- **kx.ro** afișează acum doar o pagină de login, așa că am lăsat cardul KX fără link.
- Cifrele pe care nu le-am putut confirma au rămas cum erau: +180% programări (PsyHelp), 487 parcele (Parcelata), +347% (testimonial KX), 5.0 rating. Dacă vreuna nu e reală, scoate-o.
