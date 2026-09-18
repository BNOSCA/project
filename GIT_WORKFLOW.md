# 梅竹黑客松 Git Workflow

這份文件是 5 人、24 小時黑客松的協作約定。目標很單純：`main` 隨時能啟動並 Demo、大家可以平行開發、最後一小時不被 Git conflict 拖住。

## 核心規則

1. `main` 永遠保持可執行；除輪值整合者合併 PR 外，沒有人直接在 `main` 開發。
2. 一個分支只處理一個可描述的功能，完成後盡快發 PR，不要把整個模組做完才整合。
3. 改共用介面前先在群組告知：`backend/main.py`、API request/response schema、`requirements.txt`、`package.json`、`.env.example`、資料夾結構都屬於共用介面。
4. 每次 merge 到 `main` 後，輪值整合者都要確認最小展示流程仍可跑。
5. 不提交 `.env`、API key、token、個資或大型暫存資料；只提交 `.env.example`。

## 角色與檔案責任

依照目前的產品草稿，各人優先在自己的模組內工作，其他人不要為了方便直接改動該模組。

| 角色 | 主要範圍 | 需要先溝通的部分 |
| --- | --- | --- |
| A 前端／使用者體驗 | `frontend/` | API 呼叫格式、畫面需要的回傳欄位 |
| B 需求理解 | `backend/intent.py` | 偏好 JSON schema、LLM timeout 與錯誤回應 |
| C 推薦與資料 | `backend/recommender.py`、`data/` | 商品 schema、排序輸入與輸出、資料格式 |
| D 個人化回饋 | `backend/feedback.py` | profile 格式、回饋事件、重排介面 |
| E 後端／整合 | `backend/main.py`、端對端測試與部署 | API 路由、Pydantic schema、環境變數與啟動方式 |

`backend/main.py` 是協調各模組的入口，不是所有人都能隨意修改的地方。若 B、C、D 必須更動介面，先提出 JSON 範例與相容方案，再由當班整合者確認。

## 賽前第一次設定

目前 repo 還沒有 commit，請由第一位整合者在 `project/` 內完成以下一次性設定。先確認沒有真實 key 被加入暫存區；必要時先建立 `.gitignore`，至少忽略 `.env`、`node_modules/`、Python 虛擬環境與快取檔。

```bash
cd project
git branch -m main
git add .
git status
git commit -m "chore: initialize hackathon project"
git remote add origin <GitHub repository URL>
git push -u origin main
```

在 GitHub repository settings 將預設分支設為 `main`。若時間允許，開啟「PR 才能合併」保護；不要要求太多 approvals，避免黑客松期間卡關。請將每位隊友加入 repository，並確認每人都能 `git pull`。

## 日常開發流程

### 1. 從最新 main 開一個短期分支

分支名稱使用 `feature/<範圍>`、`fix/<問題>` 或 `chore/<事項>`。例如 `feature/intent-schema`、`feature/product-rerank`、`fix/frontend-empty-state`。

```bash
git switch main
git pull origin main
git switch -c feature/intent-schema
```

### 2. 小範圍提交、持續推送

完成一個可辨識的小成果就 commit，例如「定義偏好 schema」或「新增無商品結果畫面」。commit 訊息以動詞開頭，讓其他人一眼看懂變更。

```bash
git status
git add backend/intent.py tests/test_intent.py
git commit -m "feat: extract structured clothing preferences"
git push -u origin feature/intent-schema
```

不要用 `git add .` 把 `.env`、下載資料或無關檔案一起提交；提交前先看 `git status` 和 `git diff --staged`。

### 3. 發 PR，交給輪值整合者

PR 一律從功能分支指向 `main`。PR 描述至少包含：

- 做了什麼，以及影響哪個模組。
- 怎麼測試；無法測試時明確寫出原因。
- 是否改動 API 或 JSON schema；若有，附上一組 request/response 範例。
- 未完成項目、已知限制或需要下一位接手者處理的事項。

一般功能可以很小，一個 PR 只要可運作就能合併；不要等到「完美」才送。若 PR 未完成但需要提早對齊，也可開 Draft PR。

### 4. 合併前同步 main

在輪值整合者要求、PR 已落後 `main`，或你即將發 PR 時，同步主分支。以下採用 rebase，讓歷史保持直線；若團隊已經共同使用該分支，改用 merge 或先通知協作者，避免重寫他人的歷史。

```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

`--force-with-lease` 只用於**自己的功能分支 rebasing 後**，絕不能用在 `main`，也不能用來覆蓋共同開發中的分支。

合併完成後，原作者回到最新 `main` 再建立下一個分支：

```bash
git switch main
git pull origin main
git branch -d feature/intent-schema
```

## 輪值整合者流程

輪值不是「只有這個人能幫忙」，而是每個時段有一位明確負責最後判斷與交接的人。建議在團隊群組標示目前值班者與交接時間。

每次接班時：

1. 拉取最新 `main`，確認目前能啟動或至少能跑既有 smoke test。
2. 瀏覽待合併 PR，優先處理小而獨立、已說明測試方式的 PR。
3. 核對輸入／輸出資料契約：前端需要的欄位、B 的偏好 JSON、C 的推薦 JSON、D 的回饋事件，以及 E 的 API schema 是否一致。
4. 合併後立即做最小 smoke test：後端可啟動、關鍵 endpoint 不報錯；若前端已可用，完成一次「輸入需求 → 顯示推薦 → 提交回饋」流程。
5. 在群組公告：已合併的 PR、目前 `main` 狀態、已知問題、下一位整合者要優先查看的事項。

只有確認 `main` 沒有明顯壞掉才合併。若功能還需要別人的 PR 才能運作，可先以 Draft PR 或說明相依關係，不要強行把半套介面放進 `main`。

## Conflict 與問題處理

### 兩人改到同一個檔案

先停止猜測，找出這個檔案的主要負責人或當班整合者協調。更新分支後手動保留兩邊真正需要的變更；不要直接選 `ours` 或 `theirs` 把隊友的工作丟掉。

```bash
git fetch origin
git rebase origin/main
# 手動編輯衝突檔，移除 <<<<<<<、=======、>>>>>>> 標記
git add <已解決的檔案>
git rebase --continue
```

若你發現自己 rebase 到錯誤方向，先停止而不是硬修：

```bash
git rebase --abort
```

解完 conflict 後，重新跑受影響模組的測試或最小手動流程，並在 PR 註明衝突已處理、介面是否有改變。

### 尚未合併的功能想放棄或重做

不要刪掉遠端分支或硬 reset，先把目前進度保留成 commit，然後在 PR 說明停止原因。若只是想暫時收起本機變更：

```bash
git stash push -m "wip: describe current work"
# 之後恢復
git stash pop
```

若功能分支已經錯得很嚴重，找整合者確認後重新從 `main` 建一條新分支；舊分支保留到確認不再需要為止。

### main 已經壞掉

立刻在群組公告「main 壞掉」、指出最後一個可疑 PR 與錯誤訊息，並由當班整合者建立 `fix/...` 分支處理。不要直接在 `main` 修改，也不要急著改寫公開歷史。修復 PR 要描述怎麼重現、怎麼驗證修好。

## Demo 前節奏

### 距離 Demo 3–4 小時：功能凍結

- 不再開大型功能；只接受能強化主流程、可在短時間驗證的小改動。
- 整合者建立並維護一條確定可展示的 `main`，每次 merge 都跑 smoke test。
- 將 Demo 使用的輸入、預期推薦結果、備用假資料與啟動指令寫入 README 或團隊筆記。

### 距離 Demo 1 小時：只修阻塞問題

- 只合併會讓 Demo 無法完成的修復，例如啟動失敗、核心 API 500、商品無法顯示。
- 其他想法、視覺微調與非必要重構都記下來，不再冒險合併。
- 每個人從 `main` 重新拉一次，在自己的裝置做至少一次 Demo 演練。

## 不要做

- 不直接 push 到 `main`，也不 force-push `main`。
- 不提交 `.env`、API key、token 或使用者資料；曾誤提交 key 時立刻撤銷／輪替該 key，不能只刪除檔案。
- 不未溝通就改 API schema、共用設定或別人主要負責的模組。
- 不把尚未測過的大型合併、重構或套件升級留到 Demo 前。
- 不用 `git reset --hard`、`git push --force` 或 `--ours`／`--theirs` 當作快速解 conflict 的預設作法。
- 不讓 PR 長時間沒人回覆；輪值整合者無法處理時，應在群組交接給下一位。

## 兩個情境範例

### 情境一：一般功能 PR

C 在 `feature/product-rerank` 完成推薦排序，提交測試並推送。C 開 PR，附上推薦 JSON 範例與測試結果。輪值整合者確認 B 的偏好欄位能被 C 使用、E 的 API 能回傳推薦結果，合併後啟動後端並呼叫一次推薦 endpoint。確認無誤後在群組公告「推薦排序已進 main」，A 就能從最新 `main` 串接畫面。

### 情境二：共用檔案衝突

B 與 E 同時修改 `backend/main.py`：B 加入新的偏好欄位，E 正在新增 endpoint。B 不直接選擇任一版本，而是通知當班整合者，先對齊 request/response JSON，再 rebase 並手動保留兩邊程式。B 跑 API 的最小測試，更新 PR 說明 schema 已對齊；整合者確認前端不會因欄位改名失效後才合併。
