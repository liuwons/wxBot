#!/usr/bin/env python
# coding: utf-8

from wxbot import *

class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 5:
            self.send_msg(msg['user_name'], 'hi')

def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.run()

if __name__ == '__main__':
    main()
