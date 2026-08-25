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

## 排版

`assets/css/extended/typography.css`。PaperMod 會自動把 `assets/css/extended/*.css` 接在主題 CSS 之後，
**不要改主題原始碼**，也不需要。刪掉這支檔案，站就回到主題預設樣子。

可調數值集中在檔案最上面的 `:root`，手機的另一組在最下面的 `@media (max-width: 768px)`：

| | 電腦 | 手機 |
|---|---|---|
| 內文字級 | 16px | 16px |
| 行距 | 2.0 | 1.75 |
| 字距 | 0.02em | 0.02em |
| 段落間距 | 1.55em | 1.5em |
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

不要用一般的 `@media (prefers-color-scheme: dark)` 代替 `<noscript>`：JS 正常時，在深色系統上手動
切成淺色的使用者同樣沒有 `.dark`，純 media query 分不出這兩種情況，會把他們的淺色頁面內文塗成淺灰。

## 建置

- Hugo **extended** ≥ 0.146（CI 用 0.147.8）
- `go.mod` 要求 Go 1.25.1，CI 的 `setup-go` 也設 `1.25.x`。兩邊要對齊，否則每次 build 會多下載一次 toolchain
- 本機：`hugo mod tidy && hugo server`
- CI：`.github/workflows/hugo.yml`。push 到 `main` → build + deploy；`pull_request` → 只 build 不部署

## 不要做的事

- **不要 commit `public/`**（已在 `.gitignore`）。Hugo 不會清空目的目錄，舊產物留在版控裡會被一起打包部署 ——
  曾經有 30 個測試殘留檔（`posts/test1`、`posts/hello` 之類）就是這樣一直掛在線上
- **不要建 `layouts/_default/list.html`**。那會整個取代 PaperMod 的列表模板，文章列表會消失。
  分頁頁碼是 `hugo.toml` 的 `ShowPageNums = true`，主題內建，不需要自己寫模板
- **不要直接推 `main`**
