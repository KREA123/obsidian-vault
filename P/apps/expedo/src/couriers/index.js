import mock from './mock.js';
import cargus from './cargus.js';
import sameday from './sameday.js';
import fancourier from './fancourier.js';
import gls from './gls.js';
import dpd from './dpd.js';

export const couriers = Object.fromEntries([cargus, sameday, fancourier, gls, dpd, mock].map((c) => [c.id, c]));
export const getCourier = (id) => couriers[id];
