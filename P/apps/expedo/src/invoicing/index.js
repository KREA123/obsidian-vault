import mock from './mock.js';
import smartbill from './smartbill.js';
import fgo from './fgo.js';
import oblio from './oblio.js';

export const invoicers = Object.fromEntries([smartbill, fgo, oblio, mock].map((p) => [p.id, p]));
export const getInvoicer = (id) => invoicers[id];
