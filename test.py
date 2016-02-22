#!/usr/bin/env python
# coding: utf-8

import time
from wxbot import *

class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 5:
            self.send_msg(msg['user_name'], 'hi')
'''
    def schedule(self):
        self.send_msg('tb', 'schedule')
        time.sleep(1)
'''

def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.run()

if __name__ == '__main__':
    main()
