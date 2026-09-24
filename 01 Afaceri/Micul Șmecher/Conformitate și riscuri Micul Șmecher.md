---
tip: risc
afacere: Micul Șmecher
status: activ
actualizat: 2026-09-24
---
# Conformitate și riscuri — Micul Șmecher

> Nu e consultanță juridică. Sursa detaliată: `micul-smecher/research/03-compliance-2026-09-24.md`. Înainte de primul ban încasat: o oră cu un consultant de conformitate (~€200).

## Ce e obligatoriu ca să vinzi în UE
| Regula | Ce înseamnă pentru noi | Cost / timp (estimare) |
|---|---|---|
| **CE / RED** (radio: Bluetooth, Wi-Fi) | Declarație de conformitate + teste EN 300 328, EN 301 489, EN 62368-1, EN 62479. Plăcile Waveshare au cip ESP32 fără modul certificat → teste radio complete. Cu modul **ESP32-S3-WROOM** pe PCB propriu refolosim o parte din dovezile Espressif. | €5–12k (laborator PL/RO), 4–12 săpt. |
| **Securitate cibernetică RED** (EN 18031, din 1.08.2025) | Se aplică dacă e conectat la internet (și prin telefon/PC), sau dacă e **purtabil** cu microfon/senzori, chiar offline. Fără parole implicite, update-uri semnate, Bluetooth securizat (îl avem: împerechere cu cod de 6 cifre). | €0–9k |
| **Cyber Resilience Act** | Raportare vulnerabilități din 11.09.2026; obligații complete din 11.12.2027. | proces intern |
| **Bateria (Reg. 2023/1542, art. 11)** | **Din 18.02.2027 bateria trebuie înlocuibilă de utilizator cu unelte obișnuite** — fără lipici, capac cu șuruburi, piese de schimb 5 ani. Se aplică pe fiecare bucată pusă pe piață după acea dată (și pre-comenzile livrate după). | design, nu cost mare |
| **GPSR** (siguranța produselor) | Analiză de risc, lot/serie pe produs, nume + adresă + email, instrucțiuni în RO, canal de reclamații, informații pe pagina de vânzare. | €0,5–1,5k |
| **DEEE + baterii (România, ANMAP)** | Înregistrare producător EEE (500 lei) + baterii (500 lei), contract cu organizație colectivă, declarații lunare AFM. **Vânzare în alte țări UE = înregistrare în fiecare țară** (€1–3k/țară/an). | ~€200 + câteva sute €/an |
| **Transportul bateriilor** | UN38.3 de la furnizorul de celule; 1,85 Wh în echipament = UN3481 Secțiunea II. Curieri expres OK; unele poște refuză. | ~0 |
| **Consumatori (pre-comenzi)** | 14 zile drept de retragere de la primire; **buton de retragere online obligatoriu din 19.06.2026**; dată de livrare estimată clară + rambursare dacă întârziem. | redactare |
| **Jucării** | E jucărie dacă e pentru copii sub 14 ani. Noi: marketing pentru adulți + „Nu e jucărie. Nu e pentru copii sub 14 ani.” | — |
| **AI Act** | **Art. 50: trebuie să spună că e AI** (din 2.08.2026). Fără manipulare, fără exploatarea vulnerabilităților. Nu promovăm „îți citește emoțiile”. | — |
| **GDPR** | Tot ce e doar pe dispozitiv: nu suntem operator. Cloud-ul de voce/memorie: suntem operator → politică de confidențialitate, servere UE, ștergere la cerere (avem deja endpoint-ul). | €0,3–1,5k |
| **Politica Anthropic** | Dezvăluire AI obligatorie; fără conținut erotic; fără manipulare; produsele pentru minori cer măsuri suplimentare → lansăm 18+ (sau 16+ cu grijă). | — |

## Scurtături legitime
- **Founders Desk Edition pe USB, fără baterie**: scapă de regulamentul bateriei, UN38.3 și riscul de încărcare la 2 A al plăcii 1.43. Rămâne de lămurit dosarul CE pentru o placă Waveshare (marcată CE de producător) pusă într-o carcasă cu firmware-ul nostru — întrebarea pentru consultant.
- **Ediția 0 doar în România** (sau prin distribuitori UE care preiau rolul de producător) până avem EPR în alte țări.
- **Baterie înlocuibilă din prima zi** — ca să nu refacem designul în februarie 2027.

## Buget total conformitate
- Ediția Founders/Ediția 0 (≤ 300 buc.): **€5–12k** (laborator în China, doar RO) până la €15–30k (laborator UE + DE/FR).
- Producție 1.000+: **€30–80k**, 4–6 luni.

## Registrul de riscuri
| Risc | Probabilitate | Impact | Ce facem |
|---|---|---|---|
| Anthropic schimbă API-ul Hardware Buddy (e în „developer mode”) | medie | mediu | Claude e un strat, nu fundația; cerem statut de proiect maker |
| Meta Muse Charm domină piața de masă | medie | mare | nișă premium + confidențialitate + orice AI + dezvoltatori |
| Numele SUFLET nu e disponibil ca marcă | necunoscut | mediu | verificare EUIPO/USPTO **înainte** de orice material tipărit |
| Întârzieri de producție | mare | mare | promitem +3 luni; nu luăm bani înainte de DVT pentru producția de masă |
| Cost voce scăpat de sub control | medie | mediu | minute incluse + pachete; limită de utilizare corectă |
| Incident de siguranță a bateriei | mică | foarte mare | celule certificate, încărcare 200 mA, test de îmbătrânire |
| Plângere GDPR / AI Act | mică | mare | carta companionului, servere UE, memorie ștergibilă, „sunt un AI” |

## Legat de
[[Micul Șmecher]] · [[Planul de bani Micul Șmecher]] · [[Produs și dezvoltare Micul Șmecher]]
