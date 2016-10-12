#!/usr/bin/env python
# coding: utf-8

from wxbot import *


class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            self.send_msg_by_uid(u'hi', msg['user']['id'])
            self.send_img_msg_by_uid("img/1.png", msg['user']['id'])
            self.send_file_msg_by_uid("img/1.png", msg['user']['id'])

    def schedule(self):
        self.send_msg(u'测试群', u'测试')
        self.send_img_msg_by_uid("img/1.png", self.get_user_id(u"测试群"))
        self.send_file_msg_by_uid("img/1.png", self.get_user_id(u"测试群"))
        time.sleep(5)


def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.SCHEDULE_INTV = 20
    bot.conf['qr'] = 'png'
    bot.run()


if __name__ == '__main__':
    main()
