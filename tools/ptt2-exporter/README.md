# PTT2 → Hugo 匯出器

這是一個唯讀工具，用來匯出 PTT2 公開看板的一般文章與 `z` 精華區，並打包成
可供本站（Hugo + PaperMod）審稿的 ZIP。預設看板是 `InAddition`。

## 線上使用

1. 到 GitHub repository 的 **Actions** 頁面。
2. 選擇 **Export PTT2 board** → **Run workflow**。
3. 輸入看板名稱；`scope` 可選全部、一般文章或精華區。
4. `max_posts` 與 `max_essence_documents` 填 `0` 代表全部，填正整數可先小量測試。
5. 執行完成後，在該次 workflow run 的 **Artifacts** 下載 ZIP。

PTT2 的匿名訪客有同時上線人數限制。工具會自動重試 guest 登入；如果仍遇到
`guest capacity is full`，可稍後重跑，或在 repository 的
**Settings → Secrets and variables → Actions** 建立：

- `PTT2_ID`
- `PTT2_PASSWORD`

帳密只會由 GitHub Actions 在執行期間讀取，不要把帳密寫進程式、issue、PR 或聊天內容。

## ZIP 內容

```text
content/posts/ptt2/<board>/          Hugo 一般文章草稿
content/posts/ptt2/<board>/essence/  Hugo 精華區草稿
ptt2-archive/<board>/                去除 IP 後的結構化 JSON 原始備份
manifest.json                        數量、錯誤與每個 Markdown 的 SHA-256
```

所有 Hugo 檔案一律設定 `draft = true`。確認作者、內容、授權與版面後，再把要發布的
檔案複製到 repository 的 `content/posts/` 並改成 `draft = false`。

匯出檔刻意不保存文章與推文 IP。PTT 的純文字與 ASCII art 放在 Markdown code fence
內，避免被 Hugo 誤判成標題、短代碼或 HTML。

## 本機使用

需要 Python 3.11 以上：

```bash
python -m pip install -r tools/ptt2-exporter/requirements.txt
python tools/ptt2-exporter/ptt2_export.py \
  --board InAddition \
  --scope both \
  --max-posts 0 \
  --max-essence-documents 0
```

需要註冊帳號時，透過環境變數 `PTT2_ID`、`PTT2_PASSWORD` 傳入。匯出器只有讀取
流程，不會發文、推文、寄信或變更看板。

## 測試

```bash
python -m unittest discover -s tools/ptt2-exporter/tests -v
```

一般文章使用 PyPtt 的公開讀取 API；精華區因 PyPtt 沒有對應的高階 API，使用
VT100 畫面的狀態機遞迴導覽。若 PTT2 日後更改精華區畫面格式，離線 parser 測試會
保留目前支援的格式，實際匯出錯誤則會出現在 Actions log。
