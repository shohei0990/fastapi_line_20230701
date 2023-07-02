# fastapi_line_20230701
## LINE developer × FAST API 連携 Google Cloud Run でのサーバー動作

・main.py 機能<br>
　LINE連携<br>
　チャットのオウム返し<br>
　バーコード画像読み取り・商品検索・商品情報FB<br>

・20230701追加<br>
　LINEIDの取得<br>
　リッチメニュー追加<br>
　リッチメニューのテキスト返答に対するコメント返信追加<br>


---------------------------------------------------------------
以下はDockerとGoogleCloudRunのデプロイ方法のやり方<br>

Docker参考<br>
・Docker 参考リンク:Dockerで"Hello world"<br>


  https://www.utakata.work/entry/docker-python-tutorial/1


## Dockerでサンプルファイルを動かす。<br>

1.ターミナル起動して以下コマンド入力<br>

cd C:\Users\redgr\workspace_docker\Dockerfileが入ったフォルダ名　<br>
docker build -t fastapi4 .　<br>
docker run -p 8000:8000 fastapi4　 <br>

※ <br> fastapi4はDockerのimageファイル名　 <br>
※ まずはローカルで確認だがLINEdeveloperだと、ローカルでの確認ができない。(難しい..!)

## Google Cloud run 確認

・参考リンク<br>
https://qiita.com/massie_g/items/5a9ce514eaa7c460b5e3　　<br>

https://laid-back-scientist.com/cloud-run-python　<br>



・以下 コマンド<br>
gcloud components update<br>
gcloud components install beta <br>

<認証><br>
gcloud auth login<br>
gcloud auth configure-docker<br>

<デフォルトのプロジェクトとリージョンの設定><br>
<プロジェクトID（ここでは cloud-run-0001-XXXX）><br>
gcloud config set project cloud-run-0001-XXXX<br>
gcloud config set run/region us-central1<br>

<サービスの名前（ここでは fastapi07）を使う場合には次のようにビルド> <br>
gcloud builds submit --project  cloud-run-0001-XXXX --tag gcr.io/cloud-run-0001-XXXX/fastapi07<br>

<デプロイ> <br>
gcloud run deploy --project cloud-run-0001-XXXX --image gcr.io/cloud-run-0001-XXXX/fastapi07<br>
<br>
これでURLが発行されて動作の確認ができるようになる。ちなみによくDocker時のメモリ設定がimageファイルよりも大きくないと動かないのでGooglrCloudRunにて調整する。

<コード更新> <br>
gcloud builds submit --project cloud-run-0001-XXXX --tag gcr.io/cloud-run-0001-XXXX/fastapi07:v2<br>

< 更新デプロイ>　〇〇〇はサービス名 <br>
gcloud run deploy 〇〇〇--project cloud-run-0001-XXXX --image gcr.io/cloud-run-0001-XXXX/fastapi07:v2<br>


※　LINEに上げるときには、URLの名前にアンダーバーなどあるとはじかれる。<br>

※ もしサーバーをアイドル状態にしておきたい場合<br>
　https://sleepless-se.net/2021/04/19/keep-cloud-run-always-warm/

