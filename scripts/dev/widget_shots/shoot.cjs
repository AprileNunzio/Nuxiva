const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const [base, outDir, prefix, lang = "it"] = process.argv.slice(2);
const PROFILES = {
  desktop: { viewport: { width: 1920, height: 1080 }, per: 9 },
  mobile: { viewport: { width: 390, height: 844 }, per: 4, isMobile: true, hasTouch: true },
};

(async () => {
  const ids = await (await fetch(`${base}/instances.json`)).json();
  const all = ids.map((i) => i.id);
  const browser = await chromium.launch();
  fs.mkdirSync(outDir, { recursive: true });
  for (const [name, p] of Object.entries(PROFILES)) {
    const ctx = await browser.newContext({ viewport: p.viewport, deviceScaleFactor: name === "desktop" ? 1 : 2, isMobile: !!p.isMobile, hasTouch: !!p.hasTouch });
    for (let n = 0; n * p.per < all.length; n++) {
      const chunk = all.slice(n * p.per, (n + 1) * p.per);
      const page = await ctx.newPage();
      await page.goto(`${base}/harness?lang=${lang}&ids=${chunk.join(",")}`);
      await page.waitForSelector("body[data-ready='1']", { timeout: 20000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const file = path.join(outDir, `${prefix}-${name}-${String(n + 1).padStart(2, "0")}.png`);
      await page.screenshot({ path: file, fullPage: true });
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
})();
