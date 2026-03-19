/**
 * auto_solve.cjs - 全自动作业解题脚本
 * 功能：
 * 1. 截取题干图片（无LaTeX的图片）
 * 2. 提取所有题目文字和LaTeX
 * 3. 输出结构化题目JSON供AI解题
 * 4. 填写答案（需传入answers参数）
 * 5. 验证并提交
 *
 * 用法：
 * # 步骤1: 提取题目（在dowork页面）
 * node auto_solve.cjs extract /tmp/cx_work
 *
 * # 步骤2: 填写+提交（在解题后）
 * node auto_solve.cjs submit /tmp/cx_work '{"1":"A","2":"B",...}'
 */

const { chromium } = require('/home/maniubi/openclaw/node_modules/playwright-core/index.js');
const { writeFileSync, readFileSync, mkdirSync, existsSync } = require('fs');
const path = require('path');

const MODE = process.argv[2] || 'extract';
const OUT_DIR = process.argv[3] || '/tmp/cx_work';
const ANSWERS_JSON = process.argv[4] || '{}';

mkdirSync(OUT_DIR, { recursive: true });

async function findDoworkPage(browser) {
  let best = null, bestCount = 0;
  for (const ctx of browser.contexts()) {
    for (const page of ctx.pages()) {
      const url = page.url();
      if (!url.includes('chaoxing') || !url.includes('dowork')) continue;
      const cdpTmp = await ctx.newCDPSession(page);
      const res = await cdpTmp.send('Runtime.evaluate', {
        expression: `document.querySelectorAll('.questionLi').length`
      });
      await cdpTmp.detach();
      const count = res.result.value || 0;
      if (count > bestCount) { bestCount = count; best = page; }
    }
  }
  return best;
}

async function extractQuestions(page, cdp) {
  // 1. Extract text + LaTeX
  const res = await cdp.send('Runtime.evaluate', {
    expression: `
      JSON.stringify(Array.from(document.querySelectorAll('.questionLi')).map((q, qi) => {
        const decodeLatex = img => {
          const raw = img.getAttribute('data');
          if (!raw) return null;
          try { return decodeURIComponent(raw).replace(/^"|"$/g,'').trim(); } catch(e) { return null; }
        };
        const stemEl = q.querySelector('h3.mark_name, h3.workTextWrap');
        const stemLatex = Array.from((stemEl||q).querySelectorAll('img[data]')).map(decodeLatex).filter(Boolean);
        const stemNoDataImgs = Array.from((stemEl||q).querySelectorAll('img:not([data])')).map(img => ({
          src: img.src.split('/').pop(),
          nW: img.naturalWidth,
          nH: img.naturalHeight,
          pageY: img.getBoundingClientRect().top + window.scrollY,
          x: img.getBoundingClientRect().left
        })).filter(i => i.nW > 5);
        const options = Array.from(q.querySelectorAll('[role=radio]')).map((opt, oi) => ({
          label: ['A','B','C','D','E'][oi],
          text: opt.innerText.trim(),
          latex: Array.from(opt.querySelectorAll('img[data]')).map(decodeLatex).filter(Boolean)
        }));
        return { q: qi+1, stemText: (stemEl||q).innerText.substring(0,300), stemLatex, stemNoDataImgs, options };
      }))
    `
  });
  return JSON.parse(res.result.value);
}

async function screenshotStemImg(cdp, imgInfo, qNum, imgIdx) {
  await cdp.send('Runtime.evaluate', {
    expression: `window.scrollTo(0, ${Math.max(0, imgInfo.pageY - 150)})`
  });
  await new Promise(r => setTimeout(r, 350));
  const sy = (await cdp.send('Runtime.evaluate', { expression: 'window.scrollY' })).result.value;
  const vy = imgInfo.pageY - sy;
  if (vy < 0 || vy > 850) return null;
  const pad = 12;
  const shot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
    clip: { x: Math.max(0, imgInfo.x - pad), y: Math.max(0, vy - pad), width: Math.min(imgInfo.nW + pad*2, 1280), height: imgInfo.nH + pad*2, scale: 1 }
  });
  const buf = Buffer.from(shot.data, 'base64');
  const fname = `q${qNum}_img${imgIdx}.png`;
  writeFileSync(path.join(OUT_DIR, fname), buf);
  return { fname, bytes: buf.length };
}

async function fillAndSubmit(page, cdp, answers) {
  // Fill answers using addChoice()
  const result = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        const ANSWERS = ${JSON.stringify(answers)};
        const questions = Array.from(document.querySelectorAll('.questionLi'));
        const results = [], errors = [];
        questions.forEach((q, qi) => {
          const qNum = qi + 1;
          const ans = ANSWERS[qNum] || ANSWERS[String(qNum)];
          if (!ans) { errors.push('题'+qNum+': 未提供答案'); return; }
          const opts = Array.from(q.querySelectorAll('[role=radio]'));
          const map = {};
          opts.forEach((o, oi) => { map[['A','B','C','D','E'][oi]] = o; });
          const target = map[ans.toUpperCase()];
          if (!target) { errors.push('题'+qNum+': 选项'+ans+'不存在'); return; }
          addChoice(target);
          // Verify written to hidden input
          const inp = q.querySelector('input[id*=answer][type=hidden]');
          const written = inp ? inp.value : '?';
          results.push('✅ 题'+qNum+': 选'+ans+' hidden='+written);
        });
        return JSON.stringify({results, errors});
      })()
    `
  });
  const { results, errors } = JSON.parse(result.result.value);
  console.log(results.join('\n'));
  if (errors.length) console.log('Errors:', errors.join(', '));
  
  // Verify all answered
  const verifyRes = await cdp.send('Runtime.evaluate', {
    expression: `Array.from(document.querySelectorAll('input[id*=answer][type=hidden]')).filter(i=>i.id.startsWith('answer2')).map(i=>i.id+'='+i.value).join(', ')`
  });
  console.log('Hidden inputs:', verifyRes.result.value?.substring(0, 200));
  
  return results.length;
}

(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const page = await findDoworkPage(browser);
  if (!page) { console.error('No dowork page found'); process.exit(1); }
  console.log('Page:', page.url().substring(0,100));
  
  const cdp = await page.context().newCDPSession(page);

  if (MODE === 'extract') {
    console.log('\n=== EXTRACTING QUESTIONS ===');
    const questions = await extractQuestions(page, cdp);
    
    // Screenshot no-data images
    for (const q of questions) {
      for (let j = 0; j < q.stemNoDataImgs.length; j++) {
        const r = await screenshotStemImg(cdp, q.stemNoDataImgs[j], q.q, j);
        if (r) {
          console.log(`q${q.q} img${j}: screenshot saved ${r.fname} (${r.bytes}b)`);
          q.stemNoDataImgs[j].screenshotFile = r.fname;
        }
      }
    }
    
    writeFileSync(path.join(OUT_DIR, 'questions.json'), JSON.stringify(questions, null, 2));
    console.log(`\nSaved ${questions.length} questions to ${OUT_DIR}/questions.json`);
    console.log('Screenshot dir:', OUT_DIR);
    
  } else if (MODE === 'submit') {
    const answers = JSON.parse(ANSWERS_JSON);
    console.log('\n=== FILLING ANSWERS ===', answers);
    const filled = await fillAndSubmit(page, cdp, answers);
    console.log(`\nFilled ${filled} answers`);
  }
  
  await cdp.detach();
  process.exit(0);
})().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
