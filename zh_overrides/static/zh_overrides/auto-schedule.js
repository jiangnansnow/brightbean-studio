/* zh_overrides 本地定制：文件夹自动排期 V2（24h 滚动 + 武装总开关）。
 *
 * 零上游模板改动：功能 DOM 全部由本脚本注入。
 *  - 作曲器页：媒体库旁「排期文件夹」按钮（开关关则置灰）；文件夹弹窗（步入式）；
 *    选定后文件夹卡片与单素材「同位互斥」；模式选择器置灰；点原生「加入队列」
 *    拦截改走 /zh-auto/queue/；
 *  - 社交账号页：红框位「自动排期」+ 单开关（绿=开/灰=关，无其它文字）；
 *  - 发布队列页：「自动 N」批次标签，两步确认一键清除。
 */
(function () {
  "use strict";

  var m =
    location.pathname.match(/^\/workspace\/([0-9a-fA-F-]{36})\//) ||
    location.pathname.match(/^\/social-accounts\/([0-9a-fA-F-]{36})(?:\/|$)/);
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
        .catch(function () { return {}; })
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
    '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>';

  function composerApp() {
    var el = document.querySelector('[x-data="composerApp()"]');
    return el && window.Alpine ? window.Alpine.$data(el) : null;
  }

  /* ── 作曲器：弹窗 ─────────────────────────────────────────────────── */

  window.zhAutoModal = function () {
    return {
      zhOpenState: false,
      zhFolderId: "",
      zhFolderLabel: "",
      zhOpen: function () {
        this.zhFolderId = "";
        this.zhOpenState = true;
        var self = this;
        this.$nextTick(function () {
          htmx.ajax("GET", BASE + "/folders/", {
            target: self.$refs.zhBrowser,
            swap: "innerHTML",
          });
        });
      },
      zhClose: function () { this.zhOpenState = false; },
      zhPickFolder: function (id, label) {
        this.zhFolderId = id;
        this.zhFolderLabel = label;
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
          bar.querySelector("[data-label]").textContent = "媒体库 / " + label;
          bar.style.display = "flex";
        }
      },
      zhAddFolder: function () {
        if (!this.zhFolderId) return;
        this.zhOpenState = false;
        if (window.zhOnFolderAdded) window.zhOnFolderAdded(this.zhFolderId, this.zhFolderLabel);
      },
    };
  };

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
    '<div id="zh-auto-browser-host" x-ref="zhBrowser"></div>' +
    '<div id="zh-select-bar" style="display:none;" class="mt-3 pt-3 border-t border-stone-100 items-center justify-between">' +
    '<div class="flex items-center gap-2 min-w-0 text-xs text-stone-500"><span>已选：</span><span data-label class="font-medium text-stone-700 truncate"></span></div>' +
    '<button type="button" @click="zhAddFolder()"' +
    ' class="px-4 py-2 text-sm font-semibold text-white rounded-lg transition-colors cursor-pointer bg-orange-500 hover:bg-orange-600 flex-shrink-0">添加文件夹</button>' +
    "</div></div></div></div>";

  /* ── 作曲器：文件夹卡片与互斥 ────────────────────────────────────── */

  var armed = false;
  var folderActive = false;
  var pickFolderId = "";
  var pickFolderLabel = "";
  var pickVideoCount = 0;

  function mediaRow() {
    var dz = document.querySelector(".media-dropzone-inline");
    return dz ? dz.parentElement : null;
  }

  function mediaList() {
    return document.getElementById("media-list");
  }

  function clearMediaClient() {
    var app = composerApp();
    if (app && Array.isArray(app.mediaItems)) app.mediaItems = [];
    var ml = mediaList();
    if (ml) ml.innerHTML = "";
    var hid = document.querySelectorAll('[name="pending_media_ids"]');
    hid.forEach(function (el) { el.remove(); });
    document.body.dispatchEvent(new CustomEvent("previewUpdate"));
  }

  function setModeSelectorDisabled(disabled) {
    var btn = document.getElementById("publish-mode-btn");
    if (!btn) return;
    btn.disabled = disabled;
    if (disabled) {
      btn.classList.add("opacity-50", "cursor-not-allowed");
      btn.setAttribute("aria-disabled", "true");
    } else {
      btn.classList.remove("opacity-50", "cursor-not-allowed");
      btn.removeAttribute("aria-disabled");
    }
  }

  function fbAccounts() {
    var app = composerApp();
    if (!app) return [];
    return (app.selectedAccounts || []).filter(function (id) {
      return app.charLimits && app.charLimits[id] && app.charLimits[id].platform === "facebook";
    });
  }

  function buildFolderExtras() {
    var ml = mediaList();
    var existing = document.getElementById("zh-folder-extras");
    if (existing) existing.remove();
    if (!folderActive || !ml) return;

    var fbIds = fbAccounts();
    if (!fbIds.length) return;

    var box = document.createElement("div");
    box.id = "zh-folder-extras";
    box.className = "px-4 pb-2 space-y-2";
    fbIds.forEach(function (accId) {
      var row = document.createElement("div");
      row.className = "flex items-center gap-2";
      var label = document.createElement("span");
      label.className = "text-[11px] font-semibold text-stone-400 uppercase tracking-wider";
      label.textContent = "Publish as";
      var sel = document.createElement("select");
      sel.name = "facebook_post_type_" + accId;
      sel.className = "text-xs px-2 py-1 rounded-md border border-stone-200 bg-white outline-none focus:border-orange-500";
      sel.innerHTML =
        '<option value="video" selected>Regular video</option>' +
        '<option value="reel">Reel</option>';
      row.appendChild(label);
      row.appendChild(sel);
      box.appendChild(row);
    });
    var rowRef = mediaRow();
    if (rowRef && rowRef.parentElement) rowRef.parentElement.insertBefore(box, rowRef.nextSibling);
  }

  function updateNoAccountHint() {
    var hint = document.getElementById("zh-folder-no-account");
    if (!folderActive) { if (hint) hint.remove(); return; }
    var app = composerApp();
    var has = app && (app.selectedAccounts || []).length > 0;
    if (!has) {
      if (!hint) {
        hint = document.createElement("p");
        hint.id = "zh-folder-no-account";
        hint.className = "px-4 pb-2 text-xs text-red-600";
        hint.textContent = "Select at least one platform account above first.";
        var rowRef = mediaRow();
        if (rowRef && rowRef.parentElement) {
          var extras = document.getElementById("zh-folder-extras");
          if (extras) extras.parentElement.insertBefore(hint, extras.nextSibling);
          else rowRef.parentElement.insertBefore(hint, rowRef.nextSibling);
        }
      }
    } else if (hint) hint.remove();
  }

  function activateFolder(id, label) {
    pickFolderId = id;
    pickFolderLabel = label;
    folderActive = true;

    var app = composerApp();
    if (app) {
      // 互斥：清空已选素材（session + DOM + Alpine），文件夹卡片上位。
      api("POST", BASE + "/clear-media/").catch(function () {});
      clearMediaClient();
      // 读取该文件夹可排期数量（从点击卡片上的角标直接取，兜底为 0）。
      var gridCard = document.getElementById("zh-folder-" + id);
      var cntEl = gridCard ? gridCard.querySelector("[data-count]") : null;
      pickVideoCount = cntEl ? parseInt(cntEl.textContent || "0", 10) || 0 : 0;
    }

    var ml = mediaList();
    if (ml) {
      var card = document.createElement("div");
      card.id = "zh-folder-card";
      card.style.cssText =
        "width:96px;height:96px;border-radius:8px;border:1px solid #FDBA74;" +
        "background:#FFF7ED;position:relative;overflow:hidden;display:flex;" +
        "flex-direction:column;align-items:center;justify-content:center;gap:2px;flex-shrink:0;";
      card.innerHTML =
        '<svg style="width:22px;height:22px;color:#F97316;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>' +
        '<span style="font-size:11px;font-weight:500;color:#44403C;max-width:88px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
        escapeHtml(label) + "</span>" +
        '<span style="font-size:10px;color:#9CA3AF;">' + pickVideoCount + " 个视频</span>" +
        '<button type="button" data-zh-remove-folder style="position:absolute;top:4px;right:4px;width:20px;height:20px;border-radius:50%;background:rgba(0,0,0,0.55);color:#fff;display:flex;align-items:center;justify-content:center;font-size:10px;cursor:pointer;border:none;">' +
        '<svg style="width:10px;height:10px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"/></svg>' +
        "</button>";
      ml.appendChild(card);
    }

    setModeSelectorDisabled(true);
    buildFolderExtras();
    updateNoAccountHint();
  }

  function deactivateFolder() {
    folderActive = false;
    pickFolderId = "";
    pickFolderLabel = "";
    var card = document.getElementById("zh-folder-card");
    if (card) card.remove();
    var extras = document.getElementById("zh-folder-extras");
    if (extras) extras.remove();
    var hint = document.getElementById("zh-folder-no-account");
    if (hint) hint.remove();
    setModeSelectorDisabled(false);
  }

  window.zhOnFolderAdded = function (id, label) {
    activateFolder(id, label);
  };

  function submitFolderSchedule() {
    var app = composerApp();
    if (!folderActive || !app) return;
    var form = document.getElementById("composer-form");
    var selectedInput = form ? form.querySelector('[name="selected_accounts"]') : null;
    var selected = selectedInput ? selectedInput.value : "";
    var accountIds = selected ? selected.split(",").filter(Boolean) : [];
    if (!accountIds.length) {
      updateNoAccountHint();
      return;
    }

    var fd = new FormData();
    fd.append("folder_id", pickFolderId);
    fd.append("selected_accounts", accountIds.join(","));
    var captionEl = form ? form.querySelector('[name="caption"]') : null;
    fd.append("caption", captionEl ? captionEl.value : (app.caption || ""));
    var fcEl = form ? form.querySelector('[name="first_comment"]') : null;
    if (fcEl) fd.append("first_comment", fcEl.value || "");

    var selHost = document.getElementById("zh-folder-extras") || form;
    selHost.querySelectorAll('select[name^="facebook_post_type_"]').forEach(function (sel) {
      fd.append(sel.name, sel.value);
    });

    var btn = document.getElementById("publish-action-btn");
    var orig = btn ? btn.innerHTML : "";
    if (btn) {
      btn.disabled = true;
      btn.querySelector("#publish-action-label") &&
        (btn.querySelector("#publish-action-label").textContent = "正在排期…");
    }

    api("POST", BASE + "/queue/", fd)
      .then(function (data) {
        if (data.reason && data.queued_now === 0) {
          alert(data.reason);
        }
        if (data.redirect) window.location.href = data.redirect;
      })
      .catch(function (err) {
        var hint = document.getElementById("zh-folder-no-account");
        if (hint) hint.textContent = err.message; else updateNoAccountHint();
        if (btn) {
          btn.disabled = false;
          var label = btn.querySelector("#publish-action-label");
          if (label) label.textContent = "Add to Queue";
        }
      });
  }

  function initComposer() {
    var root = document.querySelector(".composer-main");
    if (!root || document.getElementById("zh-auto-btn")) return;
    // 仅新帖（compose 而非 compose/<id>）提供文件夹模式。
    var editing = /^\/workspace\/[0-9a-fA-F-]{36}\/compose\/[0-9a-fA-F-]{36}\/?$/.test(location.pathname);
    if (editing) return;

    var mediaBtn = root.querySelector(".caption-wrap .border-t button");
    if (!mediaBtn) return;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.id = "zh-auto-btn";
    btn.disabled = true;
    btn.className =
      "text-xs font-medium text-stone-400 hover:text-orange-600 transition-colors flex items-center gap-1.5 cursor-pointer ml-3 disabled:opacity-40 disabled:cursor-not-allowed";
    btn.innerHTML = FOLDER_SVG + "<span>排期文件夹</span>";
    btn.addEventListener("click", function () {
      if (armed) window.dispatchEvent(new CustomEvent("zh-auto-open"));
    });
    mediaBtn.insertAdjacentElement("afterend", btn);

    // 弹窗
    var wrap = document.createElement("div");
    wrap.innerHTML = MODAL_HTML;
    while (wrap.firstChild) root.appendChild(wrap.firstChild);

    // 文件夹 + 素材互斥：观察 #media-list 新增素材缩略图。
    var ml = mediaList();
    if (ml) {
      var obs = new MutationObserver(function () {
        if (!folderActive) return;
        if (ml.querySelectorAll(".media-thumb").length > 0) deactivateFolder();
      });
      obs.observe(ml, { childList: true, subtree: true });
    }

    // 删除文件夹卡片的 X。
    document.addEventListener("click", function (e) {
      if (e.target.closest("[data-zh-remove-folder]")) deactivateFolder();
    });

    // 账号变化 → 重建 FB 选择器 / 无账号提示。
    var app = composerApp();
    if (app && app.$watch) {
      app.$watch("selectedAccounts", function () {
        if (folderActive) { buildFolderExtras(); updateNoAccountHint(); }
      });
    }

    // 拦截「加入队列」：文件夹模式下改走 /zh-auto/queue/。
    var form = document.getElementById("composer-form");
    if (form) {
      form.addEventListener(
        "submit",
        function (e) {
          if (!folderActive) return;
          var sub = e.submitter || document.activeElement;
          var action = sub ? sub.value : "";
          if (action === "add_to_queue") {
            e.preventDefault();
            e.stopImmediatePropagation();
            submitFolderSchedule();
          }
        },
        true
      );
    }

    // 拉取武装状态 → 决定按钮灰态。
    api("GET", BASE + "/panel/")
      .then(function (d) {
        armed = !!d.armed;
        btn.disabled = !armed;
      })
      .catch(function () { armed = false; btn.disabled = true; });
  }

  /* ── 社交账号页：总开关 ───────────────────────────────────────────── */

  function initSocialPage() {
    var anchor = document.querySelector('a[href*="/social-accounts/"][href*="/connect"]');
    if (!anchor || document.getElementById("zh-auto-toggle")) return;

    var wrap = document.createElement("div");
    wrap.id = "zh-auto-toggle";
    wrap.className = "flex items-center gap-2";
    wrap.innerHTML =
      '<span class="text-xs text-stone-600 whitespace-nowrap">自动排期</span>' +
      '<button type="button" role="switch" aria-checked="false" data-switch' +
      ' class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer bg-stone-300">' +
      '<span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform translate-x-0.5"></span>' +
      "</button>";
    anchor.parentElement.insertBefore(wrap, anchor);

    var sw = wrap.querySelector("[data-switch]");
    var knob = sw.querySelector("span");
    var busy = false;

    function paint(on) {
      sw.setAttribute("aria-checked", on ? "true" : "false");
      sw.classList.toggle("bg-green-500", on);
      sw.classList.toggle("bg-stone-300", !on);
      knob.classList.toggle("translate-x-4", on);
      knob.classList.toggle("translate-x-0.5", !on);
    }

    api("GET", BASE + "/social-toggle/")
      .then(function (d) { paint(!!d.armed); })
      .catch(function () {});

    sw.addEventListener("click", function () {
      if (busy) return;
      busy = true;
      api("POST", BASE + "/social-toggle/flip/")
        .then(function (d) { paint(!!d.armed); })
        .catch(function () {})
        .finally(function () { busy = false; });
    });
  }

  /* ── 发布队列页：「自动 N」批次标签 ────────────────────────────────── */

  var lastQueuePath = null;

  function chipHtml(b) {
    return (
      '<span class="zh-auto-chip inline-flex items-center gap-1.5 pl-3 pr-1.5 py-1 rounded-full bg-orange-50 border border-orange-200 text-xs font-medium text-orange-700" data-batch="' +
      b.batch_id + '">' +
      FOLDER_SVG.replace("w-5 h-5", "w-4 h-4 text-orange-500") +
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
    if (!batches.length) { if (bar) bar.remove(); return; }
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
      var path = (evt.detail && evt.detail.requestConfig && evt.detail.requestConfig.path) || "";
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