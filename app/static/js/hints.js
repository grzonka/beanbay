/**
 * hints.js — One-time parameter onboarding hints + "new" badge manager.
 *
 * ParamHintManager tracks which parameter hints the user has already seen
 * using localStorage, then reveals only unseen hints on page load.
 *
 * "New" badge: parameters beyond the 4 Tier-1 baseline params that appear
 * for the first time in a recommendation get a "new" badge. Tracked per-bean
 * via localStorage so the badge disappears on subsequent visits.
 *
 * Usage: included in recommend.html — no explicit initialisation needed.
 */

(function () {
  "use strict";

  /** localStorage key for dismissed hint param names (JSON array). */
  var HINTS_KEY = "bb_param_hints_seen";

  /** localStorage key for seen-params-per-bean (JSON object: beanId → [param, ...]). */
  var NEW_PARAMS_KEY = "bb_params_seen_per_bean";

  /**
   * Tier-1 baseline param names — always shown, never get a "new" badge.
   * These are the 4 core params present in every espresso campaign.
   */
  var TIER1_PARAMS = ["grind_setting", "temperature", "dose_in", "target_yield"];

  // ---------------------------------------------------------------------------
  // ParamHintManager
  // ---------------------------------------------------------------------------

  function ParamHintManager() {
    this._seen = this._load();
  }

  /** Load the set of seen param names from localStorage. */
  ParamHintManager.prototype._load = function () {
    try {
      var raw = localStorage.getItem(HINTS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (_) {
      return [];
    }
  };

  /** Persist the current seen set to localStorage. */
  ParamHintManager.prototype._save = function () {
    try {
      localStorage.setItem(HINTS_KEY, JSON.stringify(this._seen));
    } catch (_) {
      // Storage full or private mode — silently ignore.
    }
  };

  /** Return true if the user has already seen (dismissed) this param's hint. */
  ParamHintManager.prototype.hasSeen = function (paramName) {
    return this._seen.indexOf(paramName) !== -1;
  };

  /** Mark a param hint as seen and hide its card. */
  ParamHintManager.prototype.dismiss = function (paramName) {
    if (!this.hasSeen(paramName)) {
      this._seen.push(paramName);
      this._save();
    }
    var card = document.getElementById("hint-" + paramName);
    if (card) {
      card.classList.add("hidden");
    }
  };

  /** Show all unseen hint cards that are present in the DOM. */
  ParamHintManager.prototype.showUnseenHints = function () {
    var self = this;
    var cards = document.querySelectorAll(".param-hint-card");
    cards.forEach(function (card) {
      var paramName = card.getAttribute("data-param");
      if (paramName && !self.hasSeen(paramName)) {
        card.classList.remove("hidden");
      }
    });
  };

  // ---------------------------------------------------------------------------
  // "New" badge manager
  // ---------------------------------------------------------------------------

  /**
   * For the current bean, mark advanced params as "new" if this is their first
   * appearance. Injects a <span class="badge badge-accent badge-sm">new</span>
   * next to the recipe-value for each genuinely new param.
   *
   * @param {string} beanId  - Active bean identifier (e.g. "42")
   * @param {string[]} presentParams - Param names present in this recommendation
   */
  function applyNewBadges(beanId, presentParams) {
    if (!beanId || !presentParams || presentParams.length === 0) return;

    var storageObj;
    try {
      var raw = localStorage.getItem(NEW_PARAMS_KEY);
      storageObj = raw ? JSON.parse(raw) : {};
    } catch (_) {
      storageObj = {};
    }

    var seenForBean = storageObj[beanId] || [];

    presentParams.forEach(function (paramName) {
      // Skip Tier-1 baseline params — they're never "new".
      if (TIER1_PARAMS.indexOf(paramName) !== -1) return;

      var isNew = seenForBean.indexOf(paramName) === -1;
      if (isNew) {
        // Inject badge into the matching recipe-param div.
        var paramDivs = document.querySelectorAll(".recipe-param");
        paramDivs.forEach(function (div) {
          // Match by data-param attribute if set, else skip (badge is best-effort).
          var attr = div.getAttribute("data-param");
          if (attr === paramName) {
            var valueEl = div.querySelector(".recipe-value");
            if (valueEl && !div.querySelector(".badge-new-param")) {
              var badge = document.createElement("span");
              badge.className = "badge badge-accent badge-sm badge-new-param ml-1";
              badge.textContent = "new";
              valueEl.appendChild(badge);
            }
          }
        });

        // Record as seen so badge only shows once.
        seenForBean.push(paramName);
      }
    });

    // Persist updated seen list.
    storageObj[beanId] = seenForBean;
    try {
      localStorage.setItem(NEW_PARAMS_KEY, JSON.stringify(storageObj));
    } catch (_) {
      // Ignore storage errors.
    }
  }

  // ---------------------------------------------------------------------------
  // Initialise on DOMContentLoaded
  // ---------------------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", function () {
    var manager = new ParamHintManager();
    // Expose globally so inline onclick handlers (dismiss button) can call it.
    window.paramHintManager = manager;

    // Show hints for params the user hasn't seen yet.
    manager.showUnseenHints();

    // Apply "new" badges using meta tags injected by the template.
    var beanMeta = document.querySelector("meta[name='bb-bean-id']");
    var paramsMeta = document.querySelector("meta[name='bb-rec-params']");
    if (beanMeta && paramsMeta) {
      var beanId = beanMeta.getAttribute("content");
      var recParams;
      try {
        recParams = JSON.parse(paramsMeta.getAttribute("content"));
      } catch (_) {
        recParams = [];
      }
      applyNewBadges(beanId, recParams);
    }
  });
})();
