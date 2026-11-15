// Run with: npm run test:auth  (node --test, native TypeScript type stripping)
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildLoginHref,
  decodeJwtPayload,
  getSessionState,
  getTokenExpiryMs,
  isPublicPath,
  isTokenExpired,
  safeNextPath,
} from "./session.ts";

function b64url(value) {
  return Buffer.from(value).toString("base64url");
}

function makeJwt(payload) {
  return `${b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }))}.${b64url(
    JSON.stringify(payload)
  )}.signature`;
}

const NOW = 1_700_000_000_000;
const expInSeconds = (offsetMs) => Math.floor((NOW + offsetMs) / 1000);

test("decodeJwtPayload reads base64url payloads (incl. non-ASCII)", () => {
  const token = makeJwt({ sub: "42", name: "José Ñúñez", exp: 123 });
  assert.deepEqual(decodeJwtPayload(token), {
    sub: "42",
    name: "José Ñúñez",
    exp: 123,
  });
});

test("decodeJwtPayload rejects malformed tokens", () => {
  assert.equal(decodeJwtPayload(""), null);
  assert.equal(decodeJwtPayload("not-a-jwt"), null);
  assert.equal(decodeJwtPayload("a.b"), null);
  assert.equal(decodeJwtPayload("a.!!!.c"), null);
  assert.equal(decodeJwtPayload(`a.${b64url("not json")}.c`), null);
  assert.equal(decodeJwtPayload(`a.${b64url("[1,2]")}.c`), null);
});

test("getTokenExpiryMs converts exp seconds to ms", () => {
  assert.equal(getTokenExpiryMs(makeJwt({ exp: 1000 })), 1_000_000);
  assert.equal(getTokenExpiryMs(makeJwt({ sub: "1" })), null);
  assert.equal(getTokenExpiryMs(makeJwt({ exp: "1000" })), null);
});

test("isTokenExpired", () => {
  assert.equal(isTokenExpired(makeJwt({ exp: expInSeconds(60 * 60_000) }), NOW), false);
  assert.equal(isTokenExpired(makeJwt({ exp: expInSeconds(-1_000) }), NOW), true);
  // Inside the default 10 s skew window counts as expired.
  assert.equal(isTokenExpired(makeJwt({ exp: expInSeconds(5_000) }), NOW), true);
  assert.equal(isTokenExpired(makeJwt({ exp: expInSeconds(5_000) }), NOW, 0), false);
  // Missing exp or garbage => unusable.
  assert.equal(isTokenExpired(makeJwt({ sub: "1" }), NOW), true);
  assert.equal(isTokenExpired("garbage", NOW), true);
});

test("getSessionState", () => {
  assert.equal(getSessionState(null, NOW), "none");
  assert.equal(getSessionState("", NOW), "none");
  assert.equal(getSessionState("garbage", NOW), "expired");
  assert.equal(getSessionState(makeJwt({ exp: expInSeconds(-1) }), NOW), "expired");
  assert.equal(getSessionState(makeJwt({ exp: expInSeconds(3_600_000) }), NOW), "valid");
});

test("isPublicPath", () => {
  for (const p of ["/login", "/register", "/forgot-password", "/reset-password", "/login/"]) {
    assert.equal(isPublicPath(p), true, p);
  }
  for (const p of ["/", "/telemetry", "/knowledge", "/loginx", "/account/profile"]) {
    assert.equal(isPublicPath(p), false, p);
  }
});

test("safeNextPath keeps internal paths", () => {
  assert.equal(safeNextPath("/knowledge"), "/knowledge");
  assert.equal(safeNextPath("/incidents?status=open#top"), "/incidents?status=open#top");
  assert.equal(safeNextPath("/candidates/12"), "/candidates/12");
});

test("safeNextPath blocks open redirects and junk", () => {
  const bad = [
    undefined,
    null,
    "",
    "knowledge",
    "https://evil.com",
    "//evil.com",
    "//evil.com/path",
    "/\\evil.com",
    "\\\\evil.com",
    "javascript:alert(1)",
    "/\tevil",
    "/\n/evil.com",
    "http:/evil.com",
    "/" + "a".repeat(3000),
  ];
  for (const value of bad) {
    assert.equal(safeNextPath(value), "/", JSON.stringify(value));
  }
  assert.equal(safeNextPath("//evil.com", "/home"), "/home");
});

test("safeNextPath never returns to a public auth page", () => {
  assert.equal(safeNextPath("/login"), "/");
  assert.equal(safeNextPath("/login?next=/x"), "/");
  assert.equal(safeNextPath("/register"), "/");
});

test("buildLoginHref", () => {
  assert.equal(buildLoginHref("/"), "/login");
  assert.equal(buildLoginHref("/knowledge"), "/login?next=%2Fknowledge");
  assert.equal(
    buildLoginHref("/incidents?status=open", { expired: true }),
    "/login?next=%2Fincidents%3Fstatus%3Dopen&reason=expired"
  );
  assert.equal(buildLoginHref("/", { expired: true }), "/login?reason=expired");
  assert.equal(buildLoginHref("//evil.com", { expired: true }), "/login?reason=expired");
  assert.equal(buildLoginHref("/login"), "/login");
});
