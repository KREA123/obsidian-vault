/* SOUL cart drawer: only loaded when pre-launch mode is OFF (theme setting). Adds to cart via AJAX and refreshes the drawer section. */
(() => {
"use strict";
const R = (window.SOUL_CONFIG || {}).routes || { root: "/", cartAdd: "/cart/add" };
const drawer = () => document.getElementById("cart-drawer");
let lastFocus = null;
function open() { const d = drawer(); if (!d) return false; lastFocus = document.activeElement; d.hidden = false; const b = d.querySelector("[data-cart-close]:not(.drawer-bg)"); if (b) b.focus(); return true; }
function close() { const d = drawer(); if (!d) return; d.hidden = true; if (lastFocus) lastFocus.focus(); }
async function refresh() {
  const r = await fetch(R.root.replace(/\/?$/, "/") + "?sections=cart-drawer");
  const j = await r.json(); const d = drawer();
  if (d && j["cart-drawer"]) { const tmp = document.createElement("div"); tmp.innerHTML = j["cart-drawer"]; const nd = tmp.querySelector("#cart-drawer"); if (nd) d.innerHTML = nd.innerHTML; }
  const c = await (await fetch(R.cart + ".js")).json();
  document.querySelectorAll("[data-cart-count]").forEach(el => { el.textContent = c.item_count; });
}
document.addEventListener("click", e => {
  if (e.target.closest("[data-cart-close]")) { close(); return; }
  const o = e.target.closest("[data-cart-open]"); if (o && open()) e.preventDefault();
});
document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
const form = document.getElementById("pdp-form");
if (form) form.addEventListener("submit", async e => {
  e.preventDefault();
  const btn = form.querySelector("[data-add]"), err = form.querySelector("[data-add-error]");
  if (btn) btn.disabled = true; if (err) err.textContent = "";
  try {
    const r = await fetch(R.cartAdd + ".js", { method: "POST", headers: { Accept: "application/json" }, body: new FormData(form) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.description || j.message || "error");
    await refresh(); open();
  } catch (x) { if (err) err.textContent = x.message; }
  if (btn) btn.disabled = false;
});
})();
