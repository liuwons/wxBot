#!/usr/bin/env python
# coding: utf-8

import pyqrcode
import requests
import json
import xml.dom.minidom
import urllib
import time
import re
import random
from requests.exceptions import *
import webbrowser
import HTMLParser


class WXBot:
    """WXBot, a framework to process WeChat messages"""

    def __init__(self):
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = ''
        self.redirect_uri = ''
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.device_id = 'e' + repr(random.random())[2:17]
        self.base_request = {}
        self.sync_key_str = ''
        self.sync_key = []
        self.sync_host = ''

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5'})
        self.conf = {'qr': 'png'}

        self.my_account = {}  # this account

        # all kind of accounts: contacts, public accounts, groups, special accounts
        self.member_list = []

        # members of all groups, {'group_id1': [member1, member2, ...], ...}
        self.group_members = {}

        # all accounts, {'group_member':{'id':{'type':'group_member', 'info':{}}, ...}, 'normal_member':{'id':{}, ...}}
        self.account_info = {'group_member': {}, 'normal_member': {}}

        self.contact_list = []  # contact list
        self.public_list = []  # public account list
        self.group_list = []  # group chat list
        self.special_list = []  # special list account

    def get_contact(self):
        """Get information of all contacts of current account."""
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' \
                              % (self.pass_ticket, self.skey, int(time.time()))
        r = self.session.post(url, data='{}')
        r.encoding = 'utf-8'
        if self.DEBUG:
            with open('contacts.json', 'w') as f:
                f.write(r.text.encode('utf-8'))
        dic = json.loads(r.text)
        self.member_list = dic['MemberList']

        special_users = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail',
                         'fmessage', 'tmessage', 'qmessage', 'qqsync', 'floatbottle',
                         'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp',
                         'blogapp', 'facebookapp', 'masssendapp', 'meishiapp',
                         'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
                         'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c',
                         'officialaccounts', 'notification_messages', 'wxid_novlwrv3lqwv11',
                         'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm', 'notification_messages']

        self.contact_list = []
        self.public_list = []
        self.special_list = []
        self.group_list = []

        for contact in self.member_list:
            if contact['VerifyFlag'] & 8 != 0:  # public account
                self.public_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'public', 'info': contact}
            elif contact['UserName'] in special_users:  # special account
                self.special_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'special', 'info': contact}
            elif contact['UserName'].find('@@') != -1:  # group
                self.group_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'group', 'info': contact}
            elif contact['UserName'] == self.my_account['UserName']:  # self
                self.account_info['normal_member'][contact['UserName']] = {'type': 'self', 'info': contact}
                pass
            else:
                self.contact_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'contact', 'info': contact}

        self.group_members = self.batch_get_group_members()

        for group in self.group_members:
            for member in self.group_members[group]:
                if member['UserName'] not in self.account_info:
                    self.account_info['group_member'][member['UserName']] = {'type': 'group_member',
                                                                             'info': member,
                                                                             'group': group}

        if self.DEBUG:
            with open('contact_list.json', 'w') as f:
                f.write(json.dumps(self.contact_list))
            with open('special_list.json', 'w') as f:
                f.write(json.dumps(self.special_list))
            with open('group_list.json', 'w') as f:
                f.write(json.dumps(self.group_list))
            with open('public_list.json', 'w') as f:
                f.write(json.dumps(self.public_list))
            with open('member_list.json', 'w') as f:
                f.write(json.dumps(self.member_list))
            with open('group_users.json', 'w') as f:
                f.write(json.dumps(self.group_members))
            with open('account_info.json', 'w') as f:
                f.write(json.dumps(self.account_info))
        return True

    def batch_get_group_members(self):
        """Get information of accounts in all groups at once."""
        url = self.base_uri + '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            "Count": len(self.group_list),
            "List": [{"UserName": group['UserName'], "EncryChatRoomId": ""} for group in self.group_list]
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        group_members = {}
        for group in dic['ContactList']:
            gid = group['UserName']
            members = group['MemberList']
            group_members[gid] = members
        return group_members

    def get_group_member_name(self, gid, uid):
        """
        Get name of a member in a group.
        :param gid: group id
        :param uid: group member id
        :return: names like {"display_name": "test_user", "nickname": "test", "remark_name": "for_test" }
        """
        if gid not in self.group_members:
            return None
        group = self.group_members[gid]
        for member in group:
            if member['UserName'] == uid:
                names = {}
                if 'RemarkName' in member and member['RemarkName']:
                    names['remark_name'] = member['RemarkName']
                if 'NickName' in member and member['NickName']:
                    names['nickname'] = member['NickName']
                if 'DisplayName' in member and member['DisplayName']:
                    names['display_name'] = member['DisplayName']
                return names
        return None

    def get_contact_info(self, uid):
        if uid in self.account_info['normal_member']:
            return self.account_info['normal_member'][uid]
        else:
            return None

    def get_group_member_info(self, uid):
        if uid in self.account_info['group_member']:
            return self.account_info['group_member'][uid]
        else:
            return None

    def get_group_member_info(self, uid, gid):
        if gid not in self.group_members:
            return None
        for member in self.group_members[gid]:
            if member['UserName'] == uid:
                return {'type': 'group_member', 'info': member}
        return None

    def get_contact_name(self, uid):
        info = self.get_contact_info(uid)
        if info is None:
            return None
        info = info['info']
        name = {}
        if 'RemarkName' in info and info['RemarkName']:
            name['remark_name'] = info['RemarkName']
        if 'NickName' in info and info['NickName']:
            name['nickname'] = info['NickName']
        if 'DisplayName' in info and info['DisplayName']:
            name['display_name'] = info['DisplayName']
        if len(name) == 0:
            return None
        else:
            return name

    def get_group_member_name(self, uid):
        info = self.get_group_member_info(uid)
        if info is None:
            return None
        info = info['info']
        name = {}
        if 'RemarkName' in info and info['RemarkName']:
            name['remark_name'] = info['RemarkName']
        if 'NickName' in info and info['NickName']:
            name['nickname'] = info['NickName']
        if 'DisplayName' in info and info['DisplayName']:
            name['display_name'] = info['DisplayName']
        if len(name) == 0:
            return None
        else:
            return name

    def get_group_member_name(self, uid, gid):
        info = self.get_group_member_info(uid, gid)
        if info is None:
            return None
        info = info['info']
        name = {}
        if 'RemarkName' in info and info['RemarkName']:
            name['remark_name'] = info['RemarkName']
        if 'NickName' in info and info['NickName']:
            name['nickname'] = info['NickName']
        if 'DisplayName' in info and info['DisplayName']:
            name['display_name'] = info['DisplayName']
        if len(name) == 0:
            return None
        else:
            return name

    @staticmethod
    def get_contact_prefer_name(name):
        if name is None:
            return None
        if 'remark_name' in name:
            return name['remark_name']
        if 'nickname' in name:
            return name['nickname']
        if 'display_name' in name:
            return name['display_name']
        return None

    @staticmethod
    def get_group_member_prefer_name(name):
        if name is None:
            return None
        if 'remark_name' in name:
            return name['remark_name']
        if 'display_name' in name:
            return name['display_name']
        if 'nickname' in name:
            return name['nickname']
        return None

    def get_user_type(self, wx_user_id):
        """
        Get the relationship of a account and current user.
        :param wx_user_id:
        :return: The type of the account.
        """
        for account in self.contact_list:
            if wx_user_id == account['UserName']:
                return 'contact'
        for account in self.public_list:
            if wx_user_id == account['UserName']:
                return 'public'
        for account in self.special_list:
            if wx_user_id == account['UserName']:
                return 'special'
        for account in self.group_list:
            if wx_user_id == account['UserName']:
                return 'group'
        for group in self.group_members:
            for member in self.group_members[group]:
                if member['UserName'] == wx_user_id:
                    return 'group_member'
        return 'unknown'

    def is_contact(self, uid):
        for account in self.contact_list:
            if uid == account['UserName']:
                return True
        return False

    def is_public(self, uid):
        for account in self.public_list:
            if uid == account['UserName']:
                return True
        return False

    def is_special(self, uid):
        for account in self.special_list:
            if uid == account['UserName']:
                return True
        return False

    def handle_msg_all(self, msg):
        """
        The function to process all WeChat messages, please override this function.
        msg:
            msg_id  ->  id of the received WeChat message
            msg_type_id  ->  the type of the message
            user  ->  the account that the message if sent from
            content  ->  content of the message
        :param msg: The received message.
        :return: None
        """
        pass

    @staticmethod
    def proc_at_info(msg):
        if not msg:
            return '', []
        segs = msg.split(u'\u2005')
        str_msg_all = ''
        str_msg = ''
        infos = []
        if len(segs) > 1:
            for i in range(0, len(segs)-1):
                segs[i] += u'\u2005'
                pm = re.search(u'@.*\u2005', segs[i]).group()
                if pm:
                    name = pm[1:-1]
                    string = segs[i].replace(pm, '')
                    str_msg_all += string + '@' + name + ' '
                    str_msg += string
                    if string:
                        infos.append({'type': 'str', 'value': string})
                    infos.append({'type': 'at', 'value': name})
                else:
                    infos.append({'type': 'str', 'value': segs[i]})
                    str_msg_all += segs[i]
                    str_msg += segs[i]
            str_msg_all += segs[-1]
            str_msg += segs[-1]
            infos.append({'type': 'str', 'value': segs[-1]})
        else:
            infos.append({'type': 'str', 'value': segs[-1]})
            str_msg_all = msg
            str_msg = msg
        return str_msg_all.replace(u'\u2005', ''), str_msg.replace(u'\u2005', ''), infos

    def extract_msg_content(self, msg_type_id, msg):
        """
        content_type_id:
            0 -> Text
            1 -> Location
            3 -> Image
            4 -> Voice
            5 -> Recommend
            6 -> Animation
            7 -> Share
            8 -> Video
            9 -> VideoCall
            10 -> Redraw
            11 -> Empty
            99 -> Unknown
        :param msg_type_id: The type of the received message.
        :param msg: The received message.
        :return: The extracted content of the message.
        """
        mtype = msg['MsgType']
        content = HTMLParser.HTMLParser().unescape(msg['Content'])
        msg_id = msg['MsgId']

        msg_content = {}
        if msg_type_id == 0:
            return {'type': 11, 'data': ''}
        elif msg_type_id == 2:  # File Helper
            return {'type': 0, 'data': content.replace('<br/>', '\n')}
        elif msg_type_id == 3:  # Group
            sp = content.find('<br/>')
            uid = content[:sp]
            content = content[sp:]
            content = content.replace('<br/>', '')
            uid = uid[:-1]
            name = self.get_contact_prefer_name(self.get_contact_name(uid))
            if not name:
                name = self.get_group_member_prefer_name(self.get_group_member_name(uid, msg['FromUserName']))
            if not name:
                name = 'unknown'
            msg_content['user'] = {'id': uid, 'name': name}
        else:  # Self, Contact, Special, Public, Unknown
            pass

        msg_prefix = (msg_content['user']['name'] + ':') if 'user' in msg_content else ''

        if mtype == 1:
            if content.find('http://weixin.qq.com/cgi-bin/redirectforward?args=') != -1:
                r = self.session.get(content)
                r.encoding = 'gbk'
                data = r.text
                pos = self.search_content('title', data, 'xml')
                msg_content['type'] = 1
                msg_content['data'] = pos
                msg_content['detail'] = data
                if self.DEBUG:
                    print '    %s[Location] %s ' % (msg_prefix, pos)
            else:
                msg_content['type'] = 0
                if msg_type_id == 3 or (msg_type_id == 1 and msg['ToUserName'][:2] == '@@'):  # Group text message
                    msg_infos = self.proc_at_info(content)
                    str_msg_all = msg_infos[0]
                    str_msg = msg_infos[1]
                    detail = msg_infos[2]
                    msg_content['data'] = str_msg_all
                    msg_content['detail'] = detail
                    msg_content['desc'] = str_msg
                else:
                    msg_content['data'] = content
                if self.DEBUG:
                    print '    %s[Text] %s' % (msg_prefix, msg_content['data'])
        elif mtype == 3:
            msg_content['type'] = 3
            msg_content['data'] = self.get_msg_img_url(msg_id)
            if self.DEBUG:
                image = self.get_msg_img(msg_id)
                print '    %s[Image] %s' % (msg_prefix, image)
        elif mtype == 34:
            msg_content['type'] = 4
            msg_content['data'] = self.get_voice_url(msg_id)
            if self.DEBUG:
                voice = self.get_voice(msg_id)
                print '    %s[Voice] %s' % (msg_prefix, voice)
        elif mtype == 42:
            msg_content['type'] = 5
            info = msg['RecommendInfo']
            msg_content['data'] = {'nickname': info['NickName'],
                                   'alias': info['Alias'],
                                   'province': info['Province'],
                                   'city': info['City'],
                                   'gender': ['unknown', 'male', 'female'][info['Sex']]}
            if self.DEBUG:
                print '    %s[Recommend]' % msg_prefix
                print '    -----------------------------'
                print '    | NickName: %s' % info['NickName']
                print '    | Alias: %s' % info['Alias']
                print '    | Local: %s %s' % (info['Province'], info['City'])
                print '    | Gender: %s' % ['unknown', 'male', 'female'][info['Sex']]
                print '    -----------------------------'
        elif mtype == 47:
            msg_content['type'] = 6
            msg_content['data'] = self.search_content('cdnurl', content)
            if self.DEBUG:
                print '    %s[Animation] %s' % (msg_prefix, msg_content['data'])
        elif mtype == 49:
            msg_content['type'] = 7
            app_msg_type = ''
            if msg['AppMsgType'] == 3:
                app_msg_type = 'music'
            elif msg['AppMsgType'] == 5:
                app_msg_type = 'link'
            elif msg['AppMsgType'] == 7:
                app_msg_type = 'weibo'
            else:
                app_msg_type = 'unknown'
            msg_content['data'] = {'type': app_msg_type,
                                   'title': msg['FileName'],
                                   'desc': self.search_content('des', content, 'xml'),
                                   'url': msg['Url'],
                                   'from': self.search_content('appname', content, 'xml')}
            if self.DEBUG:
                print '    %s[Share] %s' % (msg_prefix, app_msg_type)
                print '    --------------------------'
                print '    | title: %s' % msg['FileName']
                print '    | desc: %s' % self.search_content('des', content, 'xml')
                print '    | link: %s' % msg['Url']
                print '    | from: %s' % self.search_content('appname', content, 'xml')
                print '    --------------------------'

        elif mtype == 62:
            msg_content['type'] = 8
            msg_content['data'] = content
            if self.DEBUG:
                print '    %s[Video] Please check on mobiles' % msg_prefix
        elif mtype == 53:
            msg_content['type'] = 9
            msg_content['data'] = content
            if self.DEBUG:
                print '    %s[Video Call]' % msg_prefix
        elif mtype == 10002:
            msg_content['type'] = 10
            msg_content['data'] = content
            if self.DEBUG:
                print '    %s[Redraw]' % msg_prefix
        elif mtype == 10000:  # unknown, maybe red packet, or group invite
            msg_content['type'] = 12
            msg_content['data'] = msg['Content']
            if self.DEBUG:
                print '    [Unknown]'
        else:
            msg_content['type'] = 99
            msg_content['data'] = content
            if self.DEBUG:
                print '    %s[Unknown]' % msg_prefix
        return msg_content

    def handle_msg(self, r):
        """
        The inner function that processes raw WeChat messages.
        msg_type_id:
            0 -> Init
            1 -> Self
            2 -> FileHelper
            3 -> Group
            4 -> Contact
            5 -> Public
            6 -> Special
            99 -> Unknown
        :param r: The raw data of the messages.
        :return: None
        """
        for msg in r['AddMsgList']:
            msg_type_id = 99
            user = {'id': msg['FromUserName'], 'name': 'unknown'}
            if msg['MsgType'] == 51:  # init message
                msg_type_id = 0
                user['name'] = 'system'
            elif msg['FromUserName'] == self.my_account['UserName']:  # Self
                msg_type_id = 1
                user['name'] = 'self'
            elif msg['ToUserName'] == 'filehelper':  # File Helper
                msg_type_id = 2
                user['name'] = 'file_helper'
            elif msg['FromUserName'][:2] == '@@':  # Group
                msg_type_id = 3
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            elif self.is_contact(msg['FromUserName']):  # Contact
                msg_type_id = 4
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            elif self.is_public(msg['FromUserName']):  # Public
                msg_type_id = 5
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            elif self.is_special(msg['FromUserName']):  # Special
                msg_type_id = 6
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            else:
                msg_type_id = 99
                user['name'] = 'unknown'
            if not user['name']:
                user['name'] = 'unknown'
            user['name'] = HTMLParser.HTMLParser().unescape(user['name'])

            if self.DEBUG and msg_type_id != 0:
                print '[MSG] %s:' % user['name']
            content = self.extract_msg_content(msg_type_id, msg)
            message = {'msg_type_id': msg_type_id,
                       'msg_id': msg['MsgId'],
                       'content': content,
                       'to_user_id': msg['ToUserName'],
                       'user': user}
            self.handle_msg_all(message)

    def schedule(self):
        """
        The function to do schedule works.
        This function will be called a lot of times.
        Please override this if needed.
        :return: None
        """
        pass

    def proc_msg(self):
        self.test_sync_check()
        while True:
            check_time = time.time()
            [retcode, selector] = self.sync_check()
            if retcode == '1100':  # logout from mobile
                break
            elif retcode == '1101':  # login web WeChat from other devide
                break
            elif retcode == '0':
                if selector == '2':  # new message
                    r = self.sync()
                    if r is not None:
                        self.handle_msg(r)
                elif selector == '7':  # Play WeChat on mobile
                    r = self.sync()
                    if r is not None:
                        self.handle_msg(r)
                elif selector == '0':  # nothing
                    pass
                else:
                    pass
            self.schedule()
            check_time = time.time() - check_time
            if check_time < 0.5:
                time.sleep(0.5 - check_time)

    def send_msg_by_uid(self, word, dst='filehelper'):
        url = self.base_uri + '/webwxsendmsg?pass_ticket=%s' % self.pass_ticket
        msg_id = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
        if type(word) == 'str':
            word = word.decode('utf-8')
        params = {
            'BaseRequest': self.base_request,
            'Msg': {
                "Type": 1,
                "Content": word,
                "FromUserName": self.my_account['UserName'],
                "ToUserName": dst,
                "LocalID": msg_id,
                "ClientMsgId": msg_id
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def get_user_id(self, name):
        if name == '':
            return ''
        for contact in self.contact_list:
            if 'RemarkName' in contact and contact['RemarkName'] == name:
                return contact['UserName']
            elif 'NickName' in contact and contact['NickName'] == name:
                return contact['UserName']
            elif 'DisplayName' in contact and contact['DisplayName'] == name:
                return contact['UserName']
        return ''

    def send_msg(self, name, word, isfile=False):
        uid = self.get_user_id(name)
        if uid:
            if isfile:
                with open(word, 'r') as f:
                    result = True
                    for line in f.readlines():
                        line = line.replace('\n', '')
                        print '-> ' + name + ': ' + line
                        if self.send_msg_by_uid(line, uid):
                            pass
                        else:
                            result = False
                        time.sleep(1)
                    return result
            else:
                if self.send_msg_by_uid(word, uid):
                    return True
                else:
                    return False
        else:
            if self.DEBUG:
                print '[ERROR] This user does not exist .'
            return True

    @staticmethod
    def search_content(key, content, fmat='attr'):
        if fmat == 'attr':
            pm = re.search(key + '\s?=\s?"([^"<]+)"', content)
            if pm:
                return pm.group(1)
        elif fmat == 'xml':
            pm = re.search('<{0}>([^<]+)</{0}>'.format(key), content)
            if pm:
                return pm.group(1)
        return 'unknown'

    def run(self):
        self.get_uuid()
        self.gen_qr_code('qr.png')
        print '[INFO] Please use WeChat to scan the QR code .'
        self.wait4login(1)
        print '[INFO] Please confirm to login .'
        self.wait4login(0)
        if self.login():
            print '[INFO] Web WeChat login succeed .'
        else:
            print '[ERROR] Web WeChat login failed .'
            return
        if self.init():
            print '[INFO] Web WeChat init succeed .'
        else:
            print '[INFO] Web WeChat init failed'
            return
        self.status_notify()
        self.get_contact()
        print '[INFO] Get %d contacts' % len(self.contact_list)
        print '[INFO] Start to process messages .'
        self.proc_msg()

    def get_uuid(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time()) * 1000 + random.randint(1, 999),
        }
        r = self.session.get(url, params=params)
        r.encoding = 'utf-8'
        data = r.text
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            self.uuid = pm.group(2)
            return code == '200'
        return False

    def gen_qr_code(self, qr_file_path):
        string = 'https://login.weixin.qq.com/l/' + self.uuid
        qr = pyqrcode.create(string)
        if self.conf['qr'] == 'png':
            qr.png(qr_file_path, scale=8)
            webbrowser.open(qr_file_path)
        elif self.conf['qr'] == 'tty':
            print(qr.terminal(quiet_zone=1))

    def wait4login(self, tip):
        time.sleep(tip)
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' \
              % (tip, self.uuid, int(time.time()))
        r = self.session.get(url)
        r.encoding = 'utf-8'
        data = r.text
        param = re.search(r'window.code=(\d+);', data)
        code = param.group(1)

        if code == '201':
            return True
        elif code == '200':
            param = re.search(r'window.redirect_uri="(\S+?)";', data)
            redirect_uri = param.group(1) + '&fun=new'
            self.redirect_uri = redirect_uri
            self.base_uri = redirect_uri[:redirect_uri.rfind('/')]
            return True
        elif code == '408':
            print '[ERROR] WeChat login timeout .'
        else:
            print '[ERROR] WeChat login exception .'
        return False

    def login(self):
        if len(self.redirect_uri) < 4:
            print '[ERROR] Login failed due to network problem, please try again.'
            return False
        r = self.session.get(self.redirect_uri)
        r.encoding = 'utf-8'
        data = r.text
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.base_request = {
            'Uin': self.uin,
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.device_id,
        }
        return True

    def init(self):
        url = self.base_uri + '/webwxinit?r=%i&lang=en_US&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        self.sync_key = dic['SyncKey']
        self.my_account = dic['User']
        self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                      for keyVal in self.sync_key['List']])
        return dic['BaseResponse']['Ret'] == 0

    def status_notify(self):
        url = self.base_uri + '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % self.pass_ticket
        self.base_request['Uin'] = int(self.base_request['Uin'])
        params = {
            'BaseRequest': self.base_request,
            "Code": 3,
            "FromUserName": self.my_account['UserName'],
            "ToUserName": self.my_account['UserName'],
            "ClientMsgId": int(time.time())
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        return dic['BaseResponse']['Ret'] == 0

    def test_sync_check(self):
        for host in ['webpush', 'webpush2']:
            self.sync_host = host
            retcode = self.sync_check()[0]
            if retcode == '0':
                return True
        return False

    def sync_check(self):
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.device_id,
            'synckey': self.sync_key_str,
            '_': int(time.time()),
        }
        url = 'https://' + self.sync_host + '.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?' + urllib.urlencode(params)
        try:
            r = self.session.get(url)
        except (ConnectionError, ReadTimeout):
            return [-1, -1]
        r.encoding = 'utf-8'
        data = r.text
        pm = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    def sync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' \
                              % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            'SyncKey': self.sync_key,
            'rr': ~int(time.time())
        }
        try:
            r = self.session.post(url, data=json.dumps(params))
        except (ConnectionError, ReadTimeout):
            return None
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        if dic['BaseResponse']['Ret'] == 0:
            self.sync_key = dic['SyncKey']
            self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                          for keyVal in self.sync_key['List']])
        return dic

    def get_icon(self, uid):
        url = self.base_uri + '/webwxgeticon?username=%s&skey=%s' % (uid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_' + uid + '.jpg'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    def get_head_img(self, uid):
        url = self.base_uri + '/webwxgetheadimg?username=%s&skey=%s' % (uid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_' + uid + '.jpg'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    def get_msg_img_url(self, msgid):
        return self.base_uri + '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)

    def get_msg_img(self, msgid):
        url = self.base_uri + '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_' + msgid + '.jpg'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    def get_voice_url(self, msgid):
        return self.base_uri + '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)

    def get_voice(self, msgid):
        url = self.base_uri + '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'voice_' + msgid + '.mp3'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn
