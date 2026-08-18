import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";


const frontendRoot = resolve(import.meta.dirname, "..");
const source = readFileSync(resolve(frontendRoot, "app/crm/page.tsx"), "utf8");
const proxySource = readFileSync(resolve(frontendRoot, "proxy.ts"), "utf8");
const nextConfigSource = readFileSync(resolve(frontendRoot, "next.config.ts"), "utf8");
const diallerSource = readFileSync(resolve(frontendRoot, "app/crm/dialler.tsx"), "utf8");


describe("CareGist CRM safety contracts", () => {
  it("protects the CRM route with authenticated middleware", () => {
    assert.match(proxySource, /"\/crm"/);
  });

  it("lets /crm request the microphone so the browser permission popup can appear", () => {
    assert.match(proxySource, /microphone=\(self\)/);
    assert.doesNotMatch(nextConfigSource, /Permissions-Policy.*microphone/);
    assert.match(diallerSource, /getUserMedia\(\{ audio: true \}\)/);
  });

  it("does not expose or collect Twilio credentials in the browser", () => {
    const surface = `${source}\n${diallerSource}`;
    assert.doesNotMatch(surface, /TWILIO_ACCOUNT_SID|TWILIO_AUTH_TOKEN|TWILIO_API_KEY_SECRET/);
    assert.match(diallerSource, /\/api\/v1\/crm\/twilio\/token/);
  });

  it("uses one-time server authorization instead of sending a destination number to Twilio", () => {
    assert.match(diallerSource, /calls\/authorize/);
    assert.match(diallerSource, /params:\s*\{\s*authorization:/);
    assert.doesNotMatch(diallerSource, /params:\s*\{\s*(To|phone|phone_e164):/);
  });

  it("makes phone compliance fool-proof for operators", () => {
    assert.match(source, /Ready to call/);
    assert.match(source, /Needs screening/);
    assert.match(source, /Do not call/);
    assert.match(source, /phone-screenings\/import/);
    assert.match(source, /disabled=\{!summary\?\.calling\.enabled \|\| !readiness\.ready/);
    assert.match(source, /pending_disposition_call/);
    assert.match(source, /awaitingDisposition/);
    assert.match(source, /disabled=\{Boolean\(callSessionId\)/);
  });

  it("keeps UK SMS disabled and makes recording retention explicit", () => {
    assert.match(source, /UK SMS disabled/);
    assert.match(source, /automatic.*day deletion/);
  });

  it("includes pipeline, email campaign, reporting and AI review surfaces", () => {
    assert.match(source, /\/api\/v1\/crm\/campaigns/);
    assert.match(source, /\/api\/v1\/crm\/reports\/performance/);
    assert.match(source, /AI summary · advisory/);
    assert.match(source, /Disposition report/);
    assert.match(source, /Campaign report/);
    assert.match(source, /Compliance flags/);
    assert.match(source, /overall_qa_score/);
    assert.match(source, /complained_count/);
  });

  it("exposes accessible operator controls and inline recovery", () => {
    assert.match(source, /aria-live="assertive"/);
    assert.match(source, /aria-live="polite"/);
    assert.match(source, /aria-pressed=\{dispositionGroup === value\}/);
    assert.match(source, /aria-label="Add contact"/);
    assert.match(source, /id="loss-reason"/);
    assert.doesNotMatch(source, /window\.prompt/);
  });

  it("keeps the dialler movable and advances after an outcome", () => {
    assert.match(diallerSource, /onPointerDown=\{startDrag\}/);
    assert.match(diallerSource, /device\.register\(\)/);
    assert.match(diallerSource, /bottom: 16/);
    assert.match(source, /Next: \$\{contactName\(nextContact\)\}/);
  });

  it("supports general tasks and serializes call actions", () => {
    assert.match(source, /option value="follow_up"/);
    assert.match(source, /option value="meeting"/);
    assert.match(source, /callActionRef\.current/);
    assert.match(diallerSource, /const tokenData = await jsonRequest/);
  });
});
