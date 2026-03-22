// ── 編集コンセプト生成エンジン ──
// 素材の解析結果からプラットフォーム別の編集プランを提案する

const PLATFORM_SPECS = {
  tiktok: {
    name: "TikTok",
    maxDuration: 60,
    idealDuration: [15, 30, 60],
    aspect: "9:16",
    resolution: { w: 1080, h: 1920 },
  },
  reels: {
    name: "Instagram Reels",
    maxDuration: 90,
    idealDuration: [15, 30, 60],
    aspect: "9:16",
    resolution: { w: 1080, h: 1920 },
  },
  shorts: {
    name: "YouTube Shorts",
    maxDuration: 60,
    idealDuration: [15, 30, 60],
    aspect: "9:16",
    resolution: { w: 1080, h: 1920 },
  },
  youtube: {
    name: "YouTube",
    maxDuration: 600,
    idealDuration: [60, 180, 480],
    aspect: "16:9",
    resolution: { w: 1920, h: 1080 },
  },
};

const EDIT_STYLES = [
  {
    id: "fast-cut",
    name: "テンポ重視カット",
    description: "1〜3秒の高速カットで視聴者を引きつける。冒頭にフック、中盤にハイライト、ラストにCTA。",
    icon: "zap",
    cutInterval: 2,
    transition: "カット",
    suitable: ["tiktok", "reels", "shorts"],
  },
  {
    id: "story",
    name: "ストーリー構成",
    description: "起承転結の流れで構成。各クリップを5〜10秒ずつ使い、自然なつながりを重視。",
    icon: "book",
    cutInterval: 7,
    transition: "フェード / ディゾルブ",
    suitable: ["youtube", "reels"],
  },
  {
    id: "highlight",
    name: "ハイライト集",
    description: "ベストシーンだけを集めたダイジェスト。各クリップの見どころを2〜4秒ずつピックアップ。",
    icon: "star",
    cutInterval: 3,
    transition: "カット / ワイプ",
    suitable: ["tiktok", "reels", "shorts"],
  },
  {
    id: "cinematic",
    name: "シネマティック",
    description: "スローペースでじっくり見せる。各クリップ8〜15秒。余白を活かした落ち着いた雰囲気。",
    icon: "film",
    cutInterval: 12,
    transition: "スローフェード",
    suitable: ["youtube"],
  },
  {
    id: "before-after",
    name: "ビフォーアフター",
    description: "素材を前半・後半に分けて対比構成。変化や成長を効果的に見せる。",
    icon: "repeat",
    cutInterval: 5,
    transition: "スプリット / ワイプ",
    suitable: ["tiktok", "reels", "shorts"],
  },
];

/**
 * 素材解析結果からコンセプト提案を生成
 * @param {Array} materials - extractMetadata() の結果配列
 * @returns {Array} コンセプト提案の配列
 */
export function generateConcepts(materials) {
  const valid = materials.filter((m) => !m.error && m.duration > 0);
  if (valid.length === 0) return [];

  const totalDuration = valid.reduce((s, m) => s + m.duration, 0);
  const avgDuration = totalDuration / valid.length;

  // Detect suitable platforms from materials
  const detectedPlatforms = detectPlatforms(valid);

  const concepts = [];

  for (const style of EDIT_STYLES) {
    // Check if style is suitable for detected platforms
    const matchingPlatforms = style.suitable.filter(
      (p) => detectedPlatforms.includes(p) || detectedPlatforms.length === 0
    );

    if (matchingPlatforms.length === 0) continue;

    for (const platformId of matchingPlatforms) {
      const platform = PLATFORM_SPECS[platformId];
      const concept = buildConcept(style, platform, valid, totalDuration);
      if (concept) concepts.push(concept);
    }
  }

  // Sort: best matches first, limit to 4
  concepts.sort((a, b) => b.score - a.score);
  return concepts.slice(0, 4);
}

function detectPlatforms(materials) {
  const platforms = new Set();
  for (const m of materials) {
    if (m.platform && m.platform.length > 0) {
      for (const p of m.platform) {
        const key = p.toLowerCase().replace("instagram ", "");
        if (PLATFORM_SPECS[key]) platforms.add(key);
      }
    }
  }
  // Default: short-form if no clear platform detected
  if (platforms.size === 0) {
    platforms.add("tiktok");
    platforms.add("reels");
  }
  return [...platforms];
}

function buildConcept(style, platform, materials, totalDuration) {
  const clipCount = materials.length;

  // Calculate target duration
  let targetDuration;
  if (totalDuration <= platform.maxDuration) {
    // All clips fit
    targetDuration = Math.min(totalDuration, platform.maxDuration);
  } else {
    // Need to trim - pick best ideal duration
    targetDuration = platform.idealDuration
      .filter((d) => d <= platform.maxDuration)
      .reduce((best, d) => {
        const usable = Math.min(totalDuration, platform.maxDuration);
        return Math.abs(d - usable) < Math.abs(best - usable) ? d : best;
      }, platform.idealDuration[0]);
  }

  // How many clips to use and their individual duration
  const clipDuration = style.cutInterval;
  const usableClips = Math.min(
    clipCount,
    Math.max(1, Math.floor(targetDuration / clipDuration))
  );
  const finalDuration = Math.min(usableClips * clipDuration, targetDuration);

  // Score: higher is better match
  let score = 0;
  score += usableClips >= 3 ? 20 : usableClips >= 2 ? 10 : 5;
  score += finalDuration >= 15 ? 15 : 5;
  if (finalDuration <= platform.maxDuration) score += 10;

  // Bonus for matching aspect ratio
  const verticalMaterials = materials.filter(
    (m) => m.width && m.height && m.height > m.width
  );
  const isVerticalContent = verticalMaterials.length > clipCount / 2;
  if (
    (isVerticalContent && platform.aspect === "9:16") ||
    (!isVerticalContent && platform.aspect === "16:9")
  ) {
    score += 20;
  }

  // Build structure
  const structure = buildStructure(style, usableClips, finalDuration);

  return {
    id: `${style.id}-${platform.name.toLowerCase().replace(/\s/g, "")}`,
    styleName: style.name,
    styleDescription: style.description,
    styleIcon: style.icon,
    platform: platform.name,
    platformId: Object.keys(PLATFORM_SPECS).find(
      (k) => PLATFORM_SPECS[k] === platform
    ),
    targetDuration: finalDuration,
    targetDurationStr: formatDur(finalDuration),
    clipCount: usableClips,
    totalClips: clipCount,
    resolution: `${platform.resolution.w}x${platform.resolution.h}`,
    aspect: platform.aspect,
    transition: style.transition,
    structure,
    score,
    materials: materials.slice(0, usableClips),
  };
}

function buildStructure(style, clipCount, duration) {
  const parts = [];

  if (style.id === "fast-cut" || style.id === "highlight") {
    parts.push({
      name: "フック",
      duration: "0〜2秒",
      note: "最もインパクトのあるシーンを冒頭に配置",
    });
    const bodyClips = Math.max(1, clipCount - 2);
    parts.push({
      name: "メインパート",
      duration: `2〜${Math.floor(duration * 0.85)}秒`,
      note: `${bodyClips}クリップをテンポよくカット`,
    });
    parts.push({
      name: "エンディング",
      duration: `ラスト${Math.max(2, Math.floor(duration * 0.15))}秒`,
      note: "余韻を残すシーンまたはCTA",
    });
  } else if (style.id === "story") {
    parts.push({
      name: "導入",
      duration: `0〜${Math.floor(duration * 0.2)}秒`,
      note: "状況設定・世界観の提示",
    });
    parts.push({
      name: "展開",
      duration: `${Math.floor(duration * 0.2)}〜${Math.floor(duration * 0.7)}秒`,
      note: "メインコンテンツを展開",
    });
    parts.push({
      name: "クライマックス・結末",
      duration: `${Math.floor(duration * 0.7)}〜${Math.floor(duration)}秒`,
      note: "見どころ・まとめ",
    });
  } else if (style.id === "before-after") {
    parts.push({
      name: "Before",
      duration: `0〜${Math.floor(duration * 0.45)}秒`,
      note: "変化前のシーンを見せる",
    });
    parts.push({
      name: "転換",
      duration: "1〜2秒",
      note: "トランジション演出",
    });
    parts.push({
      name: "After",
      duration: `${Math.floor(duration * 0.55)}〜${Math.floor(duration)}秒`,
      note: "変化後のシーンを見せる",
    });
  } else {
    // cinematic etc
    const perClip = Math.floor(duration / Math.max(1, clipCount));
    parts.push({
      name: "オープニング",
      duration: `0〜${perClip}秒`,
      note: "スローで雰囲気を作る",
    });
    if (clipCount > 2) {
      parts.push({
        name: "本編",
        duration: `${perClip}〜${perClip * (clipCount - 1)}秒`,
        note: `${clipCount - 2}シーンをじっくり展開`,
      });
    }
    parts.push({
      name: "エンディング",
      duration: `ラスト${perClip}秒`,
      note: "フェードアウトで余韻",
    });
  }

  return parts;
}

function formatDur(seconds) {
  if (!seconds || !isFinite(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + ":" + s.toString().padStart(2, "0");
}

export { PLATFORM_SPECS };
