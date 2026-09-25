/* Experiment 002 stays visibly pending until a verified local result file exists. */
(function () {
  "use strict";

  const resultPanel = document.getElementById("experiment-002-results");
  const badge = document.getElementById("experiment-002-badge");

  function element(tag, className, content) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = String(content);
    return node;
  }

  function safeHref(value) {
    if (typeof value !== "string" || !value.trim()) return null;
    try {
      const url = new URL(value, document.baseURI);
      if (url.protocol === "https:" || url.protocol === "http:" ||
          (location.protocol === "file:" && url.protocol === "file:")) return url.href;
    } catch (_) {
      // A malformed download path is omitted from the published card.
    }
    return null;
  }

  function renderExperiment002(data) {
    if (!resultPanel || !badge || !data || typeof data !== "object") return false;
    if (!["status", "headline", "summary"].every(key =>
      typeof data[key] === "string" && data[key].trim())) return false;

    const content = document.createDocumentFragment();
    content.append(element("p", "result-label", "RELEASED OUTCOME"));
    content.append(element("p", "result-status", data.status));
    content.append(element("h4", "result-headline", data.headline));
    content.append(element("p", "result-summary", data.summary));

    if (Array.isArray(data.metrics) && data.metrics.length) {
      const metrics = element("div", "result-metrics");
      for (const metric of data.metrics) {
        if (!metric || typeof metric.label !== "string" ||
            !["string", "number"].includes(typeof metric.value)) continue;
        const item = element("div", "result-metric");
        item.append(element("span", "", metric.label));
        item.append(element("strong", "", metric.value));
        if (typeof metric.detail === "string" && metric.detail.trim())
          item.append(element("small", "", metric.detail));
        metrics.append(item);
      }
      if (metrics.childElementCount) content.append(metrics);
    }

    if (Array.isArray(data.downloads) && data.downloads.length) {
      const list = element("ul", "result-downloads");
      for (const download of data.downloads) {
        const href = download && safeHref(download.url);
        if (!href || typeof download.label !== "string" || !download.label.trim()) continue;
        const item = document.createElement("li");
        const link = element("a", "", download.label);
        link.href = href;
        item.append(link);
        list.append(item);
      }
      if (list.childElementCount) {
        content.append(element("p", "result-subheading", "Downloads"));
        content.append(list);
      }
    }

    if (Array.isArray(data.limitations) && data.limitations.length) {
      const list = element("ul", "result-limitations");
      for (const limitation of data.limitations) {
        if (typeof limitation !== "string" || !limitation.trim()) continue;
        list.append(element("li", "", limitation));
      }
      if (list.childElementCount) {
        content.append(element("p", "result-subheading", "Limitations"));
        content.append(list);
      }
    }

    resultPanel.replaceChildren(content);
    badge.textContent = data.status;
    return true;
  }

  window.EEGT = Object.freeze({ renderExperiment002 });

  fetch("./data/experiment-002.json", { cache: "no-store" })
    .then(response => response.ok ? response.json() : null)
    .then(data => { if (data) renderExperiment002(data); })
    .catch(() => { /* The HTML already contains the accurate pending state. */ });
}());
