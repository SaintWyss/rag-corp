/**
 * k6 Load Test for RAG API
 * 
 * Run: k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
 * 
 * Stages:
 *   - Ramp up to 10 VUs
 *   - Sustain 10 VUs for 1 minute
 *   - Ramp down
 */

import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const askLatency = new Trend('ask_latency', true);
const healthLatency = new Trend('health_latency', true);

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up
    { duration: '1m', target: 10 },   // Sustain
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.1'],         // <10% errors
    http_req_duration: ['p(95)<2000'],     // 95% < 2s
    ask_latency: ['p(95)<3000'],           // Ask < 3s
    health_latency: ['p(95)<100'],         // Health < 100ms
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const ADMIN_EMAIL = __ENV.K6_ADMIN_EMAIL || 'admin@example.com';
const ADMIN_PASSWORD = __ENV.K6_ADMIN_PASSWORD || 'admin';

const testQueries = [
  '¿Qué es RAG?',
  '¿Cómo funciona la búsqueda semántica?',
  'Explica embeddings',
  '¿Qué modelos de LLM existen?',
  '¿Cómo se calcula la similitud coseno?',
];

export function setup() {
  // Verify API is healthy before test
  const healthRes = http.get(`${BASE_URL}/healthz`);
  if (healthRes.status !== 200) {
    throw new Error(`API not healthy: ${healthRes.status}`);
  }

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  if (loginRes.status !== 200) {
    throw new Error(`Login failed: ${loginRes.status} ${loginRes.body}`);
  }

  let accessToken;
  try {
    const body = JSON.parse(loginRes.body);
    accessToken = body.access_token;
  } catch {
    throw new Error(`Login response invalid JSON: ${loginRes.body}`);
  }

  if (!accessToken) {
    throw new Error(`Login response missing access_token: ${loginRes.body}`);
  }

  const workspaceRes = http.post(
    `${BASE_URL}/v1/workspaces`,
    JSON.stringify({ name: `k6-workspace-${Date.now()}` }),
    {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (workspaceRes.status !== 201) {
    throw new Error(`Workspace create failed: ${workspaceRes.status} ${workspaceRes.body}`);
  }

  let workspaceId;
  try {
    const body = JSON.parse(workspaceRes.body);
    workspaceId = body.id;
  } catch {
    throw new Error(`Workspace create response invalid JSON: ${workspaceRes.body}`);
  }

  if (!workspaceId) {
    throw new Error(`Workspace create missing id: ${workspaceRes.body}`);
  }

  return { startTime: Date.now(), workspaceId, accessToken };
}

export default function (data) {
  const workspaceId = data.workspaceId;
  const accessToken = data.accessToken;
  // Health check (20% of requests)
  if (Math.random() < 0.2) {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/healthz`);
    healthLatency.add(Date.now() - start);
    
    check(res, {
      'health status 200': (r) => r.status === 200,
    });
    errorRate.add(res.status !== 200);
    sleep(0.5);
    return;
  }

  // Ask endpoint (80% of requests)
  const query = testQueries[Math.floor(Math.random() * testQueries.length)];
  const payload = JSON.stringify({ query, top_k: 3 });
  const params = {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    timeout: '10s',
  };

  const start = Date.now();
  const res = http.post(`${BASE_URL}/v1/workspaces/${workspaceId}/ask`, payload, params);
  askLatency.add(Date.now() - start);

  const success = check(res, {
    'ask status 200': (r) => r.status === 200,
    'ask has answer': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.answer && body.answer.length > 0;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!success);
  sleep(1 + Math.random());  // 1-2s between requests
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`Test completed in ${duration.toFixed(1)}s`);
}
