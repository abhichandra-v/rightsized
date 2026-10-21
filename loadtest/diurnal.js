// Diurnal load for Online Boutique: one compressed "day" of traffic.
//
// The same script, seed and shape drive the baseline and the candidate, so any SLO delta
// comes from the resource change rather than from different traffic.
//
//   BASE_URL     frontend URL                      (default http://localhost:8080)
//   PEAK_RPS     iterations/s at the daily peak    (default 40)
//   DAY_MINUTES  wall-clock length of one "day"    (default 20)
//   SUMMARY      where to write the JSON summary   (default summary.json)
import http from 'k6/http';
import { check } from 'k6';
import exec from 'k6/execution';

const BASE = __ENV.BASE_URL || 'http://localhost:8080';
const PEAK = Number(__ENV.PEAK_RPS || 40);
const DAY = Number(__ENV.DAY_MINUTES || 20);

// Fraction of peak by hour of day: overnight trough, morning ramp, lunch peak, evening shoulder.
const SHAPE = [
  [0, 0.10], [6, 0.10], [9, 0.60], [12, 0.85], [13, 1.00], [14, 0.70],
  [18, 0.75], [20, 0.90], [22, 0.40], [24, 0.15],
];

function stages() {
  const out = [];
  for (let i = 1; i < SHAPE.length; i++) {
    const [h0] = SHAPE[i - 1];
    const [h1, frac] = SHAPE[i];
    const secs = Math.max(1, Math.round(((h1 - h0) / 24) * DAY * 60));
    out.push({ duration: `${secs}s`, target: Math.max(1, Math.round(PEAK * frac)) });
  }
  return out;
}

export const options = {
  scenarios: {
    shoppers: {
      executor: 'ramping-arrival-rate',
      startRate: Math.max(1, Math.round(PEAK * SHAPE[0][1])),
      timeUnit: '1s',
      preAllocatedVUs: PEAK * 2,
      maxVUs: PEAK * 10,
      stages: stages(),
    },
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(95)', 'p(99)', 'max'],
  discardResponseBodies: true,
};

const PRODUCTS = [
  '0PUK6V6EV0', '1YMWWN1N4O', '2ZYFJ3GM2N', '66VCHSJNUP', '6E92ZMYYFZ',
  '9SIQT8TOJO', 'L9ECAV7KIM', 'LS4PSXUNUM', 'OLJCESPC7Z',
];
const CURRENCIES = ['EUR', 'USD', 'JPY', 'CAD', 'GBP', 'TRY'];

// Deterministic per-iteration choice, so runs are comparable.
function pick(arr, salt) {
  const i = exec.scenario.iterationInTest;
  return arr[(i * 7919 + salt) % arr.length];
}

export default function () {
  const i = exec.scenario.iterationInTest;
  const roll = (i * 2654435761) % 100;
  const form = { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } };

  // Weights roughly follow the upstream Locust file: browse-heavy, a few checkouts.
  let res;
  if (roll < 10) {
    res = http.get(`${BASE}/`, { tags: { name: 'home' } });
  } else if (roll < 60) {
    res = http.get(`${BASE}/product/${pick(PRODUCTS, 1)}`, { tags: { name: 'product' } });
  } else if (roll < 70) {
    res = http.post(`${BASE}/setCurrency`, { currency_code: pick(CURRENCIES, 2) }, { ...form, tags: { name: 'currency' } });
  } else if (roll < 80) {
    res = http.get(`${BASE}/cart`, { tags: { name: 'cart' } });
  } else if (roll < 95) {
    res = http.post(`${BASE}/cart`, { product_id: pick(PRODUCTS, 3), quantity: '1' }, { ...form, tags: { name: 'add' } });
  } else {
    http.post(`${BASE}/cart`, { product_id: pick(PRODUCTS, 4), quantity: '1' }, form);
    res = http.post(`${BASE}/cart/checkout`, {
      email: 'someone@example.com', street_address: '1600 Amphitheatre Parkway', zip_code: '94043',
      city: 'Mountain View', state: 'CA', country: 'United States', credit_card_number: '4432801561520454',
      credit_card_expiration_month: '1', credit_card_expiration_year: '2039', credit_card_cvv: '672',
    }, { ...form, tags: { name: 'checkout' } });
  }
  check(res, { 'status < 400': (r) => r.status < 400 });
}

export function handleSummary(data) {
  return { [__ENV.SUMMARY || 'summary.json']: JSON.stringify(data, null, 2) };
}
