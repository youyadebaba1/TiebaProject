from django.shortcuts import render, redirect
from django.shortcuts import HttpResponse
from . import utils
import uuid
from .models import Tieba, User, Sign, Data, Robot
from django.shortcuts import reverse
import logging
import requests
import json

# Create your views here.
logging.basicConfig(filename='app.log', format='%(asctime)s %(filename)s[line:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d')


def test(request):
    u = User.objects.get(username='旬阳城管')
    res = utils.get_at(u.bduss)
    at_num = res['message']['atme']
    at_list = res['at_list']
    for i in range(int(at_num)):
        post_id = at_list[i]['post_id']
        title = at_list[i]['title']
        content = at_list[i]['content'].strip('@旬阳城管 ').split(',')
        fname = at_list[i]['fname']
        is_fans = at_list[i]['replyer']['is_fans']
        thread_id = at_list[i]['thread_id']
        name = at_list[i]['replyer']['name']
        time = at_list[i]['time']
        fid = utils.get_fid(fname)
        if is_fans != '1':
            reply_content = '只有我的粉丝才可以at我 -_- #(乖)'
            utils.client_LZL(u.bduss, fname, fid, reply_content, post_id, thread_id)
            return HttpResponse('aaaa')
        else:
            try:
                user = User.objects.get(username=name)
                if content[0] == 'reply':
                    Tieba.objects.create(name=fname, fid=fid, tid=thread_id, isLou=False, time=content[1],
                                         user_id=user.pk)
                    reply_content = fname + '吧' + content[1] + "分钟/贴添加完毕"
                elif content[0] == 'info':
                    reply_content = '已签到：' + str(user.已签到()) + '未签到' + str(user.未签到()) + '已云回' + str(
                        user.tieba_set.all().count())
                else:
                    reply_content = '命令错误 -_- #(乖)'
            except Exception:
                try:
                    Robot.objects.get(thread_id=thread_id, post_id=post_id)
                except Exception:
                    if Robot.objects.filter(username=name).count() > 5:
                        reply_content = '今天不陪你玩儿了 -_- #(乖)'
                    else:
                        reply_content = '#(滑稽)'
                    Robot.objects.create(thread_id=thread_id, post_id=post_id, title=title, username=name,
                                         is_fans=is_fans, fname=fname, content=content, time=time)
            finally:
                utils.client_LZL(u.bduss, fname, fid, reply_content, post_id, thread_id)
                return HttpResponse('aaaa')


def index(request):
    if request.method == "GET":
        data = {}
        data['user'] = User.objects.all().count()
        data['yunhui'] = Data.objects.get(id=1).success
        data['sign'] = Sign.objects.filter(is_sign=True).count()
        data['unsign'] = Sign.objects.filter(is_sign=False).count()
        return render(request, 'index.html',{'data':data})
    elif request.method == "POST":
        bduss = request.POST.get('bduss', None)
        if bduss is not None:
            if len(bduss) != 192:
                return render(request,'index.html',{'msg':'BDUSS错误～'})
            name = utils.get_name(bduss)
            if name:
                token = str(uuid.uuid1())
                try:
                    user = User.objects.get(username=name)
                    user.bduss = bduss
                except Exception:
                    user = User(bduss=bduss,username=name, token=token)
                finally:
                    user.save()
                    request.session['user'] = user.username
                    request.session['token'] = user.token
                    return redirect(reverse(info))
            else:
                return render(request, 'index.html', {'msg': 'BDUSS错误～'})


def info(request):
    if request.method == "GET":
        token = request.session.get('token', None)
        if token:
            u = User.objects.get(token=token)
            t = u.tieba_set.all()
            return render(request, 'info.html', {'data': t})
        else:
            return render(request, 'info.html')
    elif request.method == "POST":
        return redirect('/')


def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    elif request.method == "POST":
        val = request.POST.get('unsure')
        if len(val) != 36:
            return render(request, 'login.html', {'msg': 'SECRET 错误'})
        else:
            try:
                u = User.objects.get(token=val)
                request.session['user'] = u.username
                request.session['token'] = u.token
                return redirect(reverse(info))
            except Exception:
                return render(request, 'login.html', {'msg': 'SECRET 错误'})


def logout(request):
    del request.session['user']
    del request.session['token']
    return redirect(reverse(index))


def delete(request, id):
    if request.method == "POST":
        return HttpResponse("请求方法错误")
    elif request.method == "GET":
        user = request.session.get('user', None)
        if user:
            try:
                u = User.objects.get(username=user)
                t = Tieba.objects.get(id=id, user=u)
                t.delete()
                return HttpResponse('success')
            except Exception:
                return render(request, 'info.html', {'msg': '越权访问'})
        else:
            return render(request, 'info.html', {'msg': '未登录'})


def switch(request, id):
    if request.method == "POST":
        return HttpResponse("请求方法错误")
    elif request.method == "GET":
        user = request.session.get('user', None)
        if user:
            try:
                u = User.objects.get(username=user)
                t = Tieba.objects.get(id=id, user=u)
                if t.stop:
                    t.stop = False
                else:
                    t.stop = True
                t.save()
                return HttpResponse('success')
            except Exception:
                return render(request, 'info.html', {'msg': '越权访问'})
        else:
            return render(request, 'info.html', {'msg': '未登录'})


def add(request):
    if request.method == 'GET':
        return render(request, 'add.html')
    elif request.method == 'POST':
        username = request.session.get('user')
        user = User.objects.get(username=username)
        # 测试阶段限制每人5条帖子
        tielist = user.tieba_set.all().count()
        if tielist >= 5:
            return render(request, 'add.html', {'msg': '测试阶段限制每人5条帖子', 'type': 'error'})
        lou = request.POST.get('lou')
        tid = request.POST.get('tid')
        _time = request.POST.get('time')
        floor = request.POST.get('floor')
        tbna = utils.get_kw(tid)
        fid = utils.get_fid(tbna)
        if lou == 'yes':
            louBin = True
            Qid = utils.get_qid(tid, floor)
        elif lou == 'no':
            louBin = False
            Qid = None
        t = Tieba(name=tbna, fid=fid, tid=tid, isLou=louBin, floor=floor, qid=Qid, time=_time, user_id=user.pk)
        t.save()
        msg = '帖子' + tid + '添加成功'
        return render(request, 'add.html', {'msg': msg})


def bduss(request):
    s = requests.session()
    if request.method == 'GET':
        url1 = 'https://passport.baidu.com/v2/api/getqrcode?lp=pc&apiver=v3&tpl=netdisk'
        headers1 = {
            'Connection': 'keep-alive',
            'Host': 'passport.baidu.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
        }
        res1 = s.get(url=url1, headers=headers1).json()
        global sign
        sign = res1['sign']
        print(sign)
        imgurl = 'https://' + res1['imgurl']
        return render(request, 'bduss.html', {'img': imgurl})
    elif request.method == 'POST':
        url2 = 'https://passport.baidu.com/channel/unicast?channel_id={}&callback=&tpl=netdisk&apiver=v3'.format(sign)
        headers2 = {
            'Host': 'passport.baidu.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
        }
        res2 = s.get(url=url2, headers=headers2).text[1:-2]
        data = json.loads(res2)
        data = json.loads(data['channel_v'])
        v = data['v']
        url3 = 'https://passport.baidu.com/v3/login/main/qrbdusslogin?bduss={}&u=https%253A%252F%252Fpan.baidu.com%252Fdisk%252Fhome&loginVersion=v4&qrcode=1&tpl=netdisk&apiver=v3&traceid=&callback=%27'.format(
            v)
        response = s.get(url3)
        bduss = response.cookies['BDUSS']
        return render(request, 'bduss.html', {'bduss': bduss})


def about(request):
    return render(request, 'about.html')
