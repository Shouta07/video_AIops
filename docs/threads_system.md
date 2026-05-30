# His Recoveries Threads システム設計（参照ドキュメント）

> このドキュメントは **別リポジトリ `github.com/Shouta07/threads`** で稼働している
> Threads 自動投稿システムの設計を、この `video_AIops`（Instagram / リール / Web 側）から
> 参照・整合できるように記録したものです。両システムは **同一の8仮説探索フレームワーク** を
> 共有しており、最終的には His Recoveries Growth Engine（このリポジトリの `growth_engine/`）が
> 全チャネルを横断分析します。

---

## 1. 概要

| 項目 | 内容 |
|---|---|
| アカウント | @hisrecoveries_jp |
| ブランド | His Recoveries / バイタリティデザイン合同会社 |
| プロフURL | https://www.hisrecoveries.com/ |
| リポジトリ | github.com/Shouta07/threads |
| 目的 | **事業仮説の発見**（フォロワー増ではない） |
| フェーズ | Phase 0: 探索期（8仮説を均等検証） |
| テスト | pytest 131件全パス |

## 2. アーキテクチャ（自動運用ループ）

```
毎日 07:30 JST ─┐
                 ├→ Hypothesis Engine → Writer → Validator → Poster → 投稿
毎日 22:30 JST ─┘   仮説を選択/CTA選択   仮説起点でAI生成  17項目チェック  Threads API

毎日 09:00 JST ──→ Collector → Threads API → 成果回収 → hypothesis_results.json
```

## 3. ディレクトリ構成（threads リポジトリ）

```
threads/
├── accounts/mens-body-lab/
│   ├── persona.json          Nagiキャラクター設定
│   ├── hypotheses.json       8仮説 + 4CTA + 6 Discovery Questions 定義
│   ├── experiments.json      実験状態（各仮説の投稿数・フェーズ）
│   ├── patterns.md           投稿構文パターン20種
│   ├── history.json          投稿履歴（hypothesis_id / CTA 付き）★連携の要
│   ├── monetize.json         無効化設定
│   └── rss_feeds.json        RSSフィード4件
├── core/
│   ├── hypothesis.py         仮説管理・選択・実験配分
│   ├── collector.py          投稿成果回収・仮説別集計
│   ├── writer.py             仮説起点の投稿生成（30テンプレート）
│   ├── validator.py          17項目品質チェック
│   ├── poster.py             Threads API投稿
│   ├── researcher.py         トレンド収集（キーワード検索 + RSS）
│   ├── fetcher.py            Threads APIデータ取得
│   ├── analyst.py            効果分析
│   ├── sheets.py             Google Sheets連携
│   ├── supervisor.py         安全装置（キルスイッチ・レート制限）
│   ├── monetize.py           マネタイズ（Phase 0: 無効）
│   ├── scheduler.py          時間管理
│   ├── daemon.py             半自動運用
│   ├── config.py             設定管理
│   └── main.py               CLI司令塔
├── scripts/delete_all_posts.py
├── archive/mens-body-lab/    旧設定アーカイブ
├── data/hypothesis_results.json   仮説別集計結果 ★連携の要
├── .github/workflows/
│   ├── post.yml              毎日 07:30 + 22:30 自動投稿
│   ├── collect.yml           毎日 09:00 成果回収
│   ├── ci.yml                テスト自動実行
│   └── token-refresh.yml     トークン自動更新
├── .env / SYSTEM_DESIGN.md / requirements.txt
```

## 4. Hypothesis Engine（仮説探索の中核）

### 8仮説 ← video_AIops の `shared/hypothesis.py` と **ID完全一致**

| ID | 仮説 | テーマ |
|---|---|---|
| `hygiene` | 男性は清潔感に強く反応する | 清潔感 |
| `aging_anxiety` | 男性は老化不安に強く反応する | 加齢 |
| `confidence` | 男性は自信喪失に強く反応する | 自信 |
| `presence` | 男性はPresenceに強く反応する | 印象・存在感 |
| `recovery_story` | 男性は回復実例に強く反応する | 回復 |
| `loneliness` | 男性は孤独に強く反応する | 孤独 |
| `self_investment` | 男性は自己投資に強く反応する | 自己投資 |
| `conditioning` | 男性はコンディション維持に強く反応する | 疲労・体調 |

### CTA実験（4バリアント）

| ID | テキスト |
|---|---|
| `none` | （なし） |
| `profile_nudge` | 整え方、プロフにまとめています。 |
| `assessment` | 自分の状態を知りたい方へ。プロフから。 |
| `dm_invite` | 同じ悩みを抱えていたら、いつでも。 |

### Discovery Questions（週1回）

1. 汗、髪、肌、匂い。一番長く悩んだのはどれですか？
2. 昔より気になるようになったことはありますか？
3. 20代の頃より今の方が不安なことはありますか？
4. 「整えたい」と思ったきっかけは何でしたか？
5. 誰にも言えなかった悩みはありますか？
6. 清潔感って、どこからだと思いますか？

### 実験フェーズ

| フェーズ | 期間 | 配分 |
|---|---|---|
| explore | 最初の5週 | 8仮説を均等配分 |
| focus | 6〜10週 | 上位3仮説に集中 |
| commit | 11週〜 | 最強仮説に全投下 |

## 5. 投稿テンプレート（30種）

- **悩み系（8）**: 清潔感 / ワキガ / 多汗症 / 匂い / 鏡 / スキンケア / 皮膚科 / 季節
- **モテ・信頼系（3）**: 信頼 / モテ / 仕事
- **写真キャプション系（3）**: カフェ / 横顔 / 日常
- **コミュニティ系（2）**: 共感 / DM
- **体験導線系（2）**: 体験 / 整える
- **短文系（6）**: 一言_清潔感 / 一言_匂い / 一言_鏡 / 一言_整える / 一言_汗 / 一言_信頼
- **問いかけ系（4）**: 問い_清潔感 / 問い_匂い / 問い_スキンケア / 問い_皮膚科
- **Discovery Questions（6）**: 仮説検証用の問いかけ投稿

## 6. ペルソナ: Nagi

| 項目 | 設定 |
|---|---|
| 一人称 | 「僕」固定 |
| 文体 | 丁寧体。温かみ + チル + 寄り添い |
| 絵文字 | 完全禁止 |
| ハッシュタグ | 完全禁止 |
| 文字数 | 30〜450字 |
| 立ち位置 | 半歩先（超えてきたが記憶は残っている） |
| トーン | Monocle / Otonami / NOT A HOTEL 的な静かな知性 |

**3段階構造**: ①過去の事実（過去形）→ ②今の状態（現在形）→ ③自意識の残り方（「ただ、」「でも、」「まだ」）

## 7. バリデーション（17項目）

1. 文字数（30-450字） / 2. 一人称（「僕」のみ） / 3. 絵文字ゼロ / 4. ハッシュタグゼロ /
5. NGワード（6カテゴリ） / 6. 推奨ワード1つ以上 / 7. トピック制限 / 8. メタ情報漏洩 /
9. 完了表現禁止 / 10. 二人称警告 / 11. プライバシー（医院名・地名） /
12. 類似度（閾値0.5、直近30件） / 13. 薬機法・医療広告 / 14. 3段階構造（自意識コネクター必須） /
15. リアクション誘導禁止 / 16. 完全否定禁止 / 17. 教示型チェック

## 8. 成果回収（Collector）

毎朝 09:00 に Threads API insights から取得し、`hypothesis_id` / CTA と紐付け：

| メトリクス | 取得元 |
|---|---|
| likes / views(impressions) / replies / reposts / quotes | Threads insights |

→ `history.json` に記録 → `data/hypothesis_results.json` に仮説別・CTA別クロス集計

## 9. 安全装置 / GitHub Actions / 環境変数

- **安全装置**: キルスイッチ（環境変数 + ファイルの二重）/ レート制限2投稿/時 /
  Geminiサーキットブレーカー（429で1時間停止）/ トークン自動更新（50日）/ APIキーマスク
- **Actions**: `post.yml`(07:30+22:30) / `collect.yml`(09:00) / `ci.yml`(PR毎) / `token-refresh.yml`(月1)
- **環境変数**: `THREADS_APP_ID` / `THREADS_APP_SECRET` / `THREADS_ACCESS_TOKEN` /
  `THREADS_USER_ID` / `GEMINI_API_KEY` / `GEMINI_MODEL=gemini-2.0-flash` /
  `THREADS_KEYWORD_SEARCH_APPROVED=true` / `KILL_SWITCH=false`（GitHub Secrets にも設定済み）

## 10. CVR導線

```
Threads投稿（仮説検証 + 共感）
  ↓ プロフ訪問
hisrecoveries.com（記事 + アフィ）  /  DM相談 → Quiet Sessions（オフライン体験）
```

## 11. 運用コマンド（threads リポジトリ）

```bash
python -m core.main post mens-body-lab                    # 仮説起点でAI生成→投稿
python -m core.main post mens-body-lab --mock             # mockテンプレ投稿（Gemini不要）
python -m core.main post mens-body-lab --mock --dry-run   # 確認のみ
python -m core.main collect mens-body-lab --days 3        # 成果回収
touch KILL_SWITCH                                          # 緊急停止
```

---

## 12. video_AIops との連携マップ ★このリポジトリ視点

His Recoveries は **3チャネル** で同一の仮説を検証する。threads はその Threads 側エンジン、
このリポジトリは Instagram / リール / Web 側エンジン + 全チャネル横断の Growth Engine を担う。

```
                ┌─────────────── 共有: 8仮説フレームワーク ───────────────┐
                │                                                          │
  [threads リポ] Threads 投稿/回収 ──→ data/hypothesis_results.json ──┐    │
                                                                       │    │
  [video_AIops]  Instagram/リール  ──→ instagram/poster.py 回収 ───┐  │    │
                 Web(GA4/SC)        ──→ shared/collector.py ───────┤  │    │
                                                                   ▼  ▼    │
                                          growth_engine/ 横断分析（仮説スコア・週次・ファネル）
```

### 対応関係

| レイヤ | threads リポジトリ | video_AIops（本リポジトリ） |
|---|---|---|
| 仮説定義 | `accounts/.../hypotheses.json`（8仮説 + CTA + DQ） | `shared/hypothesis.py`（8仮説、ID一致） |
| 投稿生成 | `core/writer.py`（30テンプレ / Gemini） | `instagram/script_writer.py`・`reel_editor.py`（リール3型 / GPT） |
| 品質チェック | `core/validator.py`（17項目） | （リール側は未実装 / 下記ギャップ参照） |
| 投稿 | `core/poster.py`（Threads API） | `instagram/poster.py`（Instagram Graph API） |
| 成果回収 | `core/collector.py` → `hypothesis_results.json` | `shared/collector.py`（Threads/IG/GA4/SC） |
| 横断分析 | （単チャネル） | `growth_engine/`（dashboard / weekly_insight / funnel） |

### 整合性ギャップ（次ステップ候補）

1. **CTA 帰属が未連携**: 本リポジトリの `shared/collector.py` は Threads API を直接叩くが、
   どの投稿がどの CTA バリアントだったかは threads 側の `history.json` にしかない
   （`collector.py` L81 `cta_type` が空）。
   → threads の `history.json` / `hypothesis_results.json` を読み込んで CTA を付与すると、
   `growth_engine` で **CTA別CVR** まで横断分析できる。
2. **Discovery Questions / CTA がこちら側に構造化されていない**: `shared/hypothesis.py` は
   8仮説のみ。4CTA・6 Discovery Questions を共有定義に加えると、リール/IG 側でも
   同じ実験軸を流用できる。
3. **リール側の品質チェック未実装**: threads の `validator.py`（17項目）に相当する
   Nagi ペルソナ準拠チェック（絵文字/ハッシュタグ禁止・3段階構造・薬機法 等）が
   リール台本生成側に無い。
4. **データ受け渡し方式の未定義**: threads → video_AIops は別リポジトリ。
   `hypothesis_results.json` を Google Sheets（両者の `sheets.py`）経由で共有するか、
   成果物をエクスポート/インポートするかを決める必要がある。

### 未実装・次ステップ（全体）

| 項目 | 状態 |
|---|---|
| Google Sheets 接続（両リポジトリ共通の連携ハブ候補） | コード完成、GCP サービスアカウント未設定 |
| Weekly Insight Report | video_AIops 側に `growth_engine/weekly_insight.py` 実装済み（threads単体ではP2） |
| Threads ↔ video_AIops のデータ統合（CTA帰属・横断集計） | 未着手（上記ギャップ1） |
| リール側 Nagi バリデーション | 未着手（上記ギャップ3） |
