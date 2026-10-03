# SOUL AI — creierul din cloud (v0.2)

> Pachetul Python se numește încă `suflet_ai` (nu l-am redenumit ca să nu stricăm importurile); tot ce vede utilizatorul se numește **SOUL**.

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

„Claude sau ChatGPT”: din v0.2 există stratul de acțiuni și cele trei moduri (fără AI / Claude / ChatGPT) — vezi secțiunea **SOUL: acțiuni și moduri AI** de mai jos. Companionul (`/v1/devices/...`) rămâne pe Claude.

## Reguli de siguranță din prompt (nu le scoate)

- Spune deschis că e AI (AI Act art. 50 + politica Anthropic).
- Fără roluri romantice/sexuale, fără „nu mă lăsa” ca să te țină captiv, fără presiune de cumpărare.
- La semne de criză: calm, fără glume, încurajează un om de încredere + **Telefonul Sufletului
  0800 801 200**, urgențe **112** (verificați numerele pe fiecare piață).
- Nu ține minte date sensibile (sănătate, religie, politică, bani, parole) decât la cerere explicită.
- Produs pentru adulți (16+/18+). Politica Anthropic cere măsuri suplimentare pentru minori.

## Teste

```bash
python -m pytest -q            # 49 de teste, fără nicio cheie API (clienți Claude și OpenAI simulați)
```

## Ce urmează (v1 — vocea)

Placa **Waveshare AMOLED-1.75** (2 microfoane + difuzor) cu firmware-ul open-source
**xiaozhi-esp32** (MIT) pentru fluxul audio (Opus, WebSocket), serverul lui pe infrastructura
noastră din UE, iar ca „LLM provider” — acest pachet (un adaptor mic). Ochii rămân motorul
nostru `Suflet`. Latență țintă < 1,5 s de la ultimul cuvânt la primul sunet.

---

## SOUL: acțiuni și moduri AI (v0.2)

Promisiunea de pe site (secțiunea „Your AI. Or no AI at all.”) are acum cod în spate. Ideea
centrală: **există un singur set de acțiuni**, iar fiecare mod AI doar decide *care* acțiune
se cheamă. Ecranele, sincronizarea și testele sunt aceleași pentru toate modurile.

### Acțiunile (`suflet_ai/actions.py`)

| Acțiune | Ce face | Unealta pentru LLM |
|---|---|---|
| `note.create {text, tags}` | notiță (se sincronizează pe telefon) | `note_create` |
| `reminder.create {when, text}` | memento la ora locală `YYYY-MM-DDTHH:MM` | `reminder_create` |
| `alarm.set {hhmm, days, label}` | alarmă, o dată sau pe zile | `alarm_set` |
| `timer.start {seconds, label}` | cronometru | `timer_start` |
| `focus.start {minutes, label}` | sesiune de focus | `focus_start` |
| `message.draft {to, text, channel}` | **doar ciornă**; trimiți tu de pe telefon | `message_draft` |
| `list.add {list, items}` | adaugă pe o listă (cumpărături etc.) | `list_add` |
| `answer.show {say, title, body}` | un cartonaș pe ecranul rotund + ce spune | `answer_show` |

Fiecare acțiune are un model Pydantic (validare) și o schemă JSON „strictă” (toate câmpurile
obligatorii, fără câmpuri în plus), acceptată la fel de Claude și de OpenAI. `dispatcher.py`
validează, salvează în SQLite (`state.py`) și întoarce confirmarea în română sau engleză. Când
un model greșește argumentele, primește eroarea înapoi ca rezultat de unealtă și se corectează
singur (e testat).

### Cum funcționează fiecare mod

| Mod | Ce se întâmplă când îi zici ceva lui SOUL | Ce trebuie să aibă utilizatorul | Cine plătește AI-ul |
|---|---|---|---|
| **Fără AI** (`none`, implicit) | un parser local RO/EN (`providers/rules.py`) înțelege comenzi simple: „amintește-mi la 5 să sun la bancă”, „pune alarma la 7:30”, „notează: idee breloc”, „remind me at 5 to call the bank”, cronometre, focus, liste, ciorne. Dacă nu e sigur, **întreabă** („La ce oră?”) sau propune „Salvează ca notiță” — nu ghicește. | nimic: fără cont, fără internet | nimeni |
| **Claude** (`claude`) | cu **cheia API Anthropic a utilizatorului**: Claude primește acțiunile ca unelte (tool use) și le cheamă; SOUL spune răspunsul scurt. Fără cheie: parserul local + conectorul (mai jos). | cheie API de la console.anthropic.com **sau** conectorul SOUL adăugat în Claude-ul lui | utilizatorul (factura API) / abonamentul lui Claude pentru conector |
| **ChatGPT** (`chatgpt`) | cu **cheia API OpenAI**: Responses API cu function calling, aceleași acțiuni. Fără cheie: parserul local + aplicația SOUL din ChatGPT. | cheie API OpenAI **sau** aplicația SOUL în ChatGPT | la fel |

Dacă AI-ul cade (cheie greșită, fără net, refuz, limită), SOUL **nu amuțește**: răspunde cu
parserul local și pune motivul în câmpul `note` pentru aplicația de telefon. Dacă apucase să
facă acțiuni înainte de eroare, nu le repetă.

Modelul Claude implicit: `claude-opus-5` (ca în rest), efort `low` pentru răspunsuri vorbite, cu
fallback pe server la refuz. Modelul OpenAI: `SOUL_OPENAI_MODEL` (implicit `gpt-5`; puneți ce ați
testat).

### Ce e onest și ce nu (important pentru site și pentru investitori)

- **Abonamentele de consum Claude Pro/Max și ChatGPT Plus/Pro NU pot fi folosite direct de un
  dispozitiv terț.** Nu există un API „loghează-te cu abonamentul tău” pentru hardware, iar a
  cere parola contului sau a „împrumuta” sesiunea din browser ar încălca termenii și ar fi un risc
  de securitate. Nu facem asta.
- **Căile legitime sunt două, și le avem pe amândouă:**
  1. **Conectorul / aplicația (AI → SOUL).** Utilizatorul adaugă SOUL în Claude-ul lui (conector
     personalizat MCP) sau în ChatGPT (aplicație construită pe MCP). Apoi îi cere lui Claude/ChatGPT
     „pune-mi pe SOUL planul de azi”, iar AI-ul lui cheamă uneltele SOUL. Merge cu abonamentul
     lui, dar **pornește din Claude/ChatGPT**, nu de pe piatră. SOUL nu poate „vorbi” cu
     abonamentul.
  2. **Cheia API proprie (SOUL → AI).** Conversație directă de pe SOUL, text (și voce, prin
     serviciul de voce). Cheia e a utilizatorului, factura e la Anthropic/OpenAI, separată de
     abonament.
- Pentru cine nu vrea nimic din toate astea: **modul fără AI e complet funcțional** pentru
  lucrurile de zi cu zi, și **serviciul de voce SOUL** (abonamentul nostru) e varianta „merge
  din cutie”.
- Pe site, formularea actuală („Add SOUL as a connector in your own Claude”, „Add SOUL as an app
  in your ChatGPT”, „bring your own Anthropic or OpenAI API key”, „in development”) e corectă.
  Nu scrieți „folosește abonamentul tău Claude/ChatGPT pe SOUL”.

### Cheia API proprie („bring your own key”) — `keystore.py`

- Cheia se **criptează la salvare** cu Fernet (AES + HMAC). Cheia de criptare e derivată (HKDF-SHA256)
  dintr-un secret principal, **legată de id-ul dispozitivului și de furnizor**: un rând copiat pe alt
  dispozitiv sau alt furnizor nu se decriptează (testat).
- Secretul principal: `SOUL_MASTER_SECRET` (hex/base64, ≥ 32 octeți — ideal dintr-un KMS sau din
  Keychain/Keystore), altfel un fișier `data/master.key` generat aleator, cu drepturi `0600`.
- Cheia **nu se loghează, nu se întoarce niciodată** prin API (doar „setată / nesetată”), nu apare în
  erorile de validare (le-am curățat) și nu există în clar în baza de date (testat pe fișierul SQLite).
  Se decriptează doar cât durează o cerere, ca să construim clientul.
- **Limita cinstită:** cine are și baza de date, și secretul principal poate decripta. De aceea, în
  producție secretul stă în afara volumului de date. Conform `os/ARCHITECTURE.md` (D5), cheia stă pe
  **telefon** (Keychain/Keystore) și **niciodată pe piatra SOUL**; codul de aici e ce rulează aplicația
  de telefon sau releul cloud SOUL.
- „Testează cheia” face un apel gratuit (lista de modele), nu consumă tokeni.

### Conectorul SOUL pentru Claude (MCP) — `mcp_server.py`

Un server MCP (SDK-ul oficial Python, `mcp` 2.x) cu 5 unelte, toate prin același dispecer:

| Unealtă MCP | Acțiune SOUL | Tip |
|---|---|---|
| `add_note(text, tags?)` | `note.create` | scriere |
| `add_reminder(when, text)` | `reminder.create` | scriere |
| `set_alarm(time, days?, label?)` | `alarm.set` | scriere |
| `show_on_soul(title, body?, say?)` | `answer.show` | scriere |
| `list_today(date?)` | citire din starea dispozitivului | doar citire |

Pornire:

```bash
# local, pentru Claude Desktop / Claude Code (stdio)
SOUL_DEVICE_ID=demo python -m suflet_ai.mcp_server
# HTTP fără autentificare, doar pe loopback (test local); conectorul public e mcp_remote.py, mai jos
SOUL_DEVICE_ID=demo python -m suflet_ai.mcp_server --http --port 8788
```

În Claude Desktop (local), în `claude_desktop_config.json`:

```json
{"mcpServers": {"soul": {"command": "python", "args": ["-m", "suflet_ai.mcp_server"],
  "cwd": "/cale/spre/micul-smecher/ai", "env": {"SOUL_DEVICE_ID": "demo"}}}}
```

În claude.ai: Settings → Connectors → „Add custom connector” → URL-ul public `https://…/mcp`
(disponibil pe planurile care permit conectori personalizați; verificați lista curentă).

`SOUL_DEVICE_ID` e doar pentru prototip, o singură persoană. Conectorul public e `mcp_remote.py`.

### Conectorul public (MCP la distanță + OAuth 2.1) — `mcp_remote.py`

Ce lipește utilizatorul în Claude (Settings → Connectors → *Add custom connector*) sau în ChatGPT
(modul dezvoltator): `https://{BASE}/mcp`. Implementează `docs/07-CONNECT-AI.md` §3.7–3.8:

- OAuth 2.1 pe SDK-ul `mcp` 2.2.0 (`oauth.py`, `SoulOAuthProvider`): `/authorize`, `/token`, `/register`
  (DCR cu reguli stricte pentru redirect URI și nume), `/revoke`, metadate RFC 8414 (+ `iss`, auth `none`)
  și RFC 9728 la `/.well-known/oauth-protected-resource/mcp`, PKCE S256, `iss` la redirect, token de acces
  `sat_` 1 h, refresh `srt_` rotit (90 zile glisant, fereastră de grație 60 s, revocarea familiei la reluare).
- Pagini RO/EN (CSRF, `frame-ancestors 'none'`): conectare cu cod pe email (`accounts.py`), apoi consimțământ:
  alegi SOUL-ul sau scrii codul de împerechere de pe ecran (SOUL cere apoi ✓ pe dispozitiv), bifezi ce poate
  face aplicația. Aplicațiile din afara listei verificate (claude.ai, chatgpt.com) cer bifă explicită și
  re-autentificare.
- Cele 7 unelte (`list_today`, `read_soul_inbox`, `add_note`, `add_reminder`, `set_alarm`, `show_on_soul`,
  `answer_soul`) ajung pe dispozitiv prin `gateway.py` (push + ack în 3 s); fiecare apel re-verifică grantul,
  proprietarul și „pauză conectori”; erorile încep cu un cod stabil (`read_only_grant`, `notes_scope_off`, …).

```bash
SOUL_PUBLIC_HOST=soul.example python -m suflet_ai.mcp_remote --port 8788   # dev: + rutele /v1/device/*
```

Teste: `tests/test_connector_remote.py` (tot dansul OAuth cu clientul MCP oficial), `test_connector_tools.py`,
`test_connector_gateway.py` (dispozitiv simulat cu cheie ECDSA prin gateway-ul real), `test_oauth_accounts.py`.

### Aceleași unelte ca aplicație în ChatGPT (Apps SDK)

- Aplicațiile ChatGPT (Apps SDK) sunt construite **pe MCP**, deci **același server** (`/mcp`, HTTP)
  e baza aplicației SOUL din ChatGPT. Uneltele și schemele rămân identice.
- Adnotările contează: `list_today` e marcată `readOnlyHint`, celelalte ca scrieri nedistructive —
  ChatGPT cere confirmarea utilizatorului pentru scrieri.
- Opțional, un mic widget (cartonașul SOUL randat în chat) se adaugă ca resursă HTML legată de
  unealtă, conform Apps SDK; nu e necesar pentru v1. Verificați documentația Apps SDK curentă
  pentru cheile exacte de metadate.
- Pentru testare: modul dezvoltator din ChatGPT (conectare la URL-ul MCP). Pentru toți utilizatorii:
  trimitere spre **review la OpenAI** (politici, confidențialitate, OAuth). De planificat în 0.6.
- Separat, modul `chatgpt` cu cheie API (Responses API + function calling) folosește aceleași
  acțiuni, ca unelte `function` stricte.

### Endpointuri noi (dispozitiv + aplicația de telefon)

Toate cer `Authorization: Bearer <SUFLET_API_TOKEN>`.

| Endpoint | Ce face |
|---|---|
| `POST /v1/ask` `{device_id, text, lang?}` | text → `{say, face, card, chips, actions, provider, mode, note}`, în orice mod |
| `POST /v1/action` `{device_id, name, args, lang?}` | rulează direct o acțiune (UI-ul telefonului, tastatura de pe SOUL) |
| `GET /v1/actions` | catalogul de acțiuni cu schemele JSON |
| `GET/POST /v1/mode` `{device_id, mode: none\|claude\|chatgpt, lang?}` | modul AI + ruta efectivă (`offline`, `offline+connector`, `direct-api`) |
| `POST /v1/key` `{device_id, provider: anthropic\|openai, api_key}` | salvează cheia criptată; răspunsul spune doar „setată” |
| `POST /v1/key/test` `{device_id, provider, api_key?}` | verifică o cheie (cea nouă sau cea salvată) |
| `GET /v1/key?device_id=` · `DELETE /v1/key?device_id=&provider=` | stare / ștergere |
| `GET /v1/today`, `GET /v1/sync?since=`, `GET /v1/due` | ce e azi, ce e nou de la ultimul id, mementourile scadente (o singură dată) |

### Fișiere

`actions.py` (acțiuni + scheme) · `state.py` (SQLite: elemente, setări, chei criptate) ·
`dispatcher.py` (validare + confirmări RO/EN) · `providers/rules.py` (fără AI) ·
`providers/claude.py` (Anthropic, tool use) · `providers/chatgpt.py` (OpenAI Responses) ·
`keystore.py` (BYOK) · `soul.py` (alegerea modului, fallback) · `mcp_server.py` (conectorul) ·
`server.py` (HTTP) · `tests/test_soul.py` (40 de teste noi, clienți simulați).

### SOUL Cloud, partea dispozitivului — `devices.py`, `gateway.py`, `relay.py`

Contractul e `docs/07-CONNECT-AI.md` §3.2, §3.4, §3.9–3.10 și §6. Rutele de dispozitiv **nu** folosesc
`SUFLET_API_TOKEN`: SOUL se autentifică cu propria cheie ECDSA P-256 (provocare semnată
`soul-auth-v1\n{host}\n{device_id}\n{nonce}`) și primește un token `sdt_` de 24 h.

| Rută | Ce face |
|---|---|
| `GET /v1/ping` | test de internet pentru portalul Wi-Fi (fără autentificare) |
| `POST /v1/device/challenge` · `POST /v1/device/auth` | nonce (60 s, o dată, legat de rețea) → token `sdt_` |
| `GET /v1/device/ws` (subprotocol `soul.v1`) | hello/welcome, push + ack, replay pe pagini, `ask` → `reply`, coduri 4400/4401/4403/4409/4426/4429 |
| `GET /v1/device/poll` · `POST /v1/device/send` | același protocol prin long-poll (și trezirile din somn adânc) |
| `/v1/dev/pair/claim`, `/v1/dev/push`, `/v1/dev/unpair`, `/v1/dev/config` | doar dev / self-host, cu `SUFLET_API_TOKEN`; oprite la `SOUL_ENV=production` |

- `devices.py`: identitate, înrolare (`SOUL_ENROL_POLICY=factory` în producție, `pending` doar dev/P0),
  coduri de asociere de 8 caractere (stocate ca HMAC), confirmare obligatorie pe ecranul SOUL,
  outbox per dispozitiv cu `seq` fără goluri.
- `relay.py`: răspunde la `ask` — creier A (cheia SOUL, `SOUL_ANTHROPIC_KEY` / `SOUL_OPENAI_KEY`, contorizat:
  probă pentru unitățile din fabrică, alocație lunară după asociere), B2 (cheia proprietarului din keystore,
  plafon zilnic), E (reguli offline). Modelul implicit `claude-haiku-4-5` (fără `effort`), OpenAI `gpt-6-luna`.
- Variabile: `SOUL_PUBLIC_HOST`, `SOUL_ENROL_POLICY`, `SOUL_ID_PEPPER`, `SOUL_GATEWAY_DB`, `SOUL_TRIAL_TURNS`,
  `SOUL_ALLOWANCE_TURNS`, `SOUL_B2_DAILY_CAP_MICRO`, `SOUL_BRAIN_A_KILL`, `SOUL_CLAUDE_MODEL`,
  `SOUL_OPENAI_RELAY_MODEL`. Rulați uvicorn cu `--ws-ping-interval 25 --ws-ping-timeout 45`.

Un SOUL simulat, pentru teste cap-coadă (asociere, socket, o întrebare, push-uri):

```bash
SUFLET_API_TOKEN=dev SOUL_PUBLIC_HOST=soul.example uvicorn suflet_ai.server:app --port 8787
python tools/fake_device.py --base http://127.0.0.1:8787 --claim --api-token dev --confirm yes \
    --ask "amintește-mi mâine la 9 să sun la bancă" --listen 10
python tools/fake_device.py --base http://127.0.0.1:8787 --poll --ask "notează lapte"   # long-poll
```

Teste: `tests/test_gateway_devices.py`, `test_gateway_ws.py`, `test_gateway_relay.py`, `test_fake_device.py`;
vectorul de test comun cu firmware-ul: `tests/vectors/device_auth.json`.
