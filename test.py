#!/usr/bin/env python
# coding: utf-8

import time
from wxbot import *

class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 5 and msg['user_type'] == 'contact':
            self.send_msg_by_uid('hi', msg['user_id'])
'''
    def schedule(self):
        self.send_msg('tb', 'schedule')
        time.sleep(1)
'''

def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.conf['qr'] = 'png'
    bot.run()

if __name__ == '__main__':
    main()
