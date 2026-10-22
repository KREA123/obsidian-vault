---
SoulOS 1.9.1 (SoulOS Alive) · placa Waveshare ESP32-S3-Touch-LCD-2.8C (prototipul, SOUL M)
---

# 1. Instalează SoulOS pe placă (5 minute)

## Ce îți trebuie

- Placa **Waveshare ESP32-S3-Touch-LCD-2.8C**.
- Un **cablu USB-C de date**. Unele cabluri sunt doar de încărcare și nu merg. Dacă placa nu apare, schimbă cablul.
- Un calculator cu **Google Chrome** sau **Microsoft Edge**. Safari și Firefox nu merg.
- Fișierul **`SOUL-2.8C-install.bin`** din acest pachet. (Placa produsului final, AMOLED-1.75, are fișierul ei și ghidul `1-INSTALEAZA-S-RO.md`.)

## Pașii

1. Conectează placa la calculator cu cablul USB-C.
2. Deschide în Chrome: **https://espressif.github.io/esptool-js/**
3. Apasă **Connect**. Apare o fereastră cu porturi: alege-l pe cel care conține **„USB JTAG/serial”** (sau „ESP32”), apoi **Connect**.
4. La **Flash Address** scrie exact: **0x0** (zero, x, zero).
5. La fișier apasă **Choose File** și alege **`SOUL-2.8C-install.bin`**.
6. Apasă **Program**. Așteaptă până scrie că a terminat (cam 1–2 minute). **Nu scoate cablul în timpul ăsta.**
7. Apasă butonul **RESET** de pe placă (sau scoate și bagă la loc cablul).
8. Gata: pe ecran apar **ochii pe negru**. Atinge ecranul și ochii urcă sus, iar în jurul lor apare cercul de aplicații.

## Verifică versiunea

Pe placă: glisează pe cerc până la **Setări** → **Device**. Trebuie să scrie **1.9.1**.

## Dacă nu merge

- **Placa nu apare la Connect:** ține apăsat butonul **BOOT**, apasă scurt **RESET**, apoi dă drumul la BOOT. Încearcă din nou Connect. Dacă tot nu apare, schimbă cablul sau portul USB.
- **Eroare la Program:** apasă **Erase Flash** în aceeași pagină, așteaptă, apoi repetă pașii 4–6.
- **Ecranul rămâne negru după RESET:** scoate cablul, așteaptă 5 secunde, bagă-l la loc.
- **Vrei să verifici că fișierul e cel corect (opțional):** amprenta SHA-256 e în fișierul `SHA256.txt`. Pe Windows: `certutil -hashfile SOUL-2.8C-install.bin SHA256`. Pe Mac: `shasum -a 256 SOUL-2.8C-install.bin`.

Setările, alarmele, notițele și memoria rămân dacă reinstalezi peste o versiune 1.6 sau mai nouă.
