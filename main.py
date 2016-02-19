#!/usr/bin/env python
# coding: utf-8

from wxbot import *

def auto_reply(msg):
    body = {'key': '1d2678880f734bc0a23734ace8aec5b1', 'info':msg}
    r = requests.post("http://www.tuling123.com/openapi/api", data=body)
    resp = json.loads(r.text)
    if resp['code'] == 100000:
        return resp['text']
    else:
        return None

class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 5:
            ans = auto_reply(msg['content'])
            self.send_msg(msg['user_name'], ans)

def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.run()

if __name__ == '__main__':
    main()
