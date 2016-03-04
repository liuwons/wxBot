#!/usr/bin/env python
# coding: utf-8

from wxbot import *
import ConfigParser
import json


class TulingWXBot(WXBot):
    def __init__(self):
        WXBot.__init__(self)

        self.tuling_key = ""

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

            return result
        else:
            return u"知道啦"

    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:  # text message from contact
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
                    src_name = ''
                    if 'display_name' in snames:
                        src_name = snames['display_name']
                    elif 'nickname' in snames:
                        src_name = snames['nickname']
                    elif 'remark_name' in snames:
                        src_name = snames['remark_name']

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
