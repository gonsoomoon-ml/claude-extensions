// Terminal storyboard example: start a CLI in the ttyd terminal, open one of its screens, zoom on it, leave.
// Record: node record_demo.mjs --url http://127.0.0.1:7681 --storyboard ./terminal.example.mjs --name cli-status
import { openTerminal, run, type, waitFor, waitPrompt, zoomRows } from './term.mjs';

export default async function storyboard({ page, rec, siteUrl }) {
  await openTerminal(page, siteUrl, { fontSize: 28, cols: 100 });   // 28 px and 100 columns: dialogs stay inside the zoom
  await run(page, 'cd ~/work && clear');
  await page.waitForTimeout(600);
  await rec.install();                                               // camera after the page is ready
  await rec.reset('shell');
  await type(page, 'claude'); await page.keyboard.press('Enter'); rec.note('cli_start');
  await waitPrompt(page); rec.note('ready');
  await page.waitForTimeout(3500);                                   // the first screen deserves a few seconds

  await type(page, '/status'); await page.waitForTimeout(600); await page.keyboard.press('Enter'); rec.note('status');
  await waitFor(page, 'Setting sources', 15000); await page.waitForTimeout(600);
  await zoomRows(rec, page, 'status', 'Anthropic base URL', 'Skipped sources', { pad: 30, kmax: 1.6 }, 'Status panel');
  await page.waitForTimeout(7000);
  await page.keyboard.press('Escape'); await page.waitForTimeout(800);

  await rec.reset('end');                                            // end on the wide shot; cut the clip here (no /exit tail)
  await page.waitForTimeout(1500);
}
