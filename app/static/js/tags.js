/**
 * tags.js — Flavor tag input and modal behavior for BeanBay.
 *
 * Handles:
 * - Adding tags via Enter or comma key in the brew form tag input
 * - Adding/removing tags in the edit modal tag input
 * - Max 10 tags enforcement on both inputs
 * - Updating hidden inputs with comma-separated tag values
 * - Form submit: strips name from untouched flavor sliders so they submit null
 * - HX-Trigger "openShotModal" listener: calls dialog.showModal()
 * - Re-initializing edit tag behavior after htmx content swaps
 */

(function () {
  "use strict";

  var MAX_TAGS = 10;

  // ---------------------------------------------------------------------------
  // Brew form tag input (IDs: tag-input, tag-list, flavor-tags-hidden)
  // ---------------------------------------------------------------------------

  var brewTags = [];

  function updateBrewHidden() {
    var hidden = document.getElementById("flavor-tags-hidden");
    if (hidden) {
      hidden.value = brewTags.join(",");
    }
  }

  function renderBrewTags() {
    var list = document.getElementById("tag-list");
    var input = document.getElementById("tag-input");
    if (!list) return;

    list.innerHTML = "";
    brewTags.forEach(function (tag, index) {
      var chip = document.createElement("span");
      chip.className = "tag-chip";
      chip.textContent = tag;

      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "tag-chip-remove";
      remove.setAttribute("aria-label", "Remove " + tag);
      remove.textContent = "✕";
      remove.addEventListener("click", function () {
        brewTags.splice(index, 1);
        renderBrewTags();
        updateBrewHidden();
        if (input) input.disabled = false;
      });

      chip.appendChild(remove);
      list.appendChild(chip);
    });

    if (input) {
      input.disabled = brewTags.length >= MAX_TAGS;
      if (input.disabled) {
        input.placeholder = "Max " + MAX_TAGS + " tags reached";
      } else {
        input.placeholder = "Type a flavor (e.g. chocolate, citrus)...";
      }
    }

    updateBrewHidden();
  }

  function addBrewTag(value) {
    var trimmed = value.trim().replace(/,+$/, "").trim();
    if (!trimmed) return false;
    if (brewTags.length >= MAX_TAGS) return false;
    if (brewTags.indexOf(trimmed) !== -1) return false;
    brewTags.push(trimmed);
    renderBrewTags();
    return true;
  }

  function initBrewTagInput() {
    var input = document.getElementById("tag-input");
    if (!input) return;

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        if (addBrewTag(input.value)) {
          input.value = "";
        } else {
          input.value = input.value.replace(/,+$/, "").trim();
        }
      }
    });

    input.addEventListener("blur", function () {
      if (input.value.trim()) {
        if (addBrewTag(input.value)) {
          input.value = "";
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Edit modal tag input (IDs: edit-tag-input, edit-tag-list, edit-flavor-tags-hidden)
  // Exposed as window.removeEditTag for inline onclick in pre-populated chips
  // ---------------------------------------------------------------------------

  function getEditTagsFromDOM() {
    var list = document.getElementById("edit-tag-list");
    if (!list) return [];
    var chips = list.querySelectorAll(".tag-chip[data-tag]");
    var tags = [];
    chips.forEach(function (chip) {
      tags.push(chip.getAttribute("data-tag"));
    });
    return tags;
  }

  function updateEditHidden(tags) {
    var hidden = document.getElementById("edit-flavor-tags-hidden");
    if (hidden) {
      hidden.value = tags.join(",");
    }
  }

  function renderEditTag(tag, tags) {
    var list = document.getElementById("edit-tag-list");
    if (!list) return;

    var chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.setAttribute("data-tag", tag);
    chip.textContent = tag + " ";

    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "tag-chip-remove";
    remove.setAttribute("aria-label", "Remove " + tag);
    remove.textContent = "✕";
    remove.addEventListener("click", function () {
      chip.remove();
      var current = getEditTagsFromDOM();
      updateEditHidden(current);
      var input = document.getElementById("edit-tag-input");
      if (input) input.disabled = current.length >= MAX_TAGS;
    });

    chip.appendChild(remove);
    list.appendChild(chip);
  }

  // Global function for inline onclick on pre-populated chips in _shot_edit.html
  window.removeEditTag = function (btn) {
    var chip = btn.closest(".tag-chip");
    if (chip) {
      chip.remove();
      var current = getEditTagsFromDOM();
      updateEditHidden(current);
      var input = document.getElementById("edit-tag-input");
      if (input) input.disabled = current.length >= MAX_TAGS;
    }
  };

  function addEditTag(value) {
    var trimmed = value.trim().replace(/,+$/, "").trim();
    if (!trimmed) return false;
    var current = getEditTagsFromDOM();
    if (current.length >= MAX_TAGS) return false;
    if (current.indexOf(trimmed) !== -1) return false;
    renderEditTag(trimmed, current);
    updateEditHidden(getEditTagsFromDOM());
    return true;
  }

  function initEditTagInput() {
    var input = document.getElementById("edit-tag-input");
    if (!input) return;

    // Remove old listeners by cloning
    var fresh = input.cloneNode(true);
    input.parentNode.replaceChild(fresh, input);
    input = fresh;

    // Sync hidden from pre-populated DOM chips
    var existing = getEditTagsFromDOM();
    updateEditHidden(existing);
    input.disabled = existing.length >= MAX_TAGS;

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        if (addEditTag(input.value)) {
          input.value = "";
        } else {
          input.value = input.value.replace(/,+$/, "").trim();
        }
      }
    });

    input.addEventListener("blur", function () {
      if (input.value.trim()) {
        if (addEditTag(input.value)) {
          input.value = "";
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Flavor slider: strip name from untouched sliders on form submit
  // Taste slider: block submit if untouched
  // ---------------------------------------------------------------------------

  function initFlavorSliders() {
    document.addEventListener("submit", function (e) {
      var form = e.target;

      // Taste slider: block submit if untouched (unless no taste slider on this page)
      var tasteInput = form.querySelector('#taste');
      if (tasteInput && tasteInput.dataset.touched !== 'true') {
        e.preventDefault();
        var msg = document.getElementById('taste-required-msg');
        if (msg) {
          msg.classList.add('visible');
          // Scroll the message into view so user sees it
          msg.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
      }

      // Strip name from untouched flavor sliders so they submit null
      var sliders = form.querySelectorAll(".flavor-slider");
      sliders.forEach(function (slider) {
        if (slider.dataset.touched !== "true") {
          slider.removeAttribute("name");
        }
      });
    });

    // Hide taste validation message on slider interaction
    var tasteSlider = document.getElementById('taste');
    if (tasteSlider) {
      tasteSlider.addEventListener('input', function () {
        var msg = document.getElementById('taste-required-msg');
        if (msg) msg.classList.remove('visible');
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Modal: listen for HX-Trigger "openShotModal" to call dialog.showModal()
  // ---------------------------------------------------------------------------

  function initModalTrigger() {
    document.body.addEventListener("openShotModal", function () {
      var modal = document.getElementById("shot-modal");
      if (modal) modal.showModal();
    });
  }

  // ---------------------------------------------------------------------------
  // htmx: re-init edit tag input after every content swap
  // ---------------------------------------------------------------------------

  function initHtmxHooks() {
    document.body.addEventListener("htmx:afterSettle", function () {
      initEditTagInput();
    });
  }

  // ---------------------------------------------------------------------------
  // toggleFailed — shared across recommend, best, and manual brew forms
  // Exposed as window.toggleFailed for inline onchange handlers
  // ---------------------------------------------------------------------------

  window.toggleFailed = function (checkbox) {
    var tasteGroup = document.getElementById('taste-group');
    var tasteInput = document.getElementById('taste');
    var tasteDisplay = document.getElementById('taste-display');
    var requiredMsg = document.getElementById('taste-required-msg');

    if (checkbox.checked) {
      tasteInput.value = '1';
      tasteInput.dataset.touched = 'true';
      tasteDisplay.textContent = '1.0';
      tasteGroup.classList.add('touched');
      tasteGroup.style.opacity = '0.4';
      tasteGroup.style.pointerEvents = 'none';
      if (requiredMsg) requiredMsg.classList.remove('visible');
    } else {
      tasteInput.value = '7.0';
      tasteInput.dataset.touched = 'false';
      tasteDisplay.textContent = '\u2014';
      tasteGroup.classList.remove('touched');
      tasteGroup.style.opacity = '';
      tasteGroup.style.pointerEvents = 'auto';
    }
  };

  // ---------------------------------------------------------------------------
  // Bootstrap
  // ---------------------------------------------------------------------------

  function init() {
    initBrewTagInput();
    initFlavorSliders();
    initModalTrigger();
    initHtmxHooks();
    initEditTagInput(); // in case edit form is already in DOM
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
