import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const OUTPUT_DIR = '/Users/aryateja/Projects/Deep-Agents-hackathon/demo-recording';
mkdirSync(OUTPUT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: false }); // visible browser for better rendering
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  recordVideo: {
    dir: OUTPUT_DIR,
    size: { width: 1920, height: 1080 },
  },
});

const page = await context.newPage();
console.log('Navigating to deployed site...');
await page.goto('https://alfredsjoqvist.com/sentinel?call=false', { waitUntil: 'networkidle', timeout: 30000 });
await page.waitForTimeout(3000);

// Start demo
await page.click('body');
await page.waitForTimeout(500);
console.log('Starting demo (D key)...');
await page.evaluate(() => {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', code: 'KeyD', bubbles: true }));
});
await page.keyboard.press('d');

// Let the demo run through all phases (~80s)
console.log('Demo running... waiting 85s for completion');
for (let i = 0; i < 17; i++) {
  await page.waitForTimeout(5000);
  console.log(`  ${(i+1)*5}s elapsed`);
}
await page.screenshot({ path: `${OUTPUT_DIR}/v5-85s.png` });

// Demo should be COMPLETE now. Click through the report tabs.
console.log('Clicking Incident Report tab...');
try {
  await page.click('text=Incident Report', { timeout: 5000 });
} catch { console.log('  Could not click Incident Report'); }
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUTPUT_DIR}/v5-incident.png` });

// Scroll down the incident report content
console.log('Scrolling incident report...');
for (let i = 0; i < 5; i++) {
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(1000);
}
await page.screenshot({ path: `${OUTPUT_DIR}/v5-incident-scrolled.png` });

// Click Research Report tab
console.log('Clicking Research Report tab...');
try {
  await page.click('text=Research Report', { timeout: 5000 });
} catch { console.log('  Could not click Research Report'); }
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUTPUT_DIR}/v5-research.png` });

// Scroll research report
for (let i = 0; i < 3; i++) {
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(1000);
}

// Click Kiro Specification tab
console.log('Clicking Kiro Specification tab...');
try {
  await page.click('text=Kiro Specification', { timeout: 5000 });
} catch { console.log('  Could not click Kiro Specification'); }
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUTPUT_DIR}/v5-kiro.png` });

// Scroll down to show more of the Kiro spec
for (let i = 0; i < 5; i++) {
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(800);
}
await page.screenshot({ path: `${OUTPUT_DIR}/v5-kiro-scrolled.png` });

// Hold on Kiro section for a few more seconds
await page.waitForTimeout(5000);

// Final screenshot
await page.screenshot({ path: `${OUTPUT_DIR}/v5-final.png` });
console.log('Recording complete!');

await context.close();
await browser.close();
