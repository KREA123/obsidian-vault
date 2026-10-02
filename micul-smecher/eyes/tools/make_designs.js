// Builds designs.json + designs.js: the SOUL eye collection (#001-#120).
// Every row below is hand-picked; nothing is randomly combined.
//   node tools/make_designs.js
const fs = require('fs');
const path = require('path');

const SHAPES = {
  egg: { type: 'egg', rx: 0.163, ry: 0.2, spacing: 0.19, y: 0.005, egg: 0.09, lean: 0.13 },
  round: { type: 'egg', rx: 0.172, ry: 0.172, spacing: 0.193, y: 0.005, egg: 0, lean: 0 },
  wide: { type: 'egg', rx: 0.19, ry: 0.142, spacing: 0.205, y: 0.01, egg: 0.03, lean: 0.06 },
  tall: { type: 'egg', rx: 0.13, ry: 0.215, spacing: 0.158, y: 0, egg: 0.06, lean: 0.1 },
  drop: { type: 'drop', rx: 0.165, ry: 0.195, spacing: 0.19, y: 0.01, lean: 0.24 },
  squircle: { type: 'squircle', n: 3.6, rx: 0.155, ry: 0.172, spacing: 0.185, y: 0.005, lean: 0.06 },
  crescent: { type: 'crescent', rx: 0.172, ry: 0.185, spacing: 0.195, y: 0.02, dip: 0.36, lean: 0.06 },
  almond: { type: 'almond', rx: 0.185, ry: 0.15, spacing: 0.205, y: 0.01, q: 0.55, flick: 0.2, lean: 0.05 },
};
const PUPIL = {
  round: {},
  pebble: { rx: 0.44, ry: 0.46 },
  slit: { rx: 0.5, ry: 0.62, inset: 0.05, travel: 0.4 },
  ring: { rx: 0.44, ry: 0.48 },
  double: { rx: 0.44, ry: 0.46 },
  crescent: { rx: 0.44, ry: 0.5 },
  plus: { rx: 0.4, ry: 0.4 },
  star: { rx: 0.42, ry: 0.42 },
  heart: { rx: 0.4, ry: 0.4 },
  diamond: { rx: 0.38, ry: 0.48 },
  spiral: { rx: 0.42, ry: 0.42 },
};

// [name, shape, white, pupilL, pupilR, pupilType, extra]
const COMMON = [
  ['Original', 'egg', '#FFF0C8', '#2440FF', '#FF5A1F', 'round'],
  ['Tangerine Dream', 'egg', '#FF9A3D', '#1B2BFF', '#6A2BFF', 'round'],
  ['Bucharest Night', 'egg', '#7FC8FF', '#FFE14A', '#FF3FA4', 'round'],
  ['Mint Condition', 'round', '#3DFFC8', '#6A2BFF', '#6A2BFF', 'round'],
  ['Lemonade Stand', 'egg', '#F0FF2E', '#FF2E5B', '#FF2E5B', 'round'],
  ['Bubblegum Bus', 'round', '#FF8AD8', '#2440FF', '#2440FF', 'round'],
  ['Pistachio', 'wide', '#A8FF3D', '#7A2BFF', '#FF2E5B', 'round'],
  ['Swimming Pool', 'egg', '#2BD9FF', '#FFE14A', '#FFE14A', 'round'],
  ['Peach Crate', 'round', '#FFB38A', '#2440FF', '#00A35C', 'round'],
  ['Milk Tooth', 'egg', '#F4F4F4', '#111111', '#111111', 'round'],
  ['Lilac Hour', 'egg', '#C79BFF', '#FFE14A', '#14E6FF', 'round'],
  ['Coral Snorkel', 'wide', '#FF6B6B', '#14E6FF', '#14E6FF', 'round'],
  ['Sunday Toast', 'round', '#FFD23A', '#5A2A10', '#5A2A10', 'pebble'],
  ['Ski Lift', 'tall', '#7FC8FF', '#FF5A1F', '#FF5A1F', 'round'],
  ['Rose Petal', 'egg', '#FF9EBB', '#5A0E5E', '#5A0E5E', 'pebble'],
  ['Lime Soda', 'round', '#A8FF3D', '#FF1F8F', '#2440FF', 'round'],
  ['Arcade Token', 'egg', '#FFD23A', '#6A2BFF', '#FF2E5B', 'round'],
  ['Tram 41', 'wide', '#FF4B4B', '#FFE14A', '#FFE14A', 'round'],
  ['Snow Day', 'tall', '#F4F4F4', '#2440FF', '#2440FF', 'round'],
  ['Watermelon', 'egg', '#FF6B8A', '#0E7A3A', '#0E7A3A', 'pebble'],
  ['Blue Raspberry', 'round', '#5C8BFF', '#FFE14A', '#FF9A3D', 'round'],
  ['Matcha Latte', 'egg', '#B8F07A', '#3A2A10', '#3A2A10', 'round'],
  ['Highlighter', 'wide', '#E8FF3A', '#FF1F8F', '#FF1F8F', 'round'],
  ['Flamingo Float', 'egg', '#FF8AD8', '#14E6FF', '#FFE14A', 'round'],
  ['Apricot Jam', 'round', '#FF9A3D', '#5A0E5E', '#5A0E5E', 'pebble'],
  ['Glacier', 'tall', '#BDF4FF', '#1B2BFF', '#6A2BFF', 'round'],
  ['Sherbet', 'egg', '#FFC38A', '#FF1F8F', '#2440FF', 'round'],
  ['Pea Pod', 'round', '#7CFF8A', '#111111', '#111111', 'round'],
  ['Grape Soda', 'egg', '#B57BFF', '#F0FF2E', '#F0FF2E', 'round'],
  ['Neon Taxi', 'wide', '#FFD23A', '#111111', '#111111', 'round'],
  ['Cotton Candy', 'round', '#FFB3E6', '#2BD9FF', '#B57BFF', 'round'],
  ['Danube Blue', 'egg', '#3FA9FF', '#FFF0C8', '#FFF0C8', 'round'],
  ['Pumpkin Patch', 'egg', '#FF7A1A', '#1A1A1A', '#1A1A1A', 'pebble'],
  ['Spring Onion', 'tall', '#C6FF5C', '#2440FF', '#FF2E5B', 'round'],
  ['Marshmallow', 'round', '#FFF6EC', '#FF5A1F', '#FF5A1F', 'pebble'],
  ['Fizzy Cola', 'egg', '#FF4B4B', '#FFF0C8', '#14E6FF', 'round'],
  ['Banana Boat', 'wide', '#FFF27A', '#2440FF', '#2440FF', 'round'],
  ['Morning Glory', 'egg', '#9FB4FF', '#FF1F8F', '#FF1F8F', 'round'],
  ['Kiwi Slice', 'round', '#B8FF5C', '#3A2A10', '#FF2E5B', 'round'],
  ['Sea Breeze', 'egg', '#5CFFE6', '#1B2BFF', '#1B2BFF', 'pebble'],
  ['Strawberry Milk', 'tall', '#FFB3C8', '#D0102E', '#D0102E', 'round'],
  ['Cucumber', 'egg', '#9BFFB0', '#7A2BFF', '#7A2BFF', 'round'],
  ['Traffic Cone', 'round', '#FF8A2A', '#14E6FF', '#2440FF', 'round'],
  ['Pastel de Nata', 'egg', '#FFE08A', '#8A3A0A', '#8A3A0A', 'pebble'],
  ['Polar Bear', 'wide', '#F4FAFF', '#111111', '#3FA9FF', 'round'],
  ['Sour Candy', 'egg', '#D6FF2E', '#FF2E5B', '#7A2BFF', 'round'],
  ['Blue Hour', 'round', '#7FA8FF', '#FFF0C8', '#FFE14A', 'round'],
  ['Hot Chocolate', 'egg', '#FFC9A0', '#4A1E08', '#4A1E08', 'round'],
];
const UNCOMMON = [
  ['Cat Café', 'almond', '#F0FF2E', '#111111', '#111111', 'slit'],
  ['Alley Cat', 'almond', '#A8FF3D', '#111111', '#111111', 'slit'],
  ['Siamese', 'almond', '#7FC8FF', '#10184A', '#10184A', 'slit'],
  ['Tabby Orange', 'almond', '#FF9A3D', '#2A0E00', '#2A0E00', 'slit'],
  ['Night Panther', 'almond', '#C6FF5C', '#5A0E5E', '#5A0E5E', 'slit'],
  ['Dewdrop', 'drop', '#BDF4FF', '#2440FF', '#2440FF', 'round'],
  ['Rain Boots', 'drop', '#FFE14A', '#FF2E5B', '#2440FF', 'round'],
  ['Teardrop Teal', 'drop', '#2BFFE0', '#6A2BFF', '#6A2BFF', 'pebble'],
  ['Gumdrop', 'drop', '#FF8AD8', '#FFF0C8', '#FFE14A', 'round'],
  ['Sugar Cube', 'squircle', '#F4F4F4', '#FF5A1F', '#2440FF', 'round'],
  ['Pixel Pal', 'squircle', '#A8FF3D', '#111111', '#111111', 'plus'],
  ['Tile Floor', 'squircle', '#3FA9FF', '#FFE14A', '#FFE14A', 'round'],
  ['Toaster', 'squircle', '#FFB38A', '#2A2A2A', '#2A2A2A', 'ring'],
  ['Post-it', 'squircle', '#FFF27A', '#FF1F8F', '#2440FF', 'pebble'],
  ['Half Moon Bay', 'crescent', '#FFF0C8', '#2440FF', '#FF5A1F', 'round'],
  ['Sleepy Lemon', 'crescent', '#F0FF2E', '#7A2BFF', '#7A2BFF', 'round'],
  ['Lagoon Lid', 'crescent', '#2BD9FF', '#FF1F8F', '#FF1F8F', 'round'],
  ['Bullseye', 'round', '#FFF0C8', '#FF2E5B', '#FF2E5B', 'ring'],
  ['Target Practice', 'egg', '#F4F4F4', '#2440FF', '#FF2E5B', 'ring'],
  ['Saturn Ring', 'round', '#FFB38A', '#6A2BFF', '#6A2BFF', 'ring'],
  ['Ladybug', 'egg', '#FF4B4B', '#111111', '#111111', 'double'],
  ['Domino', 'round', '#F4F4F4', '#111111', '#111111', 'double'],
  ['Bubble Tea', 'egg', '#FFD6A8', '#3A1E08', '#3A1E08', 'double'],
  ['Moonbeam', 'round', '#BDF4FF', '#2440FF', '#2440FF', 'crescent'],
  ['Croissant', 'egg', '#FFD23A', '#8A3A0A', '#8A3A0A', 'crescent'],
  ['Midnight Snack', 'wide', '#C79BFF', '#111111', '#FFE14A', 'crescent'],
  ['Odd Socks', 'egg', '#FFF0C8', '#2440FF', '#FF5A1F', 'round', { whiteR: '#2BD9FF' }],
  ['Two Scoops', 'round', '#FFB3E6', '#5A2A10', '#5A2A10', 'pebble', { whiteR: '#B8F07A' }],
  ['Split Decision', 'egg', '#F0FF2E', '#7A2BFF', '#111111', 'round', { whiteR: '#FF8AD8' }],
  ['Pebble Beach', 'wide', '#BDB8AE', '#2440FF', '#2440FF', 'pebble'],
];
const RARE = [
  ['Starstruck', 'egg', '#FFF0C8', '#FFB800', '#FFB800', 'star'],
  ['Wish Upon', 'round', '#2440FF', '#FFE14A', '#FFE14A', 'star'],
  ['Shooting Star', 'egg', '#B57BFF', '#F0FF2E', '#FFFFFF', 'star'],
  ['Gold Medal', 'round', '#FF4B4B', '#FFD23A', '#FFD23A', 'star'],
  ['Smitten', 'egg', '#FFF0C8', '#FF2E63', '#FF2E63', 'heart'],
  ['Valentine Tram', 'round', '#FF8AD8', '#D0102E', '#D0102E', 'heart'],
  ['Crush Soda', 'egg', '#2BD9FF', '#FF2E63', '#FF2E63', 'heart'],
  ['Puppy Love', 'wide', '#FFF6EC', '#FF2E63', '#B57BFF', 'heart'],
  ['Crown Jewel', 'egg', '#F4F4F4', '#6A2BFF', '#14A0FF', 'diamond'],
  ['Card Shark', 'round', '#FF4B4B', '#111111', '#111111', 'diamond'],
  ['Harlequin', 'egg', '#FFD23A', '#FF2E5B', '#2440FF', 'diamond'],
  ['First Aid', 'round', '#F4F4F4', '#FF2E5B', '#FF2E5B', 'plus'],
  ['Swiss Army', 'squircle', '#FF4B4B', '#FFFFFF', '#FFFFFF', 'plus'],
  ['Pharmacy Green', 'squircle', '#3DFFC8', '#0E7A3A', '#0E7A3A', 'plus'],
  ['Neon Sign', 'egg', '#FF4FD8', '#FF4FD8', '#2BD9FF', 'round', { fx: ['outline'] }],
  ['Wireframe', 'round', '#2BD9FF', '#2BD9FF', '#2BD9FF', 'pebble', { fx: ['outline'] }],
  ['Dragonfruit', 'almond', '#FF4FD8', '#F4F4F4', '#F4F4F4', 'slit', { whiteR: '#A8FF3D' }],
  ['Eclipse', 'round', '#F4F4F4', '#111111', '#111111', 'crescent', { whiteR: '#FFD23A' }],
  ['Hypno Toad', 'egg', '#A8FF3D', '#5A0E5E', '#5A0E5E', 'spiral'],
  ['Lollipop', 'round', '#FFB3E6', '#FF2E63', '#2440FF', 'spiral'],
];
const EPIC = [
  ['Opal', 'egg', '#E6F6FF', '#6A2BFF', '#FF4FD8', 'round', { fx: ['shimmer'] }],
  ['Pearl Diver', 'round', '#F4F0FF', '#10184A', '#10184A', 'pebble', { fx: ['shimmer'] }],
  ['Champagne', 'egg', '#FFE6A8', '#7A2BFF', '#7A2BFF', 'star', { fx: ['shimmer', 'glitter'], glitterColor: '#FFE6A8' }],
  ['Disco Ball', 'squircle', '#E8E8F0', '#FF1F8F', '#2BD9FF', 'diamond', { fx: ['glitter', 'shimmer'] }],
  ['Fairy Dust', 'drop', '#FFB3E6', '#6A2BFF', '#2440FF', 'round', { fx: ['glitter'], glitterColor: '#FFE6F6' }],
  ['Firefly', 'egg', '#C6FF5C', '#111111', '#111111', 'round', { fx: ['glitter'], glitterColor: '#E8FF9A' }],
  ['Northern Lights', 'egg', '#5CFFB0', '#10184A', '#10184A', 'round', { fx: ['aurora'], auroraColors: ['#5CFFB0', '#3FD9FF', '#B07BFF'] }],
  ['Tropical Sunset', 'wide', '#FF9A3D', '#2A0E3A', '#2A0E3A', 'pebble', { fx: ['aurora'], auroraColors: ['#FFD23A', '#FF5A8A', '#FF9A3D'] }],
  ['Laser Show', 'round', '#FF1F8F', '#14E6FF', '#F0FF2E', 'ring', { fx: ['outline', 'glitter'], glitterColor: '#14E6FF' }],
  ['Vortex', 'egg', '#14E6FF', '#111111', '#111111', 'spiral', { fx: ['shimmer'] }],
  ['Ie Cobalt', 'round', '#FFF0C8', '#1F4FBF', '#1F4FBF', 'round', { fx: ['folk'], folkThread: '#0A1A40', pupil: { rx: 0.56, ry: 0.56 } }],
  ['Ie Roșie', 'round', '#F4F4F4', '#C8102E', '#C8102E', 'round', { fx: ['folk'], folkThread: '#141414', pupil: { rx: 0.56, ry: 0.56 } }],
];
const LEGENDARY = [
  ['Brushed Alu', 'egg', '#D8DCE2', '#111111', '#2440FF', 'round', { fx: ['chrome', 'shimmer'] }],
  ['Rose Chrome', 'round', '#F2B8C0', '#5A0E5E', '#5A0E5E', 'pebble', { fx: ['chrome'] }],
  ['Midas Touch', 'egg', '#FFD23A', '#3A1E00', '#3A1E00', 'star', { fx: ['chrome', 'glitter'], glitterColor: '#FFE6A8' }],
  ['Prism Party', 'egg', '#FF6B6B', '#111111', '#111111', 'round', { fx: ['rainbow'] }],
  ['Night Over Sibiu', 'round', '#FFF0C8', '#0B1240', '#0B1240', 'round', { fx: ['starfield', 'glitter'], pupil: { rx: 0.52, ry: 0.56 } }],
  ['Deep Field', 'egg', '#B8C8FF', '#05081F', '#2A0640', 'round', { fx: ['starfield'], pupil: { rx: 0.5, ry: 0.56 } }],
  ['Altiță', 'egg', '#FFF0C8', '#C8102E', '#C8102E', 'round', { fx: ['folk', 'shimmer'], folkThread: '#D9A21A', pupil: { rx: 0.56, ry: 0.56 } }],
];
const MYTHIC = [
  ['Genesis', 'egg', '#FFF0C8', '#0B1240', '#2A0A00', 'round', { fx: ['shimmer', 'halo', 'starfield'], glint: { color: '#FFD23A', size: 1.25 }, pupil: { rx: 0.5, ry: 0.56 } }],
  ['Aurora Borealis', 'egg', '#5CFFB0', '#05081F', '#05081F', 'round', { fx: ['aurora', 'starfield', 'glitter'], auroraColors: ['#5CFFB0', '#2BD9FF', '#B57BFF', '#FF6BD0'], pupil: { rx: 0.5, ry: 0.55 } }],
  ['Sânziana', 'round', '#FFE08A', '#C8102E', '#C8102E', 'round', { fx: ['chrome', 'folk', 'halo'], folkThread: '#D9A21A', folkBase: '#FFF6E6', pupil: { rx: 0.56, ry: 0.56 } }],
];

const FAMILY_OF = (shape, pupil, extra) => (extra && extra.fx && extra.fx.length ? 'special' : pupil === 'slit' ? 'cat' : shape);
const tiers = [['common', COMMON], ['uncommon', UNCOMMON], ['rare', RARE], ['epic', EPIC], ['legendary', LEGENDARY], ['mythic', MYTHIC]];
const out = [];
const seen = new Set();
for (const [rarity, list] of tiers) for (const [name, shape, white, L, R, ptype, extra] of list) {
  if (seen.has(name)) throw new Error('duplicate name ' + name);
  seen.add(name);
  const n = out.length + 1;
  const d = {
    id: name.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
    n, num: '#' + String(n).padStart(3, '0'), name, rarity, family: FAMILY_OF(shape, ptype, extra),
    shape: Object.assign({}, SHAPES[shape]), shapeName: shape,
    white, pupil: Object.assign({ type: ptype, L, R }, PUPIL[ptype] || {}),
  };
  if (extra) {
    for (const k of Object.keys(extra)) {
      if (k === 'pupil') Object.assign(d.pupil, extra.pupil);
      else d[k] = extra[k];
    }
  }
  out.push(d);
}
const RATES = { common: 0.5, uncommon: 0.25, rare: 0.15, epic: 0.07, legendary: 0.025, mythic: 0.005 };
const counts = {};
for (const d of out) counts[d.rarity] = (counts[d.rarity] || 0) + 1;
for (const d of out) d.odds = +(RATES[d.rarity] / counts[d.rarity]).toPrecision(4);
const doc = { version: 1, count: out.length, counts, rates: RATES, designs: out };
const dir = path.join(__dirname, '..');
fs.writeFileSync(path.join(dir, 'designs.json'), JSON.stringify(doc, null, 1) + '\n');
fs.writeFileSync(path.join(dir, 'designs.js'), '/* generated by tools/make_designs.js from the same data as designs.json */\nwindow.SOUL_DESIGNS=' + JSON.stringify(doc) + ';\n');
console.log(out.length, counts);
