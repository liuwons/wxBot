#!/usr/bin/env python
# coding: utf-8

import os
import sys
import traceback
import webbrowser
import pyqrcode
import requests
import mimetypes
import json
import xml.dom.minidom
import urllib
import time
import re
import random
from traceback import format_exc
from requests.exceptions import ConnectionError, ReadTimeout
import HTMLParser

UNKONWN = 'unkonwn'
SUCCESS = '200'
SCANED = '201'
TIMEOUT = '408'

def map_username_batch(user_name):
    return {"UserName": user_name, "EncryChatRoomId": ""}


def show_image(file_path):
    """
    跨平台显示图片文件
    :param file_path: 图片文件路径
    """
    if sys.version_info >= (3, 3):
        from shlex import quote
    else:
        from pipes import quote

    if sys.platform == "darwin":
        command = "open -a /Applications/Preview.app %s&" % quote(file_path)
        os.system(command)
    else:
        webbrowser.open(os.path.join(os.getcwd(),'temp',file_path))


class SafeSession(requests.Session):
    def request(self, method, url, params=None, data=None, headers=None, cookies=None, files=None, auth=None,
                timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None,
                json=None):
        for i in range(3):
            try:
                return super(SafeSession, self).request(method, url, params, data, headers, cookies, files, auth,
                                                        timeout,
                                                        allow_redirects, proxies, hooks, stream, verify, cert, json)
            except Exception as e:
                print e.message, traceback.format_exc()
                continue

        #重试3次以后再加一次，抛出异常
        try:
            return super(SafeSession, self).request(method, url, params, data, headers, cookies, files, auth,
                                                    timeout,
                                                    allow_redirects, proxies, hooks, stream, verify, cert, json)
        except Exception as e:
            raise e


class WXBot:
    """WXBot功能类"""

    def __init__(self):
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = ''
        self.base_host = ''
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


        self.batch_count = 50    #一次拉取50个联系人的信息
        self.full_user_name_list = []    #直接获取不到通讯录时，获取的username列表
        self.wxid_list = []   #获取到的wxid的列表
        self.cursor = 0   #拉取联系人信息的游标
        self.is_big_contact = False  #通讯录人数过多，无法直接获取
        #文件缓存目录
        self.temp_pwd  =  os.path.join(os.getcwd(),'temp')
        if os.path.exists(self.temp_pwd) == False:
            os.makedirs(self.temp_pwd)

        self.session = SafeSession()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5'})
        self.conf = {'qr': 'png'}

        self.my_account = {}  # 当前账户

        # 所有相关账号: 联系人, 公众号, 群组, 特殊账号
        self.member_list = []

        # 所有群组的成员, {'group_id1': [member1, member2, ...], ...}
        self.group_members = {}

        # 所有账户, {'group_member':{'id':{'type':'group_member', 'info':{}}, ...}, 'normal_member':{'id':{}, ...}}
        self.account_info = {'group_member': {}, 'normal_member': {}}

        self.contact_list = []  # 联系人列表
        self.public_list = []  # 公众账号列表
        self.group_list = []  # 群聊列表
        self.special_list = []  # 特殊账号列表
        self.encry_chat_room_id_list = []  # 存储群聊的EncryChatRoomId，获取群内成员头像时需要用到

        self.file_index = 0

    @staticmethod
    def to_unicode(string, encoding='utf-8'):
        """
        将字符串转换为Unicode
        :param string: 待转换字符串
        :param encoding: 字符串解码方式
        :return: 转换后的Unicode字符串
        """
        if isinstance(string, str):
            return string.decode(encoding)
        elif isinstance(string, unicode):
            return string
        else:
            raise Exception('Unknown Type')

    def get_contact(self):
        """获取当前账户的所有相关账号(包括联系人、公众号、群聊、特殊账号)"""
        if self.is_big_contact:
            return False
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' \
                              % (self.pass_ticket, self.skey, int(time.time()))

        #如果通讯录联系人过多，这里会直接获取失败
        try:
            r = self.session.post(url, data='{}')
        except Exception as e:
            self.is_big_contact = True
            return False
        r.encoding = 'utf-8'
        if self.DEBUG:
            with open(os.path.join(self.temp_pwd,'contacts.json'), 'w') as f:
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
            if contact['VerifyFlag'] & 8 != 0:  # 公众号
                self.public_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'public', 'info': contact}
            elif contact['UserName'] in special_users:  # 特殊账户
                self.special_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'special', 'info': contact}
            elif contact['UserName'].find('@@') != -1:  # 群聊
                self.group_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'group', 'info': contact}
            elif contact['UserName'] == self.my_account['UserName']:  # 自己
                self.account_info['normal_member'][contact['UserName']] = {'type': 'self', 'info': contact}
            else:
                self.contact_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'contact', 'info': contact}

        self.batch_get_group_members()

        for group in self.group_members:
            for member in self.group_members[group]:
                if member['UserName'] not in self.account_info:
                    self.account_info['group_member'][member['UserName']] = \
                        {'type': 'group_member', 'info': member, 'group': group}

        if self.DEBUG:
            with open(os.path.join(self.temp_pwd,'contact_list.json'), 'w') as f:
                f.write(json.dumps(self.contact_list))
            with open(os.path.join(self.temp_pwd,'special_list.json'), 'w') as f:
                f.write(json.dumps(self.special_list))
            with open(os.path.join(self.temp_pwd,'group_list.json'), 'w') as f:
                f.write(json.dumps(self.group_list))
            with open(os.path.join(self.temp_pwd,'public_list.json'), 'w') as f:
                f.write(json.dumps(self.public_list))
            with open(os.path.join(self.temp_pwd,'member_list.json'), 'w') as f:
                f.write(json.dumps(self.member_list))
            with open(os.path.join(self.temp_pwd,'group_users.json'), 'w') as f:
                f.write(json.dumps(self.group_members))
            with open(os.path.join(self.temp_pwd,'account_info.json'), 'w') as f:
                f.write(json.dumps(self.account_info))
        return True


    def get_big_contact(self):
        total_len = len(self.full_user_name_list)
        user_info_list = []

        #一次拉取50个联系人的信息，包括所有的群聊，公众号，好友
        while self.cursor < total_len:
            cur_batch = self.full_user_name_list[self.cursor:(self.cursor+self.batch_count)]
            self.cursor += self.batch_count
            cur_batch = map(map_username_batch, cur_batch)
            user_info_list += self.batch_get_contact(cur_batch)
            print "[INFO] Get batch contacts"

        self.member_list = user_info_list
        special_users = ['newsapp', 'filehelper', 'weibo', 'qqmail',
                 'fmessage', 'tmessage', 'qmessage', 'qqsync', 'floatbottle',
                 'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp',
                 'blogapp', 'facebookapp', 'masssendapp', 'meishiapp',
                 'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
                 'weixinreminder', 'wxid_novlwrv3lqwv11',
                 'officialaccounts',
                 'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm', 'notification_messages', 'notifymessage']

        self.contact_list = []
        self.public_list = []
        self.special_list = []
        self.group_list = []
        for i, contact in enumerate(self.member_list):
            if contact['VerifyFlag'] & 8 != 0:  # 公众号
                self.public_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'public', 'info': contact}
            elif contact['UserName'] in special_users or self.wxid_list[i] in special_users:  # 特殊账户
                self.special_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'special', 'info': contact}
            elif contact['UserName'].find('@@') != -1:  # 群聊
                self.group_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'group', 'info': contact}
            elif contact['UserName'] == self.my_account['UserName']:  # 自己
                self.account_info['normal_member'][contact['UserName']] = {'type': 'self', 'info': contact}
            else:
                self.contact_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'contact', 'info': contact}
        group_members = {}
        encry_chat_room_id = {}
        for group in self.group_list:
            gid = group['UserName']
            members = group['MemberList']
            group_members[gid] = members
            encry_chat_room_id[gid] = group['EncryChatRoomId']
        self.group_members = group_members
        self.encry_chat_room_id_list = encry_chat_room_id

        for group in self.group_members:
            for member in self.group_members[group]:
                if member['UserName'] not in self.account_info:
                    self.account_info['group_member'][member['UserName']] = \
                        {'type': 'group_member', 'info': member, 'group': group}

        if self.DEBUG:
            with open(os.path.join(self.temp_pwd,'contact_list.json'), 'w') as f:
                f.write(json.dumps(self.contact_list))
            with open(os.path.join(self.temp_pwd,'special_list.json'), 'w') as f:
                f.write(json.dumps(self.special_list))
            with open(os.path.join(self.temp_pwd,'group_list.json'), 'w') as f:
                f.write(json.dumps(self.group_list))
            with open(os.path.join(self.temp_pwd,'public_list.json'), 'w') as f:
                f.write(json.dumps(self.public_list))
            with open(os.path.join(self.temp_pwd,'member_list.json'), 'w') as f:
                f.write(json.dumps(self.member_list))
            with open(os.path.join(self.temp_pwd,'group_users.json'), 'w') as f:
                f.write(json.dumps(self.group_members))
            with open(os.path.join(self.temp_pwd,'account_info.json'), 'w') as f:
                f.write(json.dumps(self.account_info))
        print '[INFO] Get %d contacts' % len(self.contact_list)
        print '[INFO] Start to process messages .'
        return True



    def batch_get_contact(self, cur_batch):
        """批量获取成员信息"""
        url = self.base_uri + '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            "Count": len(cur_batch),
            "List": cur_batch
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        #print dic['ContactList']
        return dic['ContactList']


    def batch_get_group_members(self):
        """批量获取所有群聊成员信息"""
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
        encry_chat_room_id = {}
        for group in dic['ContactList']:
            gid = group['UserName']
            members = group['MemberList']
            group_members[gid] = members
            encry_chat_room_id[gid] = group['EncryChatRoomId']
        self.group_members = group_members
        self.encry_chat_room_id_list = encry_chat_room_id

    def get_group_member_name(self, gid, uid):
        """
        获取群聊中指定成员的名称信息
        :param gid: 群id
        :param uid: 群聊成员id
        :return: 名称信息，类似 {"display_name": "test_user", "nickname": "test", "remark_name": "for_test" }
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
        return self.account_info['normal_member'].get(uid)


    def get_group_member_info(self, uid):
        return self.account_info['group_member'].get(uid)

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
        获取特定账号与自己的关系
        :param wx_user_id: 账号id:
        :return: 与当前账号的关系
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
        处理所有消息，请子类化后覆盖此函数
        msg:
            msg_id  ->  消息id
            msg_type_id  ->  消息类型id
            user  ->  发送消息的账号id
            content  ->  消息内容
        :param msg: 收到的消息
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
            for i in range(0, len(segs) - 1):
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
        :param msg_type_id: 消息类型id
        :param msg: 消息结构体
        :return: 解析的消息
        """
        mtype = msg['MsgType']
        content = HTMLParser.HTMLParser().unescape(msg['Content'])
        msg_id = msg['MsgId']

        msg_content = {}
        if msg_type_id == 0:
            return {'type': 11, 'data': ''}
        elif msg_type_id == 2:  # File Helper
            return {'type': 0, 'data': content.replace('<br/>', '\n')}
        elif msg_type_id == 3:  # 群聊
            sp = content.find('<br/>')
            uid = content[:sp]
            content = content[sp:]
            content = content.replace('<br/>', '')
            uid = uid[:-1]
            name = self.get_contact_prefer_name(self.get_contact_name(uid))
            if not name:
                name = self.get_group_member_prefer_name(self.get_group_member_name(msg['FromUserName'], uid))
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
                    try:
                        print '    %s[Text] %s' % (msg_prefix, msg_content['data'])
                    except UnicodeEncodeError:
                        print '    %s[Text] (illegal text).' % msg_prefix
        elif mtype == 3:
            msg_content['type'] = 3
            msg_content['data'] = self.get_msg_img_url(msg_id)
            msg_content['img'] = self.session.get(msg_content['data']).content.encode('hex')
            if self.DEBUG:
                image = self.get_msg_img(msg_id)
                print '    %s[Image] %s' % (msg_prefix, image)
        elif mtype == 34:
            msg_content['type'] = 4
            msg_content['data'] = self.get_voice_url(msg_id)
            msg_content['voice'] = self.session.get(msg_content['data']).content.encode('hex')
            if self.DEBUG:
                voice = self.get_voice(msg_id)
                print '    %s[Voice] %s' % (msg_prefix, voice)
        elif mtype == 37:
            msg_content['type'] = 37
            msg_content['data'] = msg['RecommendInfo']
            if self.DEBUG:
                print '    %s[useradd] %s' % (msg_prefix,msg['RecommendInfo']['NickName'])
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
                                   'from': self.search_content('appname', content, 'xml'),
                                   'content': msg.get('Content')  # 有的公众号会发一次性3 4条链接一个大图,如果只url那只能获取第一条,content里面有所有的链接
                                   }
            if self.DEBUG:
                print '    %s[Share] %s' % (msg_prefix, app_msg_type)
                print '    --------------------------'
                print '    | title: %s' % msg['FileName']
                print '    | desc: %s' % self.search_content('des', content, 'xml')
                print '    | link: %s' % msg['Url']
                print '    | from: %s' % self.search_content('appname', content, 'xml')
                print '    | content: %s' % (msg.get('content')[:20] if msg.get('content') else "unknown")
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
        elif mtype == 43:
            msg_content['type'] = 13
            msg_content['data'] = self.get_video_url(msg_id)
            if self.DEBUG:
                print '    %s[video] %s' % (msg_prefix, msg_content['data'])
        else:
            msg_content['type'] = 99
            msg_content['data'] = content
            if self.DEBUG:
                print '    %s[Unknown]' % msg_prefix
        return msg_content

    def handle_msg(self, r):
        """
        处理原始微信消息的内部函数
        msg_type_id:
            0 -> Init
            1 -> Self
            2 -> FileHelper
            3 -> Group
            4 -> Contact
            5 -> Public
            6 -> Special
            99 -> Unknown
        :param r: 原始微信消息
        """
        for msg in r['AddMsgList']:
            user = {'id': msg['FromUserName'], 'name': 'unknown'}
            if msg['MsgType'] == 51 and msg['StatusNotifyCode'] == 4:  # init message
                msg_type_id = 0
                user['name'] = 'system'
                #会获取所有联系人的username 和 wxid，但是会收到3次这个消息，只取第一次
                if self.is_big_contact and len(self.full_user_name_list) == 0:
                    self.full_user_name_list = msg['StatusNotifyUserName'].split(",")
                    self.wxid_list = re.search(r"username&gt;(.*?)&lt;/username", msg["Content"]).group(1).split(",")
                    with open(os.path.join(self.temp_pwd,'UserName.txt'), 'w') as f:
                        f.write(msg['StatusNotifyUserName'])
                    with open(os.path.join(self.temp_pwd,'wxid.txt'), 'w') as f:
                        f.write(json.dumps(self.wxid_list))
                    print "[INFO] Contact list is too big. Now start to fetch member list ."
                    self.get_big_contact()

            elif msg['MsgType'] == 37:  # friend request
                msg_type_id = 37
                pass
                # content = msg['Content']
                # username = content[content.index('fromusername='): content.index('encryptusername')]
                # username = username[username.index('"') + 1: username.rindex('"')]
                # print u'[Friend Request]'
                # print u'       Nickname：' + msg['RecommendInfo']['NickName']
                # print u'       附加消息：'+msg['RecommendInfo']['Content']
                # # print u'Ticket：'+msg['RecommendInfo']['Ticket'] # Ticket添加好友时要用
                # print u'       微信号：'+username #未设置微信号的 腾讯会自动生成一段微信ID 但是无法通过搜索 搜索到此人
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
                print u'[MSG] %s:' % user['name']
            content = self.extract_msg_content(msg_type_id, msg)
            message = {'msg_type_id': msg_type_id,
                       'msg_id': msg['MsgId'],
                       'content': content,
                       'to_user_id': msg['ToUserName'],
                       'user': user}
            self.handle_msg_all(message)

    def schedule(self):
        """
        做任务型事情的函数，如果需要，可以在子类中覆盖此函数
        此函数在处理消息的间隙被调用，请不要长时间阻塞此函数
        """
        pass

    def proc_msg(self):
        self.test_sync_check()
        while True:
            check_time = time.time()
            try:
                [retcode, selector] = self.sync_check()
                # print '[DEBUG] sync_check:', retcode, selector
                if retcode == '1100':  # 从微信客户端上登出
                    break
                elif retcode == '1101':  # 从其它设备上登了网页微信
                    break
                elif retcode == '0':
                    if selector == '2':  # 有新消息
                        r = self.sync()
                        if r is not None:
                            self.handle_msg(r)
                    elif selector == '3':  # 未知
                        r = self.sync()
                        if r is not None:
                            self.handle_msg(r)
                    elif selector == '4':  # 通讯录更新
                        r = self.sync()
                        if r is not None:
                            self.get_contact()
                    elif selector == '6':  # 可能是红包
                        r = self.sync()
                        if r is not None:
                            self.handle_msg(r)
                    elif selector == '7':  # 在手机上操作了微信
                        r = self.sync()
                        if r is not None:
                            self.handle_msg(r)
                    elif selector == '0':  # 无事件
                        pass
                    else:
                        print '[DEBUG] sync_check:', retcode, selector
                        r = self.sync()
                        if r is not None:
                            self.handle_msg(r)
                else:
                    print '[DEBUG] sync_check:', retcode, selector
                    time.sleep(10)
                self.schedule()
            except:
                print '[ERROR] Except in proc_msg'
                print format_exc()
            check_time = time.time() - check_time
            if check_time < 0.8:
                time.sleep(1 - check_time)

    def apply_useradd_requests(self,RecommendInfo):
        url = self.base_uri + '/webwxverifyuser?r='+str(int(time.time()))+'&lang=zh_CN'
        params = {
            "BaseRequest": self.base_request,
            "Opcode": 3,
            "VerifyUserListSize": 1,
            "VerifyUserList": [
                {
                    "Value": RecommendInfo['UserName'],
                    "VerifyUserTicket": RecommendInfo['Ticket']             }
            ],
            "VerifyContent": "",
            "SceneListCount": 1,
            "SceneList": [
                33
            ],
            "skey": self.skey
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def add_groupuser_to_friend_by_uid(self,uid,VerifyContent):
        """
        主动向群内人员打招呼，提交添加好友请求
        uid-群内人员得uid   VerifyContent-好友招呼内容
        慎用此接口！封号后果自负！慎用此接口！封号后果自负！慎用此接口！封号后果自负！
        """
        if self.is_contact(uid):
            return True
        url = self.base_uri + '/webwxverifyuser?r='+str(int(time.time()))+'&lang=zh_CN'
        params ={
            "BaseRequest": self.base_request,
            "Opcode": 2,
            "VerifyUserListSize": 1,
            "VerifyUserList": [
                {
                    "Value": uid,
                    "VerifyUserTicket": ""
                }
            ],
            "VerifyContent": VerifyContent,
            "SceneListCount": 1,
            "SceneList": [
                33
            ],
            "skey": self.skey
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def add_friend_to_group(self,uid,group_name):
        """
        将好友加入到群聊中
        """
        gid = ''
        #通过群名获取群id,群没保存到通讯录中的话无法添加哦
        for group in self.group_list:
            if group['NickName'] == group_name:
                gid = group['UserName']
        if gid == '':
            return False
        #通过群id判断uid是否在群中
        for user in self.group_members[gid]:
            if user['UserName'] == uid:
                #已经在群里面了,不用加了
                return True
        url = self.base_uri + '/webwxupdatechatroom?fun=addmember&pass_ticket=%s' % self.pass_ticket
        params ={
            "AddMemberList": uid,
            "ChatRoomName": gid,
            "BaseRequest": self.base_request
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def invite_friend_to_group(self,uid,group_name):
        """
        将好友加入到群中。对人数多的群，需要调用此方法。
        拉人时，可以先尝试使用add_friend_to_group方法，当调用失败(Ret=1)时，再尝试调用此方法。
        """
        gid = ''
        # 通过群名获取群id,群没保存到通讯录中的话无法添加哦
        for group in self.group_list:
            if group['NickName'] == group_name:
                gid = group['UserName']
        if gid == '':
            return False
        # 通过群id判断uid是否在群中
        for user in self.group_members[gid]:
            if user['UserName'] == uid:
                # 已经在群里面了,不用加了
                return True
        url = self.base_uri + '/webwxupdatechatroom?fun=invitemember&pass_ticket=%s' % self.pass_ticket
        params = {
            "InviteMemberList": uid,
            "ChatRoomName": gid,
            "BaseRequest": self.base_request
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def delete_user_from_group(self,uname,gid):
        """
        将群用户从群中剔除，只有群管理员有权限
        """
        uid = ""
        for user in self.group_members[gid]:
            if user['NickName'] == uname:
                uid = user['UserName']
        if uid == "":
            return False
        url = self.base_uri + '/webwxupdatechatroom?fun=delmember&pass_ticket=%s' % self.pass_ticket
        params ={
            "DelMemberList": uid,
            "ChatRoomName": gid,
            "BaseRequest": self.base_request
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def set_group_name(self,gid,gname):
        """
        设置群聊名称
        """
        url = self.base_uri + '/webwxupdatechatroom?fun=modtopic&pass_ticket=%s' % self.pass_ticket
        params ={
            "NewTopic": gname,
            "ChatRoomName": gid,
            "BaseRequest": self.base_request
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def send_msg_by_uid(self, word, dst='filehelper'):
        url = self.base_uri + '/webwxsendmsg?pass_ticket=%s' % self.pass_ticket
        msg_id = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
        word = self.to_unicode(word)
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

    def upload_media(self, fpath, is_img=False):
        if not os.path.exists(fpath):
            print '[ERROR] File not exists.'
            return None
        url_1 = 'https://file.'+self.base_host+'/cgi-bin/mmwebwx-bin/webwxuploadmedia?f=json'
        url_2 = 'https://file2.'+self.base_host+'/cgi-bin/mmwebwx-bin/webwxuploadmedia?f=json'
        flen = str(os.path.getsize(fpath))
        ftype = mimetypes.guess_type(fpath)[0] or 'application/octet-stream'
        files = {
                'id': (None, 'WU_FILE_%s' % str(self.file_index)),
                'name': (None, os.path.basename(fpath)),
                'type': (None, ftype),
                'lastModifiedDate': (None, time.strftime('%m/%d/%Y, %H:%M:%S GMT+0800 (CST)')),
                'size': (None, flen),
                'mediatype': (None, 'pic' if is_img else 'doc'),
                'uploadmediarequest': (None, json.dumps({
                    'BaseRequest': self.base_request,
                    'ClientMediaId': int(time.time()),
                    'TotalLen': flen,
                    'StartPos': 0,
                    'DataLen': flen,
                    'MediaType': 4,
                    })),
                'webwx_data_ticket': (None, self.session.cookies['webwx_data_ticket']),
                'pass_ticket': (None, self.pass_ticket),
                'filename': (os.path.basename(fpath), open(fpath, 'rb'),ftype.split('/')[1]),
                }
        self.file_index += 1
        try:
            r = self.session.post(url_1, files=files)
            if json.loads(r.text)['BaseResponse']['Ret'] != 0:
                # 当file返回值不为0时则为上传失败，尝试第二服务器上传
                r = self.session.post(url_2, files=files)
            if json.loads(r.text)['BaseResponse']['Ret'] != 0:
                print '[ERROR] Upload media failure.'
                return None
            mid = json.loads(r.text)['MediaId']
            return mid
        except Exception,e:
            return None

    def send_file_msg_by_uid(self, fpath, uid):
        mid = self.upload_media(fpath)
        if mid is None or not mid:
            return False
        url = self.base_uri + '/webwxsendappmsg?fun=async&f=json&pass_ticket=' + self.pass_ticket
        msg_id = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
        data = {
                'BaseRequest': self.base_request,
                'Msg': {
                    'Type': 6,
                    'Content': ("<appmsg appid='wxeb7ec651dd0aefa9' sdkver=''><title>%s</title><des></des><action></action><type>6</type><content></content><url></url><lowurl></lowurl><appattach><totallen>%s</totallen><attachid>%s</attachid><fileext>%s</fileext></appattach><extinfo></extinfo></appmsg>" % (os.path.basename(fpath).encode('utf-8'), str(os.path.getsize(fpath)), mid, fpath.split('.')[-1])).encode('utf8'),
                    'FromUserName': self.my_account['UserName'],
                    'ToUserName': uid,
                    'LocalID': msg_id,
                    'ClientMsgId': msg_id, }, }
        try:
            r = self.session.post(url, data=json.dumps(data))
            res = json.loads(r.text)
            if res['BaseResponse']['Ret'] == 0:
                return True
            else:
                return False
        except Exception,e:
            return False

    def send_img_msg_by_uid(self, fpath, uid):
        mid = self.upload_media(fpath, is_img=True)
        if mid is None:
            return False
        url = self.base_uri + '/webwxsendmsgimg?fun=async&f=json'
        data = {
                'BaseRequest': self.base_request,
                'Msg': {
                    'Type': 3,
                    'MediaId': mid,
                    'FromUserName': self.my_account['UserName'],
                    'ToUserName': uid,
                    'LocalID': str(time.time() * 1e7),
                    'ClientMsgId': str(time.time() * 1e7), }, }
        if fpath[-4:] == '.gif':
            url = self.base_uri + '/webwxsendemoticon?fun=sys'
            data['Msg']['Type'] = 47
            data['Msg']['EmojiFlag'] = 2
        try:
            r = self.session.post(url, data=json.dumps(data))
            res = json.loads(r.text)
            if res['BaseResponse']['Ret'] == 0:
                return True
            else:
                return False
        except Exception,e:
            return False

    def get_user_id(self, name):
        if name == '':
            return None
        name = self.to_unicode(name)
        for contact in self.contact_list:
            if 'RemarkName' in contact and contact['RemarkName'] == name:
                return contact['UserName']
            elif 'NickName' in contact and contact['NickName'] == name:
                return contact['UserName']
            elif 'DisplayName' in contact and contact['DisplayName'] == name:
                return contact['UserName']
        for group in self.group_list:
            if 'RemarkName' in group and group['RemarkName'] == name:
                return group['UserName']
            if 'NickName' in group and group['NickName'] == name:
                return group['UserName']
            if 'DisplayName' in group and group['DisplayName'] == name:
                return group['UserName']

        return ''

    def send_msg(self, name, word, isfile=False):
        uid = self.get_user_id(name)
        if uid is not None:
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
                word = self.to_unicode(word)
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
        self.gen_qr_code(os.path.join(self.temp_pwd,'wxqr.png'))
        print '[INFO] Please use WeChat to scan the QR code .'

        result = self.wait4login()
        if result != SUCCESS:
            print '[ERROR] Web WeChat login failed. failed code=%s' % (result,)
            return

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
        if self.get_contact():
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
            show_image(qr_file_path)
            # img = Image.open(qr_file_path)
            # img.show()
        elif self.conf['qr'] == 'tty':
            print(qr.terminal(quiet_zone=1))

    def do_request(self, url):
        r = self.session.get(url)
        r.encoding = 'utf-8'
        data = r.text
        param = re.search(r'window.code=(\d+);', data)
        code = param.group(1)
        return code, data

    def wait4login(self):
        """
        http comet:
        tip=1, 等待用户扫描二维码,
               201: scaned
               408: timeout
        tip=0, 等待用户确认登录,
               200: confirmed
        """
        LOGIN_TEMPLATE = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s'
        tip = 1

        try_later_secs = 1
        MAX_RETRY_TIMES = 10

        code = UNKONWN

        retry_time = MAX_RETRY_TIMES
        while retry_time > 0:
            url = LOGIN_TEMPLATE % (tip, self.uuid, int(time.time()))
            code, data = self.do_request(url)
            if code == SCANED:
                print '[INFO] Please confirm to login .'
                tip = 0
            elif code == SUCCESS:  # 确认登录成功
                param = re.search(r'window.redirect_uri="(\S+?)";', data)
                redirect_uri = param.group(1) + '&fun=new'
                self.redirect_uri = redirect_uri
                self.base_uri = redirect_uri[:redirect_uri.rfind('/')]
                temp_host = self.base_uri[8:]
                self.base_host = temp_host[:temp_host.find("/")]
                return code
            elif code == TIMEOUT:
                print '[ERROR] WeChat login timeout. retry in %s secs later...' % (try_later_secs,)

                tip = 1  # 重置
                retry_time -= 1
                time.sleep(try_later_secs)
            else:
                print ('[ERROR] WeChat login exception return_code=%s. retry in %s secs later...' %
                       (code, try_later_secs))
                tip = 1
                retry_time -= 1
                time.sleep(try_later_secs)

        return code

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
        for host1 in ['webpush.', 'webpush2.']:
            self.sync_host = host1+self.base_host
            try:
                retcode = self.sync_check()[0]
            except:
                retcode = -1
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
        url = 'https://' + self.sync_host + '/cgi-bin/mmwebwx-bin/synccheck?' + urllib.urlencode(params)
        try:
            r = self.session.get(url, timeout=60)
            r.encoding = 'utf-8'
            data = r.text
            pm = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}', data)
            retcode = pm.group(1)
            selector = pm.group(2)
            return [retcode, selector]
        except:
            return [-1, -1]

    def sync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' \
                              % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            'SyncKey': self.sync_key,
            'rr': ~int(time.time())
        }
        try:
            r = self.session.post(url, data=json.dumps(params), timeout=60)
            r.encoding = 'utf-8'
            dic = json.loads(r.text)
            if dic['BaseResponse']['Ret'] == 0:
                self.sync_key = dic['SyncKey']
                self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                              for keyVal in self.sync_key['List']])
            return dic
        except:
            return None

    def get_icon(self, uid, gid=None):
        """
        获取联系人或者群聊成员头像
        :param uid: 联系人id
        :param gid: 群id，如果为非None获取群中成员头像，如果为None则获取联系人头像
        """
        if gid is None:
            url = self.base_uri + '/webwxgeticon?username=%s&skey=%s' % (uid, self.skey)
        else:
            url = self.base_uri + '/webwxgeticon?username=%s&skey=%s&chatroomid=%s' % (
            uid, self.skey, self.encry_chat_room_id_list[gid])
        r = self.session.get(url)
        data = r.content
        fn = 'icon_' + uid + '.jpg'
        with open(os.path.join(self.temp_pwd,fn), 'wb') as f:
            f.write(data)
        return fn

    def get_head_img(self, uid):
        """
        获取群头像
        :param uid: 群uid
        """
        url = self.base_uri + '/webwxgetheadimg?username=%s&skey=%s' % (uid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'head_' + uid + '.jpg'
        with open(os.path.join(self.temp_pwd,fn), 'wb') as f:
            f.write(data)
        return fn

    def get_msg_img_url(self, msgid):
        return self.base_uri + '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)

    def get_msg_img(self, msgid):
        """
        获取图片消息，下载图片到本地
        :param msgid: 消息id
        :return: 保存的本地图片文件路径
        """
        url = self.base_uri + '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_' + msgid + '.jpg'
        with open(os.path.join(self.temp_pwd,fn), 'wb') as f:
            f.write(data)
        return fn

    def get_voice_url(self, msgid):
        return self.base_uri + '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)

    def get_voice(self, msgid):
        """
        获取语音消息，下载语音到本地
        :param msgid: 语音消息id
        :return: 保存的本地语音文件路径
        """
        url = self.base_uri + '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'voice_' + msgid + '.mp3'
        with open(os.path.join(self.temp_pwd,fn), 'wb') as f:
            f.write(data)
        return fn

    def get_video_url(self, msgid):
        return self.base_uri + '/webwxgetvideo?msgid=%s&skey=%s' % (msgid, self.skey)

    def get_video(self, msgid):
        """
        获取视频消息，下载视频到本地
        :param msgid: 视频消息id
        :return: 保存的本地视频文件路径
        """
        url = self.base_uri + '/webwxgetvideo?msgid=%s&skey=%s' % (msgid, self.skey)
        headers = {'Range': 'bytes=0-'}
        r = self.session.get(url, headers=headers)
        data = r.content
        fn = 'video_' + msgid + '.mp4'
        with open(os.path.join(self.temp_pwd,fn), 'wb') as f:
            f.write(data)
        return fn

    def set_remarkname(self,uid,remarkname):#设置联系人的备注名
        url = self.base_uri + '/webwxoplog?lang=zh_CN&pass_ticket=%s' \
                              % (self.pass_ticket)
        remarkname = self.to_unicode(remarkname)
        params = {
            'BaseRequest': self.base_request,
            'CmdId': 2,
            'RemarkName': remarkname,
            'UserName': uid
        }
        try:
            r = self.session.post(url, data=json.dumps(params), timeout=60)
            r.encoding = 'utf-8'
            dic = json.loads(r.text)
            return dic['BaseResponse']['ErrMsg']
        except:
            return None
