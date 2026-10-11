// pulls the Romanian dictionary out of site/app.js into ro.json (input for build_theme.py)
const fs = require("fs"), path = require("path");
const s = fs.readFileSync(path.join(__dirname, "../../site/app.js"), "utf8");
const a = s.indexOf("const RO = {"), b = s.indexOf("const COLS = [");
const RO = eval("(" + s.slice(a + 11, b).trim().replace(/;$/, "") + ")");
fs.writeFileSync(path.join(__dirname, "ro.json"), JSON.stringify(RO, null, 1));
