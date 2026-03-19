/**
 * get_images.cjs v1 - 通过 CDP Page.getResourceContent 获取题目图片
 * 
 * 突破防盗链的核心方案：图片已在浏览器缓存中，
 * 用 CDP Page.getResourceContent 直接读取，无需下载！
 * 
 * 用法：
 * node get_images.cjs <output_dir>
 * 
 * 输出：
 * - <output_dir>/img_q<题号>_<序号>.png  各题图片
 * - <output_dir>/manifest.json  图片与题目的映射关系
 */
const { chromium } = require('/home/maniubi/openclaw/node_modules/playwright-core/index.js');
const { writeFileSync, mkdirSync } = require('fs');
const path = require('path');

const OUT_DIR = process.argv[2] || '/tmp/cx_imgs';
mkdirSync(OUT_DIR, { recursive: true });

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');

  // Find best dowork page (most images)
  let bestPage = null, bestCount = 0;
  for (const ctx of browser.contexts()) {
    for (const p of ctx.pages()) {
      const url = p.url();
      if (!url.includes('chaoxing') || !url.includes('dowork')) continue;
      const cdpTmp = await ctx.newCDPSession(p);
      await cdpTmp.send('Page.enable');
      const res = await cdpTmp.send('Runtime.evaluate', {
        expression: `document.querySelectorAll('.questionLi img').length`
      });
      await cdpTmp.detach();
      const count = res.result.value || 0;
      console.log(url.substring(0,80), '->', count, 'imgs');
      if (count > bestCount) { bestCount = count; bestPage = p; }
    }
  }

  if (!bestPage) { console.error('No dowork page found'); process.exit(1); }
  console.log('\nUsing:', bestPage.url().substring(0,100));

  const cdp = await bestPage.context().newCDPSession(bestPage);
  await cdp.send('Page.enable');
  await cdp.send('Network.enable');

  // Get frame ID
  const frameTree = await cdp.send('Page.getFrameTree');
  const frameId = frameTree.frameTree.frame.id;

  // Get all question images with metadata
  const questionsRes = await cdp.send('Runtime.evaluate', {
    expression: `
      JSON.stringify(Array.from(document.querySelectorAll('.questionLi')).map((q, qi) => {
        const decodeLatex = img => {
          const raw = img.getAttribute('data');
          if (!raw) return null;
          try { return decodeURIComponent(raw).replace(/^"|"$/g,'').trim(); } catch(e) { return null; }
        };
        // All imgs in this question
        const allImgs = Array.from(q.querySelectorAll('img')).map(img => ({
          url: img.src,
          fname: img.src.split('/').pop(),
          nW: img.naturalWidth,
          nH: img.naturalHeight,
          hasData: !!img.getAttribute('data'),
          latex: decodeLatex(img),
          inStem: !!img.closest('h3')
        })).filter(i => i.nW > 5);
        
        const options = Array.from(q.querySelectorAll('[role=radio]')).map((opt, oi) => ({
          label: ['A','B','C','D','E'][oi],
          text: opt.innerText.trim(),
          latex: Array.from(opt.querySelectorAll('img[data]')).map(decodeLatex).filter(Boolean)
        }));
        
        return { q: qi+1, stemText: q.querySelector('h3')?.innerText?.substring(0,200)||'', allImgs, options };
      }))
    `
  });
  const questions = JSON.parse(questionsRes.result.value);
  console.log('Questions:', questions.length);

  // Download all images via Page.getResourceContent
  const urlToFile = {};
  const allUrls = [...new Set(questions.flatMap(q => q.allImgs.map(i => i.url)))];
  console.log('Unique image URLs:', allUrls.length);

  for (let i = 0; i < allUrls.length; i++) {
    const url = allUrls[i];
    const fname = url.split('/').pop();
    try {
      const content = await cdp.send('Page.getResourceContent', { frameId, url });
      const buf = Buffer.from(content.content, content.base64Encoded ? 'base64' : 'utf8');
      const outPath = path.join(OUT_DIR, fname);
      writeFileSync(outPath, buf);
      urlToFile[url] = fname;
      console.log(`✅ ${fname} (${buf.length}b)`);
    } catch(e) {
      console.log(`❌ ${fname}: ${e.message.substring(0,60)}`);
    }
  }

  // Save manifest with question structure
  const manifest = questions.map(q => ({
    ...q,
    allImgs: q.allImgs.map(img => ({
      ...img,
      localFile: urlToFile[img.url] || null
    }))
  }));
  writeFileSync(path.join(OUT_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(`\nSaved manifest.json with ${questions.length} questions`);
  console.log('Output dir:', OUT_DIR);

  await cdp.detach();
  process.exit(0);
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
