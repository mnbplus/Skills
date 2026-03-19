/**
 * screenshot_stems.cjs
 * 在做作业时立即截取所有无LaTeX的题干图片
 * 必须在浏览器停留在 dowork 页面时运行！
 * 
 * 用法：
 * node ~/.openclaw/skills/chaoxing-homework/scripts/screenshot_stems.cjs <output_dir>
 */
const { chromium } = require('/home/maniubi/openclaw/node_modules/playwright-core/index.js');
const { writeFileSync, mkdirSync } = require('fs');
const path = require('path');

const OUT_DIR = process.argv[2] || '/tmp/cx_stems';
mkdirSync(OUT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');

  // Find the active dowork page
  let targetPage = null;
  let maxImgs = 0;
  
  for (const ctx of browser.contexts()) {
    for (const page of ctx.pages()) {
      const url = page.url();
      if (!url.includes('chaoxing') || !url.includes('dowork')) continue;
      
      const cdpTmp = await ctx.newCDPSession(page);
      const res = await cdpTmp.send('Runtime.evaluate', {
        expression: `document.querySelectorAll('.questionLi img:not([data])').length`
      });
      await cdpTmp.detach();
      const count = res.result.value || 0;
      console.log(url.substring(0,80), '-> no-data imgs:', count);
      if (count > maxImgs) { maxImgs = count; targetPage = page; }
    }
  }

  if (!targetPage) { console.log('No dowork page with undata images found'); process.exit(0); }
  console.log('\nUsing:', targetPage.url().substring(0,100));
  console.log('No-data images:', maxImgs);

  const cdp = await targetPage.context().newCDPSession(targetPage);

  // Get all questionLi elements and their no-data imgs
  const questionsData = await cdp.send('Runtime.evaluate', {
    expression: `
      JSON.stringify(Array.from(document.querySelectorAll('.questionLi')).map((q, qi) => {
        const stemImgs = Array.from(q.querySelectorAll('h3 img:not([data])'));
        return {
          q: qi + 1,
          stemText: q.querySelector('h3')?.innerText?.substring(0, 100) || '',
          imgs: stemImgs.map(img => ({
            src: img.src.split('/').pop(),
            nW: img.naturalWidth,
            nH: img.naturalHeight,
            pageY: img.getBoundingClientRect().top + window.scrollY,
            x: img.getBoundingClientRect().left
          }))
        };
      }).filter(q => q.imgs.length > 0))
    `
  });
  
  const questions = JSON.parse(questionsData.result.value);
  console.log('Questions with no-data imgs:', questions.length);

  for (const qData of questions) {
    for (let j = 0; j < qData.imgs.length; j++) {
      const img = qData.imgs[j];
      if (img.nW < 5) { console.log(`q${qData.q} img${j}: empty skip`); continue; }
      
      // Scroll to image
      await cdp.send('Runtime.evaluate', {
        expression: `window.scrollTo(0, ${Math.max(0, img.pageY - 150)})`
      });
      await new Promise(r => setTimeout(r, 350));
      
      const sy = (await cdp.send('Runtime.evaluate', { expression: 'window.scrollY' })).result.value;
      const vy = img.pageY - sy;
      
      if (vy < 0 || vy > 850) { console.log(`q${qData.q}: vy=${Math.round(vy)} out of view, re-scroll`); continue; }
      
      const pad = 12;
      const shot = await cdp.send('Page.captureScreenshot', {
        format: 'png',
        captureBeyondViewport: false,
        clip: {
          x: Math.max(0, img.x - pad),
          y: Math.max(0, vy - pad),
          width: Math.min(img.nW + pad * 2, 1280),
          height: img.nH + pad * 2,
          scale: 1
        }
      });
      
      const buf = Buffer.from(shot.data, 'base64');
      const fname = `q${qData.q}_stem${j}.png`;
      writeFileSync(path.join(OUT_DIR, fname), buf);
      console.log(`q${qData.q} img${j}: saved ${fname} (${buf.length} bytes, ${img.nW}x${img.nH})`);
    }
  }

  await cdp.detach();
  console.log('\nScreenshots saved to:', OUT_DIR);
  process.exit(0);
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
