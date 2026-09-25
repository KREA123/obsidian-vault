---
tip: audit
afacere: MundiShop
data: 2026-09-25
---
# Audit mundishop.ro — 25.09 (read-only, telefon + browser Facebook)

## 1. Viteză și tracking (posibila cauză a scăderii LPV de la 94% la 57%)
- **Pagina de produs se încarcă greu:** ~300 de cereri, ~3,3 MB, încărcare completă în 10–13 s pe 4G. Pixelul Meta pornește la ~9 s, ultimul din toate scripturile. Cine iese mai devreme nu e numărat ca vizită.
- **Scripturile grele:**
  - Shopify Forms, 925 KB, doar pentru popup-ul „Reducere 5%”;
  - 3 taguri Google, dintre care unul încărcat de două ori;
  - pixel TikTok;
  - Judge.me, deși are 0 recenzii de produs;
  - Google Pay.
- **Tema a fost modificată pe 24.09, la 08:42 UTC**, cu o zi înainte de scăderea LPV. De verificat primul.
- **Posibil impact al bannerului de cookie:** consent mode e setat implicit pe „denied”. Neverificat din România.

## 2. Preț și ofertă
- **Prețurile sunt la nivelul PVR, iar piața e cu 20–55% mai jos.**
  - 31148: 159,99 lei la noi, ~97–121 lei la Altex, Media Galaxy, Bebe Tei.
  - 60443: 159,99 lei la noi, 109,99 lei la Altex.
  - 31167: 479,99 lei la noi, 329 lei la Smyk.
- **Colecția Reduceri:** 48 din 137 de produse nu au preț redus. Risc ANPC. Prețurile „înainte” trebuie aliniate la Omnibus (HG 686/2022).
- **Pachetele-cadou costă doar 480–530 lei.** Nu există niciunul sub 200 lei.

## 3. Livrare, plată, retur
- **Livrare fixă de 25 lei, fără prag de livrare gratuită.** Concurența are prag: Noriel 199–249 lei, Smyk 200, Brick Depot 299, lego.com 299.
- Nu există easybox, rate sau ambalaj cadou.
- **Checkout-ul preselectează cardul**, deși 61–80% dintre clienți plătesc ramburs.
- **Retur în 14 zile, pe banii clientului.** Concurența oferă 30–35 de zile.
- **Termenul de livrare diferă:** site-ul spune 24–72h, unele reclame 24–48h.

## 4. Încredere
- **Widgetul de recenzii afișează „0 recenzii”.** Cele 12 recenzii ale magazinului sunt ascunse în alt tab.
- **Emailul de contact e office@krea.ro**, nu o adresă @mundishop.ro.
- **„Peste 1.000 de seturi din stoc” e fals:** sunt ~520 de seturi în stoc.
- **Etichetele de stoc se contrazic:** „Ultimele 2” în listă, dar „În stoc” pe pagina produsului.

## 5. Merchandising
- **Pe telefon, colecțiile arată câte un produs pe rând.** Colecția Creator are ~25 de ecrane.
- **Sortarea implicită începe cu seturile scumpe.**
- **32% din produse sunt fără stoc:** 334 din 1.037, inclusiv în tabul „Sub 100 lei”.
- **„Back to School” e încă în meniu** la sfârșitul lui septembrie.

## De făcut săptămâna asta, din admin, fără programator
1. **Checkout:** aplicație de personalizare a plăților, cu ramburs pus primul și preselectat.
2. **Livrare:**
   - livrare gratuită de la 199–249 lei, cu bară „mai ai X lei”;
   - același termen de livrare peste tot;
   - „Back to School” scos din meniu.
3. **Viteză și încredere:**
   - Shopify Forms oprit;
   - TikTok scos, dacă nu rulează reclame acolo;
   - tagul Google duplicat scos;
   - recenziile magazinului afișate implicit;
   - emailul schimbat pe @mundishop.ro;
   - „1.000 de seturi” corectat.

   După 48 de ore se verifică LPV-ul din nou.
