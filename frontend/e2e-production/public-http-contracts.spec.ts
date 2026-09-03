import { expect, test } from "@playwright/test";

test("unknown service pages return the standard noindex UI with HTTP 404", async ({ request }) => {
  for (const path of [
    "/services/this-service-does-not-exist",
    "/services/HOME-CARE",
    "/services/constructor",
    "/services/%5F%5Fproto%5F%5F",
  ]) {
    const response = await request.get(path, { maxRedirects: 0 });
    const body = await response.text();

    expect(response.status(), path).toBe(404);
    expect(response.headers().location, path).toBeUndefined();
    expect(response.headers()["content-security-policy"], path).toContain("default-src 'self'");
    expect(body, path).toContain("Page not found");
    expect(body, path).toMatch(/<meta[^>]+name="robots"[^>]+content="noindex"/i);
  }

  // Next canonicalizes trailing slashes before Proxy. Following that single
  // canonical redirect must still terminate at the same honest 404 response.
  const trailing = await request.get("/services/this-service-does-not-exist/");
  expect(trailing.status()).toBe(404);
  expect(await trailing.text()).toContain("Page not found");
});

test("known, paginated, and ordinary route contracts retain their statuses", async ({ request }) => {
  for (const path of ["/services/home-care", "/services/home-care?page=2"]) {
    const response = await request.get(path, { maxRedirects: 0 });
    expect(response.status(), path).toBe(200);
  }

  expect((await request.get("/services/unknown/nested", { maxRedirects: 0 })).status()).toBe(404);
  expect((await request.get("/ordinary-route-does-not-exist", { maxRedirects: 0 })).status()).toBe(404);
});
