# Video AIops - 動画編集オペレーションシステム

AI支援による動画編集ワークフローを管理するシステムです。

## ディレクトリ構成

```
video_AIops/
├── input/              # 素材動画（.gitignore対象）
├── output/
│   ├── tiktok/         # TikTok向け書き出し
│   ├── instagram/      # Instagram向け書き出し
│   └── youtube/        # YouTube向け書き出し
├── assets/
│   └── fonts/          # テロップ用フォント
├── reports/
│   └── thumbnails/     # 素材解析サムネイル
├── captions/           # キャプション・ハッシュタグ
└── clients/            # クライアント別設定
```

## ワークフロー

1. **素材解析** - `input/` に動画を配置し、ffprobeで情報取得・サムネイル生成
2. **コンセプト提案** - プラットフォームに合わせた編集構成を設計
3. **編集** - トリミング・結合・テロップ挿入・手振れ補正
4. **書き出し** - 各プラットフォーム向けにエンコード
5. **キャプション生成** - 投稿用テキスト・ハッシュタグを作成

## 書き出し仕様

| プラットフォーム | アスペクト比 | 解像度 | 備考 |
|---|---|---|---|
| TikTok | 9:16 | 1080x1920 | BGMはアプリ内で追加 |
| Instagram Reels | 9:16 | 1080x1920 | - |
| YouTube Shorts | 9:16 | 1080x1920 | - |

## 必要ツール

- `ffmpeg` / `ffprobe` - 動画処理
- Claude Code - AI支援による編集提案・キャプション生成

## 関連システム

His Recoveries は **3チャネル（Threads / Instagram・リール / Web）** で同一の8仮説を検証している。

- **Threads 側エンジン**: 別リポジトリ [`Shouta07/threads`](https://github.com/Shouta07/threads)（自動投稿・成果回収）
- **Instagram・リール / Web 側 + 横断分析**: 本リポジトリ（`growth_engine/`, `instagram/`, `shared/`）

両システムは `shared/hypothesis.py` の8仮説とID互換。設計詳細と連携マップは
[`docs/threads_system.md`](docs/threads_system.md) を参照。
