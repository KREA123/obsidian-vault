---
SoulOS 1.9.1 (SoulOS Alive) · SOUL S · placa Waveshare ESP32-S3-Touch-AMOLED-1.75
---

# 1. Instalează SoulOS pe placa SOUL S (5 minute)

Asta e placa produsului final: ecran rotund **AMOLED de 1,75"**, 466 × 466. Prototipul de test (placa 2.8C) are ghidul lui, `1-INSTALEAZA-RO.md`.

## Ce îți trebuie

- Placa **Waveshare ESP32-S3-Touch-AMOLED-1.75**.
- Un **cablu USB-C de date**. Unele cabluri sunt doar de încărcare și nu merg. Dacă placa nu apare, schimbă cablul.
- Un calculator cu **Google Chrome** sau **Microsoft Edge**. Safari și Firefox nu merg.
- Fișierul **`SOUL-1.75-install.bin`** din acest pachet. **Nu** folosi `SOUL-2.8C-install.bin` pe placa asta: e pentru alt ecran.
- Opțional: un **difuzor** pus în mufa de difuzor a plăcii (pentru alarme) și o **baterie LiPo** în mufa MX1.25. **Verifică polaritatea (+ și −) pe placă înainte să bagi bateria.**

## Pașii

1. Conectează placa la calculator cu cablul USB-C.
2. Deschide în Chrome: **https://espressif.github.io/esptool-js/**
3. Apasă **Connect**. Apare o fereastră cu porturi: alege-l pe cel care conține **„USB JTAG/serial”** (sau „ESP32”), apoi **Connect**.
4. La **Flash Address** scrie exact: **0x0** (zero, x, zero).
5. La fișier apasă **Choose File** și alege **`SOUL-1.75-install.bin`**.
6. Apasă **Program**. Așteaptă până scrie că a terminat (cam 1–2 minute). **Nu scoate cablul în timpul ăsta.**
7. Apasă butonul **RESET** de pe placă (sau scoate și bagă la loc cablul).
8. Gata: pe ecran apar **ochii pe negru**. Atinge ecranul și ochii urcă sus, iar în jurul lor apare cercul de aplicații.

## Verifică versiunea

Pe placă: glisează pe cerc până la **Setări** → **Device**. Trebuie să scrie **SoulOS 1.9.1 · S**.

## Ce e nou și trebuie verificat pe S (versiunea asta n-a rulat încă pe placă)

Scrie-mi la fiecare: merge / nu merge / ce ai văzut.

1. **Sunetul.** Pune o alarmă peste 2 minute (**Alarme → + Nouă**). Trebuie să sune din difuzor. Dacă titlul listei de alarme scrie **„Alarme · fără sunet”** (în engleză „Alarms · silent”, portocaliu), placa nu și-a găsit difuzorul: spune-mi.
2. **Ecranul fără rupturi.** Deschide și închide câteva aplicații din cerc și rotește o listă repede. Nu trebuie să apară nicio linie ruptă pe ecran (o parte din imagine veche, o parte nouă). Dacă poți, filmează cu telefonul în slow motion.
3. **Atingerile.** Atinge rânduri din Setări cu degetul normal, nu foarte atent. O atingere trebuie să deschidă rândul, nu să rotească lista.
4. **Întoarce-l cu fața în jos** un minut, apoi ridică-l: ochii revin repede, fără o imagine veche pe ecran.
5. **Bateria (dacă ai pus una).** În **Setări → Device** procentul trebuie să aibă sens și să crească pe USB.

Pentru măsurători mai precise (cu monitorul serial): `../BRINGUP.md` §S.

## Dacă nu merge

- **Placa nu apare la Connect:** ține apăsat butonul **BOOT**, apasă scurt **RESET**, apoi dă drumul la BOOT. Încearcă din nou Connect. Dacă tot nu apare, schimbă cablul sau portul USB.
- **Eroare la Program:** apasă **Erase Flash** în aceeași pagină, așteaptă, apoi repetă pașii 4–6.
- **Ecranul rămâne negru după RESET:** scoate cablul, așteaptă 5 secunde, bagă-l la loc.
- **Placa se oprește singură pe baterie:** bateria e aproape goală; SOUL își salvează memoria și se oprește. Pune-o pe USB și apasă butonul **PWR**.
- **Vrei să verifici că fișierul e cel corect (opțional):** amprenta SHA-256 e mai jos și în `README.md`. Pe Windows: `certutil -hashfile SOUL-1.75-install.bin SHA256`. Pe Mac: `shasum -a 256 SOUL-1.75-install.bin`.
  `b208fbbb2181faba517897a1b3a4a8f503817b072d0b43ab4c6d5c50b3e358bf`

Setările, alarmele, notițele și memoria rămân dacă reinstalezi peste o versiune mai veche de pe aceeași placă.
