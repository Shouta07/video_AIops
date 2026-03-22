// ── ジャンル別バズパターン辞書 ──
// TikTok/Reels で実際に伸びている構成パターンをジャンルごとに定義

export const GENRES = [
  {
    id: "food",
    name: "料理・グルメ",
    icon: "🍳",
    patterns: [
      {
        id: "food-result-first",
        name: "完成品フック型",
        description: "完成品を冒頭に見せて「どうやって作るの？」と興味を引く。TikTok料理系で最も伸びやすい型。",
        totalDuration: 30,
        structure: [
          { name: "完成品フック", start: 0, end: 2, note: "完成品のアップ。テロップ「これ○○で作れます」", position: "center" },
          { name: "材料紹介", start: 2, end: 5, note: "材料を並べたカット。テロップで材料名", position: "bottom" },
          { name: "調理過程", start: 5, end: 24, note: "早送りで調理。各工程にテロップ", position: "bottom" },
          { name: "盛り付け", start: 24, end: 28, note: "スローで盛り付け。「完成〜」", position: "center" },
          { name: "実食・CTA", start: 28, end: 30, note: "リアクション or フォロー誘導", position: "bottom" },
        ],
        tips: ["冒頭2秒で完成品を見せるのが最重要", "調理過程は2〜3倍速", "材料テロップは読みやすく大きく"],
      },
      {
        id: "food-asmr",
        name: "ASMR調理型",
        description: "調理音を活かしたASMR風。テロップで手順を補足。",
        totalDuration: 45,
        structure: [
          { name: "食材カット音", start: 0, end: 3, note: "包丁の音で引きつける", position: "bottom" },
          { name: "調理過程", start: 3, end: 35, note: "焼く音・炒める音を活かす。テロップで手順", position: "bottom" },
          { name: "完成", start: 35, end: 42, note: "スローで湯気や溶けるチーズ等", position: "center" },
          { name: "CTA", start: 42, end: 45, note: "「レシピはプロフから」等", position: "bottom" },
        ],
        tips: ["BGMは控えめ or なし（音声が主役）", "切る・焼く・注ぐのアップショット多め"],
      },
    ],
  },
  {
    id: "travel",
    name: "旅行・Vlog",
    icon: "✈️",
    patterns: [
      {
        id: "travel-transition",
        name: "トランジション旅型",
        description: "場面転換のトランジションで視聴者を飽きさせない。カメラを手で覆う→次のシーンが定番。",
        totalDuration: 30,
        structure: [
          { name: "到着フック", start: 0, end: 3, note: "「○○来た！」テロップ＋絶景カット", position: "center" },
          { name: "スポット1", start: 3, end: 10, note: "観光地・食事。トランジションで切替", position: "bottom" },
          { name: "スポット2", start: 10, end: 18, note: "別の場所へ。テンポよくカット", position: "bottom" },
          { name: "ハイライト", start: 18, end: 26, note: "最も映えるシーン。スロー", position: "center" },
          { name: "まとめ", start: 26, end: 30, note: "「○○最高だった」テロップ", position: "bottom" },
        ],
        tips: ["1カット3秒以内でテンポを保つ", "トランジションは手で覆う/回転が定番", "場所名テロップ必須"],
      },
      {
        id: "travel-cinematic",
        name: "シネマティック旅型",
        description: "映画のような雰囲気。スローモーション多用。伸びるのはリゾート・自然系。",
        totalDuration: 45,
        structure: [
          { name: "ドローン/広角", start: 0, end: 5, note: "壮大な風景。場所名テロップ", position: "center" },
          { name: "日常シーン", start: 5, end: 20, note: "歩く・食べる・触れるをスローで", position: "bottom" },
          { name: "ハイライト", start: 20, end: 38, note: "最も美しいシーンを複数カット", position: "bottom" },
          { name: "余韻", start: 38, end: 45, note: "夕日やフェードアウト", position: "center" },
        ],
        tips: ["シネマティックバーを入れると雰囲気UP", "カラーグレーディングは暖色系が人気"],
      },
    ],
  },
  {
    id: "beauty",
    name: "美容・コスメ",
    icon: "💄",
    patterns: [
      {
        id: "beauty-before-after",
        name: "ビフォーアフター型",
        description: "変身前→変身後のギャップで伸びる。GRWM(Get Ready With Me)の定番。",
        totalDuration: 30,
        structure: [
          { name: "Before（すっぴん）", start: 0, end: 3, note: "すっぴんを見せる。「今日のメイク」テロップ", position: "center" },
          { name: "ベースメイク", start: 3, end: 10, note: "早送りで塗る過程。使用コスメ名テロップ", position: "bottom" },
          { name: "ポイントメイク", start: 10, end: 22, note: "アイ・リップ。アップショット", position: "bottom" },
          { name: "After（完成）", start: 22, end: 28, note: "スローで完成顔。「変身完了」", position: "center" },
          { name: "CTA", start: 28, end: 30, note: "使用コスメまとめ or フォロー誘導", position: "bottom" },
        ],
        tips: ["Before→Afterのギャップが大きいほど伸びる", "使用コスメのブランド名・品番は必ずテロップ"],
      },
    ],
  },
  {
    id: "fitness",
    name: "筋トレ・フィットネス",
    icon: "💪",
    patterns: [
      {
        id: "fitness-routine",
        name: "ルーティン紹介型",
        description: "「○日で腹筋割れる」等の具体的な数字フックで引きつけ、エクササイズを紹介。",
        totalDuration: 30,
        structure: [
          { name: "数字フック", start: 0, end: 3, note: "「1日3分でOK」等のテロップ大文字", position: "center" },
          { name: "種目1", start: 3, end: 10, note: "やり方をテロップで説明。回数表示", position: "bottom" },
          { name: "種目2", start: 10, end: 17, note: "次の種目。テンポよく", position: "bottom" },
          { name: "種目3", start: 17, end: 24, note: "最後の種目", position: "bottom" },
          { name: "結果・CTA", start: 24, end: 30, note: "ビフォーアフター or 「続きはフォロー」", position: "center" },
        ],
        tips: ["具体的な数字（○日、○回、○分）がフックに必須", "テロップで種目名と回数を常時表示"],
      },
    ],
  },
  {
    id: "business",
    name: "ビジネス・ノウハウ",
    icon: "📊",
    patterns: [
      {
        id: "business-list",
        name: "リスト型（○選）",
        description: "「知らないと損する○選」「○つの方法」で引きつけるリスト形式。情報系で最も伸びる型。",
        totalDuration: 45,
        structure: [
          { name: "煽りフック", start: 0, end: 3, note: "「99%が知らない」「損してる人の特徴」等", position: "center" },
          { name: "ポイント1", start: 3, end: 12, note: "1つ目を説明。テロップ大きめ", position: "center" },
          { name: "ポイント2", start: 12, end: 22, note: "2つ目。具体例を添える", position: "center" },
          { name: "ポイント3", start: 22, end: 32, note: "3つ目。最もインパクトのある内容", position: "center" },
          { name: "まとめ・CTA", start: 32, end: 45, note: "「保存して見返して」「フォローで続き」", position: "center" },
        ],
        tips: ["フックは「損」「知らない」「やばい」等のネガティブワードが強い", "テロップは画面中央に大きく", "保存を促すと保存率UP→アルゴに有利"],
      },
      {
        id: "business-story",
        name: "体験談ストーリー型",
        description: "「○○したら人生変わった」系。共感→転機→結果のストーリー構成。",
        totalDuration: 60,
        structure: [
          { name: "共感フック", start: 0, end: 5, note: "「昔の自分は○○だった」で共感を誘う", position: "center" },
          { name: "問題提起", start: 5, end: 15, note: "困っていたこと・悩みを語る", position: "center" },
          { name: "転機", start: 15, end: 25, note: "「ある日○○に出会って」", position: "center" },
          { name: "変化・結果", start: 25, end: 45, note: "具体的な成果を数字で見せる", position: "center" },
          { name: "教訓・CTA", start: 45, end: 60, note: "学び→「同じ悩みの人はフォロー」", position: "center" },
        ],
        tips: ["数字で結果を見せる（月収○万→○万等）", "顔出しの方が信頼感UP"],
      },
    ],
  },
  {
    id: "lifestyle",
    name: "ライフスタイル・日常",
    icon: "🏠",
    patterns: [
      {
        id: "lifestyle-routine",
        name: "モーニングルーティン型",
        description: "「丁寧な暮らし」系。朝の過ごし方を淡々と見せる。BGMなしでも環境音で成立。",
        totalDuration: 45,
        structure: [
          { name: "起床", start: 0, end: 5, note: "目覚まし・ストレッチ。時刻テロップ「6:00」", position: "top" },
          { name: "朝食準備", start: 5, end: 18, note: "コーヒー淹れる・朝食作り。ASMR風", position: "bottom" },
          { name: "朝食・支度", start: 18, end: 32, note: "食べる・歯磨き・着替え", position: "bottom" },
          { name: "出発", start: 32, end: 42, note: "家を出る・通勤", position: "bottom" },
          { name: "CTA", start: 42, end: 45, note: "「今日も頑張ろう」", position: "center" },
        ],
        tips: ["時刻テロップを入れるとルーティン感UP", "環境音（コーヒーの音等）を活かす"],
      },
    ],
  },
  {
    id: "education",
    name: "教育・解説",
    icon: "📚",
    patterns: [
      {
        id: "education-explain",
        name: "図解・解説型",
        description: "複雑な概念を短時間でわかりやすく。テロップが主役。",
        totalDuration: 30,
        structure: [
          { name: "問いかけ", start: 0, end: 3, note: "「○○って知ってる？」で掴む", position: "center" },
          { name: "解説①", start: 3, end: 12, note: "ポイント1を大きなテロップで説明", position: "center" },
          { name: "解説②", start: 12, end: 22, note: "ポイント2。具体例を添える", position: "center" },
          { name: "まとめ", start: 22, end: 28, note: "結論をシンプルに", position: "center" },
          { name: "CTA", start: 28, end: 30, note: "「保存して復習して」「フォローで続き」", position: "bottom" },
        ],
        tips: ["テロップは1画面1メッセージ", "難しい言葉は使わない", "保存を促す文言を入れる"],
      },
    ],
  },
  {
    id: "product",
    name: "商品紹介・レビュー",
    icon: "🛍️",
    patterns: [
      {
        id: "product-review",
        name: "正直レビュー型",
        description: "「正直に言います」で信頼感。メリット・デメリット両方見せる。",
        totalDuration: 30,
        structure: [
          { name: "商品フック", start: 0, end: 3, note: "商品アップ。「正直にレビューします」", position: "center" },
          { name: "メリット", start: 3, end: 13, note: "良い点を2〜3個。テロップで箇条書き", position: "bottom" },
          { name: "デメリット", start: 13, end: 20, note: "悪い点も正直に。信頼感UP", position: "bottom" },
          { name: "総評", start: 20, end: 27, note: "「○○な人にはおすすめ」", position: "center" },
          { name: "CTA", start: 27, end: 30, note: "「リンクはプロフから」", position: "bottom" },
        ],
        tips: ["デメリットを言うことで信頼感が上がる", "価格は必ず表示"],
      },
    ],
  },
];

/**
 * ジャンル＋パターンから編集コンセプトを生成
 * @param {string} genreId
 * @param {string} patternId
 * @param {Array} materials - 解析済み素材
 * @param {string} platformId - "tiktok" | "reels" | "shorts" | "youtube"
 * @returns {Object} コンセプト
 */
export function buildConceptFromPattern(genreId, patternId, materials, platformId) {
  const genre = GENRES.find((g) => g.id === genreId);
  if (!genre) return null;
  const pattern = genre.patterns.find((p) => p.id === patternId);
  if (!pattern) return null;

  const PLATFORM_SPECS = {
    tiktok: { name: "TikTok", w: 1080, h: 1920, aspect: "9:16" },
    reels: { name: "Instagram Reels", w: 1080, h: 1920, aspect: "9:16" },
    shorts: { name: "YouTube Shorts", w: 1080, h: 1920, aspect: "9:16" },
    youtube: { name: "YouTube", w: 1920, h: 1080, aspect: "16:9" },
  };

  const platform = PLATFORM_SPECS[platformId] || PLATFORM_SPECS.tiktok;

  return {
    id: `${pattern.id}-${platformId}`,
    styleName: `${genre.icon} ${pattern.name}`,
    styleDescription: pattern.description,
    styleIcon: "star",
    platform: platform.name,
    platformId,
    targetDuration: pattern.totalDuration,
    targetDurationStr: formatDur(pattern.totalDuration),
    clipCount: Math.min(materials.length, pattern.structure.length),
    totalClips: materials.length,
    resolution: `${platform.w}x${platform.h}`,
    aspect: platform.aspect,
    transition: "カット",
    structure: pattern.structure.map((s) => ({
      name: s.name,
      duration: `${s.start}〜${s.end}秒`,
      note: s.note,
    })),
    // Keep raw structure for editor pre-fill
    rawStructure: pattern.structure,
    tips: pattern.tips,
    score: 100,
    materials,
    genreId,
    patternId,
  };
}

/**
 * 参考動画のメタデータからパターンの尺を調整
 */
export function adjustPatternByReference(concept, refDuration) {
  if (!refDuration || refDuration <= 0) return concept;

  const ratio = refDuration / concept.targetDuration;
  const adjusted = { ...concept };
  adjusted.targetDuration = Math.round(refDuration);
  adjusted.targetDurationStr = formatDur(refDuration);
  adjusted.structure = concept.structure.map((s) => {
    const parts = s.duration.match(/(\d+)〜(\d+)/);
    if (parts) {
      const start = Math.round(parseFloat(parts[1]) * ratio);
      const end = Math.round(parseFloat(parts[2]) * ratio);
      return { ...s, duration: `${start}〜${end}秒` };
    }
    return s;
  });
  if (concept.rawStructure) {
    adjusted.rawStructure = concept.rawStructure.map((s) => ({
      ...s,
      start: Math.round(s.start * ratio * 10) / 10,
      end: Math.round(s.end * ratio * 10) / 10,
    }));
  }
  return adjusted;
}

function formatDur(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + ":" + s.toString().padStart(2, "0");
}
