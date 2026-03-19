/**
 * img2base64.cjs
 * 将截图转为 base64，供 AI 直接分析（不依赖 vision.py）
 * 
 * 用法：node img2base64.cjs <image_path>
 * 输出：base64 data URL
 */
const { readFileSync } = require('fs');
const path = require('path');

const imgPath = process.argv[2];
if (!imgPath) { console.error('Usage: node img2base64.cjs <image_path>'); process.exit(1); }

const buf = readFileSync(imgPath);
const ext = path.extname(imgPath).slice(1).toLowerCase();
const mime = ext === 'jpg' ? 'image/jpeg' : `image/${ext}`;
const b64 = buf.toString('base64');

console.log(`data:${mime};base64,${b64}`);
