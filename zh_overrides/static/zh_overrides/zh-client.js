/* Client-side Chinese localization overlay.
 *
 * Server-rendered pages are translated by ZhLocalizationMiddleware, but
 * Alpine (x-text), htmx (swaps) and plain JS (setMode, error toasts) write
 * English text after load. This script mirrors the middleware logic with a
 * MutationObserver, using the same dictionary exposed at window.__ZH__.
 *
 * Loop safety: a translated node never contains a dictionary key, so the
 * mutation our write triggers is a no-op. User-editable content
 * (contenteditable, inputs) is skipped.
 */
(function () {
  "use strict";

  var dict = window.__ZH__;
  if (!dict) return;

  var LETTER_RE = /[A-Za-z]/;
  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, NOSCRIPT: 1 };
  var ATTR_NAMES = ["title", "aria-label", "placeholder"];

  function translate(text) {
    var stripped = text.trim();
    if (stripped) {
      var replacement = dict.exact[stripped];
      if (replacement === undefined) {
        replacement = dict.lower[stripped.toLowerCase()];
      }
      if (replacement !== undefined) {
        return text.replace(stripped, replacement);
      }
    }
    for (var i = 0; i < dict.subs.length; i++) {
      var pair = dict.subs[i];
      if (text.indexOf(pair[0]) !== -1) {
        text = text.split(pair[0]).join(pair[1]);
      }
    }
    return text;
  }

  function isEditable(el) {
    if (el.isContentEditable) return true;
    var node = el;
    while (node && node.nodeType === 1) {
      if (node.getAttribute && node.getAttribute("contenteditable") === "true") {
        return true;
      }
      node = node.parentNode;
    }
    return false;
  }

  function translateTextNode(node) {
    if (!LETTER_RE.test(node.data)) return;
    var parent = node.parentNode;
    if (!parent || parent.nodeType !== 1) return;
    if (SKIP_TAGS[parent.tagName]) return;
    if (isEditable(parent)) return;
    var out = translate(node.data);
    if (out !== node.data) node.data = out;
  }

  function translateAttrs(el) {
    for (var i = 0; i < ATTR_NAMES.length; i++) {
      var name = ATTR_NAMES[i];
      if (el.hasAttribute(name)) {
        var value = el.getAttribute(name);
        var newValue = translate(value);
        if (newValue !== value) el.setAttribute(name, newValue);
      }
    }
    if (
      el.tagName === "INPUT" &&
      (el.type === "submit" || el.type === "button") &&
      el.value
    ) {
      var newVal = translate(el.value);
      if (newVal !== el.value) el.value = newVal;
    }
  }

  function walk(root) {
    if (root.nodeType === 3) {
      translateTextNode(root);
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 11) return;

    if (root.nodeType === 1) translateAttrs(root);

    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      translateTextNode(node);
    }

    if (root.querySelectorAll) {
      var elements = root.querySelectorAll("*");
      for (var j = 0; j < elements.length; j++) {
        translateAttrs(elements[j]);
      }
    }
  }

  var observer = new MutationObserver(function (mutations) {
    for (var m = 0; m < mutations.length; m++) {
      var mutation = mutations[m];
      if (mutation.type === "childList") {
        for (var k = 0; k < mutation.addedNodes.length; k++) {
          walk(mutation.addedNodes[k]);
        }
      } else if (mutation.type === "characterData") {
        translateTextNode(mutation.target);
      } else if (mutation.type === "attributes" && mutation.target.nodeType === 1) {
        translateAttrs(mutation.target);
      }
    }
  });

  function start() {
    walk(document.body);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["title", "aria-label", "placeholder", "value"]
    });
  }

  if (document.body) {
    start();
  } else {
    document.addEventListener("DOMContentLoaded", start);
  }
})();
