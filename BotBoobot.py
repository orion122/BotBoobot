from flask import Flask, request
import telegram, config, pymysql, datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

bot = telegram.Bot(config.TOKEN)
app = Flask(__name__)
context = (config.CERT, config.CERT_KEY)

#========================================================COMMANDS=======================================================
def help(update, inChat=False):
    if inChat == False:
        update.message.reply_text('/help - Помощь\n/about - Обо мне')
        update.message.reply_text('Для того чтобы выбрать чат, в который ты хочешь отправить анонимное сообщение (только текстовое сообщение), '
                                  'отправь мне такое сообщение *chat название чата*. '
                                  '(Полное название чата вводить необязательно, достаточно первых нескольких символов)',
                                   parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        update.message.reply_text('Для того чтобы выбрать чат, в который ты хочешь отправить анонимное сообщение (только текстовое сообщение), '
                                  'отправь мне личку такое сообщение *chat название чата*. '
                                  '(Полное название чата вводить необязательно, достаточно первых нескольких символов)',
                                   parse_mode=telegram.ParseMode.MARKDOWN)

def about(update, inChat=False):
    if inChat == False:
        update.message.reply_text('Я могу отправлять анонимные сообщения в чаты (только текстовые сообщения)')
    else:
        update.message.reply_text('Я могу отправлять анонимные сообщения в этот и некоторые другие чаты (только текстовые сообщения). Подробности в личке ;)')

#========================================================DATABASE=======================================================
def getConnection():
	return pymysql.connect(host='localhost', port=3306, user='boobot', passwd=config.DBPSWD, db='boobot', charset='utf8mb4')

# Add record into table chats
def dbAddChats(chatID, chatName, userID):
    conn = getConnection()
    cur = conn.cursor()
    query = "INSERT INTO chats(chatid, chatname, added, time) VALUES(%s, %s, %s, NOW())"
    cur.execute(query, (chatID, chatName, userID))
    conn.commit()
    cur.close()
    conn.close()

# Remove record from table chats
def dbRemoveChats(chatID):
    conn = getConnection()
    cur = conn.cursor()
    query = "DELETE FROM chats WHERE chatid=%s"
    cur.execute(query, (chatID))
    conn.commit()
    cur.close()
    conn.close()

# Search chat's id where chatname LIKE %chatName%
def dbSearchChatID(chatName):
    conn = getConnection()
    cur = conn.cursor()
    query = "SELECT chatid, chatName from chats WHERE chatname LIKE %s"
    cur.execute(query, ("%" + chatName + "%"))
    result = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return result

# INSERT or UPDATE record into table msg
def dbAddMsg(userid, chatid):
    conn = getConnection()
    cur = conn.cursor()
    query_check = "SELECT * FROM msg WHERE userid={}".format(userid)
    cur.execute(query_check)
    result = cur.fetchall()
    if not result:
         query = "INSERT INTO msg(userid, chatid) VALUES(%s, %s)"
         cur.execute(query, (userid, chatid))
         conn.commit()
         cur.close()
         conn.close()
    else:
         query = "UPDATE msg SET chatid=%s WHERE userid=%s"
         cur.execute(query, (chatid, userid))
         conn.commit()
         cur.close()
         conn.close()

# SEARCH recored in table msg
def dbSearchMsg(userid):
    conn = getConnection()
    cur = conn.cursor()
    query = "SELECT * from msg WHERE userid=%s"
    cur.execute(query, (userid))
    result = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return result

# UPDATE time in table msg
def dbUpdateTime(userid):
    conn = getConnection()
    cur = conn.cursor()
    query = "UPDATE msg SET time=NOW() WHERE userid=%s"
    cur.execute(query, (userid))
    result = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return result

# If select chat by InlineKeyboardButton, but bot was deletedcfrom this chat
def dbCheckBotIsMember(chatid):
    conn = getConnection()
    cur = conn.cursor()
    query = "SELECT * FROM chats WHERE chatid=%s"
    cur.execute(query, (chatid))
    result = cur.fetchall()
    cur.close()
    conn.close()
    if result:
        return True
    return False
#=======================================================================================================================
# Chats where user is member
def whereMember(chats, userid):
    here_member = []
    for chat in chats:
       if (bot.get_chat_member(chat[0], userid).status) != 'left':
           here_member.append(chat)
    return here_member

# Select chat among chats
def selectChat(chats, userid):
    keyboard= []
    for chat in chats:
        tmp = [InlineKeyboardButton(chat[1], callback_data='choosenCHAT{}'.format(str(chat[0])))]
        keyboard.append(tmp)
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.sendMessage(chat_id=userid, text='Нашел несколько чатов с похожим названием. Выбери нужный', reply_markup=reply_markup)


def compareTimes(last_msg_time):
    dt = (datetime.datetime.now() - datetime.datetime.strptime(str(last_msg_time), '%Y-%m-%d %H:%M:%S')).total_seconds() / 60
    return dt


def checkSelectedChat(update, userID, chatID=0):
    if (chatID != 0):
        if dbCheckBotIsMember(chatID):
            dbAddMsg(userID, chatID)
            bot.sendMessage(chat_id=userID, text='OK! Теперь чтобы отправить анонимное сообщение в выбранный ранее чат, '
                                                 'отправь мне такое сообщение *msg текст анонимного сообщения*', 
                            parse_mode=telegram.ParseMode.MARKDOWN)
            return
        else:
            bot.sendMessage(chat_id=userID, text='Меня удалили из этого чата')
            return

    chatName = update.message.text[5:]
    found_chats = dbSearchChatID(chatName)
    chats_where_is_member = whereMember(found_chats, userID)

    if (len(chats_where_is_member) > 1):
        selectChat(chats_where_is_member, userID)
    elif (len(chats_where_is_member) == 1):
        bot.sendMessage(chat_id=userID, text='Сообщение будет отправлено в чат: *{}*\n'
                                             'Теперь отправь мне такое сообщение: *msg текст анонимного сообщения*'.format(chats_where_is_member[0][1]), 
                        parse_mode=telegram.ParseMode.MARKDOWN)
        chatid_anon_msg = chats_where_is_member[0][0]
        dbAddMsg(userID, chatid_anon_msg)
    else:
        bot.sendMessage(chat_id=userID, text='Чат с таким названием не найден. '
                                             'Причин может быть несколько:\n1) Меня не добавили в этот чат\n2) Ты не состоишь в этом чате\n3) Ты немного ошибся в названии чата\n4) Название чата изменилось (в этом случае меня нужно удалить из чата и добавить заново)\n\nДобавь меня в чат, в который хочешь отправлять анонимные сообщения или попроси админа чата, чтобы добавил меня.')

def checkAnonMsg(update, userID):
    msg = update.message.text[4:]
    result_msg = dbSearchMsg(userID)
    if result_msg:
        if result_msg[0][2] == None:
            bot.sendMessage(chat_id=int(result_msg[0][1]), text=msg)
            dbUpdateTime(userID)
        else:
            compare_times = compareTimes(result_msg[0][2])
            if compare_times >= config.ALLOWED_TIME:
                bot.sendMessage(chat_id=int(result_msg[0][1]), text=msg)
                dbUpdateTime(userID)
            else:
                allowed_dt = config.ALLOWED_TIME - compare_times
                bot.sendMessage(chat_id=userID,
                                text='Сообщение не будет отправлено из-за ограничений. '
                                     'Отправьте сообщение заново через *{}* секунд'.format(str(allowed_dt*60)[:str(allowed_dt*60).find('.')]), 
                                parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        bot.sendMessage(chat_id=userID,
                        text="Для начала выбери чат. Чтобы выбрать чат отправь мне такое сообщение: *chat название чата*'. "
                             "(Полное название чата вводить необязательно, достаточно первых нескольких символов", 
                        parse_mode=telegram.ParseMode.MARKDOWN)


def checkUpdateMessage(update):
    message = update.message.text
    userID = update.message.from_user.id
    if len(message) > 512:
        update.message.reply_text('Сообщение слишком длинное!')
    elif "%" in message:
        update.message.reply_text('Давай без %')
    elif message in ["/start", "/help"]:
        help(update)
    elif message in ["/help@BotBoobot"]:
        help(update, inChat=True)
    elif message in ["/about"]:
        about(update)
    elif message in ["/about@BotBoobot"]:
        about(update, inChat=True)
    elif (len(message) > 5) and (message.lower().startswith('chat ')):
        checkSelectedChat(update, userID)
    elif (len(message) > 4) and (message.lower().startswith('msg ')):
        checkAnonMsg(update, userID)
    else:
        update.message.reply_text('Неизвестная команда. Перечитай пожалуйста внимательно инструкцию. Нажми на /help')

def initAddToChat(update):
    chatID = update.message.chat.id
    chatName = update.message.chat.title
    userID = update.message.from_user.id
    dbAddChats(chatID, chatName, userID)

def initRemoveFromChat(update):
    chatID = update.message.chat.id
    dbRemoveChats(chatID)

def checkUpdate(update):
    if update.channel_post:
        print(update.channel_post)
    elif hasattr(update.message, 'text') and (len(update.message.text) > 0):
        checkUpdateMessage(update)
    elif hasattr(update.message, 'new_chat_member') and (update.message.new_chat_member != None) and (
        update.message.new_chat_member.username == 'BotBoobot'):
        initAddToChat(update)
        bot.sendMessage(chat_id=update.message.chat.id,
                        text='Привет всем! Я могу отправлять анонимные сообщения в этот чат и некоторые другие. '
                             'Для начала напиши мне в личку. Я расскажу как мной пользоваться ;)')
    elif hasattr(update.message, 'left_chat_member') and (update.message.left_chat_member != None) and (
        update.message.left_chat_member.username == 'BotBoobot'):
        initRemoveFromChat(update)
    elif hasattr(update.callback_query, 'data'):
        checkSelectedChat(update, update.callback_query.from_user.id, update.callback_query.data[11:])

#=======================================================================================================================
@app.route('/' + config.TOKEN, methods=['POST'])
def webhook():
    update = telegram.update.Update.de_json(request.get_json(force=True), bot)
    checkUpdate(update)
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
