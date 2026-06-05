# 📘 Auto Research — ステップ・バイ・ステップ チュートリアル

🌐 [English](README.md) ・ **日本語（このページ）**

このチュートリアルでは、Auto Research を **1 ステップずつ** 解説します。まっさ
らな GitHub アカウントから、毎朝 Web ソースに基づいた新鮮なリサーチ・ブリーフ
ィングを自動で起票するリポジトリができあがるまでを案内します。サーバー不要・コー
ディング不要。ブラウザと約 5 分があれば十分です。

短縮版だけ知りたい場合は、メインの [README（日本語）](../README.ja.md) に
クイックスタートがあります。このページは、各ステップが *なぜ* 必要なのかまで
ていねいに説明する、ゆっくり版のガイドです。

> 🧭 まずは**研究者**のために作られていますが、同じ仕組みは日々の
> **tech / business / hobby / finance** トラッカーとしても使え、テーマごとに最適な
> レンズを自動で選びます（[ステップ 5](#ステップ-5-任意リサーチトピックを選ぶ)を参照）。
> 各実行は4つの並列ジョブを **GitHub Issue** に起票し、さらに **GitHub Pages の
> ドキュメントサイト**の公開や **Slack** 通知もできます。

---

## はじめる前に

必要なもの:

- **GitHub アカウント**（無料プランで問題ありません）。
- **いずれか 1 つ** の Claude 認証情報:
  - **Claude Pro/Max プラン**（ここからトークンを発行します）、または
  - [console.anthropic.com](https://console.anthropic.com) の **API 課金**。
- *(任意)* 各結果をチャットに通知したい場合は、Incoming Webhook を作成できる
  **Slack ワークスペース**。

不要なもの: サーバー、GitHub 用のクレジットカード、ローカルへの Python
インストール、コーディング。

> 💡 **ポイント:** 以下のステップはすべてやり直し可能で、ワークフローは
> *セットアップ中に壊れない* よう設計されています。認証情報が未設定でも、
> スケジュール実行は成功し、「何を追加すればよいか」を知らせるメモを残します。

---

## ステップ 1 — テンプレートから自分用のコピーを作成する

Auto Research は **GitHub のリポジトリ・テンプレート** です。フォークやクローン
ではなく、独立した自分専用のコピーを作ります。

1. GitHub でテンプレートリポジトリを開きます。
2. 右上付近の緑色の **「Use this template」** ボタンをクリックします。
3. **「Create a new repository」** を選びます。
4. 名前（例: `my-auto-research`）を付け、**Public** か **Private** を選びます。
   - Public リポジトリは **GitHub Actions の実行時間が無料・無制限** なので、
     最もコストがかかりません。Private でも動作しますが、Actions の使用量を
     消費します。
5. **「Create repository」** をクリックします。

これでワークフロー・スクリプト・設定ファイルがすべて揃った、自分専用のコピーが
手に入りました。

> **なぜフォークではなくテンプレート?** テンプレートなら、上流リンクも共有履歴も
> ない、まっさらなリポジトリが手に入ります。完全に *自分のもの* として自由に
> 編集できます。

---

## ステップ 2 — GitHub Actions を有効化する

GitHub は安全のため、テンプレートから作った新規リポジトリでは Actions を初期状態
で無効にしています。最初に一度だけ有効化が必要です。

1. 新しいリポジトリで、上部の **「Actions」** タブをクリックします。
2. ワークフローが無効になっている旨の案内が表示されます。**ワークフローを有効化**
   するボタン（多くの場合
   *「I understand my workflows, go ahead and enable them」*）をクリックします。

これで、スケジュール・ジョブが実行できるようになりました。

---

## ステップ 3 — Claude の認証情報を 1 つ用意する

Auto Research は Claude と通信します。次の 2 つのうち **どちらか 1 つ** を選んで
ください。両方は不要です。

### 方法 A — Claude Pro/Max プラン（OAuth トークン）

Claude の **Pro** または **Max** プランを契約している場合、別途 API 課金なしで
そこからトークンを発行できます。

1. まだなら Claude Code をローカルにインストールします:
   `npm install -g @anthropic-ai/claude-code`（または公式インストール手順に
   従ってください）。
2. ターミナルで次を実行します:

   ```bash
   claude setup-token
   ```

3. 開いたブラウザ画面でログインします。
4. ターミナルに表示されたトークンをコピーします。これが
   `CLAUDE_CODE_OAUTH_TOKEN` です。

### 方法 B — API 課金（API キー）

従量課金を使いたい場合:

1. [console.anthropic.com](https://console.anthropic.com) を開きます。
2. **API キー** を作成します。
3. それをコピーします。これが `ANTHROPIC_API_KEY` です。

> **どちらを選ぶ?** すでに Pro/Max プランに課金しているなら、方法 A がその契約を
> 再利用できます。そうでなければ、方法 B（従量課金）が一番シンプルです。Auto
> Research ではどちらも同じように動作します。

---

## ステップ 4 — 認証情報をリポジトリの Secret として追加する

**Secret** は GitHub がログに決して出力しない暗号化された値で、トークンやキーの
保管にうってつけです。

1. リポジトリの **Settings → Secrets and variables → Actions** を開きます。
2. **「Secrets」** タブをクリックします。
3. **「New repository secret」** をクリックします。
4. ステップ 3 で取得した認証情報に応じて入力します:

   | 持っているもの | Secret の名前 | 値として貼り付けるもの |
   | --- | --- | --- |
   | プランのトークン（方法 A） | `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token` のトークン |
   | API キー（方法 B） | `ANTHROPIC_API_KEY` | コンソールのキー |

5. **「Add secret」** をクリックします。

> ⚠️ 追加するのは **どちらか 1 つだけ** です。トークンを API キー欄に貼ったり、
> その逆をしたりしないでください。名前が重要です。

---

## ステップ 5 —（任意）リサーチトピックを選ぶ

デフォルトでは、Auto Research は広いトピック `AI` を検索します。絞り込むには:

1. **Settings → Secrets and variables → Actions** を開き、**「Variables」** タブ
   を選びます（トピックは機密ではないので Secrets ではありません）。
2. **「New repository variable」** をクリックします。
3. 名前を `RESEARCH_TOPIC` にし、値にトピックを設定します。例:
   `Retrieval-augmented generation`、`protein folding`、`RISC-V compilers`。
4. **「Add variable」** をクリックします。

**研究室に特化した、より充実した結果を得たい場合** は、リポジトリ内の
**`config/research_topics.md`** も編集してください（GitHub 上で鉛筆 ✏️ アイコン
をクリックするとブラウザで編集できます）。トピック・データセット・制約・未解決の
問いを書き出しておくと、Claude が毎回その内容を文脈として読み込みます。

**信頼できる情報源を優先させたい場合** は、**`config/priority_sources.md`** を
編集し、よく見るフィード・ブログ・一覧ページを1行1URLで列挙してください。Claude は
自由なウェブ検索の前に**まずそれらの URL を巡回**し、そこで見つけた個別リンクを
たどります。お気に入りの情報源が毎回優先的にクロールされます。あくまで優先順位で
あってホワイトリストではないため、巡回後は新しい情報を自由に検索します。

**レンズは自動です。** 実行は学術リサーチに限りません — テーマを5つのドメイン
（**research / tech / business / hobby / finance**、各 `config/domains/` のガイド）の
どれかで読めます。デフォルトは `auto`：各実行の最初に小さなピッカーがテーマを読んで
最適なレンズを選び、そのテーマ用に記憶します。通常ここは **何も設定不要** です。
固定したいときは `RESEARCH_DOMAIN` Variable をその5つのいずれかに設定します。

---

## ステップ 6 — スケジュールを待たずに今すぐ実行する

翌朝まで待つ必要はありません。手動で実行して動作を確認しましょう。

1. **「Actions」** タブを開きます。
2. 左サイドバーで **「Auto Research」** ワークフローをクリックします。
3. 右側の **「Run workflow」** ボタンをクリックし、確認します。
4. 実行が始まります。数分かかります — Claude が実在するソースを Web 検索し、
   パブリッシャーが Issue を作成しています。

完了したら **「Issues」** タブを開きます。新しい Issue が **項目ごとに 1 つずつ**
作成され、タイトルとラベルが付き、クリックできる実在のソースリンクが添えられて
います。

> 💡 まだ認証情報を追加していない場合、実行は **成功します** がリサーチ Issue は
> 作られません。ログに「何を追加すべきか」を示す `::notice` が出力されます。
> ステップ 4 に戻って設定し、再実行してください。

---

## ステップ 7 — 結果を読み、トリアージし、方向づける

各結果は通常の GitHub Issue なので、普段の作業フローにそのまま組み込めます。

- 1 行の要点（takeaway）を **読み**、ソースへクリックして移動します。
- 他の Issue と同じように **コメント** ・ **担当者割り当て** ・ **クローズ** が
  できます。
- **タグで絞り込む。** 後続の *Auto Label* ワークフローが、その日の Issue に
  **トピックタグ**を自動付与します（パイプラインのラベルに加えて）。テーマ別に
  バックログを切り分けられます。
- ワンクリックで **次回の実行を方向づけ** られます:
  - 気に入った Issue に **👍** → Claude が似たものを *より多く* 出します。
  - イマイチな Issue に **👎** → Claude が次回その種類を *避けます*。
  - （`good` / `bad` ラベルを付けても同じ効果です。）

さらに、毎回の実行ではまず既存の Issue を要約し、**繰り返さないよう** 指示されて
います。そのため、同じ論文の再掲ではなく、毎日きちんと新しい素材が得られます。

---

## ステップ 8 — 毎日自動で動かす

これで完了です。以降、ワークフローは **1 日 1 回自動的に** 実行され（デフォルトは
日本時間 04:17 / UTC 19:17）、あなたが眠っている間に新しい Issue を起票します。

実行 *時刻* を変えるには、**`.github/workflows/auto-research.yml`** の `cron` 行
1 つを編集します（cron の時刻は常に **UTC** です）:

```yaml
schedule:
  - cron: "0 22 * * *"   # 毎日 07:00 JST
  - cron: "17 19 * * 1"  # 月曜のみ 04:17 JST
  - cron: "0 */12 * * *" # 12 時間ごと
```

自分のスケジュールは [crontab.guru](https://crontab.guru) で組み立てられます。
もちろん Actions タブからいつでも手動実行できます（ステップ 6）。

---

## 任意の追加機能

以下はすべて **Settings → Secrets and variables → Actions** で設定する 1 行の
項目です。コード編集は不要です。

### 各項目を Slack に通知する

1. Slack の [Incoming Webhook](https://api.slack.com/messaging/webhooks) を作成し、
   その URL をコピーします。
2. それを `SLACK_WEBHOOK_URL` という名前の **Secret** として追加します。

すると各項目が、セクションの絵文字（📰 / 💡 / 📚 / 👀）を先頭にした 1 行メッセージで
投稿され、タイトルと Issue へのリンクが付きます。デフォルトではセクションごとに
1つのダイジェスト投稿にまとめられます。`SLACK_DIGEST=false` にすると項目ごとに
1投稿になります。オン/オフ用の別フラグはありません。Webhook の存在 **そのものが
スイッチ** です。Webhook がなければ投稿されません。

### 英語ではなく日本語で書く

**Variable** の `OUTPUT_LANGUAGE` を `ja` に設定します（デフォルトは `en`）。
これで Claude が書く言語と、各 Issue の見出し・ラベルの言語の両方が切り替わります。

### 4 つのジョブのうち使うものを選ぶ

各ジョブは独立した並列ジョブで、**Variable** を `false` にするとオフにできます。

| Variable | 制御対象 | デフォルト |
| --- | --- | --- |
| `ENABLE_RESEARCH_NEWS` | 📰 ニュースレポート | オン |
| `ENABLE_HYPOTHESIS_GENERATION` | 💡 仮説レポート | オン |
| `ENABLE_RELATED_WORK` | 📚 関連研究レポート | オン |
| `ENABLE_SITE_WATCH` | 👀 サイト監視（ページ差分ウォッチャー） | オン |

**サイト監視**は **`config/watch_targets.json`** に列挙したページ（初期状態では
Hacker News のトップページ）を実際のヘッドレスブラウザで監視し、変化があるとその
差分を要約した Issue を作成します。新しいページの初回実行は基準（baseline）を
取得するだけで、何も起票しません。

### すべてをドキュメントサイトとして公開する

2つ目のワークフロー **`publish-site.yml`** が、各 Auto Research / Auto Label 実行の
直後に動き、すべての Issue を **Astro + Starlight** 製のリッチなドキュメントサイト
（サイドバー・全文検索・ダークモード、各項目のタグ・リアクション・コメントつき）に
変換します。専用の **`gh-pages*`** ブランチへ公開されます。**初回のみの設定:**
配信場所によって CSS/JS に焼き込まれる `base` パスが決まるため、初回実行
（`SITE_BASE` Variable 未設定）では **`gh-pages`**（base `/<リポジトリ名>/`、公開
プロジェクト Pages 用）と **`gh-pages-root`**（base `/`、プライベートのルート Pages
用）の両方を公開します。*Settings → Pages → Build and deployment* を開き、**Source
=「Deploy from a branch」**、ブランチに **CSS が当たって正しく表示される方**を選んで
ください。公開ケースなら `https://<ユーザー名>.github.io/<リポジトリ名>/` で公開され
ます。（`SITE_BASE` を `/` または `/<リポジトリ名>/` に設定すると、以降は該当ブラン
チのみ再ビルドされます。）

### 各項目を Markdown ファイルとしても保存する

`ENABLE_FILE_OUTPUT=true` を設定すると、項目ごとに 1 ファイル
（`outputs/YYYY-MM-DD-<section>-<n>.md`）を *追加で* 書き出し、ダウンロード可能な
GitHub Actions アーティファクトとしてアップロードします。デフォルトはオフ
（Issue が主たる出力です）。

### 件数とモデルを調整する

- `ITEMS_PER_REPORT`（デフォルト `5`）— レポートあたりおおよその項目数。
- `ANTHROPIC_MODEL`（デフォルト `claude-sonnet-4-6`）— 使用する Claude モデル。

全項目はメイン README の [設定リファレンス](../README.ja.md) を参照してください。

---

## パブリッシャーをローカルで試す（GitHub 不要）

リサーチ部分には Claude Code Action が必要ですが、決定論的な **パブリッシャー** は
Python があればどこでも動き、Markdown のプレビューに便利です。標準ライブラリのみ
を使うので、インストールするものはありません。

```bash
export SECTION_JSON='{"items":[{"title":"Example","url":"https://arxiv.org/abs/0000.00000","takeaway":"…"}]}'
export OUTPUT_LANGUAGE=ja
ENABLE_FILE_OUTPUT=true python3 scripts/publish_section.py news
# → outputs/<date>-news-01.md を項目ごとに 1 ファイル生成
#   （Issue 作成には GITHUB_TOKEN が必要）
```

---

## トラブルシューティング

| 症状 | 考えられる原因と対処 |
| --- | --- |
| 実行は成功するがリサーチ Issue が出ない | Claude 認証情報がない。実行ログの `::notice` を確認し、`CLAUDE_CODE_OAUTH_TOKEN` **または** `ANTHROPIC_API_KEY` を追加（ステップ 4）。 |
| 「Run workflow」ボタンが見当たらない | Actions が未有効（ステップ 2）、またはサイドバーで **Auto Research** ワークフローを選んでいない。 |
| Slack に投稿されない | `SLACK_WEBHOOK_URL` が未設定、またはダミー値。ログに `Slack webhook is not configured. Skipping Slack post.` と出る。 |
| 出力の言語が違う | `OUTPUT_LANGUAGE` Variable を `en` か `ja` に設定。認識できない値は英語にフォールバックします。 |
| 同じ論文が再び出てくる | `EXISTING_CONTEXT_MAX` を上げ、重複排除のために要約する過去 Issue 数を増やす（デフォルト `40`）。 |
| トピックが広すぎる/一般的すぎる | `RESEARCH_TOPIC` を設定し、`config/research_topics.md` を充実させる（ステップ 5）。 |

> **セキュリティに関する注意:** API キー・OAuth トークン・Slack Webhook といった
> Secret は、ログに **決して出力されません**。`.env` は gitignore 済みで、
> コミットされるのはダミー値の `.env.example` だけです。

---

## 次のステップ

- **[メイン README（日本語）](../README.ja.md)** — 全機能と設定リファレンス。
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — テンプレートの拡張方法。
- **さらに先へ:** 新しいレポートの追加、スキーマの拡張、日次ダイジェストの作成、
  複数トピックのマトリクス実行など — README の「Going further」セクションを
  参照してください。

よいリサーチを！🔬
