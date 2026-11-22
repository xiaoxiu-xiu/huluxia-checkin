(function () {
    "use strict";

    var $ = function (id) { return document.getElementById(id); };

    async function api(path, options) {
        var opts = options || {};
        if (!opts.headers) opts.headers = {};
        if (opts.body) opts.headers["Content-Type"] = "application/json";
        opts.credentials = "same-origin";
        var resp = await fetch(path, opts);
        if (resp.status === 401) {
            showLogin();
            return { success: false, msg: "登录已失效，请重新登录" };
        }
        try {
            return await resp.json();
        } catch (e) {
            return { success: false, msg: "后台返回异常" };
        }
    }

    function showLogin() {
        $("appView").classList.add("hidden");
        $("loginView").classList.remove("hidden");
    }

    function showApp(nick, uid) {
        $("loginView").classList.add("hidden");
        $("appView").classList.remove("hidden");
        $("nickText").textContent = (nick || "已登录") +
            (uid ? " · UID " + uid : "");
    }

    async function doLogin() {
        var account = $("account").value.trim();
        var password = $("password").value;
        var err = $("loginError");
        err.textContent = "";
        if (!account || !password) {
            err.textContent = "请输入账号和密码";
            return;
        }
        var btn = $("loginBtn");
        btn.disabled = true;
        btn.textContent = "登录中...";
        try {
            var d = await api("/api/login", {
                method: "POST",
                body: JSON.stringify({ account: account, password: password })
            });
            if (!d.success) {
                err.textContent = d.msg || "登录失败";
                return;
            }
            $("password").value = "";
            showApp(d.nick, d.uid);
        } catch (e) {
            err.textContent = "网络错误: " + e.message;
        } finally {
            btn.disabled = false;
            btn.textContent = "登 录";
        }
    }

    async function doLogout() {
        try { await api("/api/logout", { method: "POST" }); } catch (e) { }
        showLogin();
        $("resultBox").innerHTML = '<div class="result-empty">还没有签到记录</div>';
        $("statSuccess").textContent = "-";
        $("statTotal").textContent = "-";
        $("resultSummary").textContent = "";
    }

    function renderResults(results) {
        var box = $("resultBox");
        if (!results || !results.length) {
            box.innerHTML = '<div class="result-empty">没有返回签到结果</div>';
            return;
        }
        box.innerHTML = results.map(function (item) {
            var cls = item.ok ? "ok" : "fail";
            var msg = item.msg || (item.ok ? "签到成功" : "签到失败");
            return '<div class="result-item ' + cls + '">' +
                '<span class="name">' + escapeHtml(item.title || "未知板块") +
                " (" + item.cat_id + ")</span>" +
                '<span class="msg">' + escapeHtml(msg) + "</span></div>";
        }).join("");
    }

    function escapeHtml(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    async function doCheckIn() {
        var btn = $("checkinBtn");
        if (btn.disabled) return;
        var label = btn.textContent;
        btn.disabled = true;
        btn.textContent = "签到中...";
        $("checkinError").textContent = "";
        $("checkinHint").textContent = "正在逐个板块签到，请稍候...";
        try {
            var d = await api("/api/checkin", { method: "POST" });
            if (!d.success) {
                $("checkinError").textContent = d.msg || "签到失败";
            }
            $("statSuccess").textContent = d.count != null ? d.count : "-";
            $("statTotal").textContent = d.total != null ? d.total : "-";
            $("resultSummary").textContent = d.msg || "";
            renderResults(d.results);
            $("checkinHint").textContent = d.msg || "签到已完成";
        } catch (e) {
            $("checkinError").textContent = "网络错误: " + e.message;
            $("checkinHint").textContent = "";
        } finally {
            btn.disabled = false;
            btn.textContent = label;
        }
    }

    $("loginBtn").addEventListener("click", doLogin);
    $("password").addEventListener("keydown", function (e) {
        if (e.key === "Enter") doLogin();
    });
    $("account").addEventListener("keydown", function (e) {
        if (e.key === "Enter") $("password").focus();
    });
    $("logoutBtn").addEventListener("click", doLogout);
    $("checkinBtn").addEventListener("click", doCheckIn);

    (async function boot() {
        var d = await api("/api/me");
        if (d && d.logged_in) showApp(d.nick, d.uid);
        else showLogin();
    })();
})();
