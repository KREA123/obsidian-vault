"""The phone pages: /pair and /me (docs/07-CONNECT-AI.md §0.1 steps 4 and 6, §3.4, §3.5).

    GET  /pair                      the pairing QR lands here (`#c=CODE&d=soul-…` in the fragment, read by JS only:
                                    GET never claims anything). Not signed in: "Continue with email" -> /login.
    POST /pair/claim                form: code -> pair.confirm on SOUL -> /pair/wait?pid=…
    GET  /pair/wait                 "Tap Yes on SOUL" (JS polls /v1/me/pair/{pid}; without JS: a button)
    GET  /pair/brain?d=soul-…       after the tap (no AI paid by SOUL, founder decisions of 3 Oct 2026):
                                      first and biggest: "Connect your Claude account" — 1. sign in at the Anthropic
                                        Console, 2. create a key named SOUL (+ a monthly spend limit), 3. paste it:
                                        live check (models.list), brain `claude`, a "Claude connected" card on SOUL
                                      then: Connect my ChatGPT (Sign in with ChatGPT: stub, pending OpenAI approval;
                                        meanwhile the ChatGPT connector steps) · my own OpenAI key · the Claude app
                                        connector (step by step + the address to copy) · Offline (no AI)
                                    SOUL Cloud's built-in AI (brain A) appears only with SOUL_BUILTIN_AI=1.
    POST /v1/me/pair/claim          JSON (session + X-CSRF-Token), §3.4: 202 {pid, device, state, expires_in}
    GET  /v1/me/pair/{pid}          JSON {state: awaiting_device | paired | rejected | expired}
    GET  /me                        devices (online, brain, firmware), keys (masked), connected apps, revoke
    GET  /me/connect-claude, /me/connect-chatgpt   the connector, step by step, with a copy button
    POST /me/devices/{id}/brain     cloud | claude | chatgpt | none (claude/chatgpt need a stored key)
    POST /me/devices/{id}/unpair    fresh sign-in required; revokes the SOUL's connector grants
    POST /me/keys                   provider + key (+ device to switch): fresh sign-in required, prefix rules,
                                    live check (GET /v1/models: free) -> verified / unverified / refused
    POST /me/keys/{provider}/delete
    POST /me/grants/{id}/revoke     disconnect an app (its whole token family)
    POST /me/logout
    GET  /me/signin-chatgpt         "Connect my ChatGPT": stub ("coming soon, pending OpenAI approval") + the
                                    ChatGPT connector steps meanwhile (§1.10)
    POST /me/devices/{id}/bridge    SOUL Bridge (docs/08): a one-time code + the `soul-bridge pair` command
    POST /me/bridge/{id}/revoke     forget a paired computer (its bridge token dies, a connected bridge is closed)
    GET  /me/wifi-help              public: how to put SOUL back on Wi-Fi (the §6.13 messages and what to do)
    GET  /me/export, /v1/me/export  GDPR: everything about the account as one JSON download (no secrets)
    GET/POST /me/delete, DELETE /v1/me   GDPR erasure (fresh sign-in; the form wants DELETE / STERGE typed)

Rules kept: every page has the security headers; every POST checks CSRF (double submit); every device id is
checked against the signed-in account; keys are never shown back (masked: first 7 + "…" + last 4), never logged.
RO/EN from the account (or ?lang / Accept-Language before sign-in). Mobile first, SOUL brand (cream / ink,
Bricolage Grotesque, Martian Mono for codes), no external requests (CSP default-src 'self').
"""
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from jinja2 import DictLoader, Environment, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from .config import builtin_ai_enabled, default_brain
from .accounts import AuthError, Session, clear_session_cookies, ensure_csrf_cookie, require_csrf

log = logging.getLogger("suflet_ai.web_me")

WEB = Path(__file__).resolve().parent / "web"
BRAINS = ("cloud", "claude", "chatgpt", "bridge", "none")


def brain_choices() -> tuple:
    """What the owner may pick. No AI paid by SOUL by default: "cloud" only with SOUL_BUILTIN_AI=1."""
    return BRAINS if builtin_ai_enabled() else ("claude", "chatgpt", "bridge", "none")
PROVIDER_OF = {"claude": "anthropic", "chatgpt": "openai"}
_PID = re.compile(r"^p_[A-Za-z0-9_-]{4,40}$")
_DEV = re.compile(r"^soul-[0-9a-f]{12}$")
_KEY_CHECKS = """
CREATE TABLE IF NOT EXISTS key_checks (
    account_id TEXT NOT NULL, provider TEXT NOT NULL, verified INTEGER NOT NULL, checked INTEGER NOT NULL,
    PRIMARY KEY (account_id, provider)
);
"""


# ============================================================ key checks ==

def check_key_live(provider: str, key: str, timeout: float = 5.0) -> str:
    """One free call with the user's key: GET /v1/models. -> "ok" | "bad" | "unverified".

    "bad" only on 401 / 403 (the provider says the key is wrong). Anything else (no network, 5xx, a proxy
    in the way, SOUL_KEY_CHECK=0) leaves the key saved but marked unverified. Never logs the key."""
    if os.environ.get("SOUL_KEY_CHECK", "1") == "0":
        return "unverified"
    import httpx

    try:
        if provider == "anthropic":
            base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
            r = httpx.get(base + "/v1/models", headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                          timeout=timeout)
        else:
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            r = httpx.get(base + "/models", headers={"authorization": f"Bearer {key}"}, timeout=timeout)
    except Exception as e:  # noqa: BLE001 - no network is not the user's fault
        log.info("key check for %s not possible: %s", provider, type(e).__name__)
        return "unverified"
    if r.status_code == 200:
        return "ok"
    if r.status_code in (401, 403):
        return "bad"
    return "unverified"


def mask_key(k: Optional[str]) -> str:
    if not k:
        return ""
    return f"{k[:7]}…{k[-4:]}" if len(k) > 14 else "…"


# ================================================================== text ==

_T: Dict[str, Dict[str, str]] = {
    "en": dict(
        pair_title="Pair your SOUL", pair_lead="Connect this SOUL to your account. It takes a minute.",
        continue_email="Continue with email", signed_in_as="Signed in as", code_label="The code on SOUL's screen",
        code_hint="8 letters and digits, like 7KQ3-M9XD", pair_btn="Pair", not_you="Not you? Sign out",
        wait_title="Look at your SOUL", wait_lead="SOUL asks “Pair with {name}?”. Tap <b>Yes, pair</b> on its screen.",
        wait_again="I tapped it", wait_note="Only a touch on SOUL can say yes. This page updates by itself.",
        rejected="SOUL said no. If that was not you, nothing happened. Scan the new code to try again.",
        expired="The request expired. SOUL shows a new code: scan it again.",
        brain_title="Who answers on SOUL?", brain_lead="When you ask SOUL something on its screen, who should answer?",
        b_cloud="SOUL Cloud", b_cloud_sub="Claude inside SOUL. Included, nothing to set up. Not your claude.ai account.",
        b_key="My own API key", b_key_sub="Anthropic or OpenAI. Billed to you, per question. Stored encrypted.",
        ca_title="Connect your Claude account", ca_lead="Three steps, about two minutes. Then you talk to Claude on SOUL.",
        ca_s1="Sign in to your Claude account at the Anthropic Console", ca_s1_btn="Open the Anthropic Console",
        ca_s1_note="Same Anthropic login as Claude; “Continue with Google” works.",
        ca_s2="Create a key named SOUL",
        ca_s2_shot="In the Console: <b>API keys</b> → <b>Create key</b> → name it <b>SOUL</b> → <b>Add</b> → "
                   "<b>Copy</b> the key (it starts with <code>sk-ant-</code>; it is shown only once).",
        ca_s2_btn="Go to API keys", ca_s2_limit="Tip: set a monthly spend limit, e.g. <b>$5</b>, so SOUL can never "
        "cost more.", ca_limits="Limits", ca_s3="Paste the key here",
        ca_btn="Connect Claude", ca_honest="Uses your Anthropic account (pay as you go, ~$1/month typical) — Claude "
        "Pro/Max subscriptions can't be used by other companies' devices.",
        other_ways="Other ways", b_oai="My own OpenAI key", b_oai_sub="ChatGPT's models on SOUL, billed to your "
        "OpenAI account, per question. Stored encrypted.", claude_connected="Claude connected",
        claude_connected_body="Ask me anything: I answer with your Claude.",
        b_chatgpt="Connect my ChatGPT", b_chatgpt_sub="Sign in with your ChatGPT account so SOUL can talk to "
        "your ChatGPT. Until then, your ChatGPT can put things on SOUL through the SOUL app (connector).",
        soon="Coming soon, pending OpenAI's approval.",
        b_claude="The Claude app connector", b_claude_sub="Command SOUL from the Claude app: Claude puts notes, "
        "reminders, alarms and cards on SOUL. Works with any Claude plan; you can add it as well as your key.",
        b_none="Offline (no AI)", b_none_sub="Alarms, timers, reminders and notes work on SOUL itself; nothing "
        "leaves the house.", opt_key="Optional: your Anthropic API key, to talk to Claude on SOUL itself",
        b_app="My own Claude or ChatGPT app",
        b_app_sub="Your Claude puts notes, reminders and alarms on SOUL. SOUL's own questions use the offline rules "
                  "(you can turn SOUL Cloud on any time).",
        choose="Choose", provider="Provider", api_key="API key", save_key="Save key and use it",
        key_advice="Use a dedicated key with a monthly spend limit and no expiry. SOUL never shows it back.",
        me_title="Your SOUL", devices="Your SOULs", no_devices="No SOUL yet.", pair_one="Pair a SOUL",
        online="online", offline="offline", brain="Answers", fw="firmware", last_seen="last seen",
        paused="Claude & co. paused on SOUL", keys="Your API keys", not_set="not set", verified="checked",
        unverified="saved, not checked yet", remove="Remove", apps="Connected apps", no_apps="No app connected yet.",
        revoke="Disconnect", connect_claude="Connect your Claude", connect_chatgpt="Connect ChatGPT (advanced)",
        sign_out="Sign out", unpair="Unpair this SOUL", sign_in_first="Sign in to see your SOUL.",
        sign_in="Sign in", copy="Copy", copied="Copied", conn_addr="Connector address",
        claude_title="Connect your Claude to SOUL",
        claude_steps="<li>Open <b>claude.ai</b> on a computer (or the Claude app) and sign in.</li>"
                     "<li>Go to <b>Settings → Connectors</b> (on some plans: <b>Customize → Connectors</b>) and choose "
                     "<b>Add custom connector</b>.</li><li>Name it <b>SOUL</b> and paste the address below.</li>"
                     "<li>If Claude asks how to register, either choice works (<b>Use Claude's published identity</b> or "
                     "<b>Register automatically</b>).</li>"
                     "<li>Click <b>Connect</b>. Sign in to SOUL with your email code and tap <b>Allow</b>.</li>"
                     "<li>In a chat, type: <i>Show hello on my SOUL</i>. SOUL shows “Claude connected”.</li>",
        claude_plans="Every Claude plan can add one custom connector (Free: one). Work account? Ask your Claude admin "
                     "to add it for the organisation. Adding it from a phone alone is in beta: a computer is easiest.",
        chatgpt_title="Connect ChatGPT to SOUL (advanced)",
        chatgpt_steps="<li>On <b>chatgpt.com</b> (web): <b>Settings → Security and login → Developer mode</b>.</li>"
                      "<li>Add an app with the address below (it ends in <code>/mcp</code>).</li>"
                      "<li>Sign in to SOUL with your email code and tap <b>Allow</b>.</li>"
                      "<li>ChatGPT asks you to confirm every change it makes on SOUL.</li>",
        chatgpt_note="SOUL is not a listed ChatGPT app yet; developer mode is for people comfortable with it.",
        siwc_title="Connect my ChatGPT", siwc_body="Coming soon, pending OpenAI's approval. “Sign in with ChatGPT” "
        "is open only to approved apps (waitlist). When SOUL is approved you will sign in here, in your browser; your "
        "password and tokens stay between your browser, OpenAI and SOUL Cloud, never on the device. Meanwhile, "
        "your ChatGPT can already put things on SOUL:",
        back_me="Back to your SOUL", done_cloud="Done. SOUL answers with Claude inside SOUL.",
        done_key="Done. SOUL answers with your own key.", done_none="Done. SOUL uses its offline rules.",
        bad_code="That code is not valid. Check the screen (8 characters).",
        code_expired="That code expired; SOUL shows a new one.",
        device_owned="This SOUL belongs to another account. Ask its owner to release it.",
        rate="Too many tries. Wait a little and try again.", forbidden="That is not one of your SOULs.",
        need_key="Add a key for that provider first.", key_bad="The provider says this key does not work.",
        key_refused="That is not a standard API key (admin keys and subscription tokens are refused).",
        reauth="For your safety, confirm it is you with a new email code first.", expired_form="The form expired. Try again.",
        trial="free answers left before pairing", allowance="answers left this month",
        b_bridge="My Claude on my computer", b_bridge_sub="Your own Claude Code (Pro/Max), signed in by you on your "
        "computer, answers what you ask on SOUL. Experimental: the computer must be on with Start SOUL open.",
        computers="Your computers (SOUL Bridge)", no_computers="No computer paired yet.",
        add_computer="Pair a computer", forget="Forget", br_online="connected", br_offline="not connected",
        br_title="Pair a computer with SOUL", br_lead="On the computer where you use Claude Code, run:",
        br_steps="<li>Install Node.js 20+ and Claude Code, then run <code>claude</code> once and sign in to "
                 "<b>your own</b> Claude account (SOUL never sees it).</li>"
                 "<li><code>npm install -g soul-bridge</code></li>"
                 "<li>Run the command below (the code works once, for 5 minutes).</li>"
                 "<li><code>soul-bridge setup</code>, then double-click <b>Start SOUL</b> and keep its window open.</li>",
        br_note="The code is the same kind SOUL shows under Settings › AI › My Claude on my computer.",
        export="Download my data", export_sub="Everything SOUL Cloud keeps about you, as one JSON file "
        "(keys and tokens are never included).",
        delete_title="Delete my account", delete_sub="Unpairs every SOUL and erases its data in SOUL Cloud, "
        "disconnects every app and computer, removes your keys, then your account. This cannot be undone.",
        delete_confirm="Type DELETE to confirm", delete_btn="Delete my account for good",
        delete_word="DELETE", deleted="Your account and its data are gone. Your SOUL keeps working offline; "
        "pair it again any time.", delete_typo="Type the word exactly to confirm.",
        erase_too="Also erase this SOUL's data in SOUL Cloud",
        wifi_title="SOUL lost its Wi-Fi?", wifi_lead="SOUL keeps your alarms and notes without the internet. "
        "To join it to a network again:",
        wifi_steps="<li>Hold SOUL's side button for <b>5 seconds</b> (or <b>Settings › Wi-Fi</b> on SOUL). Its "
                   "screen shows a Wi-Fi QR code and the network name <b>SOUL-xxxx</b>.</li>"
                   "<li>Scan the QR with your phone's camera (or join <b>SOUL-xxxx</b> with the password on the "
                   "screen). The setup page opens; if it does not, open <b>http://192.168.4.1</b>.</li>"
                   "<li>Pick your home network, type its password, tap <b>Connect</b>. SOUL tests it and says what "
                   "happened, on the page and on its screen.</li>",
        wifi_errors="If it says…", wifi_e1="“Network not found”", wifi_e1b="Is your Wi-Fi 5 GHz only? SOUL needs "
        "2.4 GHz. Most routers have both; turn 2.4 GHz on, or use a separate 2.4 GHz name.",
        wifi_e2="“Wrong password”", wifi_e2b="Passwords are case sensitive. Check the one on the router's label.",
        wifi_e3="“This network type is not supported”", wifi_e3b="WPA3-only and company (enterprise) networks do "
        "not work yet. Use WPA2 or WPA2/WPA3 mixed mode, or a guest network without a login page.",
        wifi_e4="“Joined, but no internet”", wifi_e4b="A hotel or guest Wi-Fi with a login page. SOUL cannot click "
        "through it: use a phone hotspot or a home network.",
        wifi_more="Nothing helps? Restart the router, keep SOUL within a few metres of it, and try again. The setup "
                  "network closes by itself 60 s after a success or after 15 minutes.",
        privacy="Your data",
    ),
    "ro": dict(
        pair_title="Leagă-ți SOUL-ul", pair_lead="Leagă acest SOUL de contul tău. Durează un minut.",
        continue_email="Continuă cu emailul", signed_in_as="Conectat ca", code_label="Codul de pe ecranul SOUL",
        code_hint="8 litere și cifre, ca 7KQ3-M9XD", pair_btn="Leagă", not_you="Nu ești tu? Ieși din cont",
        wait_title="Uită-te la SOUL", wait_lead="SOUL întreabă „Mă leg de contul lui {name}?”. Atinge <b>Da, leagă</b> "
        "pe ecranul lui.", wait_again="Am atins", wait_note="Doar o atingere pe SOUL poate spune da. Pagina se "
        "actualizează singură.",
        rejected="SOUL a spus nu. Dacă nu ai fost tu, nu s-a întâmplat nimic. Scanează noul cod ca să încerci din nou.",
        expired="Cererea a expirat. SOUL arată un cod nou: scanează-l din nou.",
        brain_title="Cine răspunde pe SOUL?", brain_lead="Când îl întrebi ceva pe SOUL, pe ecranul lui, cine să răspundă?",
        b_cloud="SOUL Cloud", b_cloud_sub="Claude în SOUL. Inclus, nimic de configurat. Nu e contul tău claude.ai.",
        b_key="Cheia mea API", b_key_sub="Anthropic sau OpenAI. Plătești tu, pe întrebare. Păstrată criptat.",
        ca_title="Conectează-ți contul Claude", ca_lead="Trei pași, cam două minute. Apoi vorbești cu Claude pe SOUL.",
        ca_s1="Intră în contul tău Claude în Anthropic Console", ca_s1_btn="Deschide Anthropic Console",
        ca_s1_note="Același cont Anthropic ca la Claude; merge și „Continue with Google”.",
        ca_s2="Creează o cheie numită SOUL",
        ca_s2_shot="În Console: <b>API keys</b> → <b>Create key</b> → numește-o <b>SOUL</b> → <b>Add</b> → "
                   "<b>Copy</b> (cheia începe cu <code>sk-ant-</code>; se arată o singură dată).",
        ca_s2_btn="Mergi la API keys", ca_s2_limit="Sfat: pune o limită lunară de cheltuieli, de ex. <b>5 $</b>, ca "
        "SOUL să nu coste niciodată mai mult.", ca_limits="Limite", ca_s3="Lipește cheia aici",
        ca_btn="Conectează Claude", ca_honest="Folosește contul tău Anthropic (plătești cât folosești, de obicei ~1 $/lună) "
        "— abonamentele Claude Pro/Max nu pot fi folosite de dispozitivele altor companii.",
        other_ways="Alte variante", b_oai="Cheia mea OpenAI", b_oai_sub="Modelele ChatGPT pe SOUL, plătite din contul "
        "tău OpenAI, pe întrebare. Păstrată criptat.", claude_connected="Claude conectat",
        claude_connected_body="Întreabă-mă orice: îți răspund cu Claude-ul tău.",
        b_chatgpt="Conectează-mi ChatGPT", b_chatgpt_sub="Te conectezi cu contul tău ChatGPT ca SOUL să poată "
        "vorbi cu ChatGPT-ul tău. Până atunci, ChatGPT-ul tău poate pune lucruri pe SOUL prin aplicația SOUL (conector).",
        soon="În curând, după aprobarea OpenAI.",
        b_claude="Conectorul din aplicația Claude", b_claude_sub="Comanzi SOUL din aplicația Claude: Claude pune "
        "notițe, mementouri, alarme și carduri pe SOUL. Merge cu orice plan Claude; îl poți avea pe lângă cheie.",
        b_none="Offline (fără AI)", b_none_sub="Alarmele, cronometrele, mementourile și notițele merg pe SOUL; "
        "nimic nu iese din casă.", opt_key="Opțional: cheia ta API Anthropic, ca să vorbești cu Claude pe SOUL",
        b_app="Aplicația mea Claude sau ChatGPT",
        b_app_sub="Claude-ul tău pune notițe, mementouri și alarme pe SOUL. Întrebările puse pe SOUL folosesc regulile "
                  "offline (poți porni SOUL Cloud oricând).",
        choose="Alege", provider="Furnizor", api_key="Cheia API", save_key="Salvează cheia și folosește-o",
        key_advice="Folosește o cheie separată, cu limită lunară de cheltuieli și fără expirare. SOUL nu o arată "
                   "niciodată înapoi.",
        me_title="SOUL-ul tău", devices="SOUL-urile tale", no_devices="Niciun SOUL încă.", pair_one="Leagă un SOUL",
        online="online", offline="offline", brain="Răspunde", fw="firmware", last_seen="văzut ultima dată",
        paused="Claude & co. pe pauză pe SOUL", keys="Cheile tale API", not_set="nesetată", verified="verificată",
        unverified="salvată, neverificată încă", remove="Șterge", apps="Aplicații conectate",
        no_apps="Nicio aplicație conectată încă.", revoke="Deconectează", connect_claude="Conectează-ți Claude",
        connect_chatgpt="Conectează ChatGPT (avansat)", sign_out="Ieși din cont", unpair="Dezleagă acest SOUL",
        sign_in_first="Conectează-te ca să-ți vezi SOUL-ul.", sign_in="Conectează-te", copy="Copiază",
        copied="Copiat", conn_addr="Adresa conectorului", claude_title="Conectează-ți Claude la SOUL",
        claude_steps="<li>Deschide <b>claude.ai</b> pe calculator (sau aplicația Claude) și conectează-te.</li>"
                     "<li>Mergi la <b>Settings → Connectors</b> (pe unele planuri: <b>Customize → Connectors</b>) și "
                     "alege <b>Add custom connector</b>.</li><li>Numește-l <b>SOUL</b> și lipește adresa de mai jos.</li>"
                     "<li>Dacă Claude întreabă cum să înregistreze aplicația, merge oricare variantă (<b>Use Claude's published "
                     "identity</b> sau <b>Register automatically</b>).</li>"
                     "<li>Apasă <b>Connect</b>. Conectează-te la SOUL cu codul din email și apasă <b>Permite</b>.</li>"
                     "<li>Într-o conversație scrie: <i>Show hello on my SOUL</i>. SOUL arată „Claude conectat”.</li>",
        claude_plans="Orice plan Claude poate adăuga un conector propriu (Free: unul). Cont de firmă? Roagă "
                     "administratorul Claude să-l adauge pentru organizație. Adăugarea doar de pe telefon e în beta: "
                     "de pe calculator e cel mai simplu.",
        chatgpt_title="Conectează ChatGPT la SOUL (avansat)",
        chatgpt_steps="<li>Pe <b>chatgpt.com</b> (web): <b>Settings → Security and login → Developer mode</b>.</li>"
                      "<li>Adaugă o aplicație cu adresa de mai jos (se termină în <code>/mcp</code>).</li>"
                      "<li>Conectează-te la SOUL cu codul din email și apasă <b>Permite</b>.</li>"
                      "<li>ChatGPT îți cere confirmare pentru fiecare schimbare pe SOUL.</li>",
        chatgpt_note="SOUL nu e încă o aplicație listată în ChatGPT; modul dezvoltator e pentru cine se descurcă cu el.",
        siwc_title="Conectează-mi ChatGPT", siwc_body="În curând, după aprobarea OpenAI. „Sign in with ChatGPT” e "
        "deschis doar aplicațiilor aprobate (listă de așteptare). Când SOUL e aprobat te vei conecta aici, în browser; "
        "parola și tokenurile rămân între browserul tău, OpenAI și SOUL Cloud, niciodată pe dispozitiv. Până atunci, "
        "ChatGPT-ul tău poate deja pune lucruri pe SOUL:",
        back_me="Înapoi la SOUL-ul tău", done_cloud="Gata. SOUL răspunde cu Claude în SOUL.",
        done_key="Gata. SOUL răspunde cu cheia ta.", done_none="Gata. SOUL folosește regulile offline.",
        bad_code="Codul nu e valid. Verifică ecranul (8 caractere).",
        code_expired="Codul a expirat; SOUL arată unul nou.",
        device_owned="Acest SOUL aparține altui cont. Roagă proprietarul să-l elibereze.",
        rate="Prea multe încercări. Mai așteaptă puțin.", forbidden="Acesta nu e unul dintre SOUL-urile tale.",
        need_key="Adaugă întâi o cheie pentru acel furnizor.", key_bad="Furnizorul spune că această cheie nu merge.",
        key_refused="Asta nu e o cheie API obișnuită (cheile de admin și tokenurile de abonament sunt refuzate).",
        reauth="Pentru siguranță, confirmă întâi că ești tu cu un cod nou pe email.",
        expired_form="Formularul a expirat. Încearcă din nou.", trial="răspunsuri gratuite până la legare",
        allowance="răspunsuri rămase luna aceasta",
        b_bridge="Claude-ul meu de pe calculator", b_bridge_sub="Claude Code-ul tău (Pro/Max), conectat de tine pe "
        "calculatorul tău, răspunde la ce întrebi pe SOUL. Experimental: calculatorul trebuie să fie pornit, cu Start "
        "SOUL deschis.",
        computers="Calculatoarele tale (SOUL Bridge)", no_computers="Niciun calculator legat încă.",
        add_computer="Leagă un calculator", forget="Uită", br_online="conectat", br_offline="neconectat",
        br_title="Leagă un calculator de SOUL", br_lead="Pe calculatorul unde folosești Claude Code, rulează:",
        br_steps="<li>Instalează Node.js 20+ și Claude Code, apoi rulează o dată <code>claude</code> și conectează-te "
                 "în <b>contul tău</b> Claude (SOUL nu-l vede niciodată).</li>"
                 "<li><code>npm install -g soul-bridge</code></li>"
                 "<li>Rulează comanda de mai jos (codul merge o singură dată, 5 minute).</li>"
                 "<li><code>soul-bridge setup</code>, apoi dublu-click pe <b>Start SOUL</b> și lasă fereastra deschisă.</li>",
        br_note="E același fel de cod pe care SOUL îl arată la Setări › AI › Claude-ul meu de pe calculator.",
        export="Descarcă datele mele", export_sub="Tot ce păstrează SOUL Cloud despre tine, într-un fișier JSON "
        "(cheile și tokenurile nu sunt incluse niciodată).",
        delete_title="Șterge-mi contul", delete_sub="Dezleagă fiecare SOUL și îi șterge datele din SOUL Cloud, "
        "deconectează toate aplicațiile și calculatoarele, îți șterge cheile, apoi contul. Nu se poate anula.",
        delete_confirm="Scrie STERGE ca să confirmi", delete_btn="Șterge-mi contul definitiv",
        delete_word="STERGE", deleted="Contul tău și datele lui au fost șterse. SOUL-ul tău merge mai departe "
        "offline; îl poți lega din nou oricând.", delete_typo="Scrie exact cuvântul ca să confirmi.",
        erase_too="Șterge și datele acestui SOUL din SOUL Cloud",
        wifi_title="SOUL a pierdut Wi-Fi-ul?", wifi_lead="SOUL îți păstrează alarmele și notițele și fără internet. "
        "Ca să-l conectezi din nou la o rețea:",
        wifi_steps="<li>Ține apăsat butonul lateral al SOUL <b>5 secunde</b> (sau <b>Setări › Wi-Fi</b> pe SOUL). "
                   "Ecranul arată un cod QR de Wi-Fi și rețeaua <b>SOUL-xxxx</b>.</li>"
                   "<li>Scanează QR-ul cu camera telefonului (sau intră în <b>SOUL-xxxx</b> cu parola de pe ecran). "
                   "Se deschide pagina de configurare; dacă nu, deschide <b>http://192.168.4.1</b>.</li>"
                   "<li>Alege rețeaua de acasă, scrie parola, apasă <b>Conectează</b>. SOUL o testează și spune ce s-a "
                   "întâmplat, pe pagină și pe ecranul lui.</li>",
        wifi_errors="Dacă scrie…", wifi_e1="„Rețeaua nu a fost găsită”", wifi_e1b="Wi-Fi-ul tău e doar pe 5 GHz? "
        "SOUL are nevoie de 2,4 GHz. Majoritatea routerelor au ambele; pornește 2,4 GHz sau folosește un nume separat.",
        wifi_e2="„Parolă greșită”", wifi_e2b="Contează literele mari și mici. Verifică parola de pe eticheta routerului.",
        wifi_e3="„Acest tip de rețea nu e suportat”", wifi_e3b="Rețelele doar WPA3 și cele de firmă (enterprise) nu "
        "merg încă. Folosește WPA2 sau modul mixt WPA2/WPA3, ori o rețea pentru oaspeți fără pagină de login.",
        wifi_e4="„Conectat, dar fără internet”", wifi_e4b="Un Wi-Fi de hotel sau de oaspeți cu pagină de login. SOUL "
        "nu poate trece de ea: folosește hotspotul telefonului sau o rețea de acasă.",
        wifi_more="Nu merge nimic? Repornește routerul, ține SOUL la câțiva metri de el și încearcă din nou. Rețeaua "
                  "de configurare se închide singură la 60 s după succes sau după 15 minute.",
        privacy="Datele tale",
    ),
}

BRAIN_NAME = {
    "en": {"cloud": "SOUL Cloud (Claude inside SOUL)", "claude": "Your Anthropic key", "chatgpt": "Your OpenAI key",
           "none": "Offline (no AI)", "direct": "A key on SOUL itself", "bridge": "My Claude on my computer"},
    "ro": {"cloud": "SOUL Cloud (Claude în SOUL)", "claude": "Cheia ta Anthropic", "chatgpt": "Cheia ta OpenAI",
           "none": "Offline (fără AI)", "direct": "O cheie pe SOUL", "bridge": "Claude-ul meu de pe calculator"},
}

# ============================================================= templates ==

WORDMARK = (
    '<svg class="wordmark" viewBox="0 0 489.04 144.35" role="img" aria-label="SOUL"><g transform="translate(-2.96 '
    '-61.82)"><path class="ink" d="M59.4 202.8Q45.8 202.8 35.5 199.7Q25.2 196.6 18.2 190.7Q11.2 184.8 7.9 176.3Q4.6 '
    '167.8 5 157.2L32 151.4Q32 161.4 35.8 167.4Q39.6 173.4 46.2 176.2Q52.8 179 60.6 179Q67.6 179 72.9 177.2Q78.2 '
    '175.4 81.2 172.2Q84.2 169 84.2 164.6Q84.2 159 80.2 155.6Q76.2 152.2 69.5 149.9Q62.8 147.6 54.6 145.6Q46 143.2 '
    '37.5 140.4Q29 137.6 22 133.3Q15 129 10.7 122.1Q6.4 115.2 6.4 104.8Q6.4 92.4 12.8 83.6Q19.2 74.8 30.4 70Q41.6 '
    '65.2 56.4 65.2Q71.8 65.2 83.7 70.4Q95.6 75.6 102 85.5Q108.4 95.4 107.2 110L80.6 114.4Q81 108.2 79.4 103.4Q77.8 '
    '98.6 74.6 95.2Q71.4 91.8 66.6 90.1Q61.8 88.4 55.4 88.4Q48.6 88.4 43.9 90.2Q39.2 92 36.8 95.3Q34.4 98.6 34.4 '
    '103Q34.4 108 38 111.2Q41.6 114.4 48.1 116.6Q54.6 118.8 63 121Q71.6 123.2 80.2 126Q88.8 128.8 96.2 133.4Q103.6 '
    '138 108 145.2Q112.4 152.4 112.4 163.6Q112.4 176.4 105.6 185.2Q98.8 194 86.9 198.4Q75 202.8 59.4 202.8Z M326.6 '
    '202.8Q315.6 202.8 306.8 200.3Q298 197.8 291.5 193.1Q285 188.4 280.7 181.7Q276.4 175 274.3 166.6Q272.2 158.2 '
    '272.2 148.4V68H301V146.8Q301 157.2 304.1 163.9Q307.2 170.6 312.9 173.8Q318.6 177 326.6 177Q334.8 177 340.5 '
    '173.8Q346.2 170.6 349.2 163.9Q352.2 157.2 352.2 146.8V68H381.2V148.4Q381.2 174.4 367.2 188.6Q353.2 202.8 326.6 '
    '202.8Z M408.8 200V68H437.6V175.2H490V200Z"/><circle class="glass" cx="190.2" cy="134" r="70.18"/><path '
    'class="eyes" d="M179.94 125.01A14.04 23.86 0 1 1 157.34 120.78ZM223.06 120.78A14.04 23.86 0 1 1 200.46 '
    '125.01Z"/></g></svg>')

_BASE = """<!doctype html>
<html lang="{{ lang }}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#FAF8F3">
<title>{{ title }} · SOUL</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/soul-web.css">
</head><body class="soul"><main>
<header class="top"><a href="/me" class="home">{{ wordmark|safe }}</a></header>
{% if flash %}<p class="flash">{{ flash }}</p>{% endif %}
{% if error %}<p class="err" role="alert">{{ error }}</p>{% endif %}
{% block body %}{% endblock %}
</main>
<script src="/static/soul-pair.js"></script>
</body></html>"""

_PAIR = """{% extends "base" %}{% block body %}
<h1>{{ t.pair_title }}</h1>
<p class="lead">{{ t.pair_lead }}</p>
{% if not session %}
  <div class="card">
    <p>1 · {{ t.continue_email }}</p>
    <a class="btn primary" id="signin" href="/login?next=%2Fpair&amp;lang={{ lang }}">{{ t.continue_email }}</a>
  </div>
{% else %}
  <form class="card" method="post" action="/pair/claim">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    <label for="code">{{ t.code_label }}</label>
    <input id="code" class="code" name="code" maxlength="12" autocomplete="off" autocapitalize="characters"
           spellcheck="false" placeholder="XXXX-XXXX" required value="{{ code }}">
    <p class="hint">{{ t.code_hint }}</p>
    <button class="btn primary" type="submit">{{ t.pair_btn }}</button>
  </form>
  <p class="small">{{ t.signed_in_as }} {{ hint }} · <a href="#" data-logout>{{ t.not_you }}</a></p>
  <form method="post" action="/me/logout" id="logout"><input type="hidden" name="csrf" value="{{ csrf }}"></form>
{% endif %}
{% endblock %}"""

_WAIT = """{% extends "base" %}{% block body %}
<h1>{{ t.wait_title }}</h1>
<section id="pair-wait" class="card wait" data-poll="/v1/me/pair/{{ pid }}" data-next="/pair/brain?d={{ device_id }}">
  <div class="soulface" aria-hidden="true"><span></span><span></span></div>
  <p>{{ lead|safe }}</p>
  <p class="hint">{{ t.wait_note }}</p>
  <form method="get" action="/pair/wait"><input type="hidden" name="pid" value="{{ pid }}">
  <button class="btn" type="submit">{{ t.wait_again }}</button></form>
</section>
{% endblock %}"""

_BRAIN = """{% extends "base" %}{% block body %}
<h1>{{ t.brain_title }}</h1>
<form class="card hero" method="post" action="/me/keys" id="claude-account">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="device_id" value="{{ device_id }}">
  <input type="hidden" name="provider" value="anthropic">
  <h2>{{ t.ca_title }}</h2>
  <p>{{ t.ca_lead }}</p>
  <ol class="steps big">
    <li><b>{{ t.ca_s1 }}</b><br>
      <a class="btn" href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer">{{ t.ca_s1_btn }} ↗</a>
      <span class="hint">{{ t.ca_s1_note }}</span></li>
    <li><b>{{ t.ca_s2 }}</b><br>
      <span class="shot">{{ t.ca_s2_shot|safe }}</span>
      <a class="btn" href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer">{{ t.ca_s2_btn }} ↗</a>
      <span class="hint">{{ t.ca_s2_limit|safe }}
      <a href="https://console.anthropic.com/settings/limits" target="_blank" rel="noopener noreferrer">{{ t.ca_limits }} ↗</a></span></li>
    <li><b>{{ t.ca_s3 }}</b>
      <input id="key" name="key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-api03-…" required>
    </li>
  </ol>
  <button class="btn primary" type="submit">{{ t.ca_btn }}</button>
  <p class="fine">{{ t.ca_honest }}</p>
</form>
<h2>{{ t.other_ways }}</h2>
<form class="card choice" method="post" action="/me/devices/{{ device_id }}/brain">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="brain" value="none">
  <input type="hidden" name="next" value="/me/signin-chatgpt">
  <h3>{{ t.b_chatgpt }}</h3><p>{{ t.b_chatgpt_sub }}</p><p class="note">{{ t.soon }}</p>
  <button class="btn" type="submit">{{ t.choose }}</button>
</form>
<form class="card choice" method="post" action="/me/keys">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="device_id" value="{{ device_id }}">
  <input type="hidden" name="provider" value="openai">
  <h3>{{ t.b_oai }}</h3><p>{{ t.b_oai_sub }}</p>
  <label for="okey">{{ t.api_key }}</label>
  <input id="okey" name="key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-proj-…" required>
  <p class="hint">{{ t.key_advice }}</p>
  <button class="btn" type="submit">{{ t.save_key }}</button>
</form>
<form class="card choice" method="post" action="/me/devices/{{ device_id }}/brain">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="brain" value="none">
  <input type="hidden" name="next" value="/me/connect-claude">
  <h3>{{ t.b_claude }}</h3><p>{{ t.b_claude_sub }}</p>
  <button class="btn" type="submit">{{ t.choose }}</button>
</form>
<form class="card choice" method="post" action="/me/devices/{{ device_id }}/brain">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="brain" value="none">
  <h3>{{ t.b_none }}</h3><p>{{ t.b_none_sub }}</p>
  <button class="btn" type="submit">{{ t.choose }}</button>
</form>
{% if builtin %}
<form class="card choice" method="post" action="/me/devices/{{ device_id }}/brain">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="brain" value="cloud">
  <h3>{{ t.b_cloud }}</h3><p>{{ t.b_cloud_sub }}</p>
  <button class="btn" type="submit">{{ t.choose }}</button>
</form>
{% endif %}
{% endblock %}"""

_CONNECT = """{% extends "base" %}{% block body %}
<h1>{{ heading }}</h1>
{% if intro %}<p class="lead">{{ intro }}</p>{% endif %}
<ol class="steps">{{ steps|safe }}</ol>
<div class="card">
  <label for="mcp">{{ t.conn_addr }}</label>
  <div class="copyrow"><input id="mcp" class="mono" readonly value="{{ mcp_url }}">
  <button class="btn" type="button" data-copy="mcp" data-done="{{ t.copied }}">{{ t.copy }}</button></div>
</div>
<p class="small">{{ note }}</p>
{% if key_form and session %}
<form class="card" method="post" action="/me/keys">
  <input type="hidden" name="csrf" value="{{ csrf }}"><input type="hidden" name="provider" value="anthropic">
  {% if device_id %}<input type="hidden" name="device_id" value="{{ device_id }}">{% endif %}
  <label for="key">{{ t.opt_key }}</label>
  <input id="key" name="key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-…" required>
  <p class="hint">{{ t.key_advice }}</p>
  <button class="btn" type="submit">{{ t.save_key }}</button>
</form>
{% endif %}
<p><a class="btn" href="/me">{{ t.back_me }}</a></p>
{% endblock %}"""

_ME = """{% extends "base" %}{% block body %}
{% if not session %}
  <h1>{{ t.me_title }}</h1>
  <div class="card"><p>{{ t.sign_in_first }}</p>
  <a class="btn primary" href="/login?next=%2Fme&amp;lang={{ lang }}">{{ t.sign_in }}</a></div>
{% else %}
  <h1>{{ t.me_title }}</h1>
  <p class="small">{{ t.signed_in_as }} {{ hint }}</p>
  <h2>{{ t.devices }}</h2>
  {% if not devices %}<div class="card"><p>{{ t.no_devices }}</p><a class="btn primary" href="/pair">{{ t.pair_one }}</a></div>{% endif %}
  {% for d in devices %}
  <section class="card device">
    <div class="row"><span class="soulface sm" aria-hidden="true"><span></span><span></span></span>
      <div><h3>{{ d.name or 'SOUL' }} <span class="mono id">…{{ d.device_id[-4:] }}</span></h3>
      <p class="small"><span class="dot {{ 'on' if d.online else 'off' }}"></span>{{ t.online if d.online else t.offline }}
      {% if d.last_seen %} · {{ t.last_seen }} {{ d.last_seen }}{% endif %}{% if d.fw %} · {{ t.fw }} <span class="mono">{{ d.fw }}</span>{% endif %}</p></div></div>
    {% if d.connectors_paused %}<p class="note">{{ t.paused }}</p>{% endif %}
    <form method="post" action="/me/devices/{{ d.device_id }}/brain" class="inline">
      <input type="hidden" name="csrf" value="{{ csrf }}">
      <label for="b-{{ d.device_id }}">{{ t.brain }}</label>
      <select id="b-{{ d.device_id }}" name="brain">
      {% for b in brains %}<option value="{{ b }}" {{ 'selected' if d.brain == b }}>{{ brain_name[b] }}</option>{% endfor %}
      </select>
      <button class="btn" type="submit">{{ t.choose }}</button>
    </form>
    {% if d.brain == 'cloud' and allowance and builtin %}<p class="small">{{ allowance.left }} {{ t.allowance }}</p>{% endif %}
    <h3 class="sub">{{ t.computers }}</h3>
    {% for c in d.computers %}
    <div class="row between"><p class="small"><span class="dot {{ 'on' if c.online else 'off' }}"></span>{{ c.label }} ·
      {{ t.br_online if c.online else t.br_offline }}</p>
      <form method="post" action="/me/bridge/{{ c.id }}/revoke"><input type="hidden" name="csrf" value="{{ csrf }}">
      <button class="link" type="submit">{{ t.forget }}</button></form></div>
    {% else %}<p class="small">{{ t.no_computers }}</p>{% endfor %}
    <form method="post" action="/me/devices/{{ d.device_id }}/bridge"><input type="hidden" name="csrf" value="{{ csrf }}">
    <button class="btn" type="submit">{{ t.add_computer }}</button></form>
    <form method="post" action="/me/devices/{{ d.device_id }}/unpair" class="danger">
      <input type="hidden" name="csrf" value="{{ csrf }}">
      <label class="check"><input type="checkbox" name="erase" value="1"> {{ t.erase_too }}</label>
      <button class="link" type="submit">{{ t.unpair }}</button></form>
  </section>
  {% endfor %}
  <h2>{{ t.connect_claude }}</h2>
  <div class="card"><p>{{ t.b_claude_sub }}</p>
    <div class="copyrow"><input id="mcp" class="mono" readonly value="{{ mcp_url }}">
    <button class="btn" type="button" data-copy="mcp" data-done="{{ t.copied }}">{{ t.copy }}</button></div>
    <p><a href="/me/connect-claude">{{ t.connect_claude }} →</a> · <a href="/me/signin-chatgpt">{{ t.b_chatgpt }} →</a></p>
  </div>
  <h2>{{ t.apps }}</h2>
  {% if not grants %}<div class="card"><p class="small">{{ t.no_apps }}</p></div>{% endif %}
  {% for g in grants %}
  <div class="card row between"><div><b>{{ g.name }}</b>{% if g.verified %} <span class="badge">✓</span>{% endif %}
    <p class="small">{{ g.client_host }} · {{ g.scopes }}{% if g.state != 'connected' %} · {{ g.state }}{% endif %}</p></div>
    <form method="post" action="/me/grants/{{ g.id }}/revoke"><input type="hidden" name="csrf" value="{{ csrf }}">
    <button class="btn" type="submit">{{ t.revoke }}</button></form></div>
  {% endfor %}
  <h2>{{ t.keys }}</h2>
  {% for p, k in keys.items() %}
  <div class="card row between"><div><b>{{ 'Anthropic' if p == 'anthropic' else 'OpenAI' }}</b>
    <p class="small">{% if k.set %}<span class="mono">{{ k.masked }}</span> · {{ t.verified if k.verified else t.unverified }}{% else %}{{ t.not_set }}{% endif %}</p></div>
    {% if k.set %}<form method="post" action="/me/keys/{{ p }}/delete"><input type="hidden" name="csrf" value="{{ csrf }}">
    <button class="btn" type="submit">{{ t.remove }}</button></form>{% endif %}</div>
  {% endfor %}
  <form class="card" method="post" action="/me/keys">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    <fieldset class="seg"><legend>{{ t.provider }}</legend>
      <label><input type="radio" name="provider" value="anthropic" checked> Anthropic</label>
      <label><input type="radio" name="provider" value="openai"> OpenAI</label></fieldset>
    <label for="key">{{ t.api_key }}</label>
    <input id="key" name="key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-… / sk-…" required>
    <p class="hint">{{ t.key_advice }}</p>
    <button class="btn" type="submit">{{ t.save_key }}</button>
  </form>
  <h2>{{ t.privacy }}</h2>
  <div class="card"><p class="small">{{ t.export_sub }}</p><a class="btn" href="/me/export">{{ t.export }}</a>
    <p class="small"><a href="/me/wifi-help">{{ t.wifi_title }}</a></p></div>
  <div class="card"><p class="small">{{ t.delete_sub }}</p><a class="btn" href="/me/delete">{{ t.delete_title }}</a></div>
  <form method="post" action="/me/logout"><input type="hidden" name="csrf" value="{{ csrf }}">
  <button class="btn ghost" type="submit">{{ t.sign_out }}</button></form>
{% endif %}
{% endblock %}"""

_BRIDGE = """{% extends "base" %}{% block body %}
<h1>{{ t.br_title }}</h1>
<ol class="steps">{{ t.br_steps|safe }}</ol>
<div class="card">
  <p class="code">{{ code[:4] }}-{{ code[4:] }}</p>
  <label for="cmd">{{ t.br_lead }}</label>
  <div class="copyrow"><input id="cmd" name="cmd" value="{{ cmd }}" class="mono" readonly>
  <button class="btn" type="button" data-copy="cmd" data-done="{{ t.copied }}">{{ t.copy }}</button></div>
</div>
<p class="small">{{ t.br_note }}</p>
<p><a class="btn" href="/me">{{ t.back_me }}</a></p>
{% endblock %}"""

_WIFI = """{% extends "base" %}{% block body %}
<h1>{{ t.wifi_title }}</h1>
<p class="lead">{{ t.wifi_lead }}</p>
<ol class="steps big">{{ t.wifi_steps|safe }}</ol>
<h2>{{ t.wifi_errors }}</h2>
<div class="card"><h3>{{ t.wifi_e1 }}</h3><p class="small">{{ t.wifi_e1b }}</p></div>
<div class="card"><h3>{{ t.wifi_e2 }}</h3><p class="small">{{ t.wifi_e2b }}</p></div>
<div class="card"><h3>{{ t.wifi_e3 }}</h3><p class="small">{{ t.wifi_e3b }}</p></div>
<div class="card"><h3>{{ t.wifi_e4 }}</h3><p class="small">{{ t.wifi_e4b }}</p></div>
<p class="small">{{ t.wifi_more }}</p>
<p><a class="btn" href="/me">{{ t.back_me }}</a></p>
{% endblock %}"""

_DELETE = """{% extends "base" %}{% block body %}
<h1>{{ t.delete_title }}</h1>
<form class="card" method="post" action="/me/delete">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <p>{{ t.delete_sub }}</p>
  <label for="confirm">{{ t.delete_confirm }}</label>
  <input id="confirm" name="confirm" autocomplete="off" autocapitalize="characters" spellcheck="false" required>
  <button class="btn primary" type="submit">{{ t.delete_btn }}</button>
</form>
<p><a class="btn" href="/me">{{ t.back_me }}</a></p>
{% endblock %}"""

_MSG = """{% extends "base" %}{% block body %}<h1>{{ heading }}</h1><div class="card"><p>{{ message }}</p>
{% if link %}<a class="btn primary" href="{{ link }}">{{ link_text }}</a>{% endif %}</div>{% endblock %}"""

CSS = """@font-face{font-family:"Bricolage Grotesque";src:url(/static/fonts/bricolage.woff2) format("woff2");font-weight:400 800;font-display:swap}
@font-face{font-family:"Martian Mono";src:url(/static/fonts/martian-mono.woff2) format("woff2");font-weight:100 800;font-display:swap}
:root{--glass:#0B0B0C;--cream:#FFF0C8;--ink:#16181D;--paper:#FAF8F3;--warm:#F6F3EC;--silver:#CBCDCF;
--graphite:#55575B;--ember:#D2622C;--card:#FFFFFF;--line:#E6E2D8;--muted:#55575B}
@media (prefers-color-scheme:dark){:root{--ink:#F6F3EC;--paper:#0B0B0C;--card:#16181D;--line:#2A2D33;--muted:#CBCDCF}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:500 17px/1.5 "Bricolage Grotesque",system-ui,sans-serif}
main{max-width:30rem;margin:0 auto;padding:12px 16px 48px}
.top{padding:8px 0 4px}.wordmark{height:30px;width:auto;display:block}.wordmark .ink{fill:var(--ink)}
.wordmark .glass{fill:var(--glass)}.wordmark .eyes{fill:var(--cream)}
@media (prefers-color-scheme:dark){.wordmark .glass{stroke:var(--silver);stroke-width:3}}
h1{font-weight:800;font-size:1.9rem;line-height:1.1;letter-spacing:-.01em;margin:.6em 0 .25em}
h2{font-weight:700;font-size:1.2rem;margin:1.4em 0 .5em}h3{font-weight:700;font-size:1.05rem;margin:0}
p{margin:.4em 0}.lead{font-size:1.08rem;color:var(--muted)}a{color:var(--ink);text-underline-offset:3px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px;margin:12px 0}
.card.choice h2{margin:0 0 .2em}.card.choice p{color:var(--muted);font-size:.95rem}
label{display:block;font-weight:600;margin:.7em 0 .3em}
input,select{width:100%;font:inherit;font-size:1.05rem;padding:12px 14px;border-radius:12px;border:1px solid var(--silver);
background:var(--paper);color:var(--ink)}input:focus,select:focus{outline:3px solid var(--ember);outline-offset:1px}
.code{font-family:"Martian Mono",ui-monospace,monospace;font-size:1.45rem;letter-spacing:.12em;text-align:center;text-transform:uppercase}
.mono{font-family:"Martian Mono",ui-monospace,monospace;font-size:.85em}
.btn{display:inline-block;font:inherit;font-weight:700;font-size:1rem;padding:12px 18px;margin:12px 8px 0 0;border-radius:999px;
border:1.5px solid var(--ink);background:transparent;color:var(--ink);text-decoration:none;cursor:pointer;min-height:48px}
.btn.primary{background:var(--ink);color:var(--paper);width:100%;text-align:center}.btn.ghost{border-color:var(--line)}
.link{background:none;border:0;padding:0;font:inherit;color:var(--muted);text-decoration:underline;cursor:pointer}
.hint,.small{font-size:.88rem;color:var(--muted)}.note{font-size:.92rem;color:var(--ember)}
.err{background:#FBE6DC;color:#7A2E0E;border-radius:12px;padding:12px 14px;font-weight:600}
.flash{background:var(--cream);color:#16181D;border-radius:12px;padding:12px 14px;font-weight:600}
.seg{border:0;padding:0;margin:.4em 0;display:flex;gap:8px;flex-wrap:wrap}.seg legend{font-weight:600;margin-bottom:.3em}
.seg label{display:flex;align-items:center;gap:8px;margin:0;padding:10px 14px;border:1px solid var(--silver);border-radius:999px;font-weight:500}
.seg input{width:auto}.row{display:flex;gap:12px;align-items:center}.between{justify-content:space-between}
.row .btn{margin-top:0}.inline label{margin-top:.8em}.danger{margin-top:.6em}
.copyrow{display:flex;gap:8px;align-items:center}.copyrow input{flex:1}.copyrow .btn{margin:0}
.steps{padding-left:1.3em}.steps li{margin:.5em 0}.badge{font-size:.8rem;border:1px solid var(--ink);border-radius:999px;padding:0 .45em}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:1px}
.dot.on{background:var(--ink)}.dot.off{border:1.5px solid var(--silver)}
.soulface{display:flex;gap:14%;justify-content:center;align-items:center;width:112px;height:112px;margin:8px auto 14px;
border-radius:50%;background:var(--glass);box-shadow:0 0 0 3px var(--silver)}
.soulface span{width:15%;height:30%;border-radius:50%;background:var(--cream);animation:blink 4s infinite}
.soulface.sm{width:44px;height:44px;margin:0;flex:none;box-shadow:0 0 0 2px var(--silver)}
@keyframes blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}
@media (prefers-reduced-motion:reduce){.soulface span{animation:none}}
.wait{text-align:center}
.card.hero{border:2px solid var(--ink);padding:20px}.card.hero h2{font-size:1.5rem;font-weight:800;margin:0 0 .2em}
.steps.big li{margin:1em 0}.steps.big .btn{margin:8px 0 4px}.steps.big .hint{display:block}
.shot{display:block;background:var(--warm);color:#16181D;border-radius:12px;padding:10px 12px;margin:6px 0;font-size:.92rem}
.fine{font-size:.8rem;color:var(--muted);margin-top:10px}h3{margin-bottom:.2em}
fieldset{border:1px solid var(--line);border-radius:12px;margin:.8em 0}
h3.sub{font-size:.95rem;margin-top:1em}label.check{display:flex;gap:8px;align-items:center;font-weight:500;font-size:.9rem}
label.check input{width:auto}
.client.unverified .warn,.warn{color:#9A3412}.verified .badge{border-color:var(--ink)}"""

JS = """(function(){
var h=location.hash||'';var m=/[#&]c=([0-9A-Za-z-]{8,12})/.exec(h);
try{if(m)sessionStorage.setItem('soul_pair_code',m[1].toUpperCase());}catch(e){}
var c=document.getElementById('code');
if(c&&!c.value){var v=null;try{v=sessionStorage.getItem('soul_pair_code');}catch(e){}
 if(v){c.value=v.length===8?v.slice(0,4)+'-'+v.slice(4):v;}}
if(m&&history.replaceState)history.replaceState(null,'',location.pathname+location.search);
var lo=document.querySelector('[data-logout]');if(lo)lo.addEventListener('click',function(e){e.preventDefault();
 document.getElementById('logout').submit();});
document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){
 var i=document.getElementById(b.getAttribute('data-copy'));i.select();var done=function(){var t=b.textContent;
 b.textContent=b.getAttribute('data-done');setTimeout(function(){b.textContent=t;},1600);};
 if(navigator.clipboard)navigator.clipboard.writeText(i.value).then(done,function(){document.execCommand('copy');done();});
 else{document.execCommand('copy');done();}});});
var w=document.getElementById('pair-wait');if(w){var u=w.getAttribute('data-poll'),n=0;
 var tick=function(){n++;fetch(u,{credentials:'same-origin'}).then(function(r){return r.json();}).then(function(j){
  if(j.state==='paired'){try{sessionStorage.removeItem('soul_pair_code');}catch(e){}location.href=w.getAttribute('data-next');return;}
  if(j.state==='rejected'||j.state==='expired'){location.reload();return;}
  if(n<90)setTimeout(tick,2000);}).catch(function(){if(n<90)setTimeout(tick,4000);});};setTimeout(tick,2000);}
var f=document.getElementById('pair-wait-consent');if(f){}
})();"""


# ================================================================ helpers ==

def _lang(request: Request, session: Optional[Session], *extra: Optional[str]) -> str:
    q = request.query_params.get("lang")
    for c in (q, *extra, session.account.lang if session else None):
        if c in ("ro", "en"):
            return c
    al = request.headers.get("accept-language", "").lower()
    return "ro" if al.startswith("ro") else "en"


def me_routes(rc: Any, headers: Dict[str, str], client_ip: Callable[[Request], str],
              key_check: Optional[Callable[[str, str], str]] = None) -> List[Route]:
    """The /pair and /me routes on the remote app. `rc` is mcp_remote.RemoteContext."""
    accounts, oauth, gw = rc.accounts, rc.oauth, rc.gateway
    soul = rc.service
    impl = getattr(gw, "impl", gw)
    check = key_check or check_key_live
    rc.db.script(_KEY_CHECKS)
    mcp_url = rc.oauth.resource.rstrip("/") if rc.oauth.resource.endswith("/mcp") else rc.oauth.resource
    env = Environment(loader=DictLoader({"base": _BASE, "pair": _PAIR, "wait": _WAIT, "brain": _BRAIN,
                                         "connect": _CONNECT, "me": _ME, "msg": _MSG, "bridge": _BRIDGE,
                                         "wifi": _WIFI, "delete": _DELETE}),
                      autoescape=select_autoescape(default=True, default_for_string=True))

    def page(name: str, lang: str, status: int = 200, **ctx) -> HTMLResponse:
        body = env.get_template(name).render(lang=lang, t=_T[lang], wordmark=WORDMARK, flash=ctx.pop("flash", ""),
                                             error=ctx.pop("error", ""), **ctx)
        return HTMLResponse(body, status_code=status, headers=headers)

    def msg(lang: str, heading: str, message: str, status: int = 200, link: str = "", link_text: str = "") -> Response:
        return page("msg", lang, status, title=heading, heading=heading, message=message, link=link,
                    link_text=link_text)

    def redirect(url: str) -> RedirectResponse:
        return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store"})

    async def form(request: Request) -> dict:
        f = await request.form()
        return {k: str(f.get(k) or "") for k in f.keys()}

    def to_login(nxt: str, lang: str, reauth: bool = False) -> RedirectResponse:
        return redirect(f"/login?next={quote(nxt, safe='')}&lang={lang}" + ("&reauth=1" if reauth else ""))

    async def own_device(session: Session, device_id: str) -> Optional[dict]:
        if not _DEV.match(device_id or ""):
            return None
        info = await gw.device_info(device_id)
        if not info or info.get("account_id") != session.account_id or info.get("revoked"):
            return None
        return info

    def key_status(account_id: str) -> Dict[str, dict]:
        out = {}
        for p in ("anthropic", "openai"):
            try:
                k = soul.keys.get(account_id, p)
            except ValueError:
                k = None
            row = rc.db.one("SELECT verified FROM key_checks WHERE account_id=? AND provider=?", (account_id, p))
            out[p] = {"set": bool(k), "masked": mask_key(k), "verified": bool(row and row["verified"])}
        return out

    def set_brain(device_id: str, brain: str) -> None:
        f = getattr(impl, "send_config", None)
        if callable(f):
            f(device_id, brain=brain)
        else:  # a store-only gateway (tests): persist at least
            gw.store.update_device(device_id, brain=brain)

    def csrf_ok(request: Request, f: dict, session: Session) -> bool:
        try:
            require_csrf(request, f.get("csrf"), session)
            return True
        except AuthError:
            return False

    # ------------------------------------------------------------------ /pair --
    async def pair_get(request: Request) -> Response:
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            resp = page("pair", lang, title=_T[lang]["pair_title"], session=None)
            ensure_csrf_cookie(request, resp)
            return resp
        return page("pair", lang, title=_T[lang]["pair_title"], session=session, csrf=session.csrf,
                    hint=session.account.hint, code="")

    async def claim(session: Session, code: str, request: Request) -> dict:
        f = getattr(impl, "claim", None)
        hint = session.account.hint
        if callable(f):
            try:
                return f(session.account_id, session.account.first_name or session.account.display_name,
                         session.account.email, code, client_ip(request), hint=hint)
            except TypeError:  # a gateway without the hint argument
                return f(session.account_id, session.account.first_name, session.account.email, code,
                         client_ip(request))
        pid = await gw.claim(session.account_id, code, client_ip(request), first_name=session.account.first_name,
                             email=session.account.email)
        return {"pid": pid, "state": "awaiting_device"}

    def claim_error(e: Exception, lang: str) -> tuple:
        code = getattr(e, "code", "")
        msg_ = {"device_owned": _T[lang]["device_owned"], "rate_limited": _T[lang]["rate"],
                "code_expired": _T[lang]["code_expired"]}.get(code, _T[lang]["bad_code"])
        status = getattr(e, "status", None) or {"device_owned": 409, "rate_limited": 429, "code_expired": 410}.get(
            code, 404)
        return msg_, int(status) if isinstance(status, int) else 400

    async def pair_claim(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/pair", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["pair_title"], _T[lang]["expired_form"], 403, "/pair", _T[lang]["pair_btn"])
        code = re.sub(r"[\s-]", "", f.get("code", "")).upper()
        try:
            if not re.fullmatch(r"[0-9A-Z]{8}", code):
                raise ValueError("bad code")
            res = await _maybe_await(claim(session, code, request))
        except Exception as e:  # noqa: BLE001 - GatewayError (either kind) or a bad code
            text, status = claim_error(e, lang)
            return page("pair", lang, status, title=_T[lang]["pair_title"], session=session, csrf=session.csrf,
                        hint=session.account.hint, code=f.get("code", "")[:12], error=text)
        pid = res["pid"]
        rc.pending_pairs[pid] = session.account_id
        dev = (res.get("device") or {}).get("id", "")
        rc.pending_pairs[f"dev:{pid}"] = dev
        return redirect(f"/pair/wait?pid={quote(pid)}")

    async def claim_state(pid: str, account_id: str) -> str:
        return await gw.claim_state(pid, account_id)

    async def pair_wait(request: Request) -> Response:
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/pair", lang)
        pid = request.query_params.get("pid", "")
        if not _PID.match(pid) or rc.pending_pairs.get(pid) != session.account_id:
            return msg(lang, _T[lang]["pair_title"], _T[lang]["expired"], 404, "/pair", _T[lang]["pair_btn"])
        state = await claim_state(pid, session.account_id)
        dev = rc.pending_pairs.get(f"dev:{pid}", "")
        if state == "paired":
            return redirect(f"/pair/brain?d={dev}")
        if state in ("rejected", "expired"):
            return msg(lang, _T[lang]["pair_title"], _T[lang][state], 200, "/pair", _T[lang]["pair_btn"])
        name = session.account.first_name or session.account.display_name
        lead = str(env.from_string("{{ x }}").render(x=name))  # escaped, then put in the sentence
        return page("wait", lang, title=_T[lang]["wait_title"], pid=pid, device_id=dev,
                    lead=_T[lang]["wait_lead"].format(name=lead))

    async def pair_brain(request: Request) -> Response:
        session = accounts.current_session(request)
        lang = _lang(request, session)
        dev = request.query_params.get("d", "")
        if session is None:  # SOUL's "Connect Claude" QR lands here: sign in, then come back
            return to_login(f"/pair/brain?d={dev}" if _DEV.match(dev) else "/me", lang)
        if await own_device(session, dev) is None:
            return msg(lang, _T[lang]["me_title"], _T[lang]["forbidden"], 404, "/me", _T[lang]["back_me"])
        return page("brain", lang, title=_T[lang]["brain_title"], device_id=dev, csrf=session.csrf,
                    builtin=builtin_ai_enabled())

    # ------------------------------------------------------- JSON (§3.4) --
    async def api_claim(request: Request) -> Response:
        session = accounts.current_session(request)
        if session is None:
            return JSONResponse({"error": {"code": "unauthenticated", "msg": "sign in first"}}, 401)
        try:
            require_csrf(request, None, session)
        except AuthError:
            return JSONResponse({"error": {"code": "csrf", "msg": "csrf"}}, 403)
        try:
            body = await request.json()
            code = re.sub(r"[\s-]", "", str(body.get("code", ""))).upper()
            if not re.fullmatch(r"[0-9A-Z]{8}", code):
                return JSONResponse({"error": {"code": "invalid", "msg": "a pairing code has 8 characters"}}, 422)
            res = await _maybe_await(claim(session, code, request))
        except Exception as e:  # noqa: BLE001
            code_ = getattr(e, "code", "invalid")
            _, status = claim_error(e, "en")
            return JSONResponse({"error": {"code": code_, "msg": str(getattr(e, "msg", "") or code_)}}, status)
        res = {k: v for k, v in res.items() if not k.startswith("_")}
        rc.pending_pairs[res["pid"]] = session.account_id
        rc.pending_pairs[f"dev:{res['pid']}"] = (res.get("device") or {}).get("id", "")
        return JSONResponse(res, 202, headers={"Cache-Control": "no-store"})

    async def api_pair_state(request: Request) -> Response:
        session = accounts.current_session(request)
        pid = request.path_params["pid"]
        if session is None or not _PID.match(pid):
            return JSONResponse({"error": {"code": "not_found", "msg": "unknown pairing request"}}, 404)
        state = await claim_state(pid, session.account_id)
        return JSONResponse({"state": state}, headers={"Cache-Control": "no-store"})

    # ------------------------------------------------------------------- /me --
    async def me_get(request: Request) -> Response:
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return page("me", lang, title=_T[lang]["me_title"], session=None)
        devices = [dict(d) for d in await gw.devices_of(session.account_id)
                   if d.get("account_id") == session.account_id and not d.get("revoked")]
        bridges = getattr(impl, "bridges", None)
        for d in devices:
            d["computers"] = bridges.tokens(session.account_id, d["device_id"]) if bridges is not None else []
        grants = []
        for g in oauth.grants(session.account_id):
            name = {"claude": "Claude", "chatgpt": "ChatGPT"}.get(g.client_app, g.client_host)
            grants.append({"id": g.grant_id, "name": name, "client_host": g.client_host, "verified": g.verified,
                           "scopes": ", ".join(s for s in g.scopes if s != "offline_access"), "state": g.state})
        allowance = None
        relay = getattr(impl, "relay", None)
        if relay is not None and getattr(relay, "meter", None) is not None:
            try:
                allowance = relay.meter.allowance(session.account_id)
            except Exception:  # noqa: BLE001 - a page must not fail on metering
                allowance = None
        flash = {"cloud": _T[lang]["done_cloud"], "key": _T[lang]["done_key"], "none": _T[lang]["done_none"]}.get(
            request.query_params.get("done", ""), "")
        err = {"need_key": _T[lang]["need_key"], "forbidden": _T[lang]["forbidden"]}.get(
            request.query_params.get("err", ""), "")
        return page("me", lang, title=_T[lang]["me_title"], session=session, csrf=session.csrf,
                    hint=session.account.hint, devices=devices, grants=grants, keys=key_status(session.account_id),
                    brain_name=BRAIN_NAME[lang], mcp_url=mcp_url, brains=brain_choices(), allowance=allowance, flash=flash, error=err,
                    builtin=builtin_ai_enabled())

    def connect_page(which: str) -> Callable:
        async def handler(request: Request) -> Response:
            session = accounts.current_session(request)
            lang = _lang(request, session)
            t = _T[lang]
            common = dict(session=session, csrf=session.csrf if session else "", mcp_url=mcp_url,
                          device_id=request.query_params.get("d", ""))
            if which == "claude":
                return page("connect", lang, title=t["claude_title"], heading=t["claude_title"], intro="",
                            steps=t["claude_steps"], note=t["claude_plans"], key_form=True, **common)
            if which == "siwc":  # Sign in with ChatGPT: a stub until OpenAI approves SOUL (docs/07 §1.10)
                return page("connect", lang, title=t["siwc_title"], heading=t["siwc_title"], intro=t["siwc_body"],
                            steps=t["chatgpt_steps"], note=t["chatgpt_note"], key_form=False, **common)
            return page("connect", lang, title=t["chatgpt_title"], heading=t["chatgpt_title"], intro="",
                        steps=t["chatgpt_steps"], note=t["chatgpt_note"], key_form=False, **common)
        return handler

    async def device_brain(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        dev = request.path_params["device_id"]
        if await own_device(session, dev) is None:
            return redirect("/me?err=forbidden")
        brain = f.get("brain", "")
        if brain not in brain_choices():  # "cloud" only with built-in AI (SOUL_BUILTIN_AI=1)
            return redirect("/me?err=forbidden")
        if brain in PROVIDER_OF and not key_status(session.account_id)[PROVIDER_OF[brain]]["set"]:
            return redirect("/me?err=need_key")
        set_brain(dev, brain)
        log.info("brain set to %s", brain)
        nxt = f.get("next", "")
        if nxt in ("/me/connect-claude", "/me/connect-chatgpt", "/me/signin-chatgpt"):
            return redirect(f"{nxt}?d={dev}")
        return redirect("/me?done=" + ("cloud" if brain == "cloud" else "none" if brain == "none" else "key"))

    async def device_unpair(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        dev = request.path_params["device_id"]
        if await own_device(session, dev) is None:
            return redirect("/me?err=forbidden")
        if not accounts.is_fresh(session):
            return to_login("/me", lang, reauth=True)
        f_unpair = getattr(impl, "unpair", None)
        if callable(f_unpair):
            f_unpair(dev, "user", erase=f.get("erase") == "1")  # GDPR: the owner may erase the SOUL's cloud data
        return redirect("/me")

    # ------------------------------------------------- SOUL Bridge (docs/08) --
    async def bridge_new(request: Request) -> Response:
        """A one-time code for `soul-bridge pair` (the same kind SOUL shows on its screen)."""
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        dev = request.path_params["device_id"]
        bridges = getattr(impl, "bridges", None)
        if await own_device(session, dev) is None or bridges is None:
            return redirect("/me?err=forbidden")
        c = bridges.pair_code(dev)
        return page("bridge", lang, title=_T[lang]["br_title"], code=c["code"], cmd=c["cmd"])

    async def bridge_revoke(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        bridges = getattr(impl, "bridges", None)
        if bridges is None or not bridges.revoke(session.account_id, request.path_params["token_id"]):
            return redirect("/me?err=forbidden")
        return redirect("/me")

    # ------------------------------------------------------ help and GDPR --
    async def wifi_help(request: Request) -> Response:
        session = accounts.current_session(request)
        lang = _lang(request, session)
        return page("wifi", lang, title=_T[lang]["wifi_title"])

    async def export_get(request: Request) -> Response:
        session = accounts.current_session(request)
        if session is None:
            if request.url.path.startswith("/v1/"):
                return JSONResponse({"error": {"code": "unauthenticated", "msg": "sign in first"}}, 401)
            return to_login("/me", _lang(request, None))
        from .gdpr import export_account

        data = export_account(rc, session.account_id)
        log.info("data export downloaded")
        return JSONResponse(data, headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Disposition": 'attachment; filename="soul-my-data.json"'})

    async def delete_get(request: Request) -> Response:
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me/delete", lang)
        if not accounts.is_fresh(session):  # §3.1: deleting the account needs a fresh sign-in
            return to_login("/me/delete", lang, reauth=True)
        return page("delete", lang, title=_T[lang]["delete_title"], csrf=session.csrf)

    def erase_and_sign_out(session: Session, resp: Response) -> Response:
        from .gdpr import delete_account

        delete_account(rc, session.account_id)
        clear_session_cookies(resp)
        return resp

    async def delete_post(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["delete_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        if not accounts.is_fresh(session):
            return to_login("/me/delete", lang, reauth=True)
        word = f.get("confirm", "").strip().upper().replace("Ș", "S").replace("Ş", "S")
        if word not in ("DELETE", "STERGE"):
            return page("delete", lang, 422, title=_T[lang]["delete_title"], csrf=session.csrf,
                        error=_T[lang]["delete_typo"])
        return erase_and_sign_out(session, msg(lang, _T[lang]["delete_title"], _T[lang]["deleted"]))

    async def api_delete(request: Request) -> Response:
        """`DELETE /v1/me` (§3.5): session + X-CSRF-Token + a fresh sign-in -> 204."""
        session = accounts.current_session(request)
        if session is None:
            return JSONResponse({"error": {"code": "unauthenticated", "msg": "sign in first"}}, 401)
        try:
            require_csrf(request, None, session)
        except AuthError:
            return JSONResponse({"error": {"code": "csrf", "msg": "csrf"}}, 403)
        if not accounts.is_fresh(session):
            return JSONResponse({"error": {"code": "reauth_required", "msg": "sign in again first"}}, 401)
        return erase_and_sign_out(session, Response(status_code=204))

    async def keys_post(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        provider = f.get("provider", "")
        if provider not in ("anthropic", "openai"):
            return redirect("/me?err=forbidden")
        dev = f.get("device_id", "")
        back = f"/pair/brain?d={dev}" if dev else "/me"
        if dev and await own_device(session, dev) is None:
            return redirect("/me?err=forbidden")
        if not accounts.is_fresh(session):  # §3.1: a key needs a fresh sign-in
            return to_login(back, lang, reauth=True)
        key = (f.get("key") or "").strip()
        try:
            from .keystore import REFUSED_PREFIXES

            if key.lower().startswith(REFUSED_PREFIXES):
                raise ValueError("refused")
            verdict = check(provider, key)
            if verdict == "bad":
                return msg(lang, _T[lang]["keys"], _T[lang]["key_bad"], 422, back, _T[lang]["choose"])
            soul.keys.set(session.account_id, provider, key)
        except ValueError:
            return msg(lang, _T[lang]["keys"], _T[lang]["key_refused"], 422, back, _T[lang]["choose"])
        finally:
            key = ""
            f.pop("key", None)
        rc.db.exec("INSERT INTO key_checks(account_id, provider, verified, checked) VALUES (?,?,?,?) "
                   "ON CONFLICT(account_id, provider) DO UPDATE SET verified=excluded.verified, checked=excluded.checked",
                   (session.account_id, provider, 1 if verdict == "ok" else 0, int(time.time())))
        log.info("key saved for %s (%s)", provider, verdict)
        if dev:
            set_brain(dev, "claude" if provider == "anthropic" else "chatgpt")
            if provider == "anthropic":  # SOUL's eyes go surprised -> happy with a "Claude connected" card
                push = getattr(impl, "push", None)
                if callable(push):
                    try:
                        push(dev, "answer.show", {"title": _T[lang]["claude_connected"],
                                                  "body": _T[lang]["claude_connected_body"]},
                             f"it_cc{int(time.time()) % 10**8}", {"kind": "app"})
                    except ValueError:
                        pass
            return redirect("/me?done=key")
        return redirect("/me")

    async def keys_delete(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        provider = request.path_params["provider"]
        if provider not in ("anthropic", "openai"):
            return redirect("/me?err=forbidden")
        soul.keys.remove(session.account_id, provider)
        rc.db.exec("DELETE FROM key_checks WHERE account_id=? AND provider=?", (session.account_id, provider))
        brain = "claude" if provider == "anthropic" else "chatgpt"
        for d in await gw.devices_of(session.account_id):  # a SOUL that used this key goes back to the default
            if d.get("account_id") == session.account_id and d.get("brain") == brain:
                set_brain(d["device_id"], default_brain())  # offline rules, unless built-in AI is on
        return redirect("/me")

    async def grant_revoke(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        lang = _lang(request, session)
        if session is None:
            return to_login("/me", lang)
        if not csrf_ok(request, f, session):
            return msg(lang, _T[lang]["me_title"], _T[lang]["expired_form"], 403, "/me", _T[lang]["back_me"])
        g = oauth.get_grant(request.path_params["grant_id"])
        if g is None or g.account_id != session.account_id:
            return redirect("/me?err=forbidden")
        oauth.revoke_grant(g.grant_id, "revoked")
        return redirect("/me")

    async def logout(request: Request) -> Response:
        f = await form(request)
        session = accounts.current_session(request)
        resp = redirect("/me")
        if session is not None and csrf_ok(request, f, session):
            accounts.logout(session)
            clear_session_cookies(resp)
        return resp

    async def static_css(request: Request) -> Response:
        return Response(CSS, media_type="text/css",
                        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})

    async def static_js(request: Request) -> Response:
        return Response(JS, media_type="application/javascript",
                        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"})

    async def static_file(request: Request) -> Response:
        name = request.path_params["name"]
        files = {"bricolage.woff2": "font/woff2", "martian-mono.woff2": "font/woff2", "favicon.svg": "image/svg+xml"}
        if name not in files:
            return Response(status_code=404)
        return Response((WEB / name).read_bytes(), media_type=files[name],
                        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"})

    return [
        Route("/pair", pair_get, methods=["GET"]),
        Route("/pair/claim", pair_claim, methods=["POST"]),
        Route("/pair/wait", pair_wait, methods=["GET"]),
        Route("/pair/brain", pair_brain, methods=["GET"]),
        Route("/v1/me/pair/claim", api_claim, methods=["POST"]),
        Route("/v1/me/pair/{pid}", api_pair_state, methods=["GET"]),
        Route("/me", me_get, methods=["GET"]),
        Route("/me/connect-claude", connect_page("claude"), methods=["GET"]),
        Route("/me/connect-chatgpt", connect_page("chatgpt"), methods=["GET"]),
        Route("/me/signin-chatgpt", connect_page("siwc"), methods=["GET"]),
        Route("/me/devices/{device_id}/brain", device_brain, methods=["POST"]),
        Route("/me/devices/{device_id}/unpair", device_unpair, methods=["POST"]),
        Route("/me/keys", keys_post, methods=["POST"]),
        Route("/me/keys/{provider}/delete", keys_delete, methods=["POST"]),
        Route("/me/grants/{grant_id}/revoke", grant_revoke, methods=["POST"]),
        Route("/me/logout", logout, methods=["POST"]),
        Route("/me/devices/{device_id}/bridge", bridge_new, methods=["POST"]),
        Route("/me/bridge/{token_id}/revoke", bridge_revoke, methods=["POST"]),
        Route("/me/wifi-help", wifi_help, methods=["GET"]),
        Route("/me/export", export_get, methods=["GET"]),
        Route("/v1/me/export", export_get, methods=["GET"]),
        Route("/me/delete", delete_get, methods=["GET"]),
        Route("/me/delete", delete_post, methods=["POST"]),
        Route("/v1/me", api_delete, methods=["DELETE"]),
        Route("/static/soul-web.css", static_css, methods=["GET"]),
        Route("/static/soul-pair.js", static_js, methods=["GET"]),
        Route("/static/fonts/{name}", static_file, methods=["GET"]),
        Route("/static/{name}", static_file, methods=["GET"]),
    ]


async def _maybe_await(x: Any) -> Any:
    import inspect

    return await x if inspect.isawaitable(x) else x
