#!/usr/bin/env python
# coding: utf-8
from collections import defaultdict
import pyqrcode
import requests
import json
import xml.dom.minidom
import multiprocessing
import urllib
import time, re, sys, os, random

def utf82gbk(string):
    return string.decode('utf8').encode('gbk')

def make_unicode(data):
    if not data:
        return data
    result = None
    if type(data) == unicode:
        result = data
    elif type(data) == str:
        result = data.decode('utf-8')
    return result

class WXBot:
    def __init__(self):
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = ''
        self.redirect_uri= ''
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.device_id = 'e' + repr(random.random())[2:17]
        self.base_request = {}
        self.sync_key_str = ''
        self.sync_key = []
        self.user = []
        self.member_list = []
        self.contact_list = []  # contact list
        self.public_list = []   # public account list
        self.group_list = []    # group chat list
        self.special_list = []  # special list account
        self.sync_host = ''
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5'})

        self.conf = {'qr': 'png',}

    def get_uuid(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time())*1000 + random.randint(1,999),
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
            qr.png(qr_file_path)
        elif self.conf['qr'] == 'tty':
            print(qr.terminal(quiet_zone=1))
            
    def wait4login(self, tip):
        time.sleep(tip)
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (tip, self.uuid, int(time.time()))
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
        self.user = dic['User']
        self.sync_key_str = '|'.join([ str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.sync_key['List'] ])
        return dic['BaseResponse']['Ret'] == 0

    def status_notify(self):
        url = self.base_uri + '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % (self.pass_ticket)
        self.base_request['Uin'] = int(self.base_request['Uin'])
        params = {
            'BaseRequest': self.base_request,
            "Code": 3,
            "FromUserName": self.user['UserName'],
            "ToUserName": self.user['UserName'],
            "ClientMsgId": int(time.time())
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        return dic['BaseResponse']['Ret'] == 0

    def get_contact(self):
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (self.pass_ticket, self.skey, int(time.time()))
        r = self.session.post(url, data='{}')
        r.encoding = 'utf-8'
        if self.DEBUG:
            with open('contacts.json', 'w') as f:
                f.write(r.text.encode('utf-8'))
        dic = json.loads(r.text)
        self.member_list = dic['MemberList']

        SpecialUsers = ['newsapp','fmessage','filehelper','weibo','qqmail','fmessage','tmessage','qmessage','qqsync','floatbottle','lbsapp','shakeapp','medianote',
            'qqfriend','readerapp','blogapp','facebookapp','masssendapp','meishiapp','feedsapp','voip','blogappweixin','weixin','brandsessionholder','weixinreminder','wxid_novlwrv3lqwv11',
            'gh_22b87fa7cb3c','officialaccounts','notification_messages','wxid_novlwrv3lqwv11','gh_22b87fa7cb3c','wxitil','userexperience_alarm','notification_messages']

        self.contact_list = []
        self.public_list = []
        self.special_list = []
        self.group_list = []
        for contact in self.member_list:
            if contact['VerifyFlag'] & 8 != 0: # public account
                self.public_list.append(contact)
            elif contact['UserName'] in SpecialUsers: # special account
                self.special_list.append(contact)
            elif contact['UserName'].find('@@') != -1: # group
                self.group_list.append(contact)
            elif contact['UserName'] == self.user['UserName']: # self
                pass
            else:
                self.contact_list.append(contact)

        if self.DEBUG:
            with open('contact_list.json', 'w') as f:
                f.write(json.dumps(self.contact_list))
            with open('special_list.json', 'w') as f:
                f.write(json.dumps(self.special_list))
            with open('group_list.json', 'w') as f:
                f.write(json.dumps(self.group_list))
            with open('public_list.json', 'w') as f:
                f.write(json.dumps(self.public_list))

        return True

    def batch_get_contact(self):
        url = self.base_uri + '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            "Count": len(self.group_list),
            "List": [ {"UserName": g['UserName'], "EncryChatRoomId":""} for g in self.group_list ]
        }
        r = self.session.post(url, data=params)
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        return True

    def test_sync_check(self):
        for host in ['webpush', 'webpush2']:
            self.sync_host = host
            [retcode, selector] = self.sync_check()
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
        r = self.session.get(url)
        r.encoding = 'utf-8'
        data = r.text
        pm = re.search(r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    def sync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            'SyncKey': self.sync_key,
            'rr': ~int(time.time())
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        if dic['BaseResponse']['Ret'] == 0:
            self.sync_key = dic['SyncKey']
            self.sync_key_str = '|'.join([ str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.sync_key['List'] ])
        return dic

    def get_icon(self, id):
        url = self.base_uri + '/webwxgeticon?username=%s&skey=%s' % (id, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_'+id+'.jpg'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    def get_head_img(self, id):
        url = self.base_uri + '/webwxgetheadimg?username=%s&skey=%s' % (id, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_'+id+'.jpg'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    def get_msg_img_url(self, msgid):
        return self.base_uri + '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)

    def get_msg_img(self, msgid):
        url = self.base_uri + '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'img_'+msgid+'.jpg'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    def get_voice_url(self, msgid):
        return self.base_uri + '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)

    def get_voice(self, msgid):
        url = self.base_uri + '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)
        r = self.session.get(url)
        data = r.content
        fn = 'voice_'+msgid+'.mp3'
        with open(fn, 'wb') as f:
            f.write(data)
        return fn

    #Get the NickName or RemarkName of an user by user id
    def get_user_remark_name(self, uid):
        name = 'unknown group' if uid[:2] == '@@' else 'stranger'
        for member in self.member_list:
            if member['UserName'] == uid:
                name = member['RemarkName'] if member['RemarkName'] else member['NickName']
        return name

    #Get user id of an user
    def get_user_id(self, name):
        for member in self.member_list:
            if name == member['RemarkName'] or name == member['NickName'] or name == member['UserName']:
                return member['UserName']
        return None

    def get_user_type(self, wx_user_id):
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
        return 'unknown'

    '''
    msg:
        user_type
        msg_id
        msg_type_id
        user_id
        user_name
        content
    '''
    def handle_msg_all(self, msg):
        pass

    '''
    msg_type_id:
        1 -> Location
        2 -> FileHelper
        3 -> Self
        4 -> Group
        5 -> User Text Message
        6 -> Image
        7 -> Voice
        8 -> Recommend
        9 -> Animation
        10 -> Share
        11 -> Video
        12 -> Video Call
        13 -> Redraw
        14 -> Init Message
        99 -> Unknown
    '''
    def handle_msg(self, r):
        for msg in r['AddMsgList']:
            mtype = msg['MsgType']

            wx_user_id = msg['FromUserName']
            user_type = self.get_user_type(wx_user_id)

            name = self.get_user_remark_name(wx_user_id)
            content = msg['Content'].replace('&lt;','<').replace('&gt;','>')
            msg_id = msg['MsgId']
            msg_type_id = 99


            if mtype == 51: #init message
                msg_type_id = 14
            elif mtype == 1:
                if content.find('http://weixin.qq.com/cgi-bin/redirectforward?args=') != -1:
                    r = self.session.get(content)
                    r.encoding = 'gbk'
                    data = r.text
                    pos = self.search_content('title', data, 'xml')
                    msg_type_id = 1
                    content = {'location': pos, 'xml': data}
                    if self.DEBUG:
                        print '[Location] %s : I am at %s ' % (name, pos)

                elif msg['ToUserName'] == 'filehelper':
                    msg_type_id = 2
                    content = content.replace('<br/>','\n')
                    if self.DEBUG:
                        print '[File] %s : %s' % (name, )

                elif msg['FromUserName'] == self.user['UserName']: #self
                    msg_type_id = 3

                elif msg['FromUserName'][:2] == '@@':
                    [people, content] = content.split(':<br/>')
                    group = self.get_user_remark_name(msg['FromUserName'])
                    name = self.get_user_remark_name(people)
                    msg_type_id = 4
                    content = {'group_id': msg['FromUserName'], 'group_name': group, 'user': people, 'user_name': name, 'msg': content}
                    if self.DEBUG:
                        print '[Group] |%s| %s: %s' % (group, name, content.replace('<br/>','\n'))

                else:
                    msg_type_id = 5
                    if self.DEBUG:
                        print '[Text] ', name, ' : ', content

            elif mtype == 3:
                msg_type_id = 6
                content = self.get_msg_img_url(msg_id)
                if self.DEBUG:
                    image = self.get_msg_img(msg_id)
                    print '[Image] %s : %s' % (name, image)

            elif mtype == 34:
                msg_type_id = 7
                content = self.get_voice_url(msg_id)
                if self.DEBUG:
                    voice = self.get_voice(msg_id)
                    print '[Voice] %s : %s' % (name, voice)

            elif mtype == 42:
                msg_type_id = 8

                info = msg['RecommendInfo']
                content = {}
                content['nickname'] = info['NickName']
                content['alias'] = info['Alias']
                content['province'] = info['Province']
                content['city'] = info['City']
                content['gender'] = ['unknown', 'male', 'female'][info['Sex']]
                if self.DEBUG:
                    print '[Recommend] %s : ' % name
                    print '========================='
                    print '= NickName: %s' % info['NickName']
                    print '= Alias: %s' % info['Alias']
                    print '= Local: %s %s' % (info['Province'], info['City'])
                    print '= Gender: %s' % ['unknown', 'male', 'female'][info['Sex']]
                    print '========================='

            elif mtype == 47:
                msg_type_id = 9
                url = self.search_content('cdnurl', content)
                content = url
                if self.DEBUG:
                    print '[Animation] %s : %s' % (name, url)

            elif mtype == 49:
                msg_type_id = 10
                appMsgType = defaultdict(lambda : "")
                appMsgType.update({5:'link', 3:'music', 7:'weibo'})
                content = {'type': appMsgType[msg['AppMsgType']], 'title': msg['FileName'], 'desc': self.search_content('des', content, 'xml'), 'url': msg['Url'], 'from': self.search_content('appname', content, 'xml')}
                if self.DEBUG:
                    print '[Share] %s : %s' % (name, appMsgType[msg['AppMsgType']])
                    print '========================='
                    print '= title: %s' % msg['FileName']
                    print '= desc: %s' % self.search_content('des', content, 'xml')
                    print '= link: %s' % msg['Url']
                    print '= from: %s' % self.search_content('appname', content, 'xml')
                    print '========================='

            elif mtype == 62:
                msg_type_id = 11
                if self.DEBUG:
                    print '[Video] ', name, ' sent you a video, please check on mobiles'

            elif mtype == 53:
                msg_type_id = 12
                if self.DEBUG:
                    print '[Video Call] ', name, ' call you'
            elif mtype == 10002:
                msg_type_id = 13
                if self.DEBUG:
                    print '[Redraw] ', name, ' redraw back a message'
            else:
                msg_type_id = 99
                if self.DEBUG:
                    print '[Unknown] : %s' % str(mtype)
                    print msg
            message = {'user_type': user_type, 'msg_id':msg_id, 'msg_type_id': msg_type_id, 'content': content, 'user_id': msg['FromUserName'], 'user_name': name}
            self.handle_msg_all(message)

    def schedule(self):
        pass

    def proc_msg(self):
        self.test_sync_check()
        while True:
            [retcode, selector] = self.sync_check()
            if retcode == '1100': # User have login on mobile
                pass
            elif retcode == '0':
                if selector == '2':
                    r = self.sync()
                    if r is not None:
                        self.handle_msg(r)
                elif selector == '7': # Play WeChat on mobile
                    r = self.sync()
                    if r is not None:
                        self.handle_msg(r)
                elif selector == '0':
                    time.sleep(1)
            self.schedule()

    def send_msg_by_uid(self, word, dst = 'filehelper'):
        url = self.base_uri + '/webwxsendmsg?pass_ticket=%s' % (self.pass_ticket)
        msg_id = str(int(time.time()*1000)) + str(random.random())[:5].replace('.','')
        params = {
            'BaseRequest': self.base_request,
            'Msg': {
                "Type": 1,
                "Content": make_unicode(word),
                "FromUserName": self.user['UserName'],
                "ToUserName": dst,
                "LocalID": msg_id,
                "ClientMsgId": msg_id
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        r = self.session.post(url, data = data, headers = headers)
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def send_msg(self, name, word, isfile = False):
        uid = self.get_user_id(name)
        if uid:
            if isfile:
                with open(word, 'r') as f:
                    result = True
                    for line in f.readlines():
                        line = line.replace('\n','')
                        print '-> '+name+': '+line
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

    def search_content(self, key, content, fmat = 'attr'):
        if fmat == 'attr':
            pm = re.search(key+'\s?=\s?"([^"<]+)"', content)
            if pm: return pm.group(1)
        elif fmat == 'xml':
            pm=re.search('<{0}>([^<]+)</{0}>'.format(key),content)
            if pm: return pm.group(1)
        return 'unknown'

    def run(self):
        self.get_uuid()
        self.gen_qr_code('qr.png')
        print '[INFO] Please use WeCaht to scan the QR code .'
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
