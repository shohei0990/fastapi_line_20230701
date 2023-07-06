import cv2
import os
import json
import tempfile
from fastapi import FastAPI, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import List
from linebot import (LineBotApi, WebhookHandler, WebhookParser)
from linebot.models import (MessageEvent, ImageMessage, TextMessage, TextSendMessage,)
from linebot.exceptions import (InvalidSignatureError)
from pyzbar import pyzbar
import urllib.request
from urllib.error import HTTPError

#商品名を整形するために必要なライブラリ
import openai
import requests

#スプレッドシートを扱うために必要なライブラリ
import gspread
from google.oauth2.service_account import Credentials

# FastAPIをインスタンス化
app = FastAPI()
#初期化
product_info = None

# LINE Botのシークレットとアクセストークン
# LINE Bot APIとWebhookHandlerをインスタンス化します。
# LINE Bot APIは、LINEのメッセージを送受信するためのAPIを提供します。
# WebhookHandlerは、Webhookからのイベントを処理するためのクラスです。
CHANNEL_SECRET = ""
CHANNEL_ACCESS_TOKEN = ""
# Yahoo Shopping APIのクライアントID
client_id = ""
#openAI API key
openai.api_key = ""
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
    
#############################################################
# バーコードの検索結果から商品名とメーカー名を推定
#############################################################
def list_to_name(info):
    # 設定
    info_txt = ', '.join(info)
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
            {"role": "system", "content": "下記のリストはある1つのバーコードから取得した商品名のリストデータです。セット商品等があるため複数の表現方法がなされています。このリストから共通性を見出し、メーカー名、商品名をただ一つのみ抽出してください。応答は辞書型で「メーカー名」と「商品名」をキーとし、抽出したものを値としてください。補足情報や説明は不要です。"},
            {"role": "user", "content": info_txt}
        ]
    )
    # ChatGPTの回答を出力
    res = response["choices"][0]["message"]["content"]
    res = res.replace( '\n' , '' )
    res = json.loads(res)
    return res

###################################################################
# スプシの参照
###################################################################
def read_DB():
    # 決まり文句
    scope = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
    # ダウンロードしたjsonファイル名をクレデンシャル変数に設定。
    credentials = Credentials.from_service_account_file("stokify-391613-cfe2b43a3751.json", scopes=scope)
    # OAuth2の資格情報を使用してGoogle APIにログイン。
    gc = gspread.authorize(credentials)
    # スプレッドシートIDを変数に格納する。
    SPREADSHEET_KEY = '1d6Sdymm4r2d70N5t2f_u1RxCiDJ6Tm7s0TasKllXOTU'
    # スプレッドシート（ブック）を開く
    workbook = gc.open_by_key(SPREADSHEET_KEY)
    return workbook

######################################################################
# DB上からバーコードデータ検索
######################################################################
def search_DB(barcode, id ):
    # スプレッドシートを開く関数を呼び出し
    workbook = read_DB()
    # シートの一覧を取得する。（リスト形式）
    worksheets = workbook.worksheets()
    # StockifyDBのシートを開く（商品一覧DB的扱い）
    worksheet = workbook.worksheet('UserDB')

    # B列の値をすべて取得
    barcode_list = worksheet.col_values(2)
    # B列に対応するバーコードデータがあるかどうかを検索
    if barcode in barcode_list:
        # 対応するB列の値を取得
        row_index = barcode_list.index(barcode) + 1  # 行番号は1から始まるので+1する
        maker = worksheet.cell(row_index, 3).value
        name = worksheet.cell(row_index, 4).value
        return maker,name
    else:
        # バーコードから商品を検索する関数を呼び出してinfoに保存
        info = barcode_search(barcode)
        #商品名を一意に決める関数を呼び出して、infoを渡して、resに保存
        res = list_to_name(info)
        maker = res['メーカー名']
        name =  res['商品名']
        # シートのすべての値を取得
        all_values = worksheet.get_all_values()
        # 最終行を取得
        last_row = len(all_values)
        
        # ここから新たに取得した商品データをスプレッドシートに記述
        ##################################################################
        # A列にIDを付与する
        worksheet.update_cell(last_row + 1, 1, id)
        # B列にBarcodeを記録する
        worksheet.update_cell(last_row + 1, 2, barcode)
        # B列にBarcodeを記録する
        worksheet.update_cell(last_row + 1, 3, maker)
        # B列にBarcodeを記録する
        worksheet.update_cell(last_row + 1, 4, name)
        ##################################################################
        return maker,name
    
def get_user_inventory(user_id):
    workbook = read_DB()
    worksheet = workbook.worksheet('UserDB')
    
    # ID列の値をすべて取得
    id_list = worksheet.col_values(1)
    
    # 対応するIDが存在する行の商品名を取得
    items = []
    for i, id_value in enumerate(id_list):
        if id_value == user_id:
            row_index = i + 1  # 行番号は1から始まるので+1する
            item_name = worksheet.cell(row_index, 4).value
            items.append(item_name)
    
    return "\n".join(items)

# テキストメッセージのハンドリング
def handle_text_message(event):
    text = event["message"]["text"]

    # ユーザーが「ざいことうろく」を入力した場合
    if text == "ざいことうろく":
        reply_message = "最初に、商品のバーコード写真を投稿するか カメラを撮影してください!"

         # ユーザーが「ざいこかくにん」を入力した場合
    elif text == "ざいこかくにん":
        # ユーザーIDの取得
        user_id = event["source"]["userId"]
        # ユーザーの在庫リストを取得
        user_inventory = get_user_inventory(user_id)
        reply_message = "こちらがあなたの在庫リストです:\n" + user_inventory

    # ユーザーが「かいものリスト」を入力した場合
    elif text == "かいものリスト":
        reply_message = "あなたのかいものリストはこちらです!"

    # その他のテキストメッセージにはそのまま応答します
    else:
        # ユーザーIDの取得
        user_id = event["source"]["userId"]
        reply_message = "User ID: " + user_id + "\nMessage: " + text

    # 応答メッセージを送る
    line_bot_api.reply_message(
        event["replyToken"],
        TextSendMessage(text=reply_message))
    

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
                    maker, name = search_DB(barcode_number, user_id )
                    # 商品情報をリプライとして送る：reply the found product info
                    line_bot_api.reply_message(
                        event["replyToken"],
                        TextSendMessage(text="メーカー名:"+str(maker) + "\n商品名:" + str(name)))
                
                else:
                    # # バーコードが読み取れなかった場合、エラーメッセージをリプライとして送る　if the barcode is not found or not readable, then reply an error message
                    line_bot_api.reply_message(
                        event["replyToken"],
                        TextSendMessage(text="バーコードを読み取ることができませんでした。"))
                

            elif event["message"]["type"] == "text":
                #text = event["message"]["text"]
                handle_text_message(event)
   
    return {"status": "OK"}

#if __name__ == "__main__":
#    import uvicorn
#    uvicorn.run(app, host="127.0.
