(() => {
  "use strict";
  const codeBlocks = document.querySelectorAll(".article-content .highlight, .article-content pre.chroma, .article-content .chroma");
  codeBlocks.forEach((frame) => {
    if (frame.dataset.azEnhanced === "true") return;
    const pre = frame.matches("pre") ? frame : frame.querySelector("pre");
    if (!pre) return;
    frame.dataset.azEnhanced = "true";
    frame.classList.add("az-code-frame");
    const code = pre.querySelector("code");
    const classNames = [code?.className || "", pre.className || "", frame.className || ""].join(" ");
    const lang = code?.dataset.lang || pre.dataset.lang || frame.dataset.lang ||
      (classNames.match(/language-([\w+#.-]+)/i) || [])[1] ||
      (classNames.match(/lang(?:uage)?-([\w+#.-]+)/i) || [])[1] || "CODE";
    const toolbar = document.createElement("div");
    toolbar.className = "az-code-toolbar";
    const badge = document.createElement("span");
    badge.className = "az-code-language";
    badge.textContent = lang.toUpperCase();
    const copy = document.createElement("button");
    copy.className = "az-code-copy";
    copy.type = "button";
    copy.textContent = "COPY";
    copy.setAttribute("aria-label", "コードをコピー");
    copy.addEventListener("click", async () => {
      const text = code?.innerText ?? pre.innerText;
      try {
        await navigator.clipboard.writeText(text);
        copy.textContent = "COPIED";
        copy.classList.add("is-copied");
      } catch {
        copy.textContent = "FAILED";
      }
      window.setTimeout(() => {
        copy.textContent = "COPY";
        copy.classList.remove("is-copied");
      }, 1600);
    });
    toolbar.append(badge, copy);
    frame.insertBefore(toolbar, pre);
  });
})();