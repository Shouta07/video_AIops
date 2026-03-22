# CLAUDE.md - Video AIops プロジェクト設定

## プロジェクト概要
動画編集オペレーションシステム。素材解析→コンセプト提案→編集→書き出し→キャプション生成のワークフローをAI支援で実行する。

## 作業ルール
- 編集コンセプトは必ずユーザーの承認を得てから実行に移す
- BGMは音声なしで書き出す（TikTokアプリ内で追加するため）
- エラー発生時は内容を表示し代替案を提案する
- 書き出し先は output/{platform}/ に保存する
- レポートは reports/ に保存する

## ツール
- ffmpeg / ffprobe で動画処理を行う
- サムネイル生成: reports/thumbnails/ に保存
- キャプション: reports/captions_YYYY-MM-DD.md に保存
