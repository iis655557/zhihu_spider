"""
1. 首先要获取登录的二维码图片，经过分析发现一个问题
    a>url图片的地址中有一个随机的字符串；https://www.zhihu.com/api/v3/account/api/login/qrcode/fOq7nCDCQemA1zs7/image。
2. 需要分析随机字符串fOq7nCDCQemA1zs7的来源，发现是通过向https://www.zhihu.com/api/v3/account/api/login/qrcode发送一个POST请求，会返回一个JSON字符串，其中就包含这个随机字符串，但是在向它发送POST请求的时候，需要携带5个Cookie，所以，需要继续分析这5个Cookie的来源；
    注意：一般Cookie的值是服务端返回的，服务端向客户端传递数据一般通过Response Headers或者Reponse Body进行传递，所以重点观察Url中是否有Set-Cookie以及响应体中是否携带Cookie的值。
3. 由于登录需要的这个5个Cookie并不是一次性返回的，所以在抓包的时候一定要从第一个起始url(https://www.zhihu.com/signup?next=%2F)开始抓取，在抓取时同样注意不要切换 "知乎首页" 和 "设置"这两个选项卡，因为从别的选项卡切换到知乎选项卡，知乎默认是会发起请求，并且请求中携带重要的Cookie值。
4. 经过查找每一个Cookie的值，发现https://www.zhihu.com/signup?next=%2F会返回3个Cookie：tgw_l7_route、_zap、_xsrf；https://www.zhihu.com/udid会返回1个Cookie：d_c0；https://www.zhihu.com/api/v3/oauth/captcha?lang=en会返回1个Cookie：capsion_ticket；
5. 接下来，就可以模拟登录了，但是当访问知乎首页地址的时候，发现请求头中又多了一个Cookie: z_c0，所以不要认为只要登录成功了，就获取了全部的Cookie，就可以访问任何页面了，有可能在登录成功之后，网站会继续获取Set-Cookie，并添加到接下来的请求头中；
6. 需要分析z_c0的来源：https://www.zhihu.com/api/v3/account/api/login/qrcode/fOq7nCDCQemA1zs7/scan_info发送了一个GET请求，并且url当中需要使用fOq7nCDCQemA1zs7这个随机字符串。
7. 以上步骤完成，才可以向https://www.zhihu.com/发送请求，获取网页源代码。
"""
import requests, json
from http.cookiejar import LWPCookieJar
from PIL import Image

class ZhiHuSpider(object):
    def __init__(self):
        self.session = requests.Session()
        self.session.cookies = LWPCookieJar(filename='zhihu.txt')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'
        }

    def login(self):
        # 1. 获取tgw_l7_route、_zap、_xsrf
        self.session.get(url='https://www.zhihu.com/signup?next=%2F', headers=self.headers)
        # 2. 获取d_c0
        self.session.post(url='https://www.zhihu.com/udid', headers=self.headers)
        # 3. 获取capsion_ticket
        self.session.get(url='https://www.zhihu.com/api/v3/oauth/captcha?lang=en', headers=self.headers)
        # 4. 获取二维码需要的token这个随机字符串
        json_str = self.session.post(url='https://www.zhihu.com/api/v3/account/api/login/qrcode', headers=self.headers).text
        token = json.loads(json_str).get('token')
        print('token = ', token)
        # 5. 使用token拼接登录二维码的Url地址
        content = self.session.get(url='https://www.zhihu.com/api/v3/account/api/login/qrcode/{}/image'.format(token), headers=self.headers).content
        # 将图片写入到本地
        with open('qrcode.jpg', 'wb') as f:
            f.write(content)
        # 6. 使用Image()类打开本地图片
        img = Image.open('qrcode.jpg')
        img.show()

        # 7. 等待用户扫描登录
        result = input('登录成功输入OK: ')
        if result == 'ok':
            print('扫码登录成功')
            # 登录成功之后，self.session就可以得到登录之后返回的Cookie
            # 8. 获取z_c0这个Cookie，访问首页的时候，需要这个Cookie
            self.session.get(url='https://www.zhihu.com/api/v3/account/api/login/qrcode/{}/scan_info'.format(token), headers=self.headers)

            # 9. 将所有的Cookie信息，保存到.txt文件中
            self.session.cookies.save(ignore_discard=True, ignore_expires=True)

            return 'Success'
        else:
            return 'Error'

    def get_index(self):
        # 在请求知乎首页的时候，先尝试从本地加载Cookie，如果Cookie不存在则去登录；如果Cookie存在，但是已经失效，则重新登录；如果Cookie能正常使用，直接使用Cookie访问即可。
        try:
            self.session.cookies.load(filename='zhihu.txt', ignore_expires=True, ignore_discard=True)
            print('Cookie加载成功')
            # response = self.session.get(url='https://www.zhihu.com/', headers=self.headers, allow_redirects=False)
            response = self.session.get(url='https://www.zhihu.com/api/v3/feed/topstory/recommend?session_token=c29eac0100aa2bc8f3cee96288a09a92&desktop=true&page_number=2&limit=6&action=down&after_id=5', headers=self.headers)
            if response.status_code == 200:
                # 请求成功，并且cookie是可用的
                print(response.text)
            else:
                # 可能是Cookie不能使用了，此时需要重新登录，生成新的cookie信息，并保存在cookies.txt文件中
                result = self.login()
                if result == 'Success':
                    self.get_index()
        except Exception as e:
            # 本地文件不存在，此时在进行模拟登录
            print('Cookie加载失败')
            result = self.login()
            if result == 'Success':
                self.get_index()


if __name__ == '__main__':
    # allow_redirects=False：告诉服务器禁止url重定向
    # 如果没有设置这个参数，当客户端向https://www.zhihu.com/发送GET请求的时候，服务端发现没有登录，此时服务端会自动进行重定向到登录页面的url，得到的response.status_code是200；所以一个网页或者一个请求的状态码是200，并不代表着你成功的获取了数据。
    # response = requests.get(url='https://www.zhihu.com/', headers={
    #         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'
    #     }, allow_redirects=False)
    # if response.status_code == 200:
    #     print('登录成功')
    # elif response.status_code == 302:
    #     print('重定向请求，说明登录失败')

    obj = ZhiHuSpider()
    obj.get_index()

