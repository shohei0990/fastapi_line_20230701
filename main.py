import cv2
import os
import json
import tempfile
import uvicorn
import urllib.request
from typing import List
from urllib.error import HTTPError
from fastapi import FastAPI, Depends, Request, HTTPException
from pydantic import BaseModel
from linebot import (LineBotApi, WebhookHandler, WebhookParser)
from linebot.models import (MessageEvent, ImageMessage, TextMessage, TextSendMessage,)
from linebot.exceptions import (InvalidSignatureError)
from pyzbar import pyzbar


# FastAPIをインスタンス化
app = FastAPI()

# LINE Botのシークレットとアクセストークン
CHANNEL_SECRET = "LIEN developerのシークレット"
CHANNEL_ACCESS_TOKEN = "LIEN developerのアクセストークン"
# Yahoo Shopping APIのクライアントID
client_id = "YahooAPIのID"

# LINE Bot APIを使うためのクライアントのインスタンス化
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# WebhookからのPOSTデータの構造を定義
# WebhookからのPOSTデータの構造を定義します。LINEからのWebhookは一連のイベントを含んでいます。
# これらのイベントは、ユーザーからのメッセージ、ユーザーが友達になった通知、など様々なものがあります。
class LineWebhook(BaseModel):
    destination: str
    events: List[dict]

# 画像からバーコードを読み取る関数
def read_barcode(image_path):
    # 画像を読み込む
    image = cv2.imread(image_path)
    # 画像をグレースケールに変換
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # バーコードを検出
    barcodes = pyzbar.decode(gray)

    # バーコードが見つかった場合、番号を返す
    if len(barcodes) > 0:
        barcode = barcodes[0]
        barcode_data = barcode.data.decode("utf-8")
        return barcode_data
    # バーコードが見つからない場合はNoneを返す
    return None


# バーコード番号から商品を検索する関数
def barcode_search(code):
     # Yahoo Shopping APIへのリクエストURL
    url = 'https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch?appid={0}&jan_code={1}'.format(client_id, code)
    try:
        # Yahoo Shopping APIへのリクエストとレスポンスの受け取り
        response_json = urllib.request.urlopen(url).read()
    #エラーにより分岐
    except HTTPError as e:
        if e.code == 400:
            # バーコードから商品が見つからなかった時の処理
            # HTTPエラー400の場合の処理（バーコードから商品が見つからなかった時）
            print("バーコードから商品が見つかりませんでした。")
            return None
        else:
            # その他のHTTPエラーの場合の処理
            print("HTTPエラーが発生しました。エラーコード:", e.code)
            raise
    # レスポンス（JSON）をPythonの辞書に変換
    response = json.loads(response_json)
    products_info = []
    if len(response) > 0:
        #hitsから、検索結果数をlengthで取得し、すべての名称を取得してくる
        length = len(response['hits'])
        print(length)
        for i in range(0,length):
            # レスポンスから商品情報をと取り出す。
            product_info = (response['hits'][i]['name'])
            products_info.append(product_info)
        return products_info
    else:
        err_msg = "バーコードから商品が見つかりませんでした。"
        return err_msg
    
# テキストメッセージのハンドリング
def handle_text_message(event):
    text = event["message"]["text"]

    # ユーザーが「ざいことうろく」を入力した場合
    if text == "ざいことうろく":
        reply_message = "最初に、商品のバーコード写真を投稿するか カメラを撮影してください"

    # ユーザーが「ざいこかくにん」を入力した場合
    elif text == "ざいこかくにん":
        reply_message = "こちらがのざいこリストはこちらです"

    # ユーザーが「かいものリスト」を入力した場合
    elif text == "かいものリスト":
        reply_message = "あなたのかいものリストはこちらです"

    # その他のテキストメッセージにはそのまま応答します
    else:
        # ユーザーIDの取得
        user_id = event["source"]["userId"]
        reply_message = "User ID: " + user_id + "\nMessage: " + text

    # 応答メッセージを送る
    line_bot_api.reply_message(
        event["replyToken"],
        TextSendMessage(text=reply_message)
    )

# /callbackへのPOSTリクエストを処理するルートを定義
@app.post("/callback/")
async def callback(webhook_data: LineWebhook):
    for event in webhook_data.events:
        if event["type"] == "message":

            # LINEサーバーから画像データをダウンロード
            if event["message"]["type"] == "image":
                # LINEサーバーから画像データをダウンロード：download image data from line server
                message_content = line_bot_api.get_message_content(event["message"]["id"])
                # 画像データを一時ファイルに保存：save the image data to a temp file
                image_temp = tempfile.NamedTemporaryFile(delete=False)
                for chunk in message_content.iter_content():
                    image_temp.write(chunk)
                image_temp.close()
                # # 画像からバーコードを読み取る：read the barcode from the image
                barcode_number = read_barcode(image_temp.name)

                # ユーザーIDの取得
                user_id = event["source"]["userId"]

                if barcode_number:
                    # バーコードが正常に読み取れた場合、その番号から商品を検索　if the barcode is successfully read, then search the product
                    product_info = barcode_search(barcode_number)
                    # 商品情報をリプライとして送る：reply the found product info
                    line_bot_api.reply_message(
                        event["replyToken"],
                        TextSendMessage(text=str(product_info)))
                
                else:
                    # # バーコードが読み取れなかった場合、エラーメッセージをリプライとして送る　if the barcode is not found or not readable, then reply an error message
                    line_bot_api.reply_message(
                        event["replyToken"],
                        TextSendMessage(text="バーコードを読み取ることができませんでした。"))
                

            elif event["message"]["type"] == "text":
                handle_text_message(event)
                
   
    return {"status": "OK"}
