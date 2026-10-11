const { themeCheckRun } = require('@shopify/theme-check-node');
(async () => {
  const root = process.argv[2];
  const { offenses } = await themeCheckRun(root, undefined, () => {});
  const sev = ['ERROR', 'WARNING', 'INFO'];
  const counts = {};
  for (const o of offenses) {
    counts[sev[o.severity]] = (counts[sev[o.severity]] || 0) + 1;
    console.log(`${sev[o.severity]} ${o.check} ${o.uri.replace('file://' + root + '/', '')}:${o.start ? o.start.line + 1 : ''} ${o.message}`);
  }
  console.log('SUMMARY', JSON.stringify(counts), 'total', offenses.length);
})().catch(e => { console.error(e); process.exit(2); });
