# Confidently Incorrect

個人中文部落格。Hugo + PaperMod（以 **Hugo Module** 引入，不是 submodule，主題原始碼不在 repo 裡），
GitHub Actions 建置後部署到 GitHub Pages，網域 `hmszeit.me`（根目錄 `CNAME` 指定）。

## 上稿流程

使用者會把文章文字丟過來，或只講重點請你整理。你負責機械的部分，**但不推 `main`**：

1. 在 `content/posts/` 新增 `.md`，檔名 `YYYY-MM-DD-slug.md`（**全小寫、用連字號，不要空白或底線**）
2. 補 front matter（見下）
3. commit、推到 `claude/…` 分支、開 PR
4. **使用者自己按 Merge** —— 發布權在他手上，不要代勞

部署有兩條路：**push 到 `main`**（merge 就是走這條），以及在 GitHub 上手動觸發
**`workflow_dispatch`**。PR 只跑建置檢查，不會部署。Merge 後約 50 秒上線。

`workflow_dispatch` 會直接部署當下 `main` 的內容，**繞過上面第 4 步的把關**。
它是留給使用者手動重跑部署用的（例如上一次部署失敗），**你不要主動去觸發它**。

這個 blog 寫的是很私人的內容。**不要替使用者判斷哪些該公開、哪句該刪**，那一關永遠留給他。

### Front matter

TOML，用 `+++` 包住。欄位範本在 `archetypes/default.md`：

```toml
+++
author = "hms"
title = "文章標題"
date = 2026-01-01T12:00:00+08:00
draft = false
tags = ["memory"]
categories = ["thoughts"]
summary = ""
slug = ""
showtoc = false
tocopen = false
ShowReadingTime = false
ShowWordCount = false
disableShare = false
comments = true
+++
```

現有的分類：`thoughts`、`diary`、`travel`。
現有的標籤：`memory`、`guitar`、`soccer`、`animal`、`privacy`、`ngo`、`social housing`、`nthu`、`program`。
沿用既有的，不要每篇都發明新的。

注意 `social housing` 在 front matter 裡是**有空白**的，Hugo 會自己轉成網址上的 `social-housing`。
沿用原字串，不要改成連字號，否則會多出一個重複的標籤頁。

`content/posts/_index.md` 是區段索引頁，不是文章，不要動它。

早期有兩篇沒照檔名慣例（`2024-07-09_wierd week.md`、`2025-10-17_apparent.md`），
其中含空白的那篇產生了很難看的網址。新文章一律照上面的慣例，舊的不用回頭改。

`ShowReadingTime` 與 `ShowWordCount` 保持 `false` —— PaperMod 是以英文空白斷詞計算，中文會算出離譜的數字。

## ResearchNotes（`content/research-notes/`）

第二個 section，跟 `content/posts/` 平行，放使用者看到、覺得值得留存的資料 ——
摘錄、出處連結、他自己的註記。**刻意不出現在首頁的文章列表**，避免把文章洗掉。

上稿方式跟文章完全一樣（開 PR、使用者按 Merge），只是檔案放進 `content/research-notes/`。
front matter 範本在 `archetypes/research-notes.md`，比文章多一組欄位：

```toml
canonicalURL = "https://example.org/原文網址"
ShowCanonicalLink = true
```

填了之後，標題下方的 meta 列會顯示「Source example.org」並連向原文。
這是 PaperMod 內建的，不必改模板；顯示文字由 `hugo.toml` 的 `CanonicalLinkText` 控制。

這一區的對外文字（選單、頁面標題、說明）使用者指定用英文，網址則維持 `/research-notes/`（小寫連字號）。
新增筆記時標題用什麼語言由使用者決定，不必強制英文。

### 議題分類

筆記用 `topics` 這個 taxonomy 分議題，**跟 posts 的 `tags` / `categories` 是分開的**，
兩套詞彙才不會混在同一個列表頁。目前五個：
`Philosophy`、`Tech`、`Literature`、`Politics`、`Health`。

front matter 裡 `topics = ["Philosophy"]`，可複選（一則筆記可同時屬於多個議題，
會在每個議題頁都出現）。不填就只出現在 `/research-notes/`。

**新增一個議題時有兩件事要一起做**，少一件就會出問題：

1. 建 `content/topics/<小寫slug>/_index.md`，裡面寫 `title = "顯示名稱"`。
   沒有這個檔案的話，議題頁只有在「已經有筆記」時才存在 —— 空議題的連結會 404
2. 把連結加進 `content/research-notes/_index.md` 的內文那一行

`/topics/` 那頁是 Hugo 自動產生的詞條總覽，但**只列出已經有筆記的議題**，
所以完整的議題入口是 `/research-notes/` 頁面上那一行，不是 `/topics/`。

筆記的單篇頁底下會顯示議題 chip，點得回議題頁 —— 這是靠
`layouts/research-notes/single.html` 做的，見下面「覆寫過的主題模板」。

各處的行為（都實際建置驗證過）：

| | ResearchNotes 會出現嗎 |
|---|---|
| 首頁文章列表 | 否 —— 這是重點 |
| `/research-notes/` | 是，這是它的家 |
| 站內搜尋 | 是 |
| 主 RSS `/index.xml` | 是（使用者要的） |
| Archives | 否 |
| Tags / Categories | 有標才會 |
| `/topics/<議題>/` | 有填 `topics` 才會 |

## 排版

`assets/css/extended/typography.css`。PaperMod 會自動把 `assets/css/extended/*.css` 接在主題 CSS 之後，
**不要改主題原始碼**，也不需要。刪掉這支檔案，站就回到主題預設樣子。

可調數值集中在檔案最上面的 `:root`，手機的另一組在最下面的 `@media (max-width: 768px)`：

| | 電腦 | 手機 |
|---|---|---|
| 內文字級 | 16px | 16px |
| 行距 | 1.85 | 1.75 |
| 字距 | 0.02em | 0.02em |
| 段落間距 | 1.5em | 1.5em |
| 閱讀欄寬 | 560px | 螢幕寬 |

內文用思源黑體 Noto Sans TC、文章標題用思源宋體 Noto Serif TC，由
`layouts/partials/extend_head.html` 從 Google Fonts 載入。刪掉那支 partial 就退回系統中文字型，CSS 不必動。

內文裡的分節標題（h2/h3）刻意留在黑體 —— 宋體大標配黑體小標。

### 深色模式的坑

PaperMod 的深色模式靠 JS 在 `<body>` 加 `.dark` class。JS 停用時，主題改用自己 `<noscript>` 區塊裡的
`@media (prefers-color-scheme: dark)` 直接換掉 `--theme` / `--primary` / `--content`。

**所以新增任何自訂顏色變數時，三個地方都要顧到**：

1. `:root` —— 淺色值
2. `.dark` —— 深色值
3. `extend_head.html` 的 `<noscript>` —— 無 JS 的深色值

漏掉第三個就會出現深底配深字。`--read-color` 就發生過，對比一度只有 1.47:1。
目前需要這樣顧的自訂變數有三個：`--read-color`（typography.css）、
`--tag-chip-bg` 與 `--tag-chip-color`（meta-tags.css）。

不要用一般的 `@media (prefers-color-scheme: dark)` 代替 `<noscript>`：JS 正常時，在深色系統上手動
切成淺色的使用者同樣沒有 `.dark`，純 media query 分不出這兩種情況，會把他們的淺色頁面內文塗成淺灰。

## 建置

- Hugo **extended** ≥ 0.146（CI 用 0.147.8）
- `go.mod` 要求 Go 1.25.1，CI 的 `setup-go` 也設 `1.25.x`。兩邊要對齊，否則每次 build 會多下載一次 toolchain
- 本機：`hugo mod tidy && hugo server`
- CI：`.github/workflows/hugo.yml`。push 到 `main` → build + deploy；`pull_request` → 只 build 不部署

## 覆寫過的主題模板

repo 裡有兩份從 PaperMod 複製出來、加了東西的版型。兩份都是**整份複製**，
所以**升級主題時要回去比對原始檔有沒有變動**，否則會停在舊版：

| 檔案 | 從哪複製 | 多了什麼 | 影響範圍 |
|---|---|---|---|
| `layouts/research-notes/single.html` | `_default/single.html` | 議題 chip（`.GetTerms "topics"`） | 只有筆記單篇頁 |
| `layouts/partials/post_meta.html` | 同名 | 日期、作者後面接標籤 chip | 首頁與 Archives 的列表 |

兩份都刻意選了影響範圍最小的掛法。

**首頁的文章列表不能靠覆寫模板來加東西** —— 它是 `_default/list.html` 畫的，
而**那支不能覆寫**（會連 tags、categories 等所有列表頁一起換掉，見「不要做的事」）。
能動的是它呼叫的 `post_meta.html` 這支 partial，順帶也服務 Archives，
所以標籤只要寫這一份，兩個地方一起有。

### post_meta.html 怎麼分辨自己在哪一頁

同一支 partial 被三個地方叫到：文章單篇頁（`_default/single.html`）、
首頁與各種列表頁（`_default/list.html`）、Archives（`_default/archives.html`）。
標籤只要出現在首頁和 Archives，所以用 Hugo 的 **`page` 全域變數**（目前正在算的那一頁）
跟 `.`（這一列代表的文章）比對：

| 脈絡 | `page.Kind` | `.` 是不是 `page` | 印標籤 |
|---|---|---|---|
| 文章單篇頁 | `page` | **是** | 否（底下本來就有 chip，會重複） |
| 首頁（含 `/page/2/`） | `home` | 否 | 是 |
| Archives | `page` | 否 | 是 |
| Tag / Category / Topic 列表 | `term` | 否 | 否 |
| Section 列表（`/posts/`…） | `section` | 否 | 否 |

判斷式就是 `and (ne .RelPermalink page.RelPermalink) (in (slice "home" "page") page.Kind)`。
想讓標籤也出現在 tag／section 列表頁的話，把 `page.Kind` 那半拿掉即可。

### 標籤 chip 的兩個坑

**一、點得到嗎**：PaperMod 的 `.post-entry` 與 `.archive-entry` 裡各有一個絕對定位、
覆蓋整格的 `.entry-link`（點哪裡都進文章）。chip 必須 `position: relative; z-index: 1`
疊上去，否則**看得到但點不到**，點下去會變成進文章。

**二、底色不能用實色**：兩個地方的背景不一樣 —— 首頁的卡片是 `--entry`（淺色下是白的），
Archives 整頁的 `body.list` 是 `--code-bg`（淺色下 `rgb(245,245,245)`）。
一開始 chip 底色用 `--code-bg`，結果在 Archives 淺色模式下**整個消失**（同色）。
現在改用半透明覆蓋（`rgba(0,0,0,0.06)` / 深色 `rgba(255,255,255,0.09)`），
墊在什麼底上都會壓深或提亮一階。樣式與註解在 `assets/css/extended/meta-tags.css`。

實測的對比（淺色／深色、有 JS／無 JS、電腦／手機共九種組合）落在 4.7:1 ～ 6.0:1。

## 不要做的事

- **不要 commit `public/`**（已在 `.gitignore`）。Hugo 不會清空目的目錄，舊產物留在版控裡會被一起打包部署 ——
  曾經有 30 個測試殘留檔（`posts/test1`、`posts/hello` 之類）就是這樣一直掛在線上
- **不要建 `layouts/_default/list.html`**。那會整個取代 PaperMod 的列表模板，文章列表會消失。
  分頁頁碼是 `hugo.toml` 的 `ShowPageNums = true`，主題內建，不需要自己寫模板。
  要在首頁的每一則上加東西，改覆寫它呼叫的 partial（例如 `post_meta.html`），不要碰 `list.html`
- **不要拿掉 `hugo.toml` 的 `mainSections = ["posts"]`**。沒有它，Hugo 會自動挑「頁數最多的
  section」當首頁來源 —— 等 `research-notes` 的則數超過 `posts`，首頁會整個翻轉成只剩筆記、
  文章全部消失，而且不會有任何錯誤訊息。實測過確實會發生
- **不要直接推 `main`**
