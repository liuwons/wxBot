# wxBot [![star this repo](http://github-svg-buttons.herokuapp.com/star.svg?user=liuwons&repo=wxBot&style=flat&background=1081C1)](http://github.com/liuwons/wxBot) [![fork this repo](http://github-svg-buttons.herokuapp.com/fork.svg?user=liuwons&repo=wxBot&style=flat&background=1081C1)](http://github.com/liuwons/wxBot/fork) ![python](https://img.shields.io/badge/python-2.7-ff69b4.svg)

Python包装WEB微信实现的微信机器人框架。可以很容易地实现微信机器人。

## 依赖
程序用到了Python requests 和 pyqrcode库，使用之前需要安装这两个库:

```bash
pip install requests
pip install pyqrcode
```

## 快速开发
### 代码

利用 **wxBot** 最简单的方法就是继承WXBot类并实现handle_msg_all函数，然后实例化子类并run，如下的代码对所有的文本消息回复 hi 。
```python
#!/usr/bin/env python
# coding: utf-8

from wxbot import *

class MyWXBot(WXBot):
    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 5:
            self.send_msg(msg['user_name'], 'hi')

def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.run()

if __name__ == '__main__':
    main()
```

### 运行

直接用python运行代码(如运行测试代码main.py):

``` python
python main.py
```

### 登录微信

程序运行之后，会在当前目录下生成二维码图片文件 qr.jpg ，用微信扫描此二维码并按操作指示确认登录网页微信。


![1](img/1.png)

## 效果展示
测试代码main.py的运行效果：

![向机器人发送消息](img/send_msg.png)

![后台](img/backfront.jpg)
