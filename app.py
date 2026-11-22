# -*- coding: utf-8 -*-
"""葫芦侠 · 一键签到（独立 Flask 版）

只保留账号密码登录 + 全部板块一键签到，不包含送葫芦/评论监控。
"""

import os
import secrets
import threading

from flask import Flask, jsonify, render_template, request, session

from hlx_api import HlxClient, HlxError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
try:
    app.json.ensure_ascii = False
except AttributeError:
    app.config["JSON_AS_ASCII"] = False

SESSIONS = {}
LOCK = threading.RLock()


def _client():
    sid = session.get("sid")
    if not sid:
        return None
    with LOCK:
        return SESSIONS.get(sid)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    account = (data.get("account") or "").strip()
    password = data.get("password") or ""
    if not account or not password:
        return jsonify({"success": False, "msg": "请输入账号和密码"})

    client = HlxClient()
    try:
        info = client.login(account, password)
    except HlxError as exc:
        return jsonify({"success": False, "msg": str(exc)})
    except Exception as exc:
        return jsonify({"success": False, "msg": "登录异常: %s" % exc})

    sid = secrets.token_urlsafe(24)
    with LOCK:
        SESSIONS[sid] = client
    session["sid"] = sid
    return jsonify({
        "success": True,
        "nick": info.get("nick") or "",
        "uid": info.get("user_id") or 0,
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    sid = session.get("sid")
    if sid:
        with LOCK:
            SESSIONS.pop(sid, None)
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me")
def api_me():
    client = _client()
    if client is None:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "nick": client.nick,
        "uid": client.user_id,
    })


@app.route("/api/checkin", methods=["POST"])
def api_checkin():
    client = _client()
    if client is None:
        return jsonify({"success": False, "msg": "请先登录"}), 401
    try:
        ok_count, total, results = client.check_in_all()
    except HlxError as exc:
        return jsonify({"success": False, "msg": "签到失败: %s" % exc})
    except Exception as exc:
        return jsonify({"success": False, "msg": "签到异常: %s" % exc})

    for item in results:
        if not item.get("ok"):
            print("[WARN] 签到失败 %s(%s): %s" % (
                item.get("title") or "", item.get("cat_id"), item.get("msg")))
    print("[INFO] 一键签到完成：%d/%d" % (ok_count, total))
    return jsonify({
        "success": ok_count > 0,
        "count": ok_count,
        "total": total,
        "msg": "签到完成：%d/%d 个板块成功" % (ok_count, total),
        "results": results,
    })


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5002"))
    print("=" * 50)
    print("  葫芦侠一键签到 · 独立版")
    print("  访问: http://127.0.0.1:%s" % port)
    print("=" * 50)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
