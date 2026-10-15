/* zh_overrides 本地定制：文件夹自动候补排期（48h 滚动 + 社交页总开关）。
 *
 * 零上游模板改动：功能 DOM 全部由本脚本注入。
 *  - 作曲器页：媒体库按钮旁注入「排期文件夹」按钮 + 纯文件夹弹窗
 *    （单击选中高亮 / 双击进入子文件夹 / 底部开启自动候补 / 顶部运行状态条）；
 *  - 社交账号页：「连接账号」左边注入唯一总开关（停用/原样恢复）；
 *  - 发布队列页：注入「自动 N」批次标签，两步确认一键清除。
 */
(function () {
  "use strict";

  var m = location.pathname.match(/^\/workspace\/([0-9a-fA-F-]{36})\//);
  if (!m) return;
  var WS_ID = m[1];
  var BASE = "/workspace/" + WS_ID + "/zh-auto";
  var QUEUE_URL = "/workspace/" + WS_ID + "/calendar/publish/queue/";
  var ROOT_ID = "root";

  function csrf() {
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function api(method, url, form) {
    var opts = { method: method, headers: { "X-CSRFToken": csrf() } };
    if (form) opts.body = form;
    return fetch(url, opts).then(function (resp) {
      return resp
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          if (!resp.ok) throw new Error(data.error || "Request failed");
          return data;
        });
    });
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var FOLDER_SVG =
    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>';

  /* ── 作曲器弹窗 ───────────────────────────────────────────────────── */

  window.zhAutoModal = function () {
    return {
      zhOpenState: false,
      zhBusy: false,
      zhError: "",
      zhFolderId: "",
      zhFolderLabel: "",
      zhHasRule: false,
      zhStatus: null, // 规则状态（运行条）

      zhOpen: function () {
        this.zhError = "";
        this.zhFolderId = "";
        this.zhOpenState = true;
        this.zhBusy = true;
        var self = this;
        this.$nextTick(function () {
          htmx.ajax("GET", BASE + "/folders/", {
            target: self.$refs.zhBrowser,
            swap: "innerHTML",
          });
          api("GET", BASE + "/panel/")
            .then(function (data) {
              self.zhHasRule = !!data.has_rule;
              self.zhStatus = data.has_rule ? data : null;
            })
            .catch(function () {})
            .finally(function () {
              self.zhBusy = false;
            });
        });
      },
      zhClose: function () {
        this.zhOpenState = false;
      },

      // 单击文件夹：仅选中高亮，不导航（双击进入由 htmx dblclick 处理）。
      zhPickFolder: function (id, label) {
        this.zhFolderId = id;
        this.zhFolderLabel = label;
        this.zhError = "";
        document.querySelectorAll(".zh-auto-folder").forEach(function (el) {
          el.classList.remove("border-orange-500", "ring-2", "ring-orange-100");
          el.classList.add("border-stone-200");
        });
        var card = document.getElementById("zh-folder-" + id);
        if (card) {
          card.classList.remove("border-stone-200");
          card.classList.add("border-orange-500", "ring-2", "ring-orange-100");
        }
        var bar = document.getElementById("zh-select-bar");
        if (bar) {
          bar.querySelector("[data-label]").textContent =
            (id === ROOT_ID ? "媒体库 / " : "媒体库 / ") + label;
          bar.style.display = "flex";
        }
      },

      zhEnable: function () {
        if (this.zhBusy) return;
        var self = this;
        this.zhError = "";
        if (!this.zhFolderId) return;
        if (!this.selectedAccounts || this.selectedAccounts.length === 0) {
          this.zhError = "Select at least one platform account above first.";
          return;
        }

        var form = new FormData();
        form.append("folder_id", this.zhFolderId);
        form.append("selected_accounts", (this.selectedAccounts || []).join(","));
        form.append("caption", this.caption || "");
        var fc = document.querySelector('#composer-form [name="first_comment"]');
        if (fc) form.append("first_comment", fc.value || "");
        document
          .querySelectorAll('#composer-form select[name^="facebook_post_type_"]')
          .forEach(function (sel) {
            form.append(sel.name, sel.value);
          });

        this.zhBusy = true;
        api("POST", BASE + "/enable/", form)
          .then(function (data) {
            self.zhStatus = data;
            self.zhHasRule = true;
            self.zhOpenState = false;
          })
          .catch(function (err) {
            self.zhError = err.message;
          })
          .finally(function () {
            self.zhBusy = false;
          });
      },

      zhDisable: function () {
        var self = this;
        this.zhBusy = true;
        api("POST", BASE + "/disable/")
          .then(function (data) {
            self.zhStatus = data;
          })
          .catch(function (err) {
            self.zhError = err.message;
          })
          .finally(function () {
            self.zhBusy = false;
          });
      },
    };
  };

  function statusBarHtml(s) {
    if (!s || !s.has_rule) return "";
    var dot = s.is_active
      ? '<span class="inline-block w-2 h-2 rounded-full bg-green-500"></span>'
      : '<span class="inline-block w-2 h-2 rounded-full bg-stone-300"></span>';
    var state = s.is_active ? "运行中" : "已停用";
    var missing = s.folder_missing ? '<span class="text-red-500">（监听文件夹已删除，请重新选择）</span>' : "";
    var btn = s.is_active
      ? '<button type="button" @click="zhDisable()" class="text-xs font-semibold text-red-500 hover:text-red-600 cursor-pointer flex-shrink-0">关闭自动候补</button>'
      : "";
    return (
      '<div class="mb-3 px-3 py-2 rounded-lg bg-stone-50 border border-stone-200 flex items-center gap-2 text-xs text-stone-600 flex-wrap">' +
      dot +
      "<span>" + state + "</span>" +
      '<span class="text-stone-400">·</span><span>监听：' + escapeHtml(s.folder_label) + "</span>" + missing +
      '<span class="text-stone-400">·</span><span>已投递 ' + (s.delivered || 0) + " 个视频</span>" +
      (s.ignored && s.ignored.length
        ? '<span class="text-stone-400 w-full pl-4">不可用：' + escapeHtml(s.ignored.join(", ")) + "</span>"
        : "") +
      '<span class="flex-1"></span>' + btn +
      "</div>"
    );
  }

  var MODAL_HTML =
    '<div x-data="zhAutoModal()" @zh-auto-open.window="zhOpen()" x-show="zhOpenState" x-cloak' +
    ' class="fixed inset-0 z-[60] flex items-center justify-center"' +
    ' x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100"' +
    ' x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0">' +
    '<div class="absolute inset-0 bg-stone-900/40 backdrop-blur-sm" @click="zhClose()"></div>' +
    '<div class="relative bg-white rounded-2xl shadow-xl border border-stone-200 w-[calc(100vw-1rem)] sm:w-[640px] mx-2 sm:mx-0 max-h-[85vh] sm:max-h-[70vh] overflow-hidden"' +
    ' x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 scale-95" x-transition:enter-end="opacity-100 scale-100">' +
    '<div class="px-4 sm:px-6 py-4 border-b border-stone-100 flex items-center justify-between">' +
    '<h2 class="text-base font-semibold text-stone-900">排期文件夹</h2>' +
    '<button type="button" @click="zhClose()"' +
    ' class="w-8 h-8 rounded-lg border border-stone-200 text-stone-400 hover:text-stone-600 hover:border-stone-300 flex items-center justify-center transition-all duration-150 cursor-pointer">' +
    '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>' +
    "</button></div>" +
    '<div class="p-4 sm:p-6">' +
    '<div x-html="zhStatus ? ' +
    "'" +
    // 运行状态条（服务端数据渲染；这里用 JS 端拼装）
    "'" +
    " : ''\"></div>" +
    '<div id="zh-auto-browser-host" x-ref="zhBrowser"></div>' +
    '<p class="text-xs text-red-600 mt-2" x-show="zhError" x-text="zhError"></p>' +
    '<div id="zh-select-bar" style="display:none;" class="mt-3 pt-3 border-t border-stone-100 items-center justify-between">' +
    '<div class="flex items-center gap-2 min-w-0 text-xs text-stone-500"><span>已选：</span><span data-label class="font-medium text-stone-700 truncate"></span></div>' +
    '<button type="button" @click="zhEnable()" :disabled="zhBusy"' +
    ' class="px-4 py-2 text-sm font-semibold text-white rounded-lg transition-colors cursor-pointer disabled:opacity-60 bg-orange-500 hover:bg-orange-600 flex-shrink-0">开启自动候补</button>' +
    "</div></div></div></div>";

  // 状态条需要随 zhStatus 变化更新，用独立 watcher 节点实现（避免 x-html 字符串转义地狱）。
  function wireStatusBar(root) {
    var Alpine = window.Alpine;
    if (!Alpine || !Alpine.effect) return;
    var component = root.querySelector('[x-data^="zhAutoModal"]')._x_dataStack
      ? Alpine.$data(root.querySelector('[x-data^="zhAutoModal"]'))
      : null;
    if (!component) return;
    Alpine.effect(function () {
      var host = root.querySelector("#zh-auto-status-host");
      if (host) host.innerHTML = statusBarHtml(component.zhStatus);
    });
  }

  function initComposer() {
    var root = document.querySelector(".composer-main");
    if (!root || root.querySelector("#zh-auto-btn")) return;

    var mediaBtn = root.querySelector(".caption-wrap .border-t button");
    if (mediaBtn) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.id = "zh-auto-btn";
      btn.className =
        "text-xs font-medium text-stone-400 hover:text-orange-600 transition-colors flex items-center gap-1.5 cursor-pointer ml-3";
      btn.innerHTML = FOLDER_SVG + "<span>排期文件夹</span>";
      btn.addEventListener("click", function () {
        window.dispatchEvent(new CustomEvent("zh-auto-open"));
      });
      mediaBtn.insertAdjacentElement("afterend", btn);
    }

    var wrap = document.createElement("div");
    // 在弹窗内容区插入状态条宿主，并把 x-html 占位替换为它。
    wrap.innerHTML = MODAL_HTML.replace(
      '<div x-html="zhStatus ? \'\' : \'\'"></div>',
      '<div id="zh-auto-status-host"></div>'
    );
    while (wrap.firstChild) root.appendChild(wrap.firstChild);
    // 兜底：若替换没命中，直接在 browser host 前插一个宿主。
    var modal = root.querySelector('[x-data^="zhAutoModal"]');
    if (modal && !modal.querySelector("#zh-auto-status-host")) {
      var host = document.createElement("div");
      host.id = "zh-auto-status-host";
      var body = modal.querySelector(".p-4");
      if (body) body.insertBefore(host, body.firstChild);
    }
    wireStatusBar(root);
  }

  /* ── 社交账号页总开关 ──────────────────────────────────────────────── */

  function initSocialPage() {
    var header = document.querySelector("#accounts-list")?.previousElementSibling;
    var anchor = document.querySelector('a[href*="/social-accounts/"][href*="/connect"]');
    if (!anchor || document.getElementById("zh-auto-toggle")) return;

    var wrap = document.createElement("div");
    wrap.id = "zh-auto-toggle";
    wrap.className = "flex items-center gap-3";
    wrap.innerHTML =
      '<span class="text-xs text-stone-500 whitespace-nowrap" data-hint>自动候补</span>' +
      '<button type="button" role="switch" aria-checked="false"' +
      ' class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer bg-stone-300"' +
      ' data-switch><span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform translate-x-1"></span></button>' +
      '<span class="text-xs text-stone-500" data-state>未开启</span>';
    anchor.parentElement.insertBefore(wrap, anchor);

    var sw = wrap.querySelector("[data-switch]");
    var knob = sw.querySelector("span");
    var stateLabel = wrap.querySelector("[data-state]");
    var hint = wrap.querySelector("[data-hint]");
    var busy = false;

    function paint(s) {
      var on = !!s.enabled;
      sw.setAttribute("aria-checked", on ? "true" : "false");
      sw.classList.toggle("bg-orange-500", on);
      sw.classList.toggle("bg-stone-300", !on);
      knob.classList.toggle("translate-x-6", on);
      knob.classList.toggle("translate-x-1", !on);
      if (!s.has_rule) {
        stateLabel.textContent = "未开启";
        stateLabel.className = "text-xs text-stone-400";
        hint.textContent = "自动候补（请先在帖子编辑器开启）";
        sw.classList.add("opacity-40", "cursor-not-allowed");
        sw.disabled = true;
        return;
      }
      sw.classList.remove("opacity-40", "cursor-not-allowed");
      sw.disabled = false;
      var label = s.folder_missing
        ? "监听文件夹已删除"
        : (on ? "运行中" : "已停用") + " · " + (s.folder_label || "");
      stateLabel.textContent = label;
      stateLabel.className = "text-xs " + (on ? "text-green-600" : "text-stone-500");
      hint.textContent = "自动候补";
    }

    api("GET", BASE + "/social-toggle/")
      .then(paint)
      .catch(function () {});

    sw.addEventListener("click", function () {
      if (busy || sw.disabled) return;
      busy = true;
      api("POST", BASE + "/social-toggle/flip/")
        .then(function (s) {
          paint(s);
        })
        .catch(function (err) {
          stateLabel.textContent = err.message;
          stateLabel.className = "text-xs text-red-500";
        })
        .finally(function () {
          busy = false;
        });
    });
  }

  /* ── 发布队列页：「自动 N」批次标签 ────────────────────────────────── */

  var lastQueuePath = null;

  function chipHtml(b) {
    return (
      '<span class="zh-auto-chip inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full bg-orange-50 border border-orange-200 text-xs font-medium text-orange-700" data-batch="' +
      b.batch_id +
      '">' +
      FOLDER_SVG.replace("w-3.5 h-3.5", "w-3.5 h-3.5 text-orange-500") +
      "<span>自动</span>" +
      '<span class="tabular-nums text-orange-500">' + b.remaining + "</span>" +
      '<button type="button" data-act="ask-clear" title="清除" class="w-5 h-5 rounded-full text-orange-400 hover:text-red-500 hover:bg-red-50 flex items-center justify-center cursor-pointer">' +
      '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>' +
      "</button></span>"
    );
  }

  function renderBar(batches) {
    var tab = document.querySelector("#tab-content");
    if (!tab) return;
    var bar = tab.querySelector("#zh-auto-bar");
    if (!batches.length) {
      if (bar) bar.remove();
      return;
    }
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "zh-auto-bar";
      bar.className = "mb-4 flex flex-wrap items-center gap-2";
      tab.insertBefore(bar, tab.firstChild);
    }
    bar.innerHTML = batches.map(chipHtml).join("");
  }

  function refreshBar() {
    api("GET", BASE + "/active/").then(renderBar).catch(function () {});
  }

  function reloadQueue() {
    htmx.ajax("GET", lastQueuePath || QUEUE_URL + location.search, {
      target: "#tab-content",
      swap: "innerHTML",
    });
  }

  function onBarClick(e) {
    var btn = e.target.closest("button[data-act]");
    if (!btn) return;
    var chip = e.target.closest(".zh-auto-chip");
    if (!chip) return;
    var id = chip.getAttribute("data-batch");
    if (btn.getAttribute("data-act") === "ask-clear") {
      chip.innerHTML =
        '<span class="text-stone-500">清除该批次？</span>' +
        '<button type="button" data-act="confirm-clear" class="px-2 py-0.5 rounded-full bg-red-500 text-white font-semibold cursor-pointer text-[11px]">是</button>' +
        '<button type="button" data-act="cancel-clear" class="px-2 py-0.5 rounded-full border border-stone-200 text-stone-500 cursor-pointer text-[11px]">否</button>';
    } else if (btn.getAttribute("data-act") === "cancel-clear") {
      refreshBar();
    } else if (btn.getAttribute("data-act") === "confirm-clear") {
      api("POST", BASE + "/batches/" + id + "/clear/").then(reloadQueue);
    }
  }

  function initCalendar() {
    if (document.getElementById("zh-auto-bar-delegated")) return;
    var marker = document.createElement("div");
    marker.id = "zh-auto-bar-delegated";
    marker.hidden = true;
    document.body.appendChild(marker);
    document.body.addEventListener("click", onBarClick);

    document.body.addEventListener("htmx:afterRequest", function (evt) {
      var path = evt.detail?.requestConfig?.path || "";
      if (path.indexOf("/publish/queue/") !== -1) {
        lastQueuePath = path;
        setTimeout(refreshBar, 0);
      } else if (path.indexOf("/publish/") !== -1) {
        var bar = document.querySelector("#zh-auto-bar");
        if (bar) bar.remove();
      }
    });

    var params = new URLSearchParams(location.search);
    if (params.get("mode") === "list" && (params.get("tab") || "queue") === "queue") {
      refreshBar();
    }
  }

  function boot() {
    if (location.pathname.indexOf("/compose") !== -1) initComposer();
    if (location.pathname.indexOf("/social-accounts/") !== -1) initSocialPage();
    if (location.pathname.indexOf("/calendar/") !== -1) initCalendar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  document.body.addEventListener("htmx:afterSettle", boot);
})();
