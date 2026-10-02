// Romanian rendering for tests that check the actual text: errors and adapter messages carry a catalog
// key + params (src/i18n); the text is made when shown, in the viewer's language.
import { renderError } from '../src/core/errors.js';
import { renderEvent } from '../src/db.js';
import { t } from '../src/i18n/index.js';

/** ProcessingError / its JSON / an issue / { ok, message: {key, params} } → same with Romanian message & hint. */
export function ro(x) {
  if (x && typeof x === 'object' && x.message && typeof x.message === 'object') return { ...x, message: t('ro', x.message) };
  return renderError(x, 'ro');
}

/** Event row → Romanian text. */
export const roEvent = (e) => renderEvent(e, 'ro');

/** A message { key, params } (or a key) → Romanian text. */
export const roText = (m, params) => t('ro', m, params);
