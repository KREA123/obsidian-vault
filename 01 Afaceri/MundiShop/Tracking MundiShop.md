---
tip: canal
afacere: MundiShop
actualizat: 2026-09-23
---
# Tracking MundiShop

- Singurul pixel Meta: canalul Facebook & Instagram din Shopify, cu CAPI. Meta = Shopify (28 = 28 pe 11.09). Calitatea corelării 9,3/10. Catalog ↔ evenimente 99,9%.
- „Invalid parameter format for currency” — cosmetic (regulă Meta care citește un script Apple Pay).
- 29% din AddToCart fără valoare (trimise doar server-side prin integrarea Shopify) — impact mic.
- Eticheta Google Ads statică în `<head>` din 18.09, verificată. Conversie principală: „Google Shopping App Purchase”; GA4 secundar.
- **Bannerul de cookie scos complet din 8.09** (decizia lui Andu): pixelii se încarcă pentru toți. ⚠️ Risc legal + conflict cu Consent Mode v2 cerut de Google. [[Eliminarea bannerului de cookie]]
- Datele GA4 de dinainte de 8.09 sunt subnumărate — nu se compară direct cu cele de după.
- Sursa de adevăr pentru comenzi: **Shopify / GA4**.

## Metodă din cercetare
[[MundiShop_Research_2026-09-23/11_Masurare_Pixel_CAPI|testele de măsurare]] · [[MundiShop_Research_2026-09-23/25_Reguli_incredere|consimțământ, EDPB]] · harta: [[Hartă cunoaștere MundiShop]]
