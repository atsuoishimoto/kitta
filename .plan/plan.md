# Kitta 実装プラン

`.plan/product.md`（製品企画書）に基づく実装計画。MVP（企画書 §26）の完成を最終ゴールとし、
Advanced Parameters / User Presets（§27）は本プランの対象外とする。

---

## 1. ゴールと成果物

MVP として以下を出荷する。

### GUI
- 画像のドラッグ&ドロップ → 複数プリセットで推論 → 横並び比較
- synchronized zoom / pan、Checker / White / Black 背景切替
- Original / Mask / Result 表示、結果選択、透過 PNG・マスク保存
- モデルのオンデマンド取得（ダウンロードプログレス表示）

### CLI
- 単体画像処理（`kitta image.jpg`）
- `--model` / `--preset` 指定、`kitta compare`、`kitta batch`

### 配布
- Windows MSIX（pyappdist）、macOS application bundle
- GitHub Actions によるビルド・テスト
- Microsoft Store 公開準備（ライセンス表示・NOTICE 含む）

---

## 2. 技術スタックとプロジェクト基盤

| 項目 | 選定 |
| --- | --- |
| Python | 3.12（pyappdist が同梱する runtime に合わせて最終決定） |
| パッケージ管理 | uv + `pyproject.toml`（単一パッケージ `kitta`） |
| GUI | PySide6 / Qt Widgets（QGraphicsView ベース） |
| 推論 | rembg + onnxruntime（CPU 版） |
| 画像処理 | Pillow / NumPy |
| CLI | argparse（依存を増やさない。必要になったら click を検討） |
| 設定/プリセット | TOML（読み: `tomllib`、書き: `tomli-w`） |
| テスト | pytest（GUI は pytest-qt） |
| Lint/Format | ruff |
| CI | GitHub Actions |
| 配布 | pyappdist |

依存関係の方針:

- `kitta.core` / `kitta.cli` は PySide6 に依存しない（企画書 §21 の「GUI に依存しない CI」の前提）。
- optional-dependencies で `kitta[gui]` を分ける構成を検討（CLI のみのインストール・CI を軽くする）。
  ただし配布物（MSIX/.app）は常に GUI 込み。

---

## 3. ディレクトリ構成

企画書 §7 の構成をベースに、実装上必要なモジュールを補う。

```text
kitta/
├── pyproject.toml
├── README.md
├── LICENSE
├── NOTICE.md                # 依存 OSS・モデルのライセンス表示
├── .github/workflows/
│   ├── test.yml             # lint + core/cli テスト（3 OS マトリクス）
│   └── build.yml            # pyappdist による MSIX / .app ビルド
├── src/kitta/
│   ├── __init__.py
│   ├── core/
│   │   ├── models.py        # モデルカタログ・プリセット定義（データ）
│   │   ├── model_store.py   # モデルのダウンロード・ローカルキャッシュ管理
│   │   ├── remove.py        # 背景除去の実行（rembg ラッパ、セッション管理）
│   │   ├── compare.py       # 複数モデル実行のオーケストレーション
│   │   ├── presets.py       # プリセット TOML の読み書き・検証
│   │   └── paths.py         # キャッシュ/設定ディレクトリ解決（platformdirs 相当）
│   ├── cli/
│   │   └── main.py          # entry point: kitta / kitta compare / kitta batch
│   └── gui/
│       ├── app.py           # entry point、QApplication 初期化
│       ├── main_window.py   # ドロップ画面 ⇔ 比較画面の切替
│       ├── drop_view.py     # 起動直後のドロップ + プリセット選択画面
│       ├── compare_view.py  # 横並び比較（グリッド、背景切替、選択、保存）
│       ├── image_view.py    # QGraphicsView 派生。zoom/pan と同期機構
│       ├── workers.py       # 推論・ダウンロードのバックグラウンド実行
│       └── batch_dialog.py  # バッチ処理ダイアログ
└── tests/
    ├── core/
    ├── cli/
    └── gui/
```

企画書との差分: `paths.py` / `drop_view.py` / `workers.py` を追加（理由は各フェーズに記載）。
`.plan/.plan/product.md` は `.plan/product.md` へ移動して入れ子を解消する。

---

## 4. 実装フェーズ

### Phase 0 — プロジェクト基盤（0.5 日）

- `pyproject.toml`（uv 管理、ruff / pytest 設定、`kitta` script entry point）
- src レイアウト、空パッケージ、smoke テスト 1 本
- GitHub Actions: ubuntu / windows / macos で lint + pytest を回す `test.yml`
- ブランチ運用: `main` へ PR ベース。作業ブランチはタスク内容に応じた名前を使用

**完了条件**: 3 OS で CI がグリーン。

### Phase 1 — Core: モデルカタログとモデルストア（1.5 日）

企画書 §8–9 に対応。GUI/CLI 双方の土台になるため最初に作る。

- `models.py`:
  - `ModelSpec`（rembg モデル名、表示名、ダウンロード URL、ファイル名、サイズ、SHA-256、ライセンス情報）
  - `Preset`（プリセット名 Fast/General/Portrait/Anime/Fine Detail → ModelSpec + デフォルトパラメータ）
  - 企画書の対応例（u2netp / BiRefNet General / BiRefNet Portrait / ISNet Anime / ISNet General）を
    仮マッピングとして実装し、検証後に差し替えられるようデータ定義に閉じ込める
- `paths.py`: モデルキャッシュディレクトリの決定
  - rembg の既定（`~/.u2net`）ではなく `U2NET_HOME` 環境変数で Kitta 専用キャッシュ
    （例: `~/.cache/kitta/models`、OS ごとの適切な場所）へ誘導する
- `model_store.py`:
  - `is_available(model)` / `download(model, progress_cb)` / `ensure(model)`
  - SHA-256 検証、`.part` への一時ダウンロード → rename、中断時の再開 or やり直し
  - `progress_cb(bytes_done, bytes_total)` コールバック（CLI のプログレスバーと GUI の
    プログレス表示を同じ口で賄う）

**完了条件**: 実ダウンロードのユニットテスト（小さいモデル u2netp で 1 本、ネットワーク必須テストは
マーカーで分離）+ モックによるハッシュ検証・再開テスト。

### Phase 2 — Core: 背景除去と比較実行（1.5 日）

企画書 §5, §11, §18 に対応。

- `remove.py`:
  - `remove_background(image, preset) -> RemovalResult`
  - `RemovalResult`: 透過 PNG 画像（Pillow Image）、アルファマスク、処理時間、使用モデル
  - rembg の `new_session` をモデルごとにキャッシュ（同一モデルの再実行を高速化）
  - 出力: `only_mask` 相当のマスク取り出しは rembg の post 処理から得る
- `compare.py`:
  - `compare(image, presets, callbacks) -> list[RemovalResult]`
  - 逐次実行を基本とする（CPU 推論の並列実行はメモリ・速度とも不利。
    コールバックで「N 件中 M 件完了」を通知し、GUI 側は 1 件ずつ結果を表示する）
  - モデル未取得の場合は model_store 経由で取得（進捗はコールバック中継）
- `presets.py`:
  - 企画書 §15 の TOML フォーマット（`model`、`[alpha_matting]`、`[output]`）の read/write と検証
  - 組み込みプリセット（§8）とユーザープリセットファイルの両方を同じ型に解決する

**完了条件**: サンプル画像に対して u2netp で E2E テスト（推論込みテストはマーカー分離）、
プリセット TOML の round-trip テスト。

### Phase 3 — CLI（1 日）

企画書 §16–17 の MVP 範囲。

- `kitta image.jpg [-o out.png] [--model NAME | --preset NAME] [--mask]`
- `kitta compare image.jpg --models a,b,c [--output-dir DIR]`
  （各モデルの結果 PNG と処理時間の一覧を出力）
- `kitta batch INPUT_DIR --preset NAME --output DIR [--skip-existing]`
  （拡張子フィルタ、ファイル名保持、進捗表示、エラーはスキップして最後に集計）
- モデルダウンロード時はテキストプログレスバー表示
- exit code / エラーメッセージの整備

**完了条件**: CLI の統合テスト（推論はモック + u2netp 実行を各 1 本）。
この時点で「GUI なしで全機能が動く」状態になる。

### Phase 4 — GUI: 骨格とドロップ画面（1 日）

企画書 §10 に対応。

- `app.py`: QApplication、High-DPI 設定、`kitta-gui` entry point
- `main_window.py`: QStackedWidget で「ドロップ画面」⇔「比較画面」を切替
- `drop_view.py`:
  - 中央に "Drop an image here"（クリックでファイルダイアログも開ける）
  - プリセットのチェックボックス群。デフォルトは Fast / General / Fine Detail を ON（§10）
  - 画像ドロップで比較処理を開始し比較画面へ遷移
- `workers.py`:
  - `QThread`（または QThreadPool + QRunnable）上で `core.compare` を実行し、
    シグナルで「モデル別完了」「ダウンロード進捗」「エラー」を UI へ通知
  - GUI スレッドで推論しないことを最初から構造として固定する

**完了条件**: 画像をドロップすると選択プリセットで推論が走り、結果が（仮表示でよいので）返る。
pytest-qt でドロップ → worker 起動のテスト。

### Phase 5 — GUI: 比較ビュー（2 日）

企画書 §11–12 に対応。MVP の中心機能であり最大の工数を割く。

- `image_view.py`:
  - QGraphicsView 派生。ホイールズーム、ドラッグパン
  - 同期機構: 各ビューの transform / スクロール変更をシグナルで通知し、
    コントローラが他ビューへ適用（無限ループ防止のガード付き）
  - 背景描画: Checker / White / Black を `drawBackground` で実装
- `compare_view.py`:
  - 選択プリセット数に応じたグリッド（3 列基本、モデル名 + 処理時間表示）
  - 推論完了したセルから順に結果を表示。未完了セルはスピナー、
    ダウンロード中セルはプログレスバー（§11「モデルダウンロード発生時はプログレスを表示」）
  - 表示切替: Original / Mask / Result（全セル一括切替）
  - 背景切替（全セル一括反映、§12）
  - 結果選択（クリックで ★ マーク）→「Save PNG」「Save Mask」
  - 保存はファイルダイアログ、デフォルトファイル名は `元名 + "-cutout.png"` / `"-mask.png"`
  - 「別の画像を試す」でドロップ画面へ戻る（新しい画像のドロップも直接受け付ける）

**完了条件**: MVP GUI 一連の流れ（ドロップ → 比較 → 選択 → 保存）が手動確認で完走。
同期 zoom/pan・背景切替のロジックにユニットテスト。

### Phase 6 — 仕上げ: エラー処理・体験調整（1 日）

- 大画像（例: 8000px 超）の扱い: 表示は等倍データで行い、推論への入力ポリシーを決める
- 非対応ファイル・破損画像・ダウンロード失敗（オフライン時）のエラーダイアログ
- ウィンドウサイズ・分割状態の記憶（QSettings）
- CLI / GUI 双方でのキャンセル（比較中に中断できる）

### Phase 7 — 配布と CI（2 日 + pyappdist 側の作業）

企画書 §3.2, §21–23 に対応。pyappdist の showcase という開発目的があるため、
pyappdist 側の不足はこのフェーズで洗い出して本体へフィードバックする。

- `build.yml`: タグ push で Windows MSIX / macOS .app を pyappdist でビルドし、
  GitHub Release へアップロード
- Windows: MSIX 化、App Execution Alias による `kitta` コマンドの検証
- macOS: application bundle 生成、（Store 外配布なら）署名 / notarization の検討
- `NOTICE.md`: PySide6(LGPL) / rembg(MIT) / onnxruntime(MIT) / Pillow / NumPy /
  各 ONNX モデルのライセンスを整理。**プリセット採用モデルはライセンス確認済みのものに限定**
  （BiRefNet: MIT、ISNet(DIS): Apache-2.0、U²-Net: Apache-2.0 — 実装時に再確認）
- GUI の About ダイアログと CLI `--version` / `--licenses` でライセンス表示
- Microsoft Store 提出物（説明文・スクリーンショット）は §2, §28 の文言を使用

**完了条件**: CI 成果物の MSIX / .app を実機インストールして MVP フローが動く。

---

## 5. 主要な設計判断

1. **Core は同期 API + 進捗コールバック**。スレッド化は GUI 層（workers.py）の責務にする。
   CLI はそのまま同期で呼べ、テストも書きやすい。
2. **推論は逐次実行**。CPU 推論の並列化は行わず、1 モデルずつ完了次第 UI に反映することで
   体感速度を確保する（最初の結果が最短で見える）。
3. **プリセットは「データ」として一元定義**（models.py）。モデル対応は検証後に差し替える前提
   （企画書 §8）なので、コードロジックから分離しておく。
4. **モデルキャッシュは Kitta 専用ディレクトリ**。rembg 既定の `~/.u2net` を汚さず、
   MSIX 環境でも書き込み可能な場所を paths.py で一元解決する。
5. **BiRefNet の重さは既知のリスクとして扱う**（モデル約 900MB / CPU 推論が遅い）。
   Phase 1 のカタログ検証時に実測し、遅すぎる場合は General プリセットの対応モデルを
   ISNet 等へ変更する。この判断はデータ差し替えだけで済む構造にしておく（判断 3）。

## 6. リスクと対応

| リスク | 対応 |
| --- | --- |
| BiRefNet が CPU で実用速度に達しない | Phase 1 で実測し、プリセット対応表を差し替え |
| rembg の API / モデル URL 変更 | rembg バージョンを固定。model_store は URL をカタログに持ち、rembg 非経由でも取得可能にする |
| pyappdist の未成熟（本プロジェクトの目的の一部） | Phase 7 を早めに素振り（Phase 3 完了時点で CLI のみを一度パッケージしてみる） |
| MSIX サンドボックスでのキャッシュ書き込み | paths.py で LocalAppData 配下を使用。Phase 7 で実機検証 |
| PySide6 の LGPL 対応 | 動的リンクのまま同梱し、NOTICE とソース入手方法を明記 |
| onnxruntime の OS/CPU 互換（macOS x86_64 / arm64） | CI マトリクスに両アーキテクチャ（or universal2 の検証）を含める |

## 7. テスト戦略

- **core / cli**: 通常のユニットテスト + マーカー分離した実推論テスト（u2netp のみ、CI では
  モデルをキャッシュ）。ネットワークテストも同様にマーカー分離。
- **gui**: pytest-qt でロジック層（同期 zoom/pan、状態遷移、worker シグナル）をテスト。
  描画自体は手動確認とし、CI（Linux）は offscreen platform で実行。
- **配布物**: リリース前チェックリスト（インストール → ドロップ → 比較 → 保存 → CLI 実行）を
  リポジトリに置き、手動で実施。

## 8. スケジュール概算

| フェーズ | 内容 | 目安 |
| --- | --- | --- |
| 0 | プロジェクト基盤 | 0.5 日 |
| 1 | モデルカタログ / モデルストア | 1.5 日 |
| 2 | 背景除去 / 比較実行 | 1.5 日 |
| 3 | CLI | 1 日 |
| 4 | GUI 骨格・ドロップ画面 | 1 日 |
| 5 | 比較ビュー | 2 日 |
| 6 | 仕上げ | 1 日 |
| 7 | 配布・CI・ライセンス | 2 日 |
| 計 | | 約 10.5 日 |

モデル性能検証（Phase 1）と pyappdist 側の対応状況により前後する。
