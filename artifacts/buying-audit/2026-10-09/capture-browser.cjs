const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('/Users/user/CareGist/frontend/node_modules/@playwright/test');
(async () => {
  const out = __dirname;
  const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const evidence = { observedAt: new Date().toISOString(), realMessagesSent: 0, realPayments: 0, pages: [] };
  for (const [name, route] of [['pricing','/pricing'],['territory','/pricing/territory'],['terms','/terms'],['checkout-return','/territory-opportunity-brief/success?session_id=cs_unverified']]) {
    const response = await page.goto('https://www.caregist.co.uk' + route, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(out, name + '-desktop.png'), fullPage: true });
    evidence.pages.push({ route, status: response.status(), text: await page.locator('body').innerText(), emailLinks: await page.locator('a[href^="mailto:"]').evaluateAll(xs => xs.map(x => ({text: x.textContent, href: x.href}))) });
    if (name === 'territory') {
      await page.getByLabel('Region', {exact:true}).selectOption('London');
      await page.getByLabel('Which provider group do you want to research?', {exact:true}).selectOption('new_90');
      const coverageResponse = page.waitForResponse(r => r.url().includes('/api/territory/coverage'));
      await page.getByRole('button', {name:'Check this territory', exact:true}).click();
      const r = await coverageResponse;
      evidence.coverage = { synthetic: false, status: r.status(), body: await r.json() };
      await page.screenshot({path:path.join(out,'coverage-result-desktop.png'), fullPage:true});
      evidence.coverage.screenText = await page.locator('body').innerText();
      await page.setViewportSize({width:390,height:844});
      await page.screenshot({path:path.join(out,'coverage-result-mobile.png'),fullPage:true});
      evidence.coverage.mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      await page.setViewportSize({width:1440,height:1000});
    }
  }
  const exportResponse = await page.request.get('https://www.caregist.co.uk/api/export?token=synthetic-invalid-token');
  evidence.export = {status:exportResponse.status(), body:await exportResponse.text()};
  fs.writeFileSync(path.join(out,'browser-observations.json'),JSON.stringify(evidence,null,2)+'\n');
  await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
