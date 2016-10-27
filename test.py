#!/usr/bin/env python
# coding: utf-8

from wxbot import *
import os,shutil,datetime
RECORD_FOLDER = "records"
TEXT_NAME = "record_base"

class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        self.checkRecordFolder()
        if msg['msg_type_id'] == 3:
            if msg['content']['type'] == 0:
                self.handleGroupTextMessage(msg)
            if msg['content']['type'] == 4:
                self.handleGroupVoiceMessage(msg)

    def getRecordFolder(self, msg):
        record_folder = os.path.join(RECORD_FOLDER, msg['user']['id'])
        if not os.path.exists(record_folder):
            os.makedirs(record_folder)
        return record_folder

    def checkRecordFolder(self):
        record_folder = RECORD_FOLDER
        if not os.path.exists(RECORD_FOLDER):
            record_folder = os.makedirs(RECORD_FOLDER)
        return record_folder

    def checkGroupFolder(self,msg):
        if msg['user']['name']:
            groupName = msg['user']['name']
        else:
            groupName = msg['user']['id']
        folderPath = os.path.join(RECORD_FOLDER,groupName)
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
        return folderPath

    def handleGroupTextMessage(self,msg):
        contentPath = os.path.join(self.checkGroupFolder(msg),datetime.date.today().strftime('%Y_%m_%d') + '.txt')
        f = open(contentPath,'a')
        f.write(msg['content']['user']['name'].encode('utf-8')+':\n')
        f.write(msg['content']['data'].encode('utf-8')+'\n')
        f.close()

    def handleGroupVoiceMessage(self,msg):
        msg_id = msg['msg_id']
        folderPath = os.path.join(self.temp_pwd,self.get_voice(msg_id))
        timeStamp = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M')
        newName = msg['content']['user']['name']+'_'+timeStamp+'.mp3'
        os.rename(folderPath,os.path.join(self.temp_pwd,newName))
        shutil.move(os.path.join(self.temp_pwd,newName),self.checkGroupFolder(msg))
'''
    def schedule(self):
        self.send_msg(u'张三', u'测试')
        time.sleep(1)
'''

def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.run()

if __name__ == '__main__':
    main()
