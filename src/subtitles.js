// ── 自動字幕生成エンジン ──
// Whisper API の文字起こし結果から、テロップデータを自動生成する
import { loadDefaultJapaneseParser } from "budoux";

const parser = loadDefaultJapaneseParser();

const MAX_CHARS_PER_SUBTITLE = 30;

/**
 * Whisper の segments からテロップデータを生成
 * @param {Array} segments - [{ id, start, end, text }]
 * @returns {Array} subtitles - [{ text, lines, startTime, endTime, fontSize, position }]
 */
export function generateSubtitles(segments) {
  const raw = [];

  for (const seg of segments) {
    const text = seg.text.trim();
    if (!text) continue;

    if (text.length <= MAX_CHARS_PER_SUBTITLE) {
      raw.push({
        text,
        startTime: seg.start,
        endTime: seg.end,
      });
    } else {
      // Split long segments using BudouX
      const chunks = splitByBudoux(text, MAX_CHARS_PER_SUBTITLE);
      const totalChars = text.length;
      const duration = seg.end - seg.start;
      let charOffset = 0;

      for (const chunk of chunks) {
        const ratio = chunk.length / totalChars;
        const chunkStart = seg.start + (charOffset / totalChars) * duration;
        const chunkEnd = chunkStart + ratio * duration;
        raw.push({
          text: chunk,
          startTime: Math.round(chunkStart * 100) / 100,
          endTime: Math.round(chunkEnd * 100) / 100,
        });
        charOffset += chunk.length;
      }
    }
  }

  // Convert to subtitle format with lines and fontSize
  return raw.map((sub, i) => {
    const { lines, fontSize } = formatSubtitle(sub.text);
    return {
      id: i,
      text: sub.text,
      lines,
      startTime: sub.startTime,
      endTime: sub.endTime,
      fontSize,
      position: "bottom",
    };
  });
}

/**
 * BudouX でテキストを文節分割し、指定文字数以内のチャンクに結合
 */
function splitByBudoux(text, maxChars) {
  const phrases = parser.parse(text);
  const chunks = [];
  let current = "";

  for (const phrase of phrases) {
    if (current.length + phrase.length > maxChars && current.length > 0) {
      chunks.push(current);
      current = phrase;
    } else {
      current += phrase;
    }
  }
  if (current) chunks.push(current);

  return chunks;
}

/**
 * テロップテキストを行分割し、フォントサイズを決定
 * - 18文字以下: 1行
 * - 19〜30文字: BudouX で均等2行
 */
function formatSubtitle(text) {
  if (text.length <= 18) {
    return {
      lines: [text],
      fontSize: getFontSize(text.length),
    };
  }

  // 2行に分割
  const phrases = parser.parse(text);
  const targetLen = Math.ceil(text.length / 2);
  let line1 = "";
  let line2 = "";
  let assigned = false;

  for (const phrase of phrases) {
    if (!assigned && line1.length + phrase.length <= targetLen + 3) {
      line1 += phrase;
    } else {
      assigned = true;
      line2 += phrase;
    }
  }

  if (!line2) {
    // Fallback: split at midpoint
    const mid = Math.ceil(text.length / 2);
    line1 = text.substring(0, mid);
    line2 = text.substring(mid);
  }

  const maxLineLen = Math.max(line1.length, line2.length);
  return {
    lines: [line1, line2],
    fontSize: getFontSize(maxLineLen),
  };
}

/**
 * 最長行の文字数からフォントサイズを決定
 */
function getFontSize(charCount) {
  if (charCount <= 8) return 72;
  if (charCount <= 12) return 64;
  if (charCount <= 18) return 56;
  if (charCount <= 24) return 48;
  return 42;
}

/**
 * SRT 形式でエクスポート
 */
export function exportSRT(subtitles) {
  return subtitles
    .map((sub, i) => {
      const start = formatSRTTime(sub.startTime);
      const end = formatSRTTime(sub.endTime);
      const text = sub.lines ? sub.lines.join("\n") : sub.text;
      return `${i + 1}\n${start} --> ${end}\n${text}\n`;
    })
    .join("\n");
}

function formatSRTTime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.round((seconds % 1) * 1000);
  return `${pad(h)}:${pad(m)}:${pad(s)},${ms.toString().padStart(3, "0")}`;
}

function pad(n) {
  return n.toString().padStart(2, "0");
}
