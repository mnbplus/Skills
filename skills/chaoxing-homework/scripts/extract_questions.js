/**
 * extract_questions.js v2 - 精确版
 * 核心改进：在每个选项元素内部单独查询 img[data]，
 * 彻底解决全局图片索引偏移导致的选项字母映射错误。
 *
 * 用法：
 * pnpm openclaw browser evaluate --browser-profile winchrome \
 *   --fn "$(tr '\n' ' ' < ~/.openclaw/skills/chaoxing-homework/scripts/extract_questions.js)" \
 *   2>&1 | grep -v plugins
 */
el => {
  // 解码单个 img 元素的 LaTeX
  const decodeLatex = img => {
    const raw = img.getAttribute('data');
    if (!raw) return null;
    try {
      return decodeURIComponent(raw)
        .replace(/^"|"$/g, '')
        .replace(/\\\\\[\s*\{?/g, '')
        .replace(/\}?\s*\\\\\]/g, '')
        .trim();
    } catch(e) {
      return raw;
    }
  };

  // 获取元素内所有 LaTeX（按 DOM 顺序）
  const getLatexList = el => {
    return Array.from(el.querySelectorAll('img[data]'))
      .map(decodeLatex)
      .filter(Boolean);
  };

  const questions = document.querySelectorAll('.questionLi');
  const result = [];

  questions.forEach((q, qi) => {
    // 题干区域（h3 或 .mark_name 内）
    const stemEl = q.querySelector('h3.mark_name, h3.workTextWrap');
    const stemText = stemEl ? stemEl.innerText.trim() : '';
    const stemLatex = stemEl ? getLatexList(stemEl) : [];

    // 选项区域（每个 [role=radio] 单独处理）
    const optionEls = Array.from(q.querySelectorAll('[role=radio]'));
    const options = optionEls.map((opt, oi) => {
      const label = ['A','B','C','D','E'][oi] || String(oi);
      const text = opt.innerText.trim();
      const latex = getLatexList(opt);
      return { label, text, latex };
    });

    // 答案区（提交后显示）
    const myAnswerEl = q.querySelector('[class*=myAnswer]');
    const rightAnswerEl = q.querySelector('[class*=rightAnswer]');

    result.push({
      q: qi + 1,
      stemText: stemText.substring(0, 200),
      stemLatex,
      options,
      myAnswer: myAnswerEl ? myAnswerEl.innerText.trim() : null,
      rightAnswer: rightAnswerEl ? rightAnswerEl.innerText.trim() : null,
    });
  });

  return JSON.stringify(result, null, 2);
}
