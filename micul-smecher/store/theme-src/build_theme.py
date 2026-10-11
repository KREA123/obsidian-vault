#!/usr/bin/env python3
"""Builds the SOUL Shopify OS 2.0 theme (store/theme) from landing v3 (site/index.html + app.js).
Run:  node extract_ro.js && python3 build_theme.py   then check with:  node run.js ../theme  (needs: npm i @shopify/theme-check-node)"""
import html, json, os, re, shutil, sys

ROOT = "/home/user/obsidian-vault/micul-smecher"
SITE = f"{ROOT}/site"
OUT = f"{ROOT}/store/theme"
SCR = os.path.dirname(os.path.abspath(__file__))

src = open(f"{SITE}/index.html", encoding="utf-8").read()
RO_SRC = json.load(open(f"{SCR}/ro.json", encoding="utf-8"))

for d in ["layout", "sections", "snippets", "templates", "config", "locales", "assets"]:
    shutil.rmtree(f"{OUT}/{d}", ignore_errors=True)  # README.md is kept
for d in ["layout", "sections", "snippets", "templates", "config", "locales", "assets"]:
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

def w(path, text):
    p = f"{OUT}/{path}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")

# ------------------------------------------------------------------ schema translations (admin UI)
SCHEMA_EN, SCHEMA_RO = {}, {}
def L(path, en, ro):
    """register an admin label under locales/*.schema.json and return its t: key"""
    def put(d, keys, v):
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = v
    put(SCHEMA_EN, path.split("."), en)
    put(SCHEMA_RO, path.split("."), ro)
    return "t:" + path

# ------------------------------------------------------------------ storefront translations
EN, RO = {}, {}
KEYMAP = {}  # landing key -> theme key (without "soul.")

def is_html(v):
    return bool(re.search(r"[<&]", v or ""))

def tkey(k):
    if k in KEYMAP:
        return KEYMAP[k]
    en, ro = EN_RAW.get(k, ""), RO_SRC.get(k, "")
    base = re.sub(r"[^a-z0-9_]", "_", k.lower().replace(".", "_"))
    nk = base + ("_html" if is_html(en) or is_html(ro) else "")
    assert nk not in KEYMAP.values(), ("key collision", k, nk)
    KEYMAP[k] = nk
    return nk

# pass 1: collect EN values from the DOM
EN_RAW = {}
def norm(s):
    return re.sub(r"\s+", " ", s).strip()

OPEN_RE = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*?)\sdata-i18n="([^"]+)"([^>]*)>')

def find_close(text, tag, start):
    depth, i = 1, start
    pat = re.compile(r"<(/?)%s\b[^>]*>" % tag, re.I)
    while True:
        m = pat.search(text, i)
        if not m:
            raise ValueError("unclosed " + tag)
        if m.group(1):
            depth -= 1
            if depth == 0:
                return m.start(), m.end()
        else:
            depth += 1
        i = m.end()

for m in OPEN_RE.finditer(src):
    tag, key = m.group(1), m.group(3)
    cs, ce = find_close(src, tag, m.end())
    EN_RAW.setdefault(key, norm(src[m.end():cs]))
for m in re.finditer(r'<[^>]*\sdata-i18n-attr="([^"]+)"[^>]*>', src):
    t = m.group(0)
    for pair in m.group(1).split(","):
        a, k = pair.split(":")
        am = re.search(r'\s%s="([^"]*)"' % re.escape(a), t)
        EN_RAW.setdefault(k, html.unescape(am.group(1)) if am else "")

missing_ro = [k for k in EN_RAW if k not in RO_SRC]
assert not missing_ro, missing_ro

# content edits that only make sense in the store
EN_RAW["res.eyebrow"] = "waitlist · from {{ price }}"
RO_SRC = dict(RO_SRC)
RO_SRC["res.eyebrow"] = "listă de așteptare · de la {{ price }}"
for d in (EN_RAW, RO_SRC):
    d["res.consent"] = d["res.consent"].replace('href="legal.html#privacy"', 'href="{{ privacy_url }}"')

# pass 2: rewrite the DOM with Liquid
SPECIAL_ARGS = {"res.eyebrow": ": price: soul_price", "res.consent": ": privacy_url: privacy_url"}

def t_expr(k):
    return "{{ 'soul.%s' | t%s }}" % (tkey(k), SPECIAL_ARGS.get(k, ""))

def rewrite(text):
    out, i = [], 0
    while True:
        m = OPEN_RE.search(text, i)
        if not m:
            out.append(text[i:])
            break
        tag, key = m.group(1), m.group(3)
        cs, ce = find_close(text, tag, m.end())
        out.append(text[i:m.end()])
        out.append(t_expr(key))
        out.append(text[cs:ce])
        i = ce
    text = "".join(out)
    def attr_sub(m):
        t = m.group(0)
        for pair in m.group(1).split(","):
            a, k = pair.split(":")
            t = re.sub(r'(\s%s=")[^"]*(")' % re.escape(a), lambda mm: mm.group(1) + t_expr(k) + mm.group(2), t, count=1)
        return t
    return re.sub(r'<[^>]*\sdata-i18n-attr="([^"]+)"[^>]*>', attr_sub, text)

# ------------------------------------------------------------------ assets
ASSET_FILES = {}
def asset_ref(path):
    name = os.path.basename(path)
    srcp = f"{SITE}/{path}"
    assert os.path.exists(srcp), srcp
    if name in ASSET_FILES:
        assert ASSET_FILES[name] == srcp, ("asset name clash", name)
    ASSET_FILES[name] = srcp
    return "{{ '%s' | asset_url }}" % name

def fix_assets(text):
    text = re.sub(r'(src|href)="((?:media|fonts)/[^"]+)"', lambda m: '%s="%s"' % (m.group(1), asset_ref(m.group(2))), text)
    def ss(m):
        parts = []
        for p in m.group(2).split(","):
            p = p.strip()
            u, *rest = p.split(" ")
            parts.append(" ".join([asset_ref(u)] + rest))
        return '%s="%s"' % (m.group(1), ", ".join(parts))
    return re.sub(r'(srcset)="((?:media)/[^"]+)"', ss, text)

for k in ["silver", "graphite", "midnight", "ember", "champagne"]:
    for sz in (520, 900):
        asset_ref(f"media/v3/col-{k}-{sz}.webp")
for f in ["front-700.avif", "front-1200.avif"]:
    asset_ref(f"media/v3/{f}")

# ------------------------------------------------------------------ split landing into sections
body = src[src.index("<body>") + 6: src.index("</body>")]
body = re.sub(r'<script src="[^"]+" defer></script>\s*', "", body)
body = body.replace('<a class="skip" href="#main" data-i18n="skip">Skip to content</a>', "")
body = body.replace('<main id="main">', "").replace("</main>", "")
body = body.replace("<!-- section: hold-demo -->", "<!-- hold-demo -->")
body = rewrite(body)
body = fix_assets(body)

parts = re.split(r"<!-- section: ([\w-]+).*?-->", body, flags=re.S)
SECTIONS = {}
for name, chunk in zip(parts[1::2], parts[2::2]):
    SECTIONS[name] = chunk.strip()
print("sections:", list(SECTIONS))

# shared replacements
HOME = "{{ home }}"
HOME_ASSIGN = "{%- liquid\n  assign home = ''\n  unless template.name == 'index'\n    assign home = routes.root_url\n  endunless\n  assign res_href = home | append: '#reserve'\n  if template.name == 'product'\n    assign res_href = '#reserve'\n  endif\n-%}\n"

def price_fix(t):
    return re.sub(r'(<(b|span) data-price="from">)[^<]*(</\2>)', r"\1{%- render 'soul-price' -%}\3", t)

def res_links(t):
    return t.replace('href="#reserve"', 'href="{{ res_href }}"')

def schema(name_key, name_en, name_ro, settings=None, presets=True, extra=None, tag="section"):
    sc = {"name": L(f"sections.{name_key}.name", name_en, name_ro), "tag": tag}
    if settings:
        sc["settings"] = settings
    if presets:
        sc["presets"] = [{"name": sc["name"]}]
    if extra:
        sc.update(extra)
    return "\n{% schema %}\n" + json.dumps(sc, ensure_ascii=False, indent=2) + "\n{% endschema %}\n"

def strip_outer(t, tag):
    """remove the outer <section ...> wrapper so Shopify's own <section> wrapper is not doubled: we keep markup as-is instead (tag: div)"""
    return t

LANDING = {
    "hero": ("Hero", "Hero"),
    "marquee": ("Facts strip", "Bandă de fapte"),
    "alive": ("It looks back", "Se uită înapoi"),
    "the-object": ("The object", "Obiectul"),
    "product-configurator": ("Colours", "Culori"),
    "born-ritual": ("Born with", "Născut cu"),
    "your-ai": ("Your AI + demo", "AI-ul tău + demo"),
    "soulos": ("SoulOS", "SoulOS"),
    "ou-egg": ("OU charging egg", "Oul de încărcare OU"),
    "privacy": ("Privacy promises", "Promisiuni intimitate"),
    "specs-and-box": ("Specs and box", "Specificații și cutie"),
    "faq": ("FAQ", "Întrebări"),
}

for name, (en, ro) in LANDING.items():
    t = SECTIONS[name]
    t = price_fix(res_links(t))
    settings = []
    if name == "soulos":
        settings = [{"type": "url", "id": "demo_url", "label": L("sections.soulos.demo_url", "SoulOS web demo link", "Link demo SoulOS"),
                     "info": L("sections.soulos.demo_info", "Leave empty to hide the button.", "Lasă gol ca să ascunzi butonul.")}]
        t = re.sub(r'<div class="os-cta">\s*<a class="btn" href="os.html">(.*?)</a>(.*?)</div>',
                   lambda m: '{%- if section.settings.demo_url != blank -%}\n    <div class="os-cta">\n      <a class="btn" href="{{ section.settings.demo_url }}" target="_blank" rel="noopener">'
                   + m.group(1) + "</a>" + m.group(2) + "</div>\n    {%- endif -%}", t, flags=re.S)
        assert "os.html" not in t
    head = HOME_ASSIGN if "res_href" in t or "home" in t else ""
    w(f"sections/{name}.liquid", head + t + schema(name.replace("-", "_"), en, ro, settings, tag="div"))

# ---------------- announcement bar
t = SECTIONS["announcement-bar"]
t = t.replace('href="#faq-ce"', 'href="{{ home }}#faq-ce"')
w("sections/announcement-bar.liquid",
  "{%- liquid\n  assign home = ''\n  unless template.name == 'index'\n    assign home = routes.root_url\n  endunless\n-%}\n" + "{%- if settings.prelaunch -%}\n" + t + "\n{%- elsif section.settings.text != blank -%}\n<div class=\"ann\" role=\"note\"><span>{{ section.settings.text }}</span></div>\n{%- endif -%}"
  + schema("announcement_bar", "Pre-launch bar", "Bară prelansare",
           [{"type": "inline_richtext", "id": "text", "label": L("sections.announcement_bar.text", "Text after launch", "Text după lansare"),
             "info": L("sections.announcement_bar.info", "While pre-launch mode is on, the CE notice is always shown.", "Cât timp modul prelansare e activ, se afișează mereu nota despre CE.")}],
           presets=False, extra={"enabled_on": {"groups": ["header"]}}, tag="div"))

# ---------------- header
t = SECTIONS["header"]
t = re.sub(r'href="#(object|colours|born|ai|os|privacy|faq)"', r'href="{{ home }}#\1"', t)
t = t.replace('href="#top"', 'href="{{ routes.root_url }}"')
lang_old = re.search(r'<div class="lang".*?</div>', t, re.S).group(0)
lang_new = """{%- if localization.available_languages.size > 1 -%}
      {%- form 'localization', class: 'lang' -%}
        <input type="hidden" name="language_code" value="{{ localization.language.iso_code }}">
        {%- for language in localization.available_languages -%}
          <button type="submit" name="language_code" value="{{ language.iso_code }}" data-lang="{{ language.iso_code }}" lang="{{ language.iso_code }}" aria-pressed="{% if language.iso_code == localization.language.iso_code %}true{% else %}false{% endif %}" aria-label="{{ language.endonym_name | escape }}">{{ language.iso_code | upcase }}</button>
        {%- endfor -%}
      {%- endform -%}
      {%- endif -%}"""
t = t.replace(lang_old, lang_new)
cta_old = re.search(r'<a class="btn" href="#reserve">.*?</a>', t, re.S).group(0)
cta_new = """{%- if settings.prelaunch -%}
      """ + cta_old.replace('href="#reserve"', 'href="{{ res_href }}"') + """
      {%- else -%}
      <a class="cartlink" href="{{ routes.cart_url }}" data-cart-open aria-label="{{ 'soul.shop.cart' | t }}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 8h12l-1 12H7L6 8Zm3 0a3 3 0 0 1 6 0" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg><span class="cart-count" data-cart-count>{{ cart.item_count }}</span></a>
      {%- if settings.soul_product != blank -%}<a class="btn" href="{{ settings.soul_product.url }}"><span>{{ 'soul.shop.buy' | t }}</span></a>{%- endif -%}
      {%- endif -%}"""
t = t.replace(cta_old, cta_new)
w("sections/header.liquid", HOME_ASSIGN + t + schema("header", "Header", "Antet", presets=False,
  extra={"enabled_on": {"groups": ["header"]}, "class": "section-header"}, tag="div"))

# ---------------- footer
t = SECTIONS["footer"]
t = t.replace('href="#top"', 'href="{{ routes.root_url }}"')
links = re.search(r'<nav class="foot-links".*?</nav>', t, re.S).group(0)
links_new = """<nav class="foot-links" aria-label="Legal">
        {%- if shop.privacy_policy -%}<a href="{{ shop.privacy_policy.url }}" data-i18n="f.privacy">{{ 'soul.f_privacy' | t }}</a>{%- endif -%}
        {%- if shop.terms_of_service -%}<a href="{{ shop.terms_of_service.url }}" data-i18n="f.terms">{{ 'soul.f_terms' | t }}</a>{%- endif -%}
        {%- if settings.cookies_page != blank -%}<a href="{{ settings.cookies_page.url }}" data-i18n="f.cookies">{{ 'soul.f_cookies' | t }}</a>{%- endif -%}
        {%- if shop.refund_policy -%}<a href="{{ shop.refund_policy.url }}">{{ 'soul.shop.refund' | t }}</a>{%- endif -%}
        {%- if settings.warranty_page != blank -%}<a href="{{ settings.warranty_page.url }}">{{ 'soul.shop.warranty' | t }}</a>{%- endif -%}
        {%- if shop.shipping_policy -%}<a href="{{ shop.shipping_policy.url }}">{{ 'soul.shop.shipping' | t }}</a>{%- endif -%}
        {%- if shop.contact_information -%}<a href="{{ shop.contact_information.url }}">{{ 'soul.shop.contact' | t }}</a>{%- endif -%}
        {%- for link in section.settings.menu.links -%}<a href="{{ link.url }}">{{ link.title | escape }}</a>{%- endfor -%}
        {%- if settings.soulos_url != blank -%}<a href="{{ settings.soulos_url }}" target="_blank" rel="noopener" data-i18n="f.os">{{ 'soul.f_os' | t }}</a>{%- endif -%}
        <a href="https://anpc.ro/ce-este-sal/" target="_blank" rel="noopener" data-i18n="f.anpc">{{ 'soul.f_anpc' | t }}</a>
      </nav>"""
t = t.replace(links, links_new)
# company identity (Legea 365/2002 art. 5): real values come from theme settings; until all are set, a plain "listed before opening" line
co_old = re.search(r'<span data-co="address" hidden>.*?</a></p>', t, re.S)
assert co_old, "footer company block"
t = t.replace(co_old.group(0), "{%- render 'soul-company' -%}</p>")
t = t.replace("ARTEMIS DIGITAL S.R.L. · ", "{{ settings.company_name | escape }} · ", 1)
assert "#legal\"" not in t.replace('id="legal"', ""), "stray #legal"
# markets / currency switcher
t = t.replace('<div class="made">', """{%- if localization.available_countries.size > 1 -%}
    {%- form 'localization', class: 'market' -%}
      <label for="market-country">{{ 'soul.shop.market' | t }}</label>
      <select class="input" id="market-country" name="country_code" onchange="this.form.submit()">
        {%- for c in localization.available_countries -%}
          <option value="{{ c.iso_code }}"{% if c.iso_code == localization.country.iso_code %} selected{% endif %}>{{ c.name }} · {{ c.currency.iso_code }} {{ c.currency.symbol }}</option>
        {%- endfor -%}
      </select>
      <noscript><button class="btn btn-sm" type="submit">{{ 'soul.shop.update' | t }}</button></noscript>
    {%- endform -%}
    {%- endif -%}
    <div class="made">""", 1)
w("sections/footer.liquid", t + schema("footer", "Footer", "Subsol",
  [{"type": "link_list", "id": "menu", "label": L("sections.footer.menu", "Extra links menu", "Meniu cu linkuri în plus")}],
  presets=False, extra={"enabled_on": {"groups": ["footer"]}}, tag="div"))

# ---------------- sticky cta (mobile dock)
t = price_fix(res_links(SECTIONS["sticky-cta"]))
w("sections/sticky-cta.liquid", HOME_ASSIGN + "{%- if settings.prelaunch -%}\n" + t + "\n{%- endif -%}" + schema("sticky_cta", "Mobile bottom bar", "Bară mobilă jos", presets=False,
  extra={"enabled_on": {"groups": ["footer"]}}, tag="div"))

# ---------------- waitlist: section + snippet with {% form 'customer' %}
t = SECTIONS["waitlist"]
form_old = re.search(r'<form class="form" id="waitlist".*?</form>\s*<div class="thanks".*?</div>\s*</div>', t, re.S).group(0)
form_html = re.search(r'<form class="form" id="waitlist".*?</form>', t, re.S).group(0)
thanks_html = re.search(r'<div class="thanks".*?</dl>', t, re.S).group(0)
inner = form_html[form_html.index(">") + 1: form_html.rindex("</form>")]
inner = re.sub(r'\s*<input type="hidden" name="form_type"[^>]*>\s*<input type="hidden" name="utf8"[^>]*>', "", inner)
inner = re.sub(r'<input type="hidden" name="contact\[tags\]"[^>]*>',
               '<input type="hidden" name="contact[tags]" id="wl-tags" value="{{ settings.waitlist_tag | default: \'waitlist\' }},colour-{{ colour | default: \'silver\' }},lang-{{ request.locale.iso_code }}">', inner)
inner = inner.replace('<select class="input" id="wl-lang" name="contact[note][language]">\n              <option value="en">English</option>\n              <option value="ro">Română</option>',
                      '<select class="input" id="wl-lang">\n              <option value="en"{% if request.locale.iso_code == \'en\' %} selected{% endif %}>English</option>\n              <option value="ro"{% if request.locale.iso_code == \'ro\' %} selected{% endif %}>Română</option>')
assert 'id="wl-lang">' in inner
inner = re.sub(r'<fieldset class="field">\s*<legend data-i18n="res.colour">.*?</fieldset>', lambda m: "{%- if show_colours -%}\n        " + m.group(0) + "\n        {%- endif -%}", inner, flags=re.S)
inner = inner.replace('<input id="wl-web" name="website"', '<input id="wl-web"')
inner = inner.replace('<p class="form-msg" id="wl-msg" role="alert"></p>',
                      '<p class="form-msg" id="wl-msg" role="alert">{%- if form.errors -%}{{ form.errors | default_errors }}{%- endif -%}</p>')
thanks = thanks_html.replace(" hidden tabindex", " tabindex")
thanks = re.sub(r"\s*<dl>.*?</dl>", "", thanks, flags=re.S)
thanks += """
          <p class="form-fine">{{ 'soul.res_sent' | t }}</p>
        </div>"""
snippet = """{%- comment -%}
  SOUL waitlist = Shopify customer form. Creates a customer with email marketing consent and tags:
  waitlist, colour-<silver|graphite|midnight|ember|champagne>, lang-<en|ro>.
  Params: show_colours (bool), colour (default colour key).
  Export: Admin > Customers > filter "Tagged with: waitlist" > Export.
{%- endcomment -%}
{%- liquid
  assign privacy_url = shop.privacy_policy.url | default: '/policies/privacy-policy'
-%}
{%- form 'customer', id: 'waitlist', class: 'form', novalidate: 'novalidate', data-native: 'true' -%}
  {%- if form.posted_successfully? -%}
        """ + thanks + """
  {%- else -%}
""" + inner + """
  {%- endif -%}
{%- endform -%}"""
w("snippets/waitlist-form.liquid", snippet)
t = t.replace(form_old, "{%- render 'waitlist-form', show_colours: true, colour: 'silver' -%}\n    </div>")
t = t.replace('<p class="eyebrow" data-i18n="res.eyebrow">', "{%- capture soul_price -%}{%- render 'soul-price' -%}{%- endcapture -%}\n        <p class=\"eyebrow\" data-i18n=\"res.eyebrow\">", 1)
w("sections/waitlist.liquid", t + schema("waitlist", "Waitlist", "Listă de așteptare", tag="div"))

EN_RAW["res.sent"] = "Saved. If you get a confirmation email, tap the link in it. We'll write when reservations open."
RO_SRC["res.sent"] = "Gata. Dacă primești un email de confirmare, apasă linkul din el. Îți scriem când se deschid rezervările."
tkey("res.sent")

# ------------------------------------------------------------------ snippets
w("snippets/soul-price.liquid", """{%- comment -%} "from" price of SOUL, formatted by Shopify (follows the visitor's market currency: EUR, RON). {%- endcomment -%}
{%- liquid
  if settings.soul_product != blank
    echo settings.soul_product.price_min | money_without_trailing_zeros
  else
    assign cents = settings.fallback_price | times: 100
    echo cents | money_without_trailing_zeros
  endif
-%}""")
w("snippets/soul-company.liquid", """{%- comment -%}Company identity lines for the footer and the legal page. Fill them in Theme settings > Company (legal).{%- endcomment -%}
{%- if settings.company_address != blank -%}{{ 'soul.f_addr' | t }} {{ settings.company_address | escape }}<br>{%- endif -%}
{%- if settings.company_cui != blank -%}{{ 'soul.f_cui' | t }} {{ settings.company_cui | escape }} · {% endif -%}
{%- if settings.company_reg != blank -%}{{ 'soul.f_reg' | t }} {{ settings.company_reg | escape }}<br>{%- endif -%}
{%- if settings.company_address == blank or settings.company_cui == blank or settings.company_reg == blank -%}{{ 'soul.f_copending' | t }}<br>{%- endif -%}
{{ 'soul.f_contact' | t }} {% if settings.contact_email != blank -%}<a class="email" href="mailto:{{ settings.contact_email }}">{{ settings.contact_email }}</a>{%- else -%}<a class="email" href="{{ routes.root_url }}">{{ shop.name }}</a>{%- endif -%}""")
w("snippets/meta-tags.liquid", """{%- liquid
  assign og_title = page_title | default: shop.name
  assign og_desc = page_description | default: shop.description | default: settings.share_description
  assign og_type = 'website'
  if request.page_type == 'product'
    assign og_type = 'product'
  endif
-%}
<meta property="og:site_name" content="{{ shop.name | escape }}">
<meta property="og:url" content="{{ canonical_url }}">
<meta property="og:title" content="{{ og_title | escape }}">
<meta property="og:type" content="{{ og_type }}">
<meta property="og:description" content="{{ og_desc | escape }}">
{%- if page_image -%}
<meta property="og:image" content="https:{{ page_image | image_url: width: 1200 }}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="{{ 1200 | divided_by: page_image.aspect_ratio | round }}">
{%- elsif settings.share_image != blank -%}
<meta property="og:image" content="https:{{ settings.share_image | image_url: width: 1200 }}">
{%- endif -%}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ og_title | escape }}">
<meta name="twitter:description" content="{{ og_desc | escape }}">""")
w("snippets/colour-key.liquid", """{%- comment -%} Maps a colour option value (EN or RO, any case) to the theme's colour key. {%- endcomment -%}
{%- liquid
  assign h = value | handleize
  case h
    when 'silver', 'argint', 'argintiu'
      echo 'silver'
    when 'graphite', 'grafit'
      echo 'graphite'
    when 'midnight', 'albastru-noapte', 'miez-de-noapte'
      echo 'midnight'
    when 'ember', 'jar'
      echo 'ember'
    when 'champagne', 'sampanie', 'șampanie'
      echo 'champagne'
    else
      echo h
  endcase
-%}""")

# ------------------------------------------------------------------ main-product
COLHEX = {"silver": "#CBCDCF", "graphite": "#55575B", "midnight": "#26324C", "ember": "#D2622C", "champagne": "#D8C3A2"}
main_product = """{%- liquid
  assign current = product.selected_or_first_available_variant
  assign colour_index = nil
  for option in product.options_with_values
    assign on = option.name | downcase
    if on == 'colour' or on == 'color' or on == 'culoare' or on == 'culoarea'
      assign colour_index = forloop.index0
    endif
  endfor
  assign colour = 'silver'
  if colour_index != nil
    capture colour
      render 'colour-key', value: current.options[colour_index]
    endcapture
  endif
  assign known = 'silver,graphite,midnight,ember,champagne' | split: ','
  unless known contains colour
    assign colour = 'silver'
  endunless
  assign prelaunch = settings.prelaunch
  if current.available == false
    assign prelaunch = true
  endif
-%}
<section class="sec pdp" id="product" aria-labelledby="pdp-title" data-section="{{ section.id }}">
  <div class="wrap pdp-grid">
    <div class="pdp-media">
      <div class="cfg-stage" id="cfg-stage" style="--tint:{{ colour_hex[colour] }}">
        <span class="tag" data-i18n="fig.render">{{ 'soul.fig_render' | t }}</span>
        <span class="floor" aria-hidden="true"></span>
        <div class="shot" data-glass="col" data-col="{{ colour }}" data-design="original" data-role="cfg" id="cfg-shot">
          {%- capture s1 -%}col-{{ colour }}-520.webp{%- endcapture -%}
          {%- capture s2 -%}col-{{ colour }}-900.webp{%- endcapture -%}
          <img id="cfg-img" src="{{ s2 | asset_url }}" srcset="{{ s1 | asset_url }} 520w, {{ s2 | asset_url }} 900w" sizes="(max-width:860px) 74vw, 440px" width="900" height="1081" fetchpriority="high" decoding="async" alt="{{ product.title | escape }} · {{ current.title | escape }}">
        </div>
      </div>
      {%- if product.media.size > 0 -%}
      <ul class="pdp-thumbs" aria-label="{{ 'soul.shop.gallery' | t }}">
        {%- for media in product.media -%}
          {%- if media.media_type == 'image' -%}
          <li>{{ media.preview_image | image_url: width: 1200 | image_tag: widths: '360, 600, 900, 1200', sizes: '(max-width:860px) 45vw, 260px', loading: 'lazy', alt: media.alt }}</li>
          {%- endif -%}
        {%- endfor -%}
      </ul>
      {%- endif -%}
    </div>
    <div class="pdp-info">
      <p class="eyebrow">{{ 'soul.hero_sayk' | t }}</p>
      <h1 class="h-l" id="pdp-title">{{ product.title | escape }}</h1>
      <p class="pdp-price" data-pdp-price>
        {%- if product.price_varies -%}<span>{{ 'soul.price_from' | t }}</span> {%- endif -%}
        <b>{{ current.price | money_without_trailing_zeros }}</b>
      </p>
      {%- if settings.prelaunch -%}<p class="pdp-note">{{ 'soul.ann_html' | t }}</p>{%- endif -%}

      {%- unless product.has_only_default_variant -%}
      <div class="pdp-options" data-options>
        {%- for option in product.options_with_values -%}
        <fieldset class="field">
          <legend>{{ option.name | escape }}: <b data-opt-label="{{ forloop.index0 }}">{{ option.selected_value | escape }}</b></legend>
          <div class="swatches">
          {%- assign oi = forloop.index0 -%}
          {%- for value in option.values -%}
            {%- if oi == colour_index -%}
              {%- capture key -%}{%- render 'colour-key', value: value -%}{%- endcapture -%}
              {%- assign hex = colour_hex[key] -%}
              {%- if value.swatch.color -%}{%- assign hex = value.swatch.color -%}{%- endif -%}
              <input class="sw" type="radio" name="opt-{{ oi }}" value="{{ key }}" data-index="{{ oi }}" data-value="{{ value | escape }}" style="--c:{{ hex | default: '#CBCDCF' }}" aria-label="{{ value | escape }}"{% if option.selected_value == value %} checked{% endif %}>
            {%- else -%}
              <label class="pill-opt"><input type="radio" name="opt-{{ oi }}" value="{{ value | escape }}" data-index="{{ oi }}" data-value="{{ value | escape }}"{% if option.selected_value == value %} checked{% endif %}><span>{{ value | escape }}</span></label>
            {%- endif -%}
          {%- endfor -%}
          </div>
        </fieldset>
        {%- endfor -%}
      </div>
      {%- endunless -%}

      {%- if prelaunch -%}
      <div class="reserve pdp-wl" id="reserve">
        <h2 class="h-m" data-i18n="res.h2">{{ 'soul.res_h2' | t }}</h2>
        <p class="lead" data-i18n="res.lead">{{ 'soul.res_lead' | t }}</p>
        {%- render 'waitlist-form', show_colours: false, colour: colour -%}
      </div>
      {%- else -%}
      {%- form 'product', product, id: 'pdp-form', class: 'pdp-form', novalidate: 'novalidate', data-type: 'add-to-cart-form' -%}
        <input type="hidden" name="id" value="{{ current.id }}" data-variant-id>
        <button class="btn" type="submit" name="add" data-add{% unless current.available %} disabled{% endunless %}>
          <span data-add-label>{%- if current.available -%}{{ 'soul.shop.add' | t }}{%- else -%}{{ 'soul.shop.sold_out' | t }}{%- endif -%}</span><span class="arr" aria-hidden="true">→</span>
        </button>
        <p class="form-msg" role="alert" data-add-error></p>
      {%- endform -%}
      {%- endif -%}

      {%- if product.description != blank -%}
      <div class="pdp-desc rte">{{ product.description }}</div>
      {%- endif -%}
      <dl class="facts">
        <div><dt data-i18n="obj.k1">{{ 'soul.obj_k1' | t }}</dt><dd>90 × 101 × 31.5 mm</dd></div>
        <div><dt data-i18n="obj.k2">{{ 'soul.obj_k2' | t }}</dt><dd data-i18n="obj.v2">{{ 'soul.obj_v2' | t }}</dd></div>
        <div><dt data-i18n="obj.k3">{{ 'soul.obj_k3' | t }}</dt><dd data-i18n="obj.v3">{{ 'soul.obj_v3' | t }}</dd></div>
        <div><dt data-i18n="obj.k4">{{ 'soul.obj_k4' | t }}</dt><dd data-i18n="obj.v4">{{ 'soul.obj_v4' | t }}</dd></div>
      </dl>
    </div>
  </div>
  <script type="application/json" data-product-json>
    {
      "colourIndex": {% if colour_index != nil %}{{ colour_index }}{% else %}null{% endif %},
      "prelaunch": {% if settings.prelaunch %}true{% else %}false{% endif %},
      "variants": [
        {%- for v in product.variants -%}
        {%- capture vk -%}{%- if colour_index != nil -%}{%- render 'colour-key', value: v.options[colour_index] -%}{%- endif -%}{%- endcapture -%}
        {"id": {{ v.id }}, "options": {{ v.options | json }}, "available": {{ v.available | json }}, "price": {{ v.price | money_without_trailing_zeros | json }}, "colour": {{ vk | json }}}{% unless forloop.last %},{% endunless %}
        {%- endfor -%}
      ],
      "labels": {"add": {{ 'soul.shop.add' | t | json }}, "soldOut": {{ 'soul.shop.sold_out' | t | json }}}
    }
  </script>
  {{ product | structured_data | default: '' }}
</section>
"""
colour_hex_liquid = "{%- liquid\n" + "".join(f"  assign colour_hex_{k} = '{v}'\n" for k, v in COLHEX.items()) + "-%}\n"
# Liquid has no hash literal: resolve colour_hex[key] via a lookup string instead
main_product = main_product.replace("{{ colour_hex[colour] }}", "{%- render 'colour-hex', key: colour -%}")
main_product = main_product.replace("{%- assign hex = colour_hex[key] -%}", "{%- capture hex -%}{%- render 'colour-hex', key: key -%}{%- endcapture -%}")
w("snippets/colour-hex.liquid", "{%- case key -%}" + "".join(f"{{%- when '{k}' -%}}{v}" for k, v in COLHEX.items()) + "{%- else -%}#CBCDCF{%- endcase -%}")
main_product += schema("main_product", "Product: SOUL", "Produs: SOUL", presets=False, extra={"enabled_on": {"templates": ["product"]}}, tag="div")
w("sections/main-product.liquid", main_product)

# ------------------------------------------------------------------ simple sections
def simple(name, en, ro, body, templates=None, settings=None):
    extra = {"enabled_on": {"templates": templates}} if templates else None
    w(f"sections/{name}.liquid", body + schema(name.replace("-", "_"), en, ro, settings, presets=False, extra=extra, tag="div"))

simple("main-page", "Page", "Pagină", """<section class="sec page-sec{% if section.settings.narrow %} page-legal{% endif %}">
  <div class="wrap">
    <div class="head">
      {%- if section.settings.eyebrow != blank -%}<p class="eyebrow">{{ section.settings.eyebrow | escape }}</p>{%- endif -%}
      <h1 class="h-l">{{ page.title | escape }}</h1>
    </div>
    {%- if section.settings.image != blank -%}
      <figure class="frame page-img">{{ section.settings.image | image_url: width: 1600 | image_tag: widths: '600, 900, 1200, 1600', sizes: '(max-width:1240px) calc(100vw - 32px), 1144px', loading: 'lazy' }}</figure>
    {%- endif -%}
    <div class="rte prose">{{ page.content }}</div>
    {%- if section.settings.company -%}
    <div class="legal page-company">
      <div>
        <h2 class="h-m">{{ 'soul.f_company' | t }}</h2>
        <p>{{ settings.company_name | escape }} · {{ 'soul.f_city' | t }}<br>{%- render 'soul-company' -%}</p>
      </div>
    </div>
    {%- endif -%}
  </div>
</section>""", settings=[
    {"type": "text", "id": "eyebrow", "label": L("sections.main_page.eyebrow", "Small label above the title", "Etichetă mică deasupra titlului")},
    {"type": "image_picker", "id": "image", "label": L("sections.main_page.image", "Image", "Imagine")},
    {"type": "checkbox", "id": "narrow", "default": False, "label": L("sections.main_page.narrow", "Legal layout (narrow text)", "Aspect legal (text îngust)")},
    {"type": "checkbox", "id": "company", "default": False, "label": L("sections.main_page.company", "Show company details", "Arată datele firmei")}])

simple("main-404", "404", "404", """<section class="sec page-sec"><div class="wrap"><div class="head">
  <p class="eyebrow">404</p><h1 class="h-l">{{ 'soul.shop.nf_title' | t }}</h1><p class="lead">{{ 'soul.shop.nf_text' | t }}</p>
  <div class="cta"><a class="btn" href="{{ routes.root_url }}">{{ 'soul.shop.home' | t }}</a></div>
</div></div></section>""", ["404"])

simple("main-search", "Search results", "Rezultate căutare", """<section class="sec page-sec"><div class="wrap">
  <div class="head"><h1 class="h-l">{{ 'soul.shop.search' | t }}</h1></div>
  <form class="chipform" action="{{ routes.search_url }}" method="get" role="search">
    <label class="sr" for="q">{{ 'soul.shop.search' | t }}</label>
    <input class="input" id="q" type="search" name="q" value="{{ search.terms | escape }}">
    <button class="btn btn-sm" type="submit">{{ 'soul.shop.search' | t }}</button>
  </form>
  {%- if search.performed -%}
    {%- paginate search.results by 24 -%}
    <ul class="list-grid">
      {%- for item in search.results -%}
      <li><a href="{{ item.url }}">{%- if item.featured_image -%}{{ item.featured_image | image_url: width: 600 | image_tag: widths: '300, 600', sizes: '280px', loading: 'lazy' }}{%- endif -%}<b>{{ item.title | escape }}</b></a></li>
      {%- else -%}
      <li>{{ 'soul.shop.no_results' | t }}</li>
      {%- endfor -%}
    </ul>
    {{ paginate | default_pagination }}
    {%- endpaginate -%}
  {%- endif -%}
</div></section>""", ["search"])

GRID_PRODUCTS = """<ul class="list-grid">
      {%- for p in PRODUCTS -%}
      <li><a href="{{ p.url }}">{%- if p.featured_image -%}{{ p.featured_image | image_url: width: 600 | image_tag: widths: '300, 600', sizes: '280px', loading: 'lazy' }}{%- endif -%}<b>{{ p.title | escape }}</b><span>{{ 'soul.price_from' | t }} {{ p.price_min | money_without_trailing_zeros }}</span></a></li>
      {%- else -%}
      <li>{{ 'soul.shop.empty' | t }}</li>
      {%- endfor -%}
    </ul>"""
simple("main-collection", "Collection", "Colecție", """<section class="sec page-sec"><div class="wrap">
  <div class="head"><h1 class="h-l">{{ collection.title | escape }}</h1>{%- if collection.description != blank -%}<div class="lead rte">{{ collection.description }}</div>{%- endif -%}</div>
  {%- paginate collection.products by 24 -%}
    """ + GRID_PRODUCTS.replace("PRODUCTS", "collection.products") + """
    {{ paginate | default_pagination }}
  {%- endpaginate -%}
</div></section>""", ["collection"])

simple("main-list-collections", "Collections list", "Listă colecții", """<section class="sec page-sec"><div class="wrap">
  <div class="head"><h1 class="h-l">{{ 'soul.shop.collections' | t }}</h1></div>
  <ul class="list-grid">
    {%- for c in collections -%}
    <li><a href="{{ c.url }}">{%- if c.featured_image -%}{{ c.featured_image | image_url: width: 600 | image_tag: widths: '300, 600', sizes: '280px', loading: 'lazy' }}{%- endif -%}<b>{{ c.title | escape }}</b></a></li>
    {%- endfor -%}
  </ul>
</div></section>""", ["list-collections"])

simple("main-blog", "Blog", "Blog", """<section class="sec page-sec"><div class="wrap">
  <div class="head"><h1 class="h-l">{{ blog.title | escape }}</h1></div>
  {%- paginate blog.articles by 12 -%}
  <ul class="list-grid">
    {%- for article in blog.articles -%}
    <li><a href="{{ article.url }}">{%- if article.image -%}{{ article.image | image_url: width: 600 | image_tag: widths: '300, 600', sizes: '280px', loading: 'lazy' }}{%- endif -%}<b>{{ article.title | escape }}</b><span>{{ article.published_at | time_tag: format: 'date' }}</span></a></li>
    {%- endfor -%}
  </ul>
  {{ paginate | default_pagination }}
  {%- endpaginate -%}
</div></section>""", ["blog"])

simple("main-article", "Article", "Articol", """<article class="sec page-sec page-legal"><div class="wrap">
  <div class="head"><p class="eyebrow">{{ article.published_at | time_tag: format: 'date' }}</p><h1 class="h-l">{{ article.title | escape }}</h1></div>
  {%- if article.image -%}<figure class="frame page-img">{{ article.image | image_url: width: 1600 | image_tag: widths: '600, 900, 1200, 1600', sizes: '(max-width:1240px) calc(100vw - 32px), 1144px' }}</figure>{%- endif -%}
  <div class="rte prose">{{ article.content }}</div>
</div></article>""", ["article"])

simple("main-cart", "Cart", "Coș", """<section class="sec page-sec"><div class="wrap">
  <div class="head"><h1 class="h-l">{{ 'soul.shop.cart' | t }}</h1></div>
  {%- if settings.prelaunch -%}
    <p class="lead">{{ 'soul.shop.cart_prelaunch' | t }}</p>
    <div class="cta"><a class="btn" href="{{ routes.root_url }}#reserve">{{ 'soul.hero_cta' | t }}</a></div>
  {%- elsif cart.item_count == 0 -%}
    <p class="lead">{{ 'soul.shop.cart_empty' | t }}</p>
  {%- else -%}
    <form action="{{ routes.cart_url }}" method="post" class="cart-form">
      <ul class="cart-lines">
        {%- for item in cart.items -%}
        <li>
          {%- if item.image -%}{{ item.image | image_url: width: 240 | image_tag: widths: '120, 240', sizes: '96px', loading: 'lazy', alt: item.title }}{%- endif -%}
          <div><a href="{{ item.url }}"><b>{{ item.product.title | escape }}</b></a>{%- unless item.product.has_only_default_variant -%}<small>{{ item.variant.title | escape }}</small>{%- endunless -%}</div>
          <label class="sr" for="qty-{{ forloop.index }}">{{ 'soul.shop.qty' | t }}</label>
          <input class="input qty" id="qty-{{ forloop.index }}" type="number" name="updates[]" value="{{ item.quantity }}" min="0">
          <span class="money">{{ item.final_line_price | money }}</span>
          <a href="{{ item.url_to_remove }}" class="rm">{{ 'soul.shop.remove' | t }}</a>
        </li>
        {%- endfor -%}
      </ul>
      <p class="cart-total">{{ 'soul.shop.subtotal' | t }} <b>{{ cart.total_price | money_with_currency }}</b></p>
      <p class="cap">{{ 'soul.shop.taxes' | t }}</p>
      <div class="cta"><button class="btn btn-ghost" type="submit" name="update">{{ 'soul.shop.update' | t }}</button><button class="btn" type="submit" name="checkout">{{ 'soul.shop.checkout' | t }}</button></div>
    </form>
  {%- endif -%}
</div></section>""", ["cart"])

# cart drawer (rendered only after launch; behind the prelaunch setting)
w("sections/cart-drawer.liquid", """<div class="drawer" id="cart-drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title" hidden>
  <div class="drawer-bg" data-cart-close></div>
  <div class="drawer-panel">
    <div class="drawer-head"><h2 class="h-m" id="drawer-title">{{ 'soul.shop.cart' | t }}</h2><button class="btn btn-ghost btn-sm" type="button" data-cart-close>{{ 'soul.shop.close' | t }}</button></div>
    {%- if cart.item_count == 0 -%}
      <p class="lead">{{ 'soul.shop.cart_empty' | t }}</p>
    {%- else -%}
      <ul class="cart-lines">
        {%- for item in cart.items -%}
        <li>
          {%- if item.image -%}{{ item.image | image_url: width: 240 | image_tag: widths: '120, 240', sizes: '96px', loading: 'lazy', alt: item.title }}{%- endif -%}
          <div><b>{{ item.product.title | escape }}</b>{%- unless item.product.has_only_default_variant -%}<small>{{ item.variant.title | escape }}</small>{%- endunless -%}<small>× {{ item.quantity }}</small></div>
          <span class="money">{{ item.final_line_price | money }}</span>
          <a href="{{ item.url_to_remove }}" class="rm">{{ 'soul.shop.remove' | t }}</a>
        </li>
        {%- endfor -%}
      </ul>
      <p class="cart-total">{{ 'soul.shop.subtotal' | t }} <b>{{ cart.total_price | money_with_currency }}</b></p>
      <form action="{{ routes.cart_url }}" method="post"><button class="btn" type="submit" name="checkout">{{ 'soul.shop.checkout' | t }}</button></form>
    {%- endif -%}
  </div>
</div>""" + schema("cart_drawer", "Cart drawer", "Sertar coș", presets=False, tag="div"))

# gift card template (required by Shopify for gift card emails)
w("templates/gift_card.liquid", """<!doctype html>
<html lang="{{ request.locale.iso_code }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ 'soul.shop.gift_card' | t }} · {{ shop.name | escape }}</title>
  {{ 'soul.css' | asset_url | stylesheet_tag }}
  {{ content_for_header }}
</head>
<body>
  <main class="sec page-sec"><div class="wrap">
    <h1 class="h-l">{{ 'soul.shop.gift_card' | t }}</h1>
    <p class="lead">{{ gift_card.balance | money }}</p>
    <p class="mono">{{ gift_card.code | format_code }}</p>
    {%- if gift_card.expires_on -%}<p class="cap">{{ gift_card.expires_on | date: '%d.%m.%Y' }}</p>{%- endif -%}
  </div></main>
</body>
</html>""")

# ------------------------------------------------------------------ section groups + templates
def jw(path, obj):
    w(path, json.dumps(obj, ensure_ascii=False, indent=2))

jw("sections/header-group.json", {"type": "header", "name": "Header group", "sections": {
    "announcement-bar": {"type": "announcement-bar", "settings": {"text": ""}},
    "header": {"type": "header", "settings": {}}}, "order": ["announcement-bar", "header"]})
jw("sections/footer-group.json", {"type": "footer", "name": "Footer group", "sections": {
    "footer": {"type": "footer", "settings": {"menu": ""}},
    "sticky-cta": {"type": "sticky-cta", "settings": {}}}, "order": ["footer", "sticky-cta"]})

def tpl(path, order, settings=None):
    sec = {}
    for name in order:
        sid = name.replace("main-", "main_") if False else name
        sec[sid] = {"type": name, "settings": (settings or {}).get(name, {})}
    jw(f"templates/{path}", {"sections": sec, "order": order})

tpl("index.json", ["hero", "marquee", "alive", "the-object", "product-configurator", "born-ritual", "your-ai", "soulos", "ou-egg", "privacy", "specs-and-box", "faq", "waitlist"],
    {"soulos": {"demo_url": ""}})
tpl("product.json", ["main-product", "born-ritual", "your-ai", "specs-and-box", "faq"])
tpl("page.json", ["main-page"], {"main-page": {"eyebrow": "", "narrow": False, "company": False}})
tpl("page.how-it-works.json", ["main-page", "alive", "the-object", "born-ritual", "your-ai", "soulos", "ou-egg", "privacy", "waitlist"],
    {"main-page": {"eyebrow": "SOUL", "narrow": False, "company": False}, "soulos": {"demo_url": ""}})
tpl("page.faq.json", ["main-page", "faq", "waitlist"], {"main-page": {"eyebrow": "SOUL", "narrow": True, "company": False}})
tpl("page.legal.json", ["main-page"], {"main-page": {"eyebrow": "ARTEMIS DIGITAL S.R.L.", "narrow": True, "company": True}})
tpl("404.json", ["main-404"])
tpl("search.json", ["main-search"])
tpl("collection.json", ["main-collection"])
tpl("list-collections.json", ["main-list-collections"])
tpl("blog.json", ["main-blog"])
tpl("article.json", ["main-article"])
tpl("cart.json", ["main-cart"])

# ------------------------------------------------------------------ config
settings_schema = [
    {"name": "theme_info", "theme_name": "SOUL", "theme_version": "3.0.0", "theme_author": "ARTEMIS DIGITAL S.R.L.",
     "theme_documentation_url": "https://help.shopify.com/manual/online-store/themes", "theme_support_url": "https://help.shopify.com/"},
    {"name": L("settings_schema.store.name", "SOUL store", "Magazin SOUL"), "settings": [
        {"type": "checkbox", "id": "prelaunch", "default": True, "label": L("settings_schema.store.prelaunch", "Pre-launch mode (waitlist only)", "Mod prelansare (doar listă de așteptare)"),
         "info": L("settings_schema.store.prelaunch_info", "On: no add-to-cart, no cart drawer, the product page shows the waitlist. Turn off only after CE certification.", "Pornit: fără adăugare în coș, fără sertar de coș, pagina produsului arată lista de așteptare. Oprește-l doar după certificarea CE.")},
        {"type": "product", "id": "soul_product", "label": L("settings_schema.store.product", "SOUL product (for prices)", "Produsul SOUL (pentru prețuri)")},
        {"type": "number", "id": "fallback_price", "default": 249, "label": L("settings_schema.store.fallback_price", "Fallback 'from' price (store currency)", "Preț „de la” de rezervă (moneda magazinului)"),
         "info": L("settings_schema.store.fallback_info", "Used only while no product is selected above.", "Folosit doar cât timp nu e ales un produs mai sus.")},
        {"type": "text", "id": "waitlist_tag", "default": "waitlist", "label": L("settings_schema.store.tag", "Waitlist customer tag", "Eticheta clienților din listă")},
        {"type": "url", "id": "soulos_url", "label": L("settings_schema.store.soulos", "SoulOS web demo link (footer)", "Link demo SoulOS (subsol)")},
        {"type": "page", "id": "cookies_page", "label": L("settings_schema.store.cookies", "Cookies page", "Pagina despre cookie-uri")},
        {"type": "page", "id": "warranty_page", "label": L("settings_schema.store.warranty", "Warranty page (2-year legal guarantee)", "Pagina despre garanție (garanția legală de 2 ani)")}]},
    {"name": L("settings_schema.company.name", "Company (legal)", "Firma (date legale)"), "settings": [
        {"type": "text", "id": "company_name", "default": "ARTEMIS DIGITAL S.R.L.", "label": L("settings_schema.company.cname", "Company name", "Denumire firmă")},
        {"type": "text", "id": "company_address", "label": L("settings_schema.company.address", "Registered address", "Sediu social")},
        {"type": "text", "id": "company_cui", "label": L("settings_schema.company.cui", "Tax ID (CUI)", "CUI")},
        {"type": "text", "id": "company_reg", "label": L("settings_schema.company.reg", "Trade Register No.", "Nr. Reg. Com.")},
        {"type": "text", "id": "contact_email", "default": "office@krea.ro", "label": L("settings_schema.company.email", "Contact email", "Email de contact")}]},
    {"name": L("settings_schema.brand.name", "Brand and sharing", "Brand și distribuire"), "settings": [
        {"type": "image_picker", "id": "favicon", "label": L("settings_schema.brand.favicon", "Favicon (square, 512 px)", "Favicon (pătrat, 512 px)")},
        {"type": "image_picker", "id": "share_image", "label": L("settings_schema.brand.share", "Social share image (1200×630)", "Imagine pentru distribuire (1200×630)")},
        {"type": "text", "id": "share_description", "default": "A palm-sized aluminium stone with two living eyes. Your own AI, embodied.", "label": L("settings_schema.brand.desc", "Fallback share description", "Descriere de rezervă pentru distribuire")}]}
]
jw("config/settings_schema.json", settings_schema)
defaults = {"prelaunch": True, "fallback_price": 249, "waitlist_tag": "waitlist", "company_name": "ARTEMIS DIGITAL S.R.L.", "contact_email": "office@krea.ro",
            "share_description": "A palm-sized aluminium stone with two living eyes. Your own AI, embodied."}
jw("config/settings_data.json", {"current": dict(defaults), "presets": {"Default": dict(defaults)}})

# ------------------------------------------------------------------ layout
w("layout/theme.liquid", """<!doctype html>
<html lang="{{ request.locale.iso_code }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <link rel="canonical" href="{{ canonical_url }}">
  <title>{{ page_title }}{% if current_tags %} · {{ current_tags | join: ', ' }}{% endif %}{% if current_page != 1 %} · {{ current_page }}{% endif %}{% unless page_title contains shop.name %} · {{ shop.name }}{% endunless %}</title>
  {%- if page_description -%}<meta name="description" content="{{ page_description | escape }}">{%- endif -%}
  {% render 'meta-tags' %}
  <meta name="theme-color" content="#FAF8F3" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0D0D0F" media="(prefers-color-scheme: dark)">
  {%- if settings.favicon != blank -%}
  <link rel="icon" type="image/png" href="{{ settings.favicon | image_url: width: 64, height: 64 }}">
  <link rel="apple-touch-icon" href="{{ settings.favicon | image_url: width: 180, height: 180 }}">
  {%- else -%}
  <link rel="icon" type="image/svg+xml" href="{{ 'favicon.svg' | asset_url }}">
  {%- endif -%}
  {{ 'bricolage.woff2' | asset_url | preload_tag: as: 'font', type: 'font/woff2', crossorigin: 'anonymous' }}
  {%- if template.name == 'index' -%}
  {{ 'front-1200.avif' | asset_url | preload_tag: as: 'image', type: 'image/avif', fetchpriority: 'high', media: '(min-width: 721px)' }}
  {{ 'front-700.avif' | asset_url | preload_tag: as: 'image', type: 'image/avif', fetchpriority: 'high', media: '(max-width: 720px)' }}
  {%- endif -%}
  <style>
    @font-face{font-family:"Bricolage Grotesque";src:url({{ 'bricolage.woff2' | asset_url }}) format("woff2");font-weight:200 800;font-display:swap}
    @font-face{font-family:"Martian Mono";src:url({{ 'martian.woff2' | asset_url }}) format("woff2");font-weight:400 500;font-display:swap}
  </style>
  {{ 'soul.css' | asset_url | stylesheet_tag }}
  <script>
    window.SOUL_CONFIG = {
      shopify: true,
      ASSET_BASE: {{ 'col-silver-520.webp' | asset_url | split: 'col-silver-520.webp' | first | json }},
      PRICES: {},
      CURRENCY: {{ cart.currency.iso_code | json }},
      CONTACT_EMAIL: {{ settings.contact_email | default: '' | json }},
      prelaunch: {{ settings.prelaunch | json }},
      routes: { root: {{ routes.root_url | json }}, cart: {{ routes.cart_url | json }}, cartAdd: {{ routes.cart_add_url | json }} }
    };
    document.documentElement.classList.add("js");
  </script>
  {{ content_for_header }}
</head>
<body class="tpl-{{ template.name }}">
  <a class="skip" href="#main" data-i18n="skip">{{ 'soul.skip' | t }}</a>
  {% sections 'header-group' %}
  <main id="main">
    {{ content_for_layout }}
  </main>
  {% sections 'footer-group' %}
  {%- unless settings.prelaunch -%}
    {% section 'cart-drawer' %}
  {%- endunless -%}
  <script src="{{ 'eyes.js' | asset_url }}" defer></script>
  <script src="{{ 'designs.js' | asset_url }}" defer></script>
  <script src="{{ 'soul-app.js' | asset_url }}" defer></script>
  {%- if template.name == 'product' -%}<script src="{{ 'soul-product.js' | asset_url }}" defer></script>{%- endif -%}
  {%- unless settings.prelaunch -%}<script src="{{ 'soul-cart.js' | asset_url }}" defer></script>{%- endunless -%}
</body>
</html>""")

# ------------------------------------------------------------------ assets: css, js, fonts, media
css = src[src.index("<style>") + 7: src.index("</style>")]
css = re.sub(r'@font-face\{[^}]*\}', "", css)
css += open(f"{SCR}/theme-extra.css", encoding="utf-8").read()
w("assets/soul.css", css)

app = open(f"{SITE}/app.js", encoding="utf-8").read()
def rep(old, new, count=1):
    global app
    assert old in app, ("app.js patch missing", old[:60])
    app = app.replace(old, new, count)
rep('const srcset = k => `media/v3/col-${k}-520.webp 520w, media/v3/col-${k}-900.webp 900w`;',
    'const AB = CFG.ASSET_BASE || "media/v3/";\nconst srcset = k => `${AB}col-${k}-520.webp 520w, ${AB}col-${k}-900.webp 900w`;')
rep('cfgImg.src = `media/v3/col-${k}-900.webp`', 'cfgImg.src = `${AB}col-${k}-900.webp`')
rep('resImg.src = `media/v3/col-${k}-520.webp`', 'resImg.src = `${AB}col-${k}-520.webp`')
rep('$$("[data-i18n-attr]").forEach(el => el.dataset.i18nAttr.split(",").forEach(pair => { const [a, k] = pair.split(":"); EN[k] = el.getAttribute(a) || ""; }));',
    '$$("[data-i18n-attr]").forEach(el => el.dataset.i18nAttr.split(",").forEach(pair => { const [a, k] = pair.split(":"); EN[k] = el.getAttribute(a) || ""; }));\n'
    '/* Shopify: the server already rendered the visitor\'s language (locales/*.json), so the DOM is the source of truth. */\n'
    'if (CFG.shopify) Object.keys(RO).forEach(k => { delete RO[k]; });')
rep('$$(".sw").forEach(i => { const cc = COLS.find(x => x.k === i.value); i.setAttribute',
    '$$(".sw").forEach(i => { const cc = COLS.find(x => x.k === i.value); if (!cc) return; if (i.dataset.value) { i.checked = i.value === COLOUR; return; } i.setAttribute')
rep('$$(".lang button").forEach(b => b.addEventListener("click", () => applyLang(b.dataset.lang, true)));\nconst saved = store.get("soul-lang");\napplyLang(location.hash === "#ro" ? "ro" : saved === "ro" ? "ro" : "en", false);',
    'if (CFG.shopify) {\n  applyLang((document.documentElement.lang || "en").slice(0, 2) === "ro" ? "ro" : "en", false);\n} else {\n'
    '$$(".lang button").forEach(b => b.addEventListener("click", () => applyLang(b.dataset.lang, true)));\nconst saved = store.get("soul-lang");\napplyLang(location.hash === "#ro" ? "ro" : saved === "ro" ? "ro" : "en", false);\n}\n'
    'window.SOUL_setColour = k => setColour(k, "product");')
rep('const links = $$(".nav-links a"), secs = links.map(a => $(a.getAttribute("href"))).filter(Boolean);',
    'const links = $$(".nav-links a").filter(a => (a.getAttribute("href") || "")[0] === "#"), secs = links.map(a => $(a.getAttribute("href"))).filter(Boolean);')
rep('let COLOUR = "silver";', 'let COLOUR = (CFG.shopify && document.querySelector("#cfg-shot") && document.querySelector("#cfg-shot").dataset.col) || "silver";')
w("assets/soul-app.js", app)
shutil.copy(f"{SCR}/soul-product.js", f"{OUT}/assets/soul-product.js")
shutil.copy(f"{SCR}/soul-cart.js", f"{OUT}/assets/soul-cart.js")
shutil.copy(f"{ROOT}/eyes/eyes.js", f"{OUT}/assets/eyes.js")
shutil.copy(f"{ROOT}/eyes/designs.js", f"{OUT}/assets/designs.js")
shutil.copy(f"{SITE}/favicon.svg", f"{OUT}/assets/favicon.svg")
for f in ["bricolage.woff2", "martian.woff2"]:
    shutil.copy(f"{SITE}/fonts/{f}", f"{OUT}/assets/{f}")
for name, p in ASSET_FILES.items():
    shutil.copy(p, f"{OUT}/assets/{name}")

# ------------------------------------------------------------------ locales
for k in list(EN_RAW):
    if k in KEYMAP or True:
        tkey(k)
SHOP = json.load(open(f"{SCR}/shop-strings.json", encoding="utf-8"))
def build_locale(src_dict, lang):
    soul = {}
    for k, nk in KEYMAP.items():
        v = src_dict.get(k, EN_RAW.get(k))
        soul[nk] = v
    soul["shop"] = SHOP[lang]
    return {"soul": soul}
jw("locales/en.default.json", build_locale(EN_RAW, "en"))
jw("locales/ro.json", build_locale(RO_SRC, "ro"))
jw("locales/en.default.schema.json", SCHEMA_EN)
jw("locales/ro.schema.json", SCHEMA_RO)

# sanity: every t key used exists
used = set()
for dp, _, fs in os.walk(OUT):
    for f in fs:
        if f.endswith(".liquid"):
            used |= set(re.findall(r"'soul\.([a-z0-9_.]+)' \| t", open(os.path.join(dp, f), encoding="utf-8").read()))
loc = json.load(open(f"{OUT}/locales/en.default.json", encoding="utf-8"))["soul"]
def has(path):
    d = loc
    for p in path.split("."):
        if not isinstance(d, dict) or p not in d:
            return False
        d = d[p]
    return True
miss = sorted(k for k in used if not has(k))
print("missing keys:", miss)
print("assets:", len(os.listdir(f"{OUT}/assets")), "keys:", len(KEYMAP))
