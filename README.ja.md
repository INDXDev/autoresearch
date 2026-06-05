# 🔬 Auto Research（自動リサーチ）

🌐 **English / 日本語** — [English](README.md) ・ **日本語（このページ）**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Runs on GitHub Actions](https://img.shields.io/badge/runs%20on-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/auto-research.yml)
[![Built with Claude](https://img.shields.io/badge/built%20with-Claude-d97757)](https://github.com/anthropics/claude-code-action)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

**毎朝、自分の GitHub リポジトリに、最新のリサーチ速報が届く —
Claude が書き、すべて実在の Web ソースに基づいています。**

*研究室・AI/ML チーム、そして手作業の毎日の情報収集なしに動きの速い分野を
追いたいすべての人のために。*

> 🧭 まずは**研究者**のために作られていますが、同じ仕組みは日々の
> **tech / business / hobby / finance** トラッカーとしても同じように使えます。
> テーマごとに最適なレンズを自動で選びます（[`config/domains/`](config/domains/) を参照）。
> 詳しくは[こちら](#1-何をリサーチするか決める)。

Auto Research は **GitHub リポジトリテンプレート**です。「Use this template」を
押し、Claude の認証情報を1つ追加するだけで、以降は毎日リサーチテーマを Web 検索し、
結果を **GitHub Issue** として投稿します。Issue なので、普段どおり読んで・コメントして・
クローズできます。

**サーバー構築もコード記述も不要**です。すべて GitHub Actions の中で動きます
（公開リポジトリなら無料で使えます）。

---

## ▶️ 5分セットアップを見る

クリックしていくだけのウォークスルー — *Use this template → Actions を有効化 →
Claude のトークンをターミナルで発行 → シークレットに登録 → ワークフローを実行* — そして
毎朝届く Issue、👍/👎 のフィードバック、Slack への投稿まで:

![Auto Research — 約5分で始められます](docs/tutorial.gif)

> 🎞️ フル画質で見たい場合は **[MP4 をダウンロード](docs/tutorial.mp4)**。映像は
> GitHub 自身の [Primer](https://primer.style) デザインシステムに寄せています。

---

## 手に入るもの

毎日、気になるテーマごとに、**4つのジョブが並行して**走り、結果を **1項目につき
1つの Issue** として投稿します — 各論文・仮説・リリース・ページ変更がそれぞれ独立して
追跡・ラベル付け・コメント・クローズできる Issue になります。

| 📰 研究ニュース | 💡 仮説 | 📚 関連研究 | 👀 サイト監視 |
| --- | --- | --- | --- |
| 最新の論文・リリース・記事を3〜6件 — 各件が実在リンク・出典・日付・1行要点つきの独立 Issue。 | 検証可能で反証可能な具体的仮説を3〜5件 — 各仮説が根拠・検証実験・主なリスクつきの独立 Issue。 | テーマごとに整理した実在論文 — 各論文を個別 Issue に、加えて未解決の課題を1つの Issue にまとめる。 | 監視ページ（例: **Hacker News** トップ）を実際のヘッドレスブラウザ（[Playwright](https://playwright.dev/)）で開き、内容が変わるたびに「何が新しいか」を要約した Issue を作成。 |

4つは独立したジョブで、1つずつオン/オフできます —
[どのジョブを使うか選ぶ](#2-どのジョブを使うか選ぶ)を参照。

### どこに届くか — 3つの出力先

各項目は同じスキーマ検証済みデータから、**最大3つの出力先に同時に**流れます。

| 🏷️ GitHub Issue | 🌐 GitHub Pages サイト | 💬 Slack |
| --- | --- | --- |
| 主な出力。1項目1 Issue で、トピックラベルが**自動付与**され、フィルタ・トリアージでき、👍/👎 で次回を誘導。 | すべての Issue から再生成する **Astro + Starlight** 製のリッチなドキュメントサイト。`gh-pages` ブランチへ公開され、全文検索・ダークモード・タグ・リアクション・コメント対応。 | 項目ごとに1行（またはセクション単位のダイジェスト）を Incoming Webhook へ投稿。各行は**公開リンク**（サイト項目ページ、無ければ本物のソース URL）を先頭に置き、GitHub Issue は副リンク `↳` のみ。任意 — Webhook の有無がスイッチ。`RESEND_API_KEY` + `EMAIL_TO` でメールにも同報。 |

どれも普通の Issue として届きます — タイトル・ラベル・クリックできるソースつきなので、
GitHub での既存のワークフローにそのまま乗ります。

```
研究ニュース: Self-RAG: Learning to Retrieve, Generate, and Critique …   [auto-research] [research-news]

テーマ: Retrieval-augmented generation
日付: 2026-06-04

出典: arXiv · 2026-05
リンク: https://arxiv.org/abs/…

いつ検索すべきかをモデル自身に判断させ、不要な検索を削減。
```

**なぜ信頼できるか:** Claude は Web 検索で**実際に開いた**論文・リンクだけを載せます。
タイトル・著者・日付・URL を**決して捏造しない**よう指示されており、不確かなときは
引用をでっち上げず、その項目を空欄のままにします。

---

## ⚡ クイックスタート — 約5分で動きます

1. このリポジトリ上部の「**Use this template**」をクリックして、自分のコピーを作成。
2. 作成したリポジトリの **Actions** タブを開き、ワークフローを**有効化**するボタンを押す。
3. Claude の認証情報を1つ用意（持っているほうでOK）:
   - **Claude Pro/Max プラン** → ローカルで `claude setup-token` を実行・ログインし、表示されたトークンをコピー。
   - **API 課金** → [console.anthropic.com](https://console.anthropic.com) で API キーを取得。
4. **Secret** に追加: *Settings → Secrets and variables → Actions → Secrets → New repository secret*。
   - 名前は `CLAUDE_CODE_OAUTH_TOKEN`（プランのトークン）**または** `ANTHROPIC_API_KEY`（API キー）。**どちらか1つ**でOK。
5. *(任意)* **Variable** に `RESEARCH_TOPIC` を作りテーマを指定 — 未設定なら `AI` がデフォルト。
6. すぐ試す: **Actions → Auto Research → Run workflow**。新しい Issue を確認したら、あとは毎日自動で走ります。

> 💡 認証情報を追加するまでの間も、定期実行は**正常終了**し、何を追加すべきかを
> ログに残します。セットアップ途中で壊れることはありません。

---

## できること — 機能を1つずつ

以下はどれも、GitHub の **Variable** または **Secret** を1つ設定するだけで
切り替え・変更できます（*Settings → Secrets and variables → Actions*）。
特記しない限りコード編集は不要です。

### 1. 何をリサーチするか決める

`RESEARCH_TOPIC` **Variable** に好きなテーマを設定 — `Retrieval-augmented
generation`、`タンパク質の折りたたみ`、`RISC-V コンパイラ` など。未設定なら `AI`。

研究室に合った濃い結果がほしいときは、**`config/research_topics.md`** も編集して、
テーマ・データセット・制約・未解決の問いを書いておきます。Claude は毎回この
ファイルを文脈として読みます。

**信頼できる情報源を指定する。** 研究室がよく見るフィード・ブログ・一覧ページの
URL を **`config/priority_sources.md`** に1行1URLで列挙しておくと、Claude は
自由なウェブ検索の前に**まずそれらの URL を巡回**し、そこで見つけた個別リンクを
たどります。お気に入りの情報源が毎回優先的にクロールされます。あくまで優先順位で
あってホワイトリストではないため、巡回し終えたあとは新しい情報を自由に検索します。

**ドメイン（レンズ）を選ぶ — おまかせも可。** 実行は学術リサーチに限りません。
テーマを5つのレンズ — **research / tech / business / hobby / finance** — のどれかで
見られます。各レンズは **`config/domains/`** 配下の Markdown ガイドです。デフォルトは
`auto`：各実行の最初に小さなピッカーがテーマを読んで最適なレンズを選び、その選択を
**テーマごとに記憶**します（テーマを変えるまで安定）。通常この設定に **Variable は不要**
です。固定したいときは `RESEARCH_DOMAIN` Variable を `research`/`tech`/`business`/
`hobby`/`finance` に設定します。どのドメインでも各実行は同じ3層 — **Foundations**
（揺らぎのない事実）・**Latest**（最新の動き）・**Takes**（考察） — を生成し、各リサーチ
Issue に `domain:<domain>` タグが付きます（👀 サイト監視 Issue は対象外）。

### 2. どのジョブを使うか選ぶ

各ジョブは独立していて、個別にオフにできます。

| Variable | 制御対象 | デフォルト |
| --- | --- | --- |
| `ENABLE_RESEARCH_NEWS` | 📰 ニュースレポート | オン |
| `ENABLE_HYPOTHESIS_GENERATION` | 💡 仮説レポート | オン |
| `ENABLE_RELATED_WORK` | 📚 関連研究レポート | オン |
| `ENABLE_SITE_WATCH` | 👀 サイト監視（ページ差分ウォッチャー） | オン |

`false` にするとスキップ。未設定（または `true`）ならオンのままです。すべて
**並行実行**されるので、任意の組み合わせで動きます。

**サイト監視**は別ファイル **`config/watch_targets.json`** で設定します — 監視する
ページの一覧（slug・名前・URL、そしてページの一部だけを追う任意の CSS `selector`）
です。初期状態では Hacker News のトップページを監視します。自分のページを追加したり、
`enabled: false` で一時停止できます。スナップショットは（main ではなく）統一の
`auto-research-state` オーファンブランチに保持され（ドメイン選択の状態と共用）、
各実行はその前回分と差分を取ります。

### 3. 英語か日本語かを選ぶ

`OUTPUT_LANGUAGE` Variable を `en` または `ja` に設定します。これで Claude が書く
言語**と** Issue の見出し・ラベルの言語の両方が切り替わります。**未設定のまま**にすると、
ドメインピッカーがテーマから最適な言語を推論します（ドメインと同様にテーマごとに記憶）。
認識できない値の場合は英語にフォールバックします。

### 4. 項目ごとに Slack 通知を受け取る

`SLACK_WEBHOOK_URL` という **Secret** に Slack の
[Incoming Webhook](https://api.slack.com/messaging/webhooks) URL を設定します。
すると各項目が、先頭にセクション絵文字（📰 / 💡 / 📚）を付けた1行メッセージを、
タイトルとリンクとともに投稿します。Webhook が無ければ投稿なし —
別途オン/オフのフラグはなく、**Webhook の有無**がそのままスイッチです。

**主リンクは GitHub Issue ではなく、必ず公開 URL です。** これは意図的です。
リポジトリが非公開でもサイトは公開でき、GitHub を開かない読者も多いためです。
各行は次の優先順で先頭にリンクを置きます:

1. 公開された[ドキュメントサイト](#12-すべてを充実したドキュメントサイトとして公開する--自動で)のその項目ページ
   — GitHub Pages API からライブ取得する（ワークフローは `pages: read` を持つ）ので、
   `/<repo>/`・ルート・独自ドメインのいずれで配信されていても常に一致します。
2. Pages が未設定なら、**キュレーションした本物のソース URL** — その項目が扱う
   実際の論文・記事・ページそのもの。
3. 最後の手段としてのみ、GitHub Issue。

それ以外では GitHub Issue は小さな副リンク `↳ GitHub Issue:` に格下げされます。
こうして読者は、リポジトリにアクセスできなくても必ず開けるリンクを得られます。

### 5. 同じ通知をメールでも受け取る

各項目を受信箱にも届けたいときは、**Secret** に `RESEND_API_KEY`
（[Resend](https://resend.com) の API キー）を、宛先に `EMAIL_TO`
（Variable または Secret、複数はカンマ区切り）を設定します。**両方**が揃うと、
Slack に投稿される各項目が**まったく同じ文面**で（ダイジェスト／項目ごとの挙動も
そのまま）メール送信されます。Slack Webhook と同様に別途のオン/オフフラグはなく、
**両方の値の有無**がそのままスイッチです。送信元はデフォルトで Resend の共有
テストアドレス `onboarding@resend.dev`（ドメイン認証するまでは自分の Resend
アカウント宛にしか届きません）。誰にでも送るには認証済みドメインの
`EMAIL_FROM` を設定し、件名の接頭辞 `[Auto Research] ` を変えるには
`EMAIL_SUBJECT_PREFIX` を設定します。

### 6. 各項目を Markdown ファイルとしても保存する

`ENABLE_FILE_OUTPUT=true` にすると、項目ごとに1ファイル
`outputs/YYYY-MM-DD-<section>-<n>.md` を**追加で**書き出し、ダウンロード可能な
GitHub Actions アーティファクトとしてアップロードします。デフォルトはオフ
（Issue が主な出力先）。

### 7. 実行タイミングを変える

デフォルトは **毎日 JST 04:17（UTC 19:17）** に1回。変更するには
`.github/workflows/auto-research.yml` の `cron` 行を編集します（cron は常に **UTC**）。

```yaml
schedule:
  - cron: "0 22 * * *"   # 毎日 JST 07:00
  - cron: "17 19 * * 1"  # 月曜のみ JST 04:17
  - cron: "0 */12 * * *" # 12時間ごと
```

[crontab.guru](https://crontab.guru) で自由に組み立てられます。**Actions** タブ
から手動でいつでも実行することもできます。

### 8. Claude のレポートの書き方を調整する

セクション別のガイドは **`config/prompts/`** にあります。

- `hypothesis_generation.md` — 仮説の立て方。
- `related_work.md` — 文献のまとめ方。
- `watch_summary.md` — サイト監視の差分のまとめ方。
- `labeling.md` — 自動ラベラーのトピックタグの選び方。
- `slack_summary.md` — Slack フォーマットのメモ。

文章を編集すればトーンや力点を誘導できます。（JSON データの**構造そのもの**を
変えたい場合は、ワークフローの `--json-schema` と `scripts/publish_section.py` の
レンダラーも編集します — [さらに先へ](#さらに先へ)を参照。）

### 9. ラベルとモデルを調整する

- `GITHUB_ISSUE_LABELS` — 全 Issue に付く共通ラベル（デフォルト `auto-research`）。各レポートには専用タグ（`research-news` / `hypothesis` / `related-work`）も付きます。
- `ENABLE_GITHUB_ISSUE` — `false` で Issue 作成を停止（`ENABLE_FILE_OUTPUT` と組み合わせてファイル出力に）。
- `ANTHROPIC_MODEL` — Claude モデルの上書き（デフォルト `claude-sonnet-4-6`）。

### 10. 1レポートあたりの投稿数を決める

`ITEMS_PER_REPORT`（デフォルト `5`）で、1レポートあたりに投稿したい項目数の目安を
設定します。これは**平均**で、Claude は多少前後します。ニュースと仮説はそのまま件数、
関連研究はテーマ全体の論文総数を目安にします。小さくすれば引き締まった日次ダイジェスト、
大きくすれば広めのスイープになります。

### 11. フィードバックで賢くする — そして繰り返さない

各実行は、まず過去に作成した Issue を要約し、すでに扱った内容は提案しないよう
Claude に指示します。だから毎日、同じ論文の再掲ではなく本当に新しい項目が届きます。

ワンクリックで**次回を誘導**することもできます。過去の Issue に 👍 / 👎 で
リアクション（または `good` / `bad` ラベルを追加）すると、Claude は 👍 の方向の
項目を*より多く*、👎 の方向を*避けて*出します。任意の Variable で調整できます。

- `EXISTING_CONTEXT_MAX` — 毎回要約する過去 Issue の件数（デフォルト `40`）。
- `GOOD_LABELS` / `BAD_LABELS` — good/bad と見なすラベル名（カンマ区切り）。デフォルトで `good,👍,useful,approved` と `bad,👎,not-useful,rejected` を含み、👍/👎 **リアクション**は設定不要で機能します。

### 12. すべてを充実したドキュメントサイトとして公開する — 自動で

2つ目のワークフロー **`publish-site.yml`** が、**Auto Label** /
**Auto Research** 実行の**直後**に動き、すべての Issue を
**[Astro](https://astro.build) + [Starlight](https://starlight.astro.build) 製の
リッチなドキュメントサイト**に変換します（サイドバー、全文検索、ダークモード、
レスポンシブ対応）。Issue（唯一の情報源）を、**各 Issue のタグ・リアクション・
コメントごと**すべて読み戻し、次を生成します。

- **スプラッシュのトップページ** — ヒーロー、統計カード、項目フィード。
- **実行ごとの個別ページ** — その日の項目をセクション別（📰 / 💡 / 📚 / 👀）に
  まとめ、各カードに項目本文・**トピックタグ**・**リアクション**チップ
  （👍 ❤️ 🚀 …）・Issue に付いた**コメント**を表示し、元の Issue へリンク。
- **項目ごとのページ** — 本文全文に、そのタグ・リアクション・コメントを添えて。
- **セクションごとのページ**（Latest / Takes / Foundations / Site Watch）と
  **リアクションごとのページ**（👍 ❤️ …） — 該当する項目を一覧。
- **タグごとのページ** — そのタグが付いた項目を一覧するファセット（タグは
  auto-label ワークフローが付与）。

確定的な Python（`scripts/build_site.py`、LLM なし）がデータ処理して Markdown を
書き出し、Astro がビルドします。本文は設定した `OUTPUT_LANGUAGE` の言語です。

**公開は専用の `gh-pages*` ブランチへ**（`peaceiris/actions-gh-pages` 経由。
`auto-research-state` と同じ「専用ブランチ」方式）なので `main` の履歴は汚れません。

**初回のみの設定:** Pages がどこで配信するかで、各 CSS/JS の URL に焼き込まれる
`base` パスが決まります。公開の*プロジェクト* Pages は `/<リポジトリ名>/` 配下、
一方**プライベート**リポジトリの Pages はランダムな
`https://<id>.pages.github.io/` ドメインの**ルート**で配信されます。ビルド側から
はどちらか判別できないため、**`SITE_BASE` Variable 未設定**の初回実行では*両方*を
公開します:

- **`gh-pages`** — base `/<リポジトリ名>/` でビルド（公開プロジェクト Pages 用）
- **`gh-pages-root`** — base `/` でビルド（プライベートのルート Pages 用）

*Settings → Pages → Build and deployment* を開き、**Source =「Deploy from a
branch」**、ブランチに **CSS が当たって正しく表示される方**を選んでください
（誤った方はスタイルが崩れて見えます）。公開ケースなら
`https://<ユーザー名>.github.io/<リポジトリ名>/` で公開されます。

> **固定する（任意）:** どちらが合うか分かったら、リポジトリ Variable
> **`SITE_BASE`** を設定します — `/`（→ `gh-pages-root` のみ再ビルド）または
> `/<リポジトリ名>/`（→ `gh-pages` のみ）。以降は該当ブランチだけが再ビルドされ、
> 他方は残っても無害なので削除して構いません。

**任意 — サイト上でのコメント＆リアクション（giscus）:** 静的ページには各 Issue の
コメント・リアクション数のスナップショットが既に表示されます。サイト上で直接
コメント／リアクションできるようにするには、**Discussions** を有効化し、
[giscus アプリ](https://github.com/apps/giscus)を導入のうえ、`GISCUS_REPO` /
`GISCUS_REPO_ID` / `GISCUS_CATEGORY` / `GISCUS_CATEGORY_ID` の Variable を
設定します（ID は [giscus.app](https://giscus.app) で取得）。未設定ならクリーンな
静的スナップショットのままです。

**Actions → Publish Site → Run workflow** からいつでも手動生成でき、セクション
あたりに取り込む Issue 数は任意の `SITE_MAX_ISSUES` Variable（デフォルト `300`）で
調整できます。

---

## 仕組み

Auto Research は **GitHub Actions** 上でスケジュール実行されます。各レポートは
**独立したジョブ**で、2つのきれいな役割に分かれています。

| 役割 | 担当 | 内容 |
| --- | --- | --- |
| **リサーチ** | [`claude-code-action`](https://github.com/anthropics/claude-code-action) | 探索的な部分。Claude が **Web 検索**で実在の最新ソースを集め、**スキーマ検証済み JSON**（`structured_output`）を返す。 |
| **パブリッシュ** | Python（`scripts/publish_section.py`） | 確定的な部分。その JSON を Markdown に整形し、ラベル付き **GitHub Issue** を作成（＋任意のファイル・Slack）。**LLM 呼び出しなし。** |

この分担がこのテンプレートの核です。**探索的でばらつくリサーチは Claude に任せて
構造化データを出させ、予測可能な処理（Markdown 整形・Issue 作成・Slack 投稿）は
すべて Python が確定的に行う** — だから出力が安定し、挙動を追いやすくなります。

Issue は **Actions が自動で用意する `GITHUB_TOKEN`** で作成するため個人アクセス
トークンは不要です。ワークフローには `issues: write` 権限を付与済みです。

---

## セットアップ途中でも壊れません

任意の連携はすべて安全に縮退します — キーや Webhook が無くても、実行は失敗せず、
明確な「スキップ」メッセージになります。

- **Claude の認証情報なし** → リサーチをスキップし、`::notice` で追加すべき項目を表示。
- **`SLACK_WEBHOOK_URL` なし** → `Slack webhook is not configured. Skipping Slack post.` とログ出力。
- **`RESEND_API_KEY` / `EMAIL_TO` なし** → `Resend email is not configured … Skipping email.` とログ出力。
- **`ENABLE_GITHUB_ISSUE=false`** → Issue 出力オフ（代わりに `ENABLE_FILE_OUTPUT`）。
- **ローカル実行で `GITHUB_TOKEN` なし** → Issue 作成をスキップ。

Secrets（API キー・OAuth トークン・Slack Webhook・Resend キー）は**ログに一切表示されません**。

---

## 設定リファレンス

すべて *Settings → Secrets and variables → Actions* 配下です。GitHub には2つの
タブがあります — **Variables**（機密でない・ログに表示される）と
**Secrets**（非表示・ログに出ない）。

### Variables タブ

| 名前 | 例 | 内容 |
| --- | --- | --- |
| `RESEARCH_TOPIC` | `Retrieval-augmented generation` | メインテーマ。未設定なら `AI`。Claude は `config/research_topics.md` も読みます。 |
| `RESEARCH_DOMAIN` | `auto` | 実行のレンズ：`auto`（デフォルト、テーマごとに選択・記憶）か、`research`/`tech`/`business`/`hobby`/`finance` で固定。ガイドは `config/domains/`。 |
| `ITEMS_PER_REPORT` | `5` | 1レポートあたりの投稿数の目安（デフォルト `5`）。関連研究はテーマ全体の論文総数。 |
| `ENABLE_RESEARCH_NEWS` | `true` | ニュースレポートの ON/OFF（デフォルトオン）。 |
| `ENABLE_HYPOTHESIS_GENERATION` | `true` | 仮説レポートの ON/OFF（デフォルトオン）。 |
| `ENABLE_RELATED_WORK` | `true` | 関連研究レポートの ON/OFF（デフォルトオン）。 |
| `ENABLE_SITE_WATCH` | `true` | 👀 サイト監視（ページ差分ウォッチャー）の ON/OFF（デフォルトオン）。監視対象は `config/watch_targets.json`。 |
| `ENABLE_AUTO_LABEL` | `true` | 自動ラベルワークフローの ON/OFF — その日の Issue にトピックタグを付与（デフォルトオン）。 |
| `WATCH_TIMEOUT_MS` | `30000` | サイト監視: 1ページあたりの Playwright ナビゲーションタイムアウト（ms、デフォルト `30000`）。 |
| `WATCH_MAX_DIFF` | `400` | サイト監視: Claude が要約する前にページごとに保持する差分の最大行数（デフォルト `400`）。 |
| `ENABLE_GITHUB_ISSUE` | `true` | レポートごとに Issue を作成（デフォルトオン）。 |
| `ENABLE_FILE_OUTPUT` | `false` | 項目ごとに `outputs/<date>-<section>-<n>.md` も保存・アップロード。 |
| `SLACK_DIGEST` | `true` | セクションごとに Slack 投稿を**1回にまとめる**（デフォルトオン）。`false` で項目ごとに1投稿。 |
| `GITHUB_ISSUE_LABELS` | `auto-research` | 全 Issue に付く共通ラベル。 |
| `OUTPUT_LANGUAGE` | `en` | 出力言語: `en` または `ja`。未設定ならピッカーがテーマから推論（テーマごとに記憶）。 |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | 使用する Claude モデル（任意）。 |
| `EXISTING_CONTEXT_MAX` | `40` | 重複排除のため毎回要約する過去 Issue の件数（デフォルト `40`）。 |
| `GOOD_LABELS` | `good,👍,useful,approved` | 過去 Issue を**良い**と印付けるラベル名（その方向へ誘導）。👍 リアクションも有効。 |
| `BAD_LABELS` | `bad,👎,not-useful,rejected` | 過去 Issue を**悪い**と印付けるラベル名（その方向を回避）。👎 リアクションも有効。 |
| `LABEL_CONTEXT_MAX` | `40` | 自動ラベル: ラベラーが対象にするその日の Issue 数（デフォルト `40`）。 |
| `LABEL_BODY_MAX` | `600` | 自動ラベル: ラベラーに渡す Issue ごとの本文の最大文字数（デフォルト `600`）。 |
| `LABEL_MAX_PER_ISSUE` | `5` | 自動ラベル: 1 Issue に付けるトピックラベル数の上限。 |
| `SITE_MAX_ISSUES` | `300` | ドキュメントサイトがセクションあたりに取り込む Issue の上限（デフォルト `300`）。 |
| `SITE_FETCH_COMMENTS` | `true` | 各 Issue のコメントをページに表示（`false` で Issue ごとのコメント取得をスキップ）。 |
| `SITE_TITLE` | `Auto Research` | ドキュメントサイトのヘッダー見出し。 |
| `EMAIL_TO` | — | 任意のメール通知の宛先（複数はカンマ区切り）。`RESEND_API_KEY` と併せると、Slack の各行が同じ文面でメール送信される。どちらのタブでも可。 |
| `EMAIL_FROM` | `onboarding@resend.dev` | メールの送信元。デフォルトのテスト送信元は自分の Resend アカウント宛にしか届かない。誰にでも送るには認証済みドメインのアドレスを設定。 |
| `EMAIL_SUBJECT_PREFIX` | `[Auto Research] ` | すべてのメール件名に付く接頭辞。 |
| `GISCUS_REPO` / `GISCUS_REPO_ID` / `GISCUS_CATEGORY` / `GISCUS_CATEGORY_ID` | — | サイト上のライブコメント/リアクションを有効化する giscus の ID（[giscus.app](https://giscus.app) で取得、任意）。 |

フラグは `true` / `1` / `yes` / `on`（または未設定）で有効。`false` を明示した
ときだけ無効化されます。

### Secrets タブ

| 名前 | 内容 |
| --- | --- |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code OAuth トークン（Claude Pro/Max）。`claude setup-token` で生成。 |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) の API キー。OAuth トークンの**代わり**に使用。 |
| `SLACK_WEBHOOK_URL` | *(任意)* Slack [Incoming Webhook](https://api.slack.com/messaging/webhooks) URL。 |
| `RESEND_API_KEY` | *(任意)* [Resend](https://resend.com) の API キー。`EMAIL_TO` を設定すると各項目が（Slack と同じ文面で）メール送信される。 |

> `CLAUDE_CODE_OAUTH_TOKEN` と `ANTHROPIC_API_KEY` は**どちらか1つ**でOK。
> `OUTPUT_LANGUAGE` はどちらのタブに置いても読み込めます。

---

## GitHub なしで試す

リサーチ部分は Claude Code Action が必要ですが、確定的な**パブリッシャー**は
サンプル JSON でローカル実行できます — Markdown のプレビューに便利です。Python
標準ライブラリのみで動くため、インストールするものはありません。

```bash
export SECTION_JSON='{"items":[{"title":"例","url":"https://arxiv.org/abs/0000.00000","takeaway":"…"}]}'
export OUTPUT_LANGUAGE=ja
ENABLE_FILE_OUTPUT=true python3 scripts/publish_section.py news
# → outputs/<日付>-news-01.md を生成（項目ごとに1ファイル。Issue 作成には GITHUB_TOKEN が必要）
```

**サイトエクスポーター**も同様に自己完結しています。`GITHUB_TOKEN` と
`GITHUB_REPOSITORY` を設定すれば実際の Issue（タグ・リアクション・コメント込み）を
取得し、未設定でも有効な空状態を生成します。エクスポーターが `site/` に Markdown を
書き出し、Astro がそれをビルドします。

```bash
python3 scripts/build_site.py site    # → site/src/content/docs/{index,runs,tags}.md
cd site && npm install && npm run build   # → site/dist/（site/dist/index.html を開く）
```

---

## さらに先へ

- **新しいレポートを追加:** ワークフローのジョブをコピーし、`--json-schema` を与え、`scripts/publish_section.py` に対応するレンダラーを追加。
- **スキーマを拡張:** 確信度スコア・著者リストなどを必須化する。
- **日次ダイジェスト:** その日の Issue をまとめて1つの Slack 要約にするジョブを追加。
- **履歴を残す:** 日次 Markdown を `reports/` ブランチにコミットしていく。
- **複数テーマを一度に:** **matrix** で複数の研究領域を並行実行する。

---

## セキュリティ

- **Secrets をコードに直接書かない。** API キー・OAuth トークン・Slack Webhook は必ず **GitHub Secrets** に置く。
- `.env` は gitignore 済み。コミットされるのはダミー値の `.env.example` のみ。
- スクリプトは Secrets や Webhook URL を `print()` しません。
- これは**公開**テンプレートなので、サンプル値はすべてダミーです。
- ワークフローは最小権限（`contents: read` + `issues: write`）で動作します。

---

## プロジェクト構成

```txt
.
├── README.md                             # 英語（メイン）
├── README.ja.md                          # 日本語（このファイル）
├── LICENSE                               # MIT
├── CONTRIBUTING.md                       # テンプレートの拡張方法
├── CLAUDE.md                             # エージェント（リサーチ役）向けガイド
├── .github/
│   ├── workflows/
│   │   ├── auto-research.yml             # select + 4ジョブ（ニュース/仮説/関連/監視）、各: リサーチ → パブリッシュ
│   │   ├── auto-label.yml               # 実行後: その日の Issue にトピックタグを付与
│   │   └── publish-site.yml             # 実行後: Issue → Astro/Starlight サイト → gh-pages ブランチ
│   └── ISSUE_TEMPLATE/                   # バグ報告 + 機能要望
├── config/
│   ├── research_topics.md                # 研究テーマ（編集してください）
│   ├── domains/                          # 🧭 ドメイン別ガイド: index.md + <domain>.{en,ja}.md（編集してください）
│   ├── priority_sources.md               # Claude が最初に巡回する URL（編集してください）
│   ├── watch_targets.json                # 👀 サイト監視が描画＆差分するページ（編集してください）
│   ├── weekly_research_template.md       # 手書きの週次ダイジェスト用ひな形
│   └── prompts/                          # 編集可能なレポート別ガイド
│       ├── hypothesis_generation.md
│       ├── related_work.md
│       ├── watch_summary.md
│       ├── labeling.md
│       └── slack_summary.md
├── scripts/
│   ├── select_domain.py                  # 確定的なドメイン/言語ピッカー（テーマごとに記憶、LLM なし）
│   ├── restore_state.sh / save_state.sh  # auto-research-state ブランチ用の競合安全ヘルパ
│   ├── publish_section.py                # 確定的な JSON → Issue パブリッシャー（リサーチ）
│   ├── watch_fetch.py                    # 👀 Playwright で描画＆snapshots/ と差分（LLM なし）
│   ├── publish_watch.py                  # 👀 確定的なサイト監視 JSON → Issue パブリッシャー
│   ├── watch_targets.py                  # 👀 config/watch_targets.json のローダー（LLM なし）
│   ├── build_site.py                     # Issue（タグ/リアクション/コメント込み）→ site/ の Starlight Markdown（LLM なし）
│   ├── existing_context.py               # 重複排除ダイジェスト + 👍/👎 フィードバック（LLM なし）
│   ├── label_context.py                  # 🏷️ 自動ラベラー用にその日の Issue + ラベル体系を収集（LLM なし）
│   ├── apply_labels.py                   # 🏷️ 自動ラベル JSON → Issue ラベルを追加付与（LLM なし）
│   ├── github_issue.py                   # GitHub Issue API（標準ライブラリ urllib）
│   ├── slack_post.py                     # 安全な Slack 投稿（標準ライブラリ urllib）
│   ├── email_post.py                     # 安全な Resend メール送信（標準ライブラリ urllib）
│   ├── site_url.py                       # オンサイト項目リンク用に Pages URL をライブ取得
│   └── i18n.py                           # 英語 / 日本語の体裁文字列
├── site/                                 # Astro + Starlight ドキュメントサイト（雛形のみ。content と dist は生成物）
│   ├── package.json                      # astro + @astrojs/starlight
│   ├── astro.config.mjs                  # Starlight 設定（base/site・サイドバー・giscus 上書き）
│   └── src/                              # content.config.ts, styles/custom.css, components/Footer.astro
├── snapshots/                            # 👀 ページスナップショット（差分の基準。main ではなく auto-research-state ブランチに保持）
├── outputs/                              # 任意の日付付きファイルの出力先
├── requirements.txt                      # （パブリッシャーはサードパーティ依存なし）
└── .env.example
```

---

_出発点として作られています。まずはシンプルに、そして研究室に合わせて拡張して
ください。_
