# -*- coding: utf-8 -*-
"""葫芦侠 API：账号登录 + 一键签到（独立版）"""

import hashlib
import json
import os
import time
import uuid
from urllib.parse import urlencode

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEVICE_FILE = os.path.join(DATA_DIR, "device.json")

BASE = "http://floor.huluxia.com"
LOGIN_BASE = "https://floor.huluxia.com"
UA = "okhttp/3.8.1"

SALT_A = "fa1c28a5b62e79c3e63d9030b6142e4b"


def _load_device():
    """设备标识只保存在本地 data/device.json，不提交到仓库。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    saved = {}
    try:
        with open(DEVICE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            if isinstance(raw, dict):
                saved = raw
    except (OSError, ValueError):
        saved = {}

    device_code = (os.environ.get("HLX_DEVICE_CODE") or
                   saved.get("device_code") or
                   "[d]" + str(uuid.uuid4()))
    android_id = (os.environ.get("HLX_ANDROID_ID") or
                  saved.get("android_id") or
                  uuid.uuid4().hex)
    if not saved or saved.get("device_code") != device_code \
            or saved.get("android_id") != android_id:
        try:
            with open(DEVICE_FILE, "w", encoding="utf-8") as f:
                json.dump({"device_code": device_code,
                           "android_id": android_id}, f, indent=2)
        except OSError:
            pass
    return device_code, android_id


DEVICE_CODE, HLX_ANDROID_ID = _load_device()

APP_VERSION = "4.4.1.6"
VERSION_CODE = "440106"
MARKET_ID = "tool_xiaomi"
PHONE_BRAND = "MI"


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sign_login(account, password_md5, device_code=DEVICE_CODE):
    raw = ("account" + account +
           "device_code" + device_code +
           "password" + password_md5 +
           "voice_code" + "")
    return md5(raw + SALT_A)


def sign_checkin(cat_id, timestamp):
    """签到签名：cat_id + time + SALT_A，MD5 小写。"""
    return md5("cat_id" + str(cat_id) + "time" + str(timestamp) + SALT_A)


class HlxError(Exception):
    def __init__(self, message, payload=None):
        super(HlxError, self).__init__(message)
        self.message = message
        self.payload = payload


class HlxClient(object):
    def __init__(self, timeout=25):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Accept-Encoding": "gzip",
            "Connection": "close",
        })
        self.key = ""
        self.user_id = 0
        self.nick = ""
        self.device_code = DEVICE_CODE

    def _request_json(self, method, url, **kwargs):
        last_err = None
        for attempt in range(3):
            try:
                resp = self.session.request(method, url, timeout=self.timeout,
                                            **kwargs)
                if resp.status_code != 200:
                    raise HlxError("HTTP %d" % resp.status_code)
                try:
                    return resp.json()
                except ValueError:
                    raise HlxError("接口返回不是 JSON")
            except (requests.RequestException, HlxError) as exc:
                last_err = exc
                if attempt < 2:
                    time.sleep(1.5)
        if isinstance(last_err, HlxError):
            raise last_err
        raise HlxError("网络错误: %s" % last_err)

    def login(self, account, password):
        account = (account or "").strip()
        password = password or ""
        if not account or not password:
            raise HlxError("请输入账号和密码")

        password_md5 = md5(password)
        params = {
            "device_code": self.device_code,
            "voice_code": "",
            "account": account,
            "login_type": "2",
            "password": password_md5,
            "phone_brand_type": PHONE_BRAND,
            "hlx_android_id": HLX_ANDROID_ID,
        }
        params["sign"] = sign_login(account, password_md5, self.device_code)
        data = self._request_json(
            "GET", LOGIN_BASE + "/account/login/ANDROID/4.1.8", params=params)

        key = data.get("_key") or ""
        if not key:
            raise HlxError(data.get("msg") or "登录失败", data)
        user = data.get("user") or {}
        self.key = key
        self.user_id = int(user.get("userID") or data.get("userID")
                           or data.get("uid") or 0)
        self.nick = (user.get("nick") or data.get("nick") or "").strip()
        return {"user_id": self.user_id, "nick": self.nick}

    def _base_params(self):
        return {
            "platform": "2",
            "gkey": "000000",
            "app_version": APP_VERSION,
            "versioncode": VERSION_CODE,
            "market_id": MARKET_ID,
            "_key": self.key,
            "device_code": self.device_code,
            "phone_brand_type": PHONE_BRAND,
        }

    def get_categories(self):
        params = self._base_params()
        params["is_hidden"] = "0"
        data = self._request_json(
            "GET", BASE + "/category/list/ANDROID/2.0", params=params)
        categories = data.get("categories") or []
        result = []
        for cat in categories:
            try:
                cid = int(cat.get("categoryID"))
            except (TypeError, ValueError):
                continue
            if cid > 0:
                result.append({"id": cid, "title": cat.get("title") or ""})
        return result

    def sign_in_category(self, category_id):
        timestamp = str(int(time.time() * 1000))
        params = self._base_params()
        params["cat_id"] = str(category_id)
        params["time"] = timestamp
        body = {"sign": sign_checkin(category_id, timestamp)}
        data = self._request_json(
            "POST", BASE + "/user/signin/ANDROID/4.1.8",
            params=params, data=body)
        ok = str(data.get("status")) == "1"
        msg = (data.get("msg") or data.get("message") or "").strip()
        if ok:
            msg = msg or "签到成功"
        else:
            msg = msg or "签到失败"
        return ok, msg

    def check_in_all(self):
        categories = self.get_categories()
        if not categories:
            raise HlxError("没有获取到板块列表")
        results = []
        success = 0
        for cat in categories:
            try:
                ok, msg = self.sign_in_category(cat["id"])
            except HlxError as exc:
                ok, msg = False, str(exc)
            results.append({
                "cat_id": cat["id"],
                "title": cat["title"],
                "ok": ok,
                "msg": msg,
            })
            if ok:
                success += 1
            time.sleep(0.2)
        return success, len(categories), results
