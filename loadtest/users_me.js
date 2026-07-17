import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://api:8000";

export const options = {
  scenarios: {
    identify: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 1000),
      timeUnit: "1s",
      duration: __ENV.DURATION || "30s",
      preAllocatedVUs: Number(__ENV.VUS || 200),
      maxVUs: Number(__ENV.MAX_VUS || 1000),
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

export function setup() {
  const res = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ email: "user@example.com", password: "ChangeMe-Please-1" }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(res, { "login ok": (r) => r.status === 200 });
  return { token: res.json("access_token") };
}

export default function (data) {
  const res = http.get(`${BASE}/api/v1/users/me`, {
    headers: { Authorization: `Bearer ${data.token}` },
  });
  check(res, { "status is 200": (r) => r.status === 200 });
}
