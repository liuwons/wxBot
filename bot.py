#!/usr/bin/env python
# coding: utf-8

from wxbot import *
import ConfigParser
import json


class TulingWXBot(WXBot):
    def __init__(self):
        WXBot.__init__(self)

        self.tuling_key = ""
        self.robot_switch = True

        try:
            cf = ConfigParser.ConfigParser()
            cf.read('conf.ini')
            self.tuling_key = cf.get('main', 'key')
        except Exception:
            pass
        print 'tuling_key:', self.tuling_key

    def tuling_auto_reply(self, uid, msg):
        if self.tuling_key:
            url = "http://www.tuling123.com/openapi/api"
            user_id = uid.replace('@', '')[:30]
            body = {'key': self.tuling_key, 'info': msg.encode('utf8'), 'userid': user_id}
            r = requests.post(url, data=body)
            respond = json.loads(r.text)
            result = ''
            if respond['code'] == 100000:
                result = respond['text'].replace('<br>', '  ')
            elif respond['code'] == 200000:
                result = respond['url']
            else:
                result = respond['text'].replace('<br>', '  ')

            print '    ROBOT:', result
            return result
        else:
            return u"知道啦"

    def auto_switch(self, msg):
        msg_data = msg['content']['data']
        STOP = [u'退下', u'走开', u'关闭', u'关掉', u'休息', u'滚开']
        START = [u'出来', u'启动', u'工作']
        if self.robot_switch:
            for i in STOP:
                if i == msg_data:
                    self.robot_switch = False
                    self.send_msg_by_uid(u'[Robot]' + u'机器人已关闭！', msg['to_user_id'])
        else:
            for i in START:
                if i == msg_data:
                    self.robot_switch = True
                    self.send_msg_by_uid(u'[Robot]' + u'机器人已开启！', msg['to_user_id'])

    def handle_msg_all(self, msg):
        if not self.robot_switch and msg['msg_type_id'] != 1:
            return
        if msg['msg_type_id'] == 1 and msg['content']['type'] == 0:  # reply to self
            self.auto_switch(msg)
        elif msg['msg_type_id'] == 4 and msg['content']['type'] == 0:  # text message from contact
            self.send_msg_by_uid(self.tuling_auto_reply(msg['user']['id'], msg['content']['data']), msg['user']['id'])
        elif msg['msg_type_id'] == 3:  # group message
            if msg['content']['data'].find('@') >= 0:  # someone @ another
                my_names = self.get_group_member_name(msg['user']['id'], self.user['UserName'])
                if my_names is None:
                    my_names = {}
                if 'NickName' in self.user and len(self.user['NickName']) > 0:
                    my_names['nickname2'] = self.user['NickName']
                if 'RemarkName' in self.user and len(self.user['RemarkName']) > 0:
                    my_names['remark_name2'] = self.user['RemarkName']
                is_at_me = False
                text_msg = ''
                for _ in my_names:
                    if msg['content']['data'].find('@'+my_names[_]) >= 0:
                        is_at_me = True
                        text_msg = msg['content']['data'].replace('@'+my_names[_], '').strip()
                        break
                if is_at_me:  # someone @ me
                    snames = self.get_group_member_name(msg['user']['id'], msg['content']['user']['id'])
                    if snames is None:
                        snames = self.get_account_name(msg['content']['user']['id'])
                    src_name = ''
                    if snames is not None:
                        if 'display_name' in snames and len(snames['display_name']) > 0:
                            src_name = snames['display_name']
                        elif 'nickname' in snames and len(snames['nickname']) > 0:
                            src_name = snames['nickname']
                        elif 'remark_name' in snames and len(snames['remark_name']) > 0:
                            src_name = snames['remark_name']
                    else:
                        return

                    if src_name != '':
                        reply = '@' + src_name + ' '
                        if msg['content']['type'] == 0:  # text message
                            reply += self.tuling_auto_reply(msg['content']['user']['id'], text_msg)
                        else:
                            reply += u"对不起，只认字，其他杂七杂八的我都不认识，,,Ծ‸Ծ,,"
                        self.send_msg_by_uid(reply, msg['user']['id'])


def main():
    bot = TulingWXBot()
    bot.DEBUG = True
    bot.conf['qr'] = 'png'

    bot.run()


if __name__ == '__main__':
    main()

