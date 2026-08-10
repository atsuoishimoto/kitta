# Kitta 製品企画書

## 1. 概要

**Kitta** は、複数のAI背景除去モデルを同じ画像に適用し、結果を横並びで比較できる、無料・オフラインのデスクトップアプリケーションである。

一般的な背景除去アプリが「特定のAIモデルによる結果を提示する」ことを目的とするのに対し、Kitta は、

> **AI背景除去を、比べて選ぶ。**

ことを

中心的な体験とする。

画像によって背景除去モデルの得手不得手が異なることを前提に、複数モデルの結果を実際に比較し、その画像・用途に最適なモデルと設定をユーザー自身が選択できるようにする。

GUIで決定したモデル・パラメータはプリセットとして保存でき、CLIによる大量画像のバッチ処理にもそのまま利用できる。

すべての推論処理をローカル環境で実行し、画像を外部サーバーへ送信しない。

---

# 2. 製品名

## Kitta

日本語の「切った」「切り抜いた」を連想させる短い名称。

英語圏では固有のブランド名として扱えることを想定する。

### 日本語キャッチコピー

> **AI背景除去を、比べて選ぶ。**

### 英語キャッチコピー

> **Compare AI background removal models side by side. Fully offline.**

### Store等での表記案

**Kitta — Offline AI Background Remover**

日本語：

**Kitta — 無料・オフラインAI背景除去**

---

# 3. 開発目的

Kitta には2つの目的がある。

## 3.1 実用的なデスクトップアプリの提供

一般ユーザーが、

* Python
* rembg
* ONNX Runtime
* AIモデル
* CLI

などを意識することなく、高性能なオープンソース背景除去モデルを利用できる環境を提供する。

特に、

* 完全オフライン
* 無料
* アカウント不要
* 複数モデル比較
* Windows / macOS / Linux対応

を特徴とする。

## 3.2 pyappdist の実証アプリ

Kitta 自体を、Pythonアプリケーション配布ツール **pyappdist** の実戦的な showcase とする。

単純なHello Worldではなく、

* Python runtime
* PySide6 / Qt
* native wheels
* ONNX Runtime
* NumPy
* Pillow
* rembg
* 外部AIモデル
* GUI
* CLI
* ローカルキャッシュ
* MSIX
* macOS application bundle

を含む現実的なPythonデスクトップアプリを配布する。

---

# 4. ターゲットユーザー

## 一般ユーザー

* 写真の背景を消したい
* 商品写真を作りたい
* 人物を切り抜きたい
* イラストの背景を透明化したい
* クラウドサービスに画像をアップロードしたくない

GUIだけで利用できることを前提とする。

## パワーユーザー

* 大量の商品画像を処理したい
* 同じ設定で数百〜数千枚を処理したい
* モデルによる結果の違いを確認したい
* 背景除去パラメータを調整したい

GUIで設定を作り、CLIのバッチ処理へ移行できる。

## 開発者・AIユーザー

* rembg のモデルを比較したい
* ONNX背景除去モデルを試したい
* モデルごとの速度や結果を確認したい
* CLI / GitHub Actionsから背景除去を利用したい

Kitta を background removal model workbench として利用できる。

---

# 5. 基本コンセプト

一般的な背景除去アプリは、

```text
Image
  ↓
AI
  ↓
Result
```

という構造になっている。

Kitta は、

```text
                       ┌─ Model A → Result A
                       │
Image → Kitta Compare ─┼─ Model B → Result B
                       │
                       └─ Model C → Result C
                                  ↓
                           Compare results
                                  ↓
                           Select the best
```

という構造にする。

Kitta 自身が「最高のAI」を主張するのではなく、

> **Different images need different models.**

という考え方を採用する。

---

# 6. 技術構成

基本構成：

```text
PySide6
   │
   ▼
Kitta Core
   │
   ▼
rembg
   │
   ▼
ONNX Runtime
   │
   ▼
ONNX Models
```

主要技術：

| 項目      | 技術                   |
| ------- | -------------------- |
| 言語      | Python               |
| GUI     | PySide6 / Qt Widgets |
| 背景除去    | rembg                |
| 推論      | ONNX Runtime         |
| 画像処理    | Pillow / NumPy       |
| パッケージング | pyappdist            |
| Windows | MSIX                 |
| macOS   | .app / 配布パッケージ       |
| CI      | GitHub Actions       |

初期版では CPU版 ONNX Runtime を基本とする。

---

# 7. アーキテクチャ

GUI・CLI・処理エンジンを分離する。

```text
                 ┌───────────┐
                 │ Kitta GUI │
                 │  PySide6  │
                 └─────┬─────┘
                       │
                       │
                 ┌─────▼─────┐
                 │ Kitta Core│
                 └─────▲─────┘
                       │
                       │
                 ┌─────┴─────┐
                 │ Kitta CLI │
                 └───────────┘

                       │
                       ▼

              rembg / ONNX Runtime
```

GUIから rembg を直接操作しない。

想定ディレクトリ構成：

```text
kitta/
├── core/
│   ├── remove.py
│   ├── compare.py
│   ├── models.py
│   ├── presets.py
│   └── model_store.py
│
├── cli/
│   └── main.py
│
└── gui/
    ├── app.py
    ├── main_window.py
    ├── compare_view.py
    ├── image_view.py
    └── batch_dialog.py
```

---

# 8. モデルプリセット

ユーザーにONNXモデル名を直接選ばせることを基本UIにはしない。

Kitta が用途別プリセットをあらかじめ用意する。

例：

```text
Fast
General
Portrait
Anime
Fine Detail
```

内部では具体的な rembg モデルに対応する。

例：

```text
Fast
  → u2netp

General
  → BiRefNet General

Portrait
  → BiRefNet Portrait

Anime
  → ISNet Anime

Fine Detail
  → ISNet General
```

実際のモデル対応はモデル性能の検証後に決定する。

Advanced UIでは内部モデル名も確認・指定できるようにする。

---

# 9. モデル配布

利用可能なプリセットは最初からアプリに登録する。

ただし、すべてのONNXモデルをアプリ本体へ同梱する必要はない。

```text
Kitta installation
      │
      ├─ Python runtime
      ├─ Kitta
      ├─ rembg
      └─ ONNX Runtime

             ↓

Model catalog

Fast          Available
General       Available
Portrait      Available
Anime         Available

             ↓

必要になったモデルだけ取得

             ↓

Local model cache
```

これにより、

* インストールサイズ削減
* モデル更新の独立
* 不要モデルのダウンロード回避
* 新モデル追加の容易化

を実現する。

---

# 10. メインGUI

起動直後は非常にシンプルな画面とする。

```text
┌─────────────────────────────────────────┐
│ Kitta                                   │
│                                         │
│                                         │
│          Drop an image here             │
│                                         │
│☑ Fast ☑ General ☑ Fine Detail ☐ Portrait│
│ ☐ Anime                                 │
│                                         │
└─────────────────────────────────────────┘
```

画像をドラッグ&ドロップすると比較処理へ進む。

デフォルトでは代表的な複数プリセットを選択済みにする。

例：

```text
Models

☑ Fast
☑ General
☑ Fine Detail
☐ Portrait
☐ Anime
```

ユーザーがAIモデルについて何も知らなくても、そのまま比較を開始できることを重視する。

---

# 11. モデル比較

Kitta の中心機能。

同じ入力画像に複数モデルを適用し、結果を横並びにする。

```text
┌────────────┬────────────┬────────────┐
│ Fast       │ General    │ Fine Detail│
│            │            │            │
│  result    │  result    │  result    │
│            │            │            │
│   0.8 s    │   1.8 s    │   2.4 s    │
│            │      ★     │            │
└────────────┴────────────┴────────────┘
```

ユーザーは最も良い結果を選択する。

各モデルについて処理時間も表示する。

モデルダウンロード発生時はプログレスを表示

---

# 12. 比較ビュー

結果の細かな違いを確認するため、画像ビューを同期できるようにする。

主な機能：

* synchronized zoom
* synchronized pan
* Original表示
* Mask表示
* Result表示

背景表示：

```text
Checker
White
Black
```

背景を切り替えるとすべての比較結果へ同時に反映する。

白背景では黒い境界、黒背景では白いフリンジなどを確認しやすくする。

---

# 13. xxxxxxxxx


# 14. パラメータ調整

Advanced モードでは rembg の主要パラメータをGUIから変更できるようにする。

例：

```text
Alpha Matting

☑ Enabled

Foreground threshold
────────────●── 240

Background threshold
──●──────────── 10

Erode
───●─────────── 10
```

設定変更後、結果を再生成して視覚的に確認できる。

一般ユーザーには Advanced UI を見せない。

---

# 15. Preset

GUIで作成したモデル・パラメータ設定をプリセットとして保存できる。

例：

```toml
model = "birefnet-general"

[alpha_matting]
enabled = true
foreground_threshold = 240
background_threshold = 10
erode_size = 10

[output]
format = "png"
```

プリセットはGUIとCLIの共通フォーマットとする。

```text
             GUI
              │
              ▼
        product.toml
              │
       ┌──────┴──────┐
       ▼             ▼
      GUI           CLI
```

---

# 16. CLI

GUIとは独立して利用できるCLIを提供する。

## 単体処理

```bash
kitta image.jpg
```

## モデル指定

```bash
kitta image.jpg --model birefnet-general
```

## プリセット指定

```bash
kitta image.jpg --preset general
```

## 比較

```bash
kitta compare image.jpg \
    --models birefnet-general,isnet-general,u2net
```

## バッチ

```bash
kitta batch ./photos \
    --preset general \
    --output ./results
```

GUIの現在設定からCLIコマンドを生成する **Copy CLI Command** 機能も検討する。

---

# 17. Batch Processing

バッチ機能は「比較」ではなく「決定した設定を大量適用する」用途とする。

```text
Batch Processing

128 images

Preset
[ Product Photos ▼ ]

Output
[ ~/Pictures/Kitta Output ]

☑ Preserve filenames
☑ Skip existing files

             [ Process 128 images ]
```

役割を明確に分ける。

```text
Compare
   ↓
モデル・設定を決定

Preset
   ↓
設定を保存

Batch
   ↓
大量画像へ適用
```

初期版では「100画像 × 5モデル」のような大量比較機能は実装しない。

---

# 18. 出力

基本出力は透過PNG。

提供する出力：

* Transparent PNG
* Alpha mask

初期版では画像編集機能を増やさない。

---

# 19. プライバシー

Kitta の重要な製品特性として、

> **100% Offline**

を明確にする。

画像データを外部サーバーへアップロードしない。

```text
Your image
    ↓
Your computer
    ↓
ONNX Runtime
    ↓
Result

No cloud
No upload
No account
```

AIモデルの初回ダウンロード以外のネットワーク通信を必要としない設計を基本とする。

---

# 20. Windows / macOS / linux

同じPythonコードベースからWindows/macOS/Linuxをサポートする。


GUIは **PySide6 + Qt Widgets** を使用する。

Qtを採用する主な理由：

* Windows/macOS共通コード
* 高品質な画像表示
* drag & drop
* zoom / pan
* Graphics View
* 非同期処理との連携
* DPI対応
* matureなdesktop GUI framework

特にKittaの中心となる画像比較UIを実装しやすいことを重視する。

---

# 21. GitHub Actions

GUIに依存しない Core / CLI を利用してCIを構築する。



# 22. 配布

## Windows

pyappdist により MSIX を生成し、Microsoft Store で公開する。

CLIについては MSIX の App Execution Alias を利用して、

```bash
kitta
```

をコマンドラインから実行可能にすることを検討する。

## macOS

pyappdist で application bundle を生成する。

Windows/macOSで可能な限り同一のPython packageを利用する。

---

# 23. ライセンス

Kitta 自体は無料アプリとして提供する。

利用する主要OSSについて、それぞれのライセンス条件に従ってライセンス表示・NOTICE等を提供する。

特に確認対象：

* PySide6 / Qt
* rembg
* ONNX Runtime
* 各ONNXモデル
* Pillow
* NumPy

モデルごとにライセンスが異なる可能性があるため、Kitta がプリセットとして提供するモデルはライセンス確認済みのものに限定する。

---

# 24. 製品名と商標

仮製品名：

**Kitta**

日本語の「切った」に由来する。


---

# 25. 実装しないもの

Kittaを小さく保つため、初期段階では以下を対象外とする。

* 本格的な画像編集
* フィルタ
* テキスト追加
* レイヤー編集
* ステッカー作成
* ドロップシャドウ
* 動画
* GIF
* 独自AIモデル開発
* クラウド推論
* ユーザーアカウント
* サーバー

Kittaは画像編集ソフトではなく、

> **背景除去モデルを比較し、最適な結果と設定を選び、それを実行するツール**

に集中する。

---

# 26. MVP

最初の公開版では機能を以下まで絞る。

### GUI

1. 画像のドラッグ&ドロップ
2. モデルプリセット
3. 複数モデルによる推論
4. 横並び比較
5. synchronized zoom / pan
6. Checker / White / Black 背景
7. 結果選択
8. PNG保存
9. Mask表示・保存
10. モデルのオンデマンド取得

### CLI

1. 単体画像処理
2. モデル・プリセット指定
3. フォルダのバッチ処理
4. 出力先指定

### 配布

1. Windows MSIX
2. macOS application
3. GitHub Actionsによるビルド
4. Microsoft Store公開

---

# 27. MVP以降

MVP公開後の候補として以下を検討する。


### Advanced Parameters

Alpha Matting等の視覚的調整。

### User Presets

GUIで作った設定をCLIと共有。


# 28. 話題化のポイント

Kitta を単に、

> 「無料の背景除去アプリを作った」

とは紹介しない。

代わりに、

> **I built an offline app that lets you run the same image through multiple open background-removal AI models and compare the results side by side.**

と紹介する。

スクリーンショット一枚で、

```text
Same image.

┌────────────┬────────────┬────────────┐
│ BiRefNet   │ ISNet      │ U²-Net     │
│            │            │            │
│  result    │  result    │  result    │
│            │            │            │
└────────────┴────────────┴────────────┘

100% Offline
```

を見せる。

「同じ画像なのにAIモデルによってこんなに違う」という視覚的な面白さそのものをプロモーション素材にする。

---

# 29. Kitta の価値

Kitta の価値は独自AIモデルではない。

既存の優れたオープンモデルに対して、

```text
Discover
   ↓
Compare
   ↓
Inspect
   ↓
Tune
   ↓
Choose
   ↓
Save preset
   ↓
Batch / CLI
```

という一貫したデスクトップ体験を提供することにある。

一般ユーザーには、

> **簡単で無料のオフライン背景除去アプリ**

として機能する。

パワーユーザーには、

> **大量画像を処理するための設定作成ツール**

となる。

AI・Python開発者には、

> **background-removal model workbench**

となる。

そして開発プロジェクトとしては、

> **pyappdist による実用Pythonデスクトップアプリ配布の showcase**

となる。

この4つを同じ小規模なコードベースで成立させることを、Kitta の製品方針とする。
