/* SOUL product page: variant picker (colour swatches + other options) -> hidden variant id, price, URL, live stage colour. */
(() => {
"use strict";
const root = document.querySelector("[data-product-json]");
if (!root) return;
let data; try { data = JSON.parse(root.textContent); } catch (e) { return; }
const sec = root.closest("section");
const inputs = [...sec.querySelectorAll("[data-options] input[type=radio]")];
const idInput = sec.querySelector("[data-variant-id]");
const priceEl = sec.querySelector("[data-pdp-price] b");
const addBtn = sec.querySelector("[data-add]"), addLabel = sec.querySelector("[data-add-label]");
function selected() {
  const opts = [];
  inputs.forEach(i => { if (i.checked) opts[+i.dataset.index] = i.dataset.value; });
  return opts;
}
function update() {
  const opts = selected();
  const v = data.variants.find(x => x.options.every((o, i) => opts[i] == null || o === opts[i]));
  opts.forEach((o, i) => { const l = sec.querySelector(`[data-opt-label="${i}"]`); if (l) l.textContent = o; });
  if (!v) return;
  if (idInput) idInput.value = v.id;
  if (priceEl) priceEl.textContent = v.price;
  if (addBtn) { addBtn.disabled = !v.available; if (addLabel) addLabel.textContent = v.available ? data.labels.add : data.labels.soldOut; }
  try { const u = new URL(location.href); u.searchParams.set("variant", v.id); history.replaceState(null, "", u); } catch (e) {}
  if (v.colour && window.SOUL_setColour) window.SOUL_setColour(v.colour);
}
inputs.forEach(i => i.addEventListener("change", update));
})();
