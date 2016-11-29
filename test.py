#!/usr/bin/env python
# coding: utf-8

from wxbot import *
import cPickle

bot = None
pickleFileName = u"wxbot.json"


class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            self.send_msg_by_uid(u'hi', msg['user']['id'])
            # self.send_img_msg_by_uid("img/1.png", msg['user']['id'])
            # self.send_file_msg_by_uid("img/1.png", msg['user']['id'])

    def initOnPickle(self):
        if self.init():
            print '{initOnPick} Web WeChat init succeed .'
        else:
            print '{initOnPick} Web WeChat init failed'
            # 保持的对象失效了.所以留着没用就删除吧
            os.remove(pickleFileName)
            return
            self.status_notify()
            self.get_contact()
        print '{initOnPick} Get %d contacts' % len(self.contact_list)
        print '{initOnPick} Start to process messages .'
        self.proc_msg()
        # update sassion
        saveSession(self)


'''
    def schedule(self):
        self.send_msg(u'张三', u'测试')
        time.sleep(1)
'''




def saveSession(ob):
    if ob:
        cPickle.dump(ob, open(pickleFileName, 'wb'))
    else:
        print (u"对象传递出错,无法保存")


def getSession():
    return cPickle.load(open(pickleFileName, 'rb'))


def main():
    global bot
    if os.path.exists(pickleFileName):
        bot = getSession()
        bot.initOnPickle()
    else:
        # bot.DEBUG = True

        bot = MyWXBot()
        bot.DEBUG = True
        bot.conf['qr'] = 'png'
        bot.run()


if __name__ == '__main__':
    #我是新手,代码写的烂.如果有问题请大神们修改代码吧. 谢谢!
    # 此处Ctrl+C 只能在看到 Get 5 contacts 果断 Ctrl+C 就能被捕捉到然后保存bot对象,
    #保存完了之后下次就不用扫码了 经测试3分钟内有效的.
    #猜想 把 持久化的对象经过网络转移到别的机器上运行应该也是没问题的.没测试过! 

    try:
        main()
    except KeyboardInterrupt:
        saveSession(ob=bot)
        sys.exit(0)
