from flask import Flask, render_template, request, redirect, url_for
import requests
import hashlib
import json
import logging.config, yaml
import random
from datetime import datetime

app = Flask(__name__)

SHOP_ID = 5
SECRET = "SecretKey01"
PAYWAY = "payeer_rub"  # (для invoice)


logging.config.dictConfig(yaml.load(open('logging.cfg'),Loader=yaml.FullLoader))
logger = logging.getLogger('file')


def signage(keys):
    """amount, currency, shop_id, shop_order_id, secretKey"""
    keys = [str(x) for x in keys]
    stringusik = ':'.join(keys)
    return hashlib.sha256(f'{stringusik}{SECRET}'.encode('utf-8')).hexdigest()


@app.route('/')
def hello():
    return render_template('index.html')


@app.route("/test", methods=['GET', 'POST'])
def test():
    select = request.form.get('currency')
    amount = request.form.get('amount')
    if not amount or amount == 0:
        return render_template('index.html', message="Please enter a valid amount")
    currency = request.form.get('currency')

    random.seed(datetime.now())
    shop_order_id = random.randint(0,100000)

    #shop_order_id = request.form.get('shop_order_id')
    shop_currency = request.args.get('shop_currency') or currency
    description = request.form.get('description') or ''
    if select == '978':
        '''Euro'''
        keys_sorted = [amount, currency, SHOP_ID, shop_order_id]
        sign = signage(keys_sorted)
        data = {
            "shop_id": SHOP_ID,
            "amount": amount,
            "currency": currency,
            "shop_order_id": shop_order_id,
            "sign": sign,
            "description": description
        }

        try:
            return redirect(url_for('.pay', data=data))
        except Exception as e:
            print(e)
            return render_template('index.html')

    elif select == '840':
        """Dollar"""
        keys_sorted = [currency, amount, shop_currency, SHOP_ID, shop_order_id]
        sign = signage(keys_sorted)
        data = {
            "shop_id": SHOP_ID,
            "amount": amount,
            "currency": currency,
            "shop_order_id": shop_order_id,
            "sign": sign,
            "shop_currency": shop_currency,
            "description": description
        }

        try:
            return redirect(url_for('.bill', data=data))
        except Exception as e:
            logger.error(f'Billing unsuccessful: {e}')
            return render_template('index.html', message="Request failed")

    elif select == "643":
        """Ruble"""
        keys = [amount, currency, PAYWAY, SHOP_ID, shop_order_id]
        sign = signage(keys)
        data = {
            "shop_id": SHOP_ID,
            "amount": amount,
            "currency": currency,
            "shop_order_id": shop_order_id,
            "sign": sign,
            "payway": PAYWAY,
            "description": description
        }
        try:
            return redirect(url_for('.invoice', data=data))
        except Exception as e:
            logger.error(f'Invoicing unsuccessful: {e}')
            return render_template('index.html', message="Request failed")


@app.route('/pay', methods=['GET', 'POST'])
def pay():
    link = "https://pay.piastrix.com/ru/pay" if str(request.accept_languages)[:2] == 'ru' \
        else "https://pay.piastrix.com/en/pay"

    source = {'data': json.loads(request.args.get('data').replace("'", "\"")), 'url': link}
    # hmm
    logger.info(f"Покупка /pay: Валюта {source['data']['currency']}, Сумма {source['data']['amount']}, "
                f"Описание '{source['data'].get('description')}', ORDER_ID {source['data']['shop_order_id']}")

    return render_template('pay.html', source=source)


@app.route('/bill', methods=['GET','POST'])
def bill():
    headers = {'Content-Type': 'application/json'}
    data = json.loads(request.args.get('data').replace("'", "\""))

    rq = requests.post(
        url="https://core.piastrix.com/bill/create",
        json={
            "shop_amount": data['amount'],
            "payer_currency": data['currency'],
            "shop_currency": data['shop_currency'],
            "shop_id": SHOP_ID,
            "shop_order_id": data['shop_order_id'],
            "sign": data['sign'],
            "description": data.get('description')
        },
        headers=headers
    )

    r = rq.json()
    if r['message'] == "Ok":
        logger.info(f"Покупка /billing: Валюта {data['currency']}, Сумма {data['amount']}, "
                    f"Описание '{data.get('description')}', ORDER_ID {data['shop_order_id']}")
        return redirect(r['data']['url'])

    logger.error(f'Billing unsuccessful: Error_code:{r["error_code"]}, Message: {r["message"]}')
    return render_template('index.html')


@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    link = 'https://core.piastrix.com/invoice/create'
    data = json.loads(request.args.get('data').replace("'", "\""))
    headers = {'Content-Type': 'application/json'}

    rq = requests.post(
        url=link,
        json={
            "amount": data['amount'],
            "currency": data['currency'],
            "shop_id": SHOP_ID,
            "shop_order_id": data['shop_order_id'],
            "payway": PAYWAY,
            "sign": data['sign'],
            "description": data.get('description')
        },
        headers=headers
        )
    r = rq.json()

    if not r['result']:
        logger.error(f'Invoice unsuccessful: Error_code:{r["error_code"]}, Message: {r["message"]}')
        return render_template('index.html', message="Request failed")

    source = {
        'data': r['data']['data'],
        'url': r['data']['url'],
        'method': r['data']['method']
    }
    logger.info(f"Покупка /invoice: Валюта {data['currency']}, Сумма {data['amount']},"
                f"Описание '{data.get('description')}', ORDER_ID {data['shop_order_id']}")
    return render_template('invoice.html', source=source)


if __name__ == '__main__':
    app.run(debug=True)
