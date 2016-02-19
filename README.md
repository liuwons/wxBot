# wxBot [![star this repo](http://github-svg-buttons.herokuapp.com/star.svg?user=liuwons&repo=wxBot&style=flat&background=1081C1)](http://github.com/liuwons/wxBot) [![fork this repo](http://github-svg-buttons.herokuapp.com/fork.svg?user=liuwons&repo=wxBot&style=flat&background=1081C1)](http://github.com/liuwons/wxBot/fork) ![python](https://img.shields.io/badge/python-2.7-ff69b4.svg)

Python包装的网页微信API。可以很容易地实现微信机器人。

## Dependencies
程序用到了Python requests 和 pyqrcode库，使用之前需要安装这两个库:

```bash
pip install requests
pip install pyqrcode
```

## Example
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

直接用python运行代码(如代码为main.py时)

``` python
python main.py
```

### 登录微信

程序运行之后，会在当前目录下生成二维码图片文件 qr.jpg ，用微信扫描此二维码并按操作指示确认登录网页微信。


![1](img/1.png)

## Demo
利用 **[图灵机器人](http://www.tuling123.com/)** 做自动回复之后，通过测试账号发送各种消息的效果：

![向机器人发送消息](img/send_msg.png)

![后台](img/backfront.jpg)
