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
  2. **Cheia API proprie (SOUL → AI).** Conversație directă de pe SOUL, **text**. Cheia e a
     utilizatorului, factura e la Anthropic/OpenAI, separată de abonament. **Vocea:** nu există
     încă un serviciu de voce SOUL în cloud (e planificat pentru Faza 2, `docs/07-CONNECT-AI.md` §5).
     Azi, vorbitul la SOUL există doar pe varianta cu microfon, prin cheia OpenAI de pe dispozitiv
     (B1, `gpt-transcribe` [U]); cine are doar o cheie Claude nu are recunoaștere de voce (Anthropic
     nu are API de voce).
- Pentru cine nu vrea nimic din toate astea: **modul fără AI e complet funcțional** pentru
  lucrurile de zi cu zi. Varianta „merge din cutie” cu AI e creierul A (Claude în SOUL, prin
  SOUL Cloud), deocamdată doar în cloud și testată doar cu un dispozitiv simulat.
- **Site-ul:** regula din `docs/07-CONNECT-AI.md` (§1.4, §5) e: **nicio afirmație „works with
  ChatGPT” / „connect your ChatGPT”** până când SOUL nu e plugin listat în ChatGPT (developer mode
  e doar pe web, scrierile pe Plus/Pro sunt [U], Free nu e suportat). Fraza de acum de pe site
  (`site/index.html`: „For AI, you connect the Claude or ChatGPT you already have”) **trebuie
  corectată** (de ex. „you connect the Claude you already have; ChatGPT later”). Nu scrieți nici
  „folosește abonamentul tău Claude/ChatGPT pe SOUL”.

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
  producție secretul stă în afara volumului de date. Nu e criptare cu KMS (aceea e planificată,
  `docs/07-CONNECT-AI.md` §1.3).
- **Unde stă cheia, de fapt** (`docs/07-CONNECT-AI.md` §1.8 înlocuiește D5 din `os/ARCHITECTURE.md`,
  care spunea „pe telefon, niciodată pe SOUL”):
  - **B1, pe dispozitiv:** în flash-ul SOUL (NVS, spațiul `soulkey`), **necriptată** dacă build-ul nu
    are criptare de flash + NVS;
  - **B2, în SOUL Cloud:** în acest keystore (opțional, la alegerea utilizatorului; azi doar prin ruta
    dev `/v1/dev/key`, pagina `/me/keys` nu există);
  - **telefonul nu ține nimic azi** (nu există aplicație de telefon).
- Keystore-ul refuză prefixele de chei de admin și de tokenuri de abonament (`sk-ant-admin` [V],
  `sk-ant-oat` [U], `sk-admin-` [U]).
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
| `/v1/dev/pair/claim`, `/v1/dev/push`, `/v1/dev/unpair`, `/v1/dev/config`, `/v1/dev/key` | doar dev / self-host, cu `SUFLET_API_TOKEN`; nu există la `SOUL_ENV=production` sau `pilot` (`/v1/dev/key` ține locul paginii `/me/keys` pentru B2) |

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

### Totul cap-coadă, local (fără chei reale) — `app.py`, `tools/e2e_demo.sh`

`suflet_ai/app.py` e aplicația care merge pe internet: partea dispozitivului (`gateway.py` + releul) și
conectorul (`mcp_remote.py` + OAuth) într-un singur proces, cu un singur `SoulService` și o singură
durată de viață (lifespan-ul MCP e transmis). `server.py` (tokenul comun vechi) **nu** e montat aici.

```bash
tools/e2e_demo.sh          # pornește un LLM fals, aplicația și un SOUL fals; ieșire 0 = tot e verde
```

Ce verifică (pe socketuri reale, `127.0.0.1`):

1. `tools/fake_device.py` (CLI) se autentifică cu cheia ECDSA, arată codul, e asociat, întreabă, primește push-ul.
2. `tools/e2e_connect.py` e un client MCP SDK (redirect loopback, ca Claude Code; **nu** e claude.ai și
   trece pe ramura de consimțământ pentru clienți neverificați): 401 → metadate → DCR → PKCE →
   cod pe email → codul de pe ecranul SOUL pe pagina de consimțământ → ✓ pe SOUL → *Allow* → token; apoi
   `add_note`, `add_reminder`, `set_alarm`, `show_on_soul`, `list_today` ajung pe socketul dispozitivului
   (`delivered: "shown"`).
3. Întrebări scrise pe SOUL → releu → Claude fals și OpenAI fals → răspuns + push-uri; alocația lunară scade
   cu 1 la fiecare tură, iar la 0 răspund regulile offline cu `note: "allowance"`.
4. Erorile au codurile din §6.9: cheie greșită `bad_key`, 429 `rate_limited`, fără credit `quota`, furnizor
   căzut `network`; SOUL offline → `delivered: "queued"`, apoi reluat la reconectare.

**Ce acoperă, cinstit:** o variantă **simulată** a pașilor 3, 5 și 7 din `docs/07-CONNECT-AI.md` §0.1.
Dispozitivul (`fake_device.py`) și modelele (`fake_llm.py`) sunt scrise de noi; pasul 4 (`/pair`) și pasul 6
(`/me`) nu există în cod; asocierea trece prin pagina de consimțământ a conectorului sau prin ruta dev
`/v1/dev/pair/claim`. Criteriul de ieșire din Faza 0 **nu** e îndeplinit până nu există `/pair` și `/me` și
nu rulează prin redirect-ul claude.ai.

`tools/fake_llm.py` imită `api.anthropic.com` (`/v1/messages`) și `api.openai.com` (`/v1/responses`);
SDK-urile oficiale sunt îndreptate spre el cu `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL`, deci codul releului
e cel din producție. Testele: `tests/test_e2e_connect.py` (aceeași poveste, plus verificările de pornire în
producție, mailerul SMTP, importul cheilor din fabrică și fișierele de deploy).

### Go live in 20 minutes

Ținta: SOUL Cloud pe Fly.io, în UE (Frankfurt), cu adresa `https://<host>/mcp` pe care o lipești în Claude.

> **Citește întâi limita:** după acești pași **un SOUL real încă nu se poate conecta** (firmware-ul de azi
> vorbește protocolul rev. 1 și nu se poate autentifica; pagina `/pair` nu există). Pasul 5 merge azi doar
> cu dispozitivul simulat `tools/fake_device.py` îndreptat spre `https://<host>` (pilot, înrolare `pending`).
> Nimic nu a fost încercat încă cu claude.ai real [U]. Detalii în „Ce nu merge încă”, mai jos.
Fișiere: `Dockerfile`, `docker-entrypoint.sh`, `fly.toml`, `constraints.txt` (versiunile testate).
Nimic secret nu intră în repo: secretele merg doar în `fly secrets`.

**Ce trebuie să existe înainte** (nu intră în cele 20 de minute): cont Fly.io + `flyctl`; un furnizor de
email tranzacțional din UE cu SPF/DKIM/DMARC pe domeniul expeditorului (codurile de conectare pleacă pe email;
fără el nimeni nu se poate conecta); opțional un domeniu propriu.

1. **Cheile (5 min).** Anthropic: în Console → *API Keys* creezi o cheie într-un workspace dedicat SOUL, cu
   **limită lunară de cheltuieli** și fără expirare. OpenAI (doar dacă vrei vocea ChatGPT pentru creierul A):
   o cheie de proiect, cu limită de buget. Numele exacte ale meniurilor nu le-am verificat azi [U].
2. **Secretele (1 min)**, generate local, niciodată în fișiere din repo:
   `python3 -c "import secrets; print(secrets.token_hex(32))"` de două ori (master secret și pepper).
3. **Configurarea (3 min).** În `fly.toml`: `app`, `SOUL_PUBLIC_HOST` (`<app>.fly.dev` sau domeniul tău),
   `SOUL_SMTP_HOST`, `SOUL_SMTP_USER`, `SOUL_MAIL_FROM`. Lasă `SOUL_ENV = "pilot"` până există lista de chei
   din fabrică (vezi mai jos).
4. **Deploy (8 min).**
   ```bash
   cd micul-smecher/ai
   tools/e2e_demo.sh                                   # înainte: totul verde local
   fly launch --no-deploy --copy-config --name <app>
   fly volumes create soul_data --region fra --size 1
   # secretele se citesc fără ecou, ca să nu rămână în istoricul shell-ului
   for v in SOUL_MASTER_SECRET SOUL_ID_PEPPER SOUL_ANTHROPIC_KEY SOUL_OPENAI_KEY SOUL_SMTP_PASSWORD; do
     read -rsp "$v: " val; echo; printf '%s=%s\n' "$v" "$val"; done | fly secrets import
   fly deploy
   curl https://<host>/healthz                         # {"ok": true, ...}
   curl https://<host>/.well-known/oauth-protected-resource/mcp
   fly ssh console -C "python -m suflet_ai.app check"  # regulile de pornire
   ```
   Cu domeniu propriu: `fly certs add <domeniu>` și înregistrările DNS pe care le cere Fly.
5. **Claude (2 min) — azi doar cu dispozitivul simulat.** Pornește întâi un SOUL fals spre cloud:
   `python tools/fake_device.py --base https://<host> --host <host> --key soul-test.pem --confirm yes --listen 600`
   (pilot, înrolare `pending`); un SOUL real are nevoie de firmware rev. 2. Apoi claude.ai →
   *Customize → Connectors → Add custom connector* → URL `https://<host>/mcp` → *Connect*; dacă dialogul
   întreabă cum se înregistrează aplicația, alege **„Register automatically”** (SOUL nu are încă CIMD, deci
   „Use Claude's published identity” probabil nu merge [U]) → codul primit pe email → codul de pe ecranul
   SOUL-ului (fals) → ✓ → *Allow*. Apoi scrii în Claude: „Show hello on my SOUL”. **Netestat încă cu
   claude.ai real [U].** Ce e verificat [V, 2 oct 2026, `docs/07-CONNECT-AI.md` §1.4] e doar partea
   Anthropic: calea din meniu (interfețe mai vechi: *Settings → Connectors*) și faptul că conectorii
   personalizați există pe toate planurile Claude, inclusiv Free (unul singur); adăugarea doar de pe
   telefon e beta și netestată de noi [U].
6. **ChatGPT (doar utilizatori avansați).** chatgpt.com (web) → *Settings → Security and login → Developer
   mode* → adaugi URL-ul care se termină în `/mcp` [V]. Fiecare scriere cere confirmare în ChatGPT [V];
   scrierile pe Plus/Pro sunt [U]. Pentru toți utilizatorii trebuie listare ca plugin ChatGPT (review OpenAI).

**`pilot` vs `production`.** Ambele refuză pornirea dacă lipsește ceva din §3.0 (`SUFLET_API_TOKEN` setat,
`SOUL_MASTER_SECRET`, `SOUL_ID_PEPPER`, `SOUL_PUBLIC_HOST`, SMTP, https). `pilot` permite în plus
`SOUL_ENROL_POLICY=pending`: o cheie nouă de dispozitiv e acceptată **doar cât timp SOUL-ul nu e asociat** și
nu are cheie din fabrică; cine asociază primul un `device_id` liber îl deține (codul e pe ecran, confirmarea e
o atingere). După asociere, chei noi pentru același `device_id` primesc `403 not_enrolled`, iar orice token
al altei chei decât cea legată e refuzat (nu vede push-uri, nu confirmă, nu întreabă, nu dă jos socketul).
Tot doar pentru testeri cunoscuți, pe un host nepublicat. `production` cere `factory`: cheile publice din fabrică se
importă cu `fly ssh console -C "python -m suflet_ai.app import-factory /data/keys.csv"` (CSV cu antetul
`device_id,pub`).

**Ce nu merge încă după deploy (onest):**

- Firmware-ul actual încă se autentifică cu secretul vechi (fără provocare ECDSA, cod de 6 cifre), deci un
  SOUL real **nu** se conectează la acest cloud până nu e actualizat la rev. 2 (vectorul comun:
  `tests/vectors/device_auth.json`).
- Pagina `/pair` (QR-ul de pe ecran duce acolo) și paginile de cont `/me` (chei B2, alegerea creierului,
  lista aplicațiilor conectate) nu există încă (`api_me.py`). Azi asocierea se face pe pagina de consimțământ
  a conectorului, cu codul de pe ecran; creierul implicit după asociere e A (cheia SOUL, vocea Claude).
- Un singur proces, SQLite pe volum: nu porni mai multe mașini (`fly scale count 1`).
- CIMD (`cimd.py`) nu e scris. Că claude.ai merge prin DCR („Register automatically”) e o presupunere [U]:
  dialogul Claude recomandă CIMD („Use Claude's published identity”) și nu știm dacă trece singur pe DCR.
  De construit `cimd.py` sau de verificat pe claude.ai real (web, Desktop, mobil) înainte de un pilot public.
  Nimic nu a fost încercat cu claude.ai sau ChatGPT reale și nici cu cheile reale Anthropic/OpenAI.

**Variabile de mediu** (lista completă: `python -m suflet_ai.app env`):

| Variabilă | Secret | Ce face |
|---|---|---|
| `SOUL_ENV` | | `production` / `pilot` pornesc verificările; altceva = dev |
| `SOUL_PUBLIC_HOST` | | host-ul public (fără schemă); emitentul OAuth e `https://{host}`, dispozitivele semnează pentru el |
| `SOUL_DATA_DIR` | | directorul cu SQLite (volumul, `/data`) |
| `SOUL_ENROL_POLICY` | | `factory` în producție, `pending` în pilot/dev |
| `SOUL_TRUST_PROXY` | | `1` în spatele proxy-ului TLS (IP-ul clientului = ultimul hop din `X-Forwarded-For`) |
| `SOUL_MASTER_SECRET` | da | ≥ 32 octeți hex; criptează cheile API ale utilizatorilor (B2) |
| `SOUL_ID_PEPPER` | da | ≥ 32 octeți hex; HMAC pentru id-uri, coduri, `safety_identifier` |
| `SOUL_ANTHROPIC_KEY` | da | cheia SOUL pentru creierul A (Claude în SOUL) |
| `SOUL_OPENAI_KEY` | da | cheia SOUL pentru creierul A cu vocea ChatGPT |
| `SOUL_SMTP_HOST`, `SOUL_SMTP_PORT`, `SOUL_SMTP_USER` | | serverul de email (STARTTLS pe 587 sau TLS pe 465) |
| `SOUL_SMTP_PASSWORD` | da | parola / tokenul SMTP |
| `SOUL_MAIL_FROM` | | expeditorul, ex. `SOUL <hello@domeniu>` |
| `SOUL_CLAUDE_MODEL`, `SOUL_OPENAI_RELAY_MODEL` | | modelele releului (implicit `claude-haiku-4-5`, `gpt-6-luna`) |
| `SOUL_ALLOWANCE_TURNS`, `SOUL_TRIAL_TURNS`, `SOUL_B2_DAILY_CAP_MICRO`, `SOUL_BRAIN_A_KILL` | | contorizare (300 ture/lună, 30 ture probă, 0,50 $/zi pe cheia proprie, oprire de urgență) [E] |
| `SUFLET_TZ` | | fusul orar al serverului (implicit `Europe/Bucharest`); orele itemelor de pe un SOUL folosesc fusul **dispozitivului** (`devices.tz`), nu pe acesta |
| `SUFLET_API_TOKEN`, `SOUL_PUBLIC_SCHEME`, `SOUL_DEV_MAILBOX` | | doar dev (rutele `/v1/dev/*`, `http` pe loopback, emailuri într-un fișier); interzise în pilot/producție |
