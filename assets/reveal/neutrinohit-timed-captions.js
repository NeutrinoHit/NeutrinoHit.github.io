(function () {
  if (window.__neutrinohitTimedCaptionsLoaded) return;
  window.__neutrinohitTimedCaptionsLoaded = true;

  function numberFromDataset(element, key, fallback) {
    if (!element || element.dataset[key] === undefined) return fallback;
    const value = Number.parseFloat(element.dataset[key]);
    return Number.isFinite(value) ? value : fallback;
  }

  function cueData(cueElements) {
    return cueElements
      .map((element, index) => ({
        element,
        index,
        start: numberFromDataset(element, "start", 0),
        end: numberFromDataset(element, "end", Number.POSITIVE_INFINITY),
        text: element.textContent.trim()
      }))
      .sort((left, right) => left.start - right.start);
  }

  function activeCue(cues, time) {
    let active = null;
    for (const cue of cues) {
      if (time < cue.start) break;
      if (time >= cue.start && time < cue.end) active = cue;
    }
    return active;
  }

  function renderCaption(state, cue) {
    if (state.activeIndex === (cue ? cue.index : -1)) return;
    state.activeIndex = cue ? cue.index : -1;

    state.cueElements.forEach((element) => element.classList.remove("is-active"));
    if (cue) cue.element.classList.add("is-active");

    state.caption.classList.remove("is-visible");

    window.setTimeout(() => {
      state.captionText.textContent = cue ? cue.text : "";
      state.caption.classList.toggle("is-visible", Boolean(cue));
    }, 90);
  }

  function setupTimedVideo(container) {
    if (container.dataset.timedCaptionsReady === "1") return;

    const video = container.querySelector("video");
    const cueList = container.querySelector("[data-caption-cues]");
    const cueElements = cueList ? Array.from(cueList.querySelectorAll("[data-start]")) : [];
    const caption = container.querySelector("[data-caption-display]");
    const captionText = caption ? caption.querySelector("[data-caption-text]") : null;

    if (!video || !cueElements.length || !caption || !captionText) return;

    container.dataset.timedCaptionsReady = "1";
    const state = {
      activeIndex: -2,
      cues: cueData(cueElements),
      cueElements,
      caption,
      captionText
    };

    function update() {
      renderCaption(state, activeCue(state.cues, video.currentTime || 0));
    }

    ["loadedmetadata", "timeupdate", "seeked", "play", "pause", "ratechange"].forEach((eventName) => {
      video.addEventListener(eventName, update);
    });

    update();
  }

  function setupAll() {
    document.querySelectorAll("[data-timed-video]").forEach(setupTimedVideo);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupAll, { once: true });
  } else {
    setupAll();
  }

  if (window.Reveal && typeof window.Reveal.on === "function") {
    window.Reveal.on("slidechanged", setupAll);
    window.Reveal.on("ready", setupAll);
  }
})();
