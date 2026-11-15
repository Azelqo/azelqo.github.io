# NotionからAzelqoへ記事を同期する設定

Notionを記事の下書き・メモ帳として使い、Statusを「公開」にした記事だけをAzelqoへ自動反映します。10分ごとに同期し、GitHub Pagesの既存Hugoデプロイを通じて公開します。

## 1. 作成済みのNotionデータベース

データベース「Azelqo記事メモ」は作成済みです。 [Notionで開く](https://app.notion.com/p/419d04e1ae7c81d2a93ed032a131c9fe)。プロパティは以下の構成です。

| プロパティ | 種類 | 用途 |
|---|---|---|
| Title | タイトル | 記事タイトル |
| Status | セレクト | 「メモ」「下書き」「公開」 |
| Date | 日付 | 公開日 |
| Slug | テキスト | URL末尾。空欄ならタイトルから自動生成 |
| Description | テキスト | 検索結果などに使う短い説明 |
| Categories | マルチセレクト | カテゴリー |
| Tags | マルチセレクト | タグ |

本文はデータベースの各行を開いたページ本文に書きます。Statusが「公開」以外ならサイトには出ません。

## 2. Notionインテグレーションを作る

1. https://www.notion.so/profile/integrations を開く
2. 新しい内部インテグレーションを作成し、名前を「Azelqo Sync」にする
3. コンテンツ読み取り権限を有効にする
4. 表示されたInternal Integration Secretをコピーする
5. 作成した記事データベースの「…」→「コネクト」から「Azelqo Sync」を追加する
6. このデータベースへのインテグレーション接続を許可します。

**トークンはチャットに貼らず、GitHub Secretsに直接登録してください。**

## 3. GitHub Secretsを登録する

リポジトリ https://github.com/Azelqo/azelqo.github.io/settings/secrets/actions を開き、Repository secretsに次の2つを追加します。

- `NOTION_TOKEN`: NotionのInternal Integration Secret
- `NOTION_DATA_SOURCE_ID`: 記事データベースのデータソースID（`419d04e1-ae7c-81ee-8edc-000ba566f43a`）

## 4. 動作確認

GitHubのActionsから「Sync Notion notes」を開き、Run workflowを実行します。成功すると `content/notion/` にMarkdown記事が作成され、その後既存のDeploy Hugo site to Pagesが動いてサイトに反映されます。

以降は10分ごとに自動同期します。NotionでStatusを「メモ」や「下書き」に戻すと、同期管理対象の記事ファイルはサイトから取り除かれます。

## 補足

- 既存の `content/posts/` の記事やHugo Stackのデザインは変更しません。
- 同期記事は `content/notion/` の中だけで管理します。
- 同期はNotionからGitHubへの一方向です。サイト上の編集内容がNotionへ戻ることはありません。
- Notionの画像ブロックはURL参照で出力します。Notion側のファイルURLは期限付きの場合があるため、長期公開用画像は別途サイト側へ置く運用がおすすめです。
