/**
 * verify_answers.js v1
 * 提交前验证：检查所有题目是否已选择答案，输出当前选中状态
 * 提交后验证：读取我的答案 vs 正确答案，生成得分报告
 *
 * 用法（提交前）：
 * pnpm openclaw browser evaluate --browser-profile winchrome \
 *   --fn "$(tr '\n' ' ' < ~/.openclaw/skills/chaoxing-homework/scripts/verify_answers.js)"
 */
el => {
  const questions = document.querySelectorAll('.questionLi');
  const isResultPage = document.querySelector('[class*=rightAnswer], [class*=myAnswer]') !== null;

  if (isResultPage) {
    // ===== 提交后：对比答案，生成报告 =====
    let correct = 0, wrong = 0, total = 0;
    const details = [];

    questions.forEach((q, qi) => {
      total++;
      const qNum = qi + 1;

      // 尝试多种选择器获取我的答案和正确答案
      const myEl = q.querySelector('[class*=myAnswer]');
      const rightEl = q.querySelector('[class*=rightAnswer]');
      const scoreEl = q.querySelector('[class*=score], .scoreBox');

      const myAns = myEl ? myEl.innerText.trim().replace('我的答案:', '').trim() : '?';
      const rightAns = rightEl ? rightEl.innerText.trim().replace('正确答案:', '').trim() : '?';
      const score = scoreEl ? scoreEl.innerText.trim() : '';

      const isCorrect = myAns !== '?' && rightAns !== '?' && myAns.includes(rightAns);
      if (isCorrect) correct++; else wrong++;

      const icon = isCorrect ? '✅' : '❌';
      details.push(`${icon} 题${qNum}: 我选${myAns} 正确${rightAns} ${score}`);
    });

    const summary = `\n📊 得分报告: ${correct}/${total} 题正确`;
    return [summary, ...details].join('\n');

  } else {
    // ===== 提交前：检查未答题目 =====
    const unanswered = [];
    const answered = [];

    questions.forEach((q, qi) => {
      const qNum = qi + 1;
      const optionEls = Array.from(q.querySelectorAll('[role=radio]'));

      const selectedOpt = optionEls.find(opt =>
        opt.classList.contains('check') ||
        opt.classList.contains('active') ||
        opt.classList.contains('checked') ||
        opt.querySelector('.checkIcon, .check_icon') !== null
      );

      if (selectedOpt) {
        const label = ['A','B','C','D','E'][optionEls.indexOf(selectedOpt)];
        answered.push(`✅ 题${qNum}: 已选${label}`);
      } else {
        unanswered.push(`⚠️  题${qNum}: 未作答`);
      }
    });

    const readyToSubmit = unanswered.length === 0;
    const summary = readyToSubmit
      ? `🟢 全部 ${answered.length} 题已作答，可以提交！`
      : `🔴 还有 ${unanswered.length} 题未作答，请检查！`;

    return [summary, ...answered, ...unanswered].join('\n');
  }
}
