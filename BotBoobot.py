from flask import Flask, request

import telegram, config

bot = telegram.Bot(config.TOKEN)
app = Flask(__name__)
context = (config.CERT, config.CERT_KEY)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/' + config.TOKEN, methods=['POST'])
def webhook():
    update = telegram.update.Update.de_json(request.get_json(force=True), bot)
    bot.sendMessage(chat_id=update.message.chat_id, text='Hello, there')

    return 'OK'


def setWebhook():
    bot.setWebhook(webhook_url='https://%s:%s/%s' % (config.HOST, config.PORT, config.TOKEN),
                   certificate=open(config.CERT, 'rb'))

if __name__ == '__main__':
    setWebhook()

    app.run(host='0.0.0.0',
            port=config.PORT,
            ssl_context=context,
            debug=True)