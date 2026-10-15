/* zh_overrides 本地定制：作曲器「文件夹」模式一键批量入队 + 队列页批次条。
 *
 * 零上游模板改动：功能 DOM 全部由本脚本注入。作曲器页注入与「媒体库」同款
 * 的弹窗（类名体系与 media picker 完全一致），弹窗节点挂在 composerApp 的
 * x-data 根内，直接继承 selectedAccounts/caption 等状态；发布队列页注入
 * 批次系统标签条，支持两步确认的一键批量清除。
 */
(function () {
  "use strict";

  var m = location.pathname.match(/^\/workspace\/([0-9a-fA-F-]{36})\//);
  if (!m) return;
  var WS_ID = m[1];
  var BASE = "/workspace/" + WS_ID + "/zh-batch";
  var QUEUE_URL = "/workspace/" + WS_ID + "/calendar/publish/queue/";

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

  var FOLDER_SVG =
    '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>';

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ── 作曲器页 ─────────────────────────────────────────────────────── */

  window.zhBatchModal = function () {
    return {
      zhOpenState: false,
      zhView: "browse",
      zhFolderId: "",
      zhFolderName: "",
      zhEligible: 0,
      zhCount: 0,
      zhMinSlots: 0,
      zhIgnored: [],
      zhError: "",
      zhBusy: false,
      zhCreated: 0,
      zhMax: 0,

      zhOpen: function () {
        this.zhView = "browse";
        this.zhFolderId = "";
        this.zhError = "";
        this.zhOpenState = true;
        var self = this;
        this.$nextTick(function () {
          htmx.ajax("GET", BASE + "/folders/", {
            target: self.$refs.zhBrowser,
            swap: "innerHTML",
          });
        });
      },
      zhClose: function () {
        this.zhOpenState = false;
      },
      zhSelectFolder: function (id, name) {
        var self = this;
        this.zhError = "";
        this.zhFolderId = "";
        this.zhEligible = 0;
        this.zhMinSlots = 0;
        this.zhCount = 0;
        this.zhIgnored = [];
        if (!this.selectedAccounts || this.selectedAccounts.length === 0) {
          this.zhFolderName = name;
          this.zhError = "Select at least one account first.";
          this.zhView = "selected";
          return;
        }
        var url =
          BASE +
          "/plan/?folder=" +
          encodeURIComponent(id) +
          "&accounts=" +
          encodeURIComponent((this.selectedAccounts || []).join(","));
        api("GET", url)
          .then(function (data) {
            self.zhFolderId = id;
            self.zhFolderName = name;
            self.zhEligible = data.eligible || 0;
            self.zhMinSlots = data.min_slots || 0;
            self.zhCount = data.default || 0;
            self.zhMax = self.zhEligible;
            self.zhIgnored = (data.ignored_accounts || []).map(function (x) {
              return x.name;
            });
            if (self.zhEligible === 0) {
              self.zhError = "No eligible videos in this folder.";
            } else if (self.zhMinSlots === 0) {
              self.zhError =
                "No open posting slot within 7 days for the selected accounts.";
            }
            self.zhView = "selected";
          })
          .catch(function (err) {
            self.zhError = err.message;
          });
      },
      zhBack: function () {
        this.zhView = "browse";
        this.zhError = "";
      },
      zhClamp: function () {
        var v = parseInt(this.zhCount, 10);
        if (isNaN(v) || v < 1) v = 1;
        if (v > this.zhMax) v = this.zhMax;
        this.zhCount = v;
      },
      zhConfirm: function () {
        if (this.zhBusy) return;
        var self = this;
        this.zhError = "";
        this.zhClamp();
        if (!this.zhFolderId || this.zhCount < 1) return;

        var form = new FormData();
        form.append("folder_id", this.zhFolderId);
        form.append("count", String(this.zhCount));
        form.append("selected_accounts", (this.selectedAccounts || []).join(","));
        form.append("caption", this.caption || "");
        var fc = document.querySelector(
          '#composer-form [name="first_comment"]'
        );
        if (fc) form.append("first_comment", fc.value || "");
        var fb = document.querySelectorAll(
          '#composer-form select[name^="facebook_post_type_"]'
        );
        Array.prototype.forEach.call(fb, function (sel) {
          form.append(sel.name, sel.value);
        });

        this.zhBusy = true;
        api("POST", BASE + "/enqueue/", form)
          .then(function (data) {
            self.zhCreated = data.created || 0;
            self.zhView = "result";
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

  var MODAL_HTML =
    '<div x-data="zhBatchModal()" @zh-batch-open.window="zhOpen()" x-show="zhOpenState" x-cloak' +
    ' class="fixed inset-0 z-[60] flex items-center justify-center"' +
    ' x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100"' +
    ' x-transition:leave="transition ease-in duration-150" x-transition:leave-start="opacity-100" x-transition:leave-end="opacity-0">' +
    '<div class="absolute inset-0 bg-stone-900/40 backdrop-blur-sm" @click="zhClose()"></div>' +
    '<div class="relative bg-white rounded-2xl shadow-xl border border-stone-200 w-[calc(100vw-1rem)] sm:w-[640px] mx-2 sm:mx-0 max-h-[85vh] sm:max-h-[70vh] overflow-hidden"' +
    ' x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0 scale-95" x-transition:enter-end="opacity-100 scale-100">' +
    '<div class="px-4 sm:px-6 py-4 border-b border-stone-100 flex items-center justify-between">' +
    '<h2 class="text-base font-semibold text-stone-900">Batch Schedule</h2>' +
    '<button type="button" @click="zhClose()"' +
    ' class="w-8 h-8 rounded-lg border border-stone-200 text-stone-400 hover:text-stone-600 hover:border-stone-300 flex items-center justify-center transition-all duration-150 cursor-pointer">' +
    '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>' +
    "</button></div>" +
    '<div class="p-4 sm:p-6">' +
    // 浏览视图：宿主节点永不参与 htmx 交换，避免 x-ref 在导航后失效。
    '<div x-show="zhView===\'browse\'" id="zh-browser-host" x-ref="zhBrowser"></div>' +
    // 选择确认视图
    '<div x-show="zhView===\'selected\'" class="space-y-4" x-cloak>' +
    '<div class="flex items-center justify-between">' +
    '<div class="flex items-center gap-2 min-w-0">' +
    '<svg class="w-4 h-4 text-stone-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>' +
    '<span class="text-sm font-semibold text-stone-800 truncate" x-text="zhFolderName"></span></div>' +
    '<button type="button" @click="zhBack()" class="text-xs font-semibold text-stone-400 hover:text-stone-700 cursor-pointer flex-shrink-0">Change</button>' +
    "</div>" +
    '<div class="flex items-center justify-between">' +
    '<span class="text-xs text-stone-400"><span x-text="zhEligible"></span> videos available</span>' +
    '<div class="flex items-center gap-2">' +
    '<button type="button" @click="if(zhCount>1)zhCount--" class="w-8 h-8 rounded-lg border border-stone-200 text-stone-600 hover:border-stone-300 hover:bg-stone-50 flex items-center justify-center cursor-pointer text-lg leading-none">−</button>' +
    '<input type="number" min="1" x-model.number="zhCount" @change="zhClamp()" class="w-16 h-8 text-center text-sm font-semibold rounded-lg border border-stone-200 outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100 tabular-nums">' +
    '<button type="button" @click="if(zhCount<zhMax)zhCount++" class="w-8 h-8 rounded-lg border border-stone-200 text-stone-600 hover:border-stone-300 hover:bg-stone-50 flex items-center justify-center cursor-pointer text-lg leading-none">+</button>' +
    "</div></div>" +
    '<p class="text-[11px] text-stone-400" x-show="zhIgnored.length" x-cloak><span>Unavailable:</span> <span x-text="zhIgnored.join(\', \')"></span></p>' +
    '<p class="text-xs text-red-600" x-show="zhError" x-text="zhError"></p>' +
    '<div class="flex justify-end pt-2 border-t border-stone-100">' +
    '<button type="button" @click="zhConfirm()" :disabled="zhBusy || zhEligible===0 || zhMinSlots===0"' +
    ' class="px-4 py-2 text-sm font-semibold text-white rounded-lg transition-colors cursor-pointer disabled:cursor-not-allowed disabled:bg-stone-300 bg-orange-500 hover:bg-orange-600">Add to Queue</button>' +
    "</div></div>" +
    // 成功视图
    '<div x-show="zhView===\'result\'" class="text-center py-6" x-cloak>' +
    '<div class="w-12 h-12 mx-auto rounded-full bg-green-50 flex items-center justify-center mb-3">' +
    '<svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></div>' +
    '<p class="text-sm font-semibold text-stone-800 mb-4"><span x-text="zhCreated"></span> posts queued</p>' +
    '<div class="flex items-center justify-center gap-2">' +
    '<a href="/workspace/' + WS_ID + '/calendar/?mode=list&amp;tab=queue" class="px-4 py-2 text-sm font-semibold text-white bg-orange-500 rounded-lg hover:bg-orange-600 transition-colors">View Queue</a>' +
    '<button type="button" @click="zhClose()" class="px-4 py-2 text-sm font-semibold text-stone-600 border border-stone-200 rounded-lg hover:bg-stone-50 transition-colors cursor-pointer">Done</button>' +
    "</div></div>" +
    "</div></div></div>";

  function initComposer() {
    var root = document.querySelector(".composer-main");
    if (!root || root.querySelector("#zh-batch-btn")) return;

    var mediaBtn = root.querySelector(".caption-wrap .border-t button");
    if (mediaBtn) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.id = "zh-batch-btn";
      btn.className =
        "text-xs font-medium text-stone-400 hover:text-orange-600 transition-colors flex items-center gap-1.5 cursor-pointer ml-3";
      btn.innerHTML = FOLDER_SVG + "<span>Batch Schedule</span>";
      btn.addEventListener("click", function () {
        window.dispatchEvent(new CustomEvent("zh-batch-open"));
      });
      mediaBtn.insertAdjacentElement("afterend", btn);
    }

    var wrap = document.createElement("div");
    wrap.innerHTML = MODAL_HTML;
    while (wrap.firstChild) root.appendChild(wrap.firstChild);
  }

  /* ── 发布队列页：批次系统标签条 ───────────────────────────────────── */

  var lastQueuePath = null;

  function chipHtml(b) {
    return (
      '<span class="zh-batch-chip inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full bg-stone-100 border border-stone-200 text-xs font-medium text-stone-600" data-batch="' +
      b.batch_id +
      '">' +
      '<svg class="w-3.5 h-3.5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>' +
      "<span>" +
      escapeHtml(b.folder_name) +
      '</span><span class="tabular-nums text-stone-400">' +
      b.remaining +
      '</span>' +
      '<button type="button" data-act="ask-clear" title="Clear" class="w-5 h-5 rounded-full text-stone-400 hover:text-red-500 hover:bg-red-50 flex items-center justify-center cursor-pointer">' +
      '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>' +
      "</button></span>"
    );
  }

  function confirmHtml(id) {
    return (
      '<span class="text-stone-500">Clear this batch?</span>' +
      '<button type="button" data-act="confirm-clear" data-batch="' +
      id +
      '" class="px-2 py-0.5 rounded-full bg-red-500 text-white font-semibold cursor-pointer">Yes</button>' +
      '<button type="button" data-act="cancel-clear" class="px-2 py-0.5 rounded-full border border-stone-200 text-stone-500 cursor-pointer">No</button>'
    );
  }

  function renderBar(batches) {
    var tab = document.querySelector("#tab-content");
    if (!tab) return;
    var bar = tab.querySelector("#zh-batch-bar");
    if (!batches.length) {
      if (bar) bar.remove();
      return;
    }
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "zh-batch-bar";
      bar.className = "mb-4 flex flex-wrap items-center gap-2";
      tab.insertBefore(bar, tab.firstChild);
    }
    bar.innerHTML = batches.map(chipHtml).join("");
  }

  function refreshBar() {
    api("GET", BASE + "/active/").then(renderBar).catch(function () {});
  }

  function reloadQueue() {
    var path = lastQueuePath || QUEUE_URL + location.search;
    htmx.ajax("GET", path, { target: "#tab-content", swap: "innerHTML" });
  }

  function onBarClick(e) {
    var btn = e.target.closest("button[data-act]");
    if (!btn) return;
    var act = btn.getAttribute("data-act");
    var chip = e.target.closest(".zh-batch-chip");
    if (!chip) return;
    var id = chip.getAttribute("data-batch");
    if (act === "ask-clear") {
      chip.innerHTML = confirmHtml(id);
    } else if (act === "cancel-clear") {
      refreshBar();
    } else if (act === "confirm-clear") {
      api("POST", BASE + "/batches/" + id + "/clear/").then(function () {
        reloadQueue();
      });
    }
  }

  function initCalendar() {
    if (document.getElementById("zh-batch-bar-delegated")) return;
    var marker = document.createElement("div");
    marker.id = "zh-batch-bar-delegated";
    marker.hidden = true;
    document.body.appendChild(marker);
    document.body.addEventListener("click", onBarClick);

    document.body.addEventListener("htmx:afterRequest", function (evt) {
      var path =
        (evt.detail &&
          evt.detail.requestConfig &&
          evt.detail.requestConfig.path) ||
        "";
      if (path.indexOf("/publish/queue/") !== -1) {
        lastQueuePath = path;
        setTimeout(refreshBar, 0);
      } else if (path.indexOf("/publish/") !== -1) {
        var bar = document.querySelector("#zh-batch-bar");
        if (bar) bar.remove();
      }
    });

    // 列表页初始即渲染队列 tab 时直接加载批次条。
    var params = new URLSearchParams(location.search);
    if (params.get("mode") === "list" && (params.get("tab") || "queue") === "queue") {
      refreshBar();
    }
  }

  function boot() {
    if (location.pathname.indexOf("/compose") !== -1) initComposer();
    if (location.pathname.indexOf("/calendar/") !== -1) initCalendar();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  // htmx 局部导航（如侧栏切换）后重新探测页面。
  document.body.addEventListener("htmx:afterSettle", function () {
    boot();
  });
})();
