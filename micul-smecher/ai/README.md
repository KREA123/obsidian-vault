# Suflet AI — creierul din cloud (v0.1)

Partea de AI a companionului: îi dă **nume și personalitate la naștere**, **vorbește** cu tine
(răspunsuri scurte, rostite, cu emoția care mișcă ochii), **ține minte** ce contează, pune
**mementouri** și **notițe**, și îți scrie **jurnalul zilei**. Firmware-ul rămâne viu și fără
el — AI-ul e un strat în plus, nu o dependență.

## Pornire rapidă (pe PC, fără hardware)

```bash
cd micul-smecher/ai
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # sau: ant auth login
python -m suflet_ai birth --device demo --seed 0xC0FFEE --owner Andu
python -m suflet_ai chat  --device demo          # scrii, îți răspunde
python -m suflet_ai diary --device demo --events examples/events_day.jsonl
```

Server HTTP (pentru aplicația de telefon / demo-ul web / poarta vocală):

```bash
SUFLET_API_TOKEN=schimba-ma uvicorn suflet_ai.server:app --port 8787
```

| Endpoint | Ce face |
|---|---|
| `POST /v1/devices/{id}/birth` | naște personajul o singură dată (nume, poveste, voce, primele cuvinte) |
| `POST /v1/devices/{id}/turn` | `{text}` → `{say, tone, reaction, remember, forget, reminders, notes}` |
| `POST /v1/devices/{id}/events` | jurnalul de evenimente de pe dispozitiv (boop, somn, Claude...) |
| `GET  /v1/devices/{id}/reminders/due` | mementourile scadente (dispozitivul le „spune”) |
| `POST /v1/devices/{id}/diary` | jurnalul zilei, în vocea personajului + o frază de share |
| `GET/DELETE /v1/devices/{id}/memory` | vezi tot ce ține minte / șterge tot (transparență) |

## Cum e construit

- **Claude prin SDK-ul oficial Anthropic** (`anthropic` 1.x), cu **ieșire structurată**
  (JSON Schema) → fiecare răspuns e validat înainte să ajungă la ochi.
- **Cache pe promptul de sistem** (personajul + regulile) → tururile repetate costă mai puțin.
- **Fallback pe server** (`fallbacks="default"`): dacă modelul refuză o cerere, o reia automat
  modelul recomandat; dacă tot nu merge, personajul spune ceva scurt și nu strică memoria.
- `tone` și `reaction` corespund exact enumerărilor din firmware (`Brain.h`).

## Alegerea modelului (decizia lui Andu)

Implicit `claude-opus-5` cu efort `low` pentru tururile vorbite. Se schimbă cu `SUFLET_MODEL`.
Prețuri Anthropic (per 1M tokeni, intrare/ieșire, iunie 2026): Opus 5 $5/$25 · Sonnet 5 $2/$10 ·
Haiku 4.5 $1/$5. Un tur tipic are ~2–3k tokeni de intrare (mare parte din cache) și ~150 de ieșire.
La 10 tururi/zi, **doar LLM-ul** e de ordinul a 1–3 $/utilizator/lună pe Opus 5 (mai puțin pe
Sonnet/Haiku) — de măsurat pe trafic real cu `usage` înainte de a fixa abonamentul. Vocea (STT+TTS)
mai adaugă ~1–4 $/lună (vezi `../research/04-ai-companions-2026-09-24.md`).

„Claude sau ChatGPT”: interfața `Llm` e locul unde se adaugă alt furnizor. v0 are doar Claude.

## Reguli de siguranță din prompt (nu le scoate)

- Spune deschis că e AI (AI Act art. 50 + politica Anthropic).
- Fără roluri romantice/sexuale, fără „nu mă lăsa” ca să te țină captiv, fără presiune de cumpărare.
- La semne de criză: calm, fără glume, încurajează un om de încredere + **Telefonul Sufletului
  0800 801 200**, urgențe **112** (verificați numerele pe fiecare piață).
- Nu ține minte date sensibile (sănătate, religie, politică, bani, parole) decât la cerere explicită.
- Produs pentru adulți (16+/18+). Politica Anthropic cere măsuri suplimentare pentru minori.

## Teste

```bash
python -m pytest -q tests      # 9 teste, fără cheie API (client Claude simulat)
```

## Ce urmează (v1 — vocea)

Placa **Waveshare AMOLED-1.75** (2 microfoane + difuzor) cu firmware-ul open-source
**xiaozhi-esp32** (MIT) pentru fluxul audio (Opus, WebSocket), serverul lui pe infrastructura
noastră din UE, iar ca „LLM provider” — acest pachet (un adaptor mic). Ochii rămân motorul
nostru `Suflet`. Latență țintă < 1,5 s de la ultimul cuvânt la primul sunet.
