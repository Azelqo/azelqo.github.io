(() => {
  "use strict";

  // Code-copy enhancement for long-form articles.
  const frames = document.querySelectorAll(".article-content .highlight, .article-content pre.chroma, .article-content .chroma");
  if (frames.length) {
    let toast;
    let toastTimer;
    const announce = (message) => {
      if (!toast) {
        toast = document.createElement("div");
        toast.className = "az-copy-toast";
        toast.setAttribute("role", "status");
        toast.setAttribute("aria-live", "polite");
        toast.setAttribute("aria-atomic", "true");
        document.body.appendChild(toast);
      }
      toast.textContent = message;
      toast.classList.add("is-visible");
      window.clearTimeout(toastTimer);
      toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 1900);
    };
    const fallbackCopy = (value) => {
      const field = document.createElement("textarea");
      field.value = value;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.opacity = "0";
      field.style.pointerEvents = "none";
      document.body.appendChild(field);
      field.select();
      let copied = false;
      try { copied = document.execCommand("copy"); } catch (_) {}
      field.remove();
      return copied;
    };
    frames.forEach((frame) => {
      if (frame.dataset.azEnhanced === "true") return;
      const pre = frame.matches("pre") ? frame : frame.querySelector("pre");
      if (!pre) return;
      frame.dataset.azEnhanced = "true";
      frame.classList.add("az-code-frame");
      const code = pre.querySelector("code");
      const classes = [code?.className || "", pre.className || "", frame.className || ""].join(" ");
      const lang = code?.dataset.lang || pre.dataset.lang || frame.dataset.lang ||
        (classes.match(/language-([\\w+#.-]+)/i) || [])[1] ||
        (classes.match(/lang(?:uage)?-([\\w+#.-]+)/i) || [])[1] || "CODE";
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
        const value = code?.innerText ?? pre.innerText;
        let copied = false;
        try {
          if (navigator.clipboard?.writeText && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
            copied = true;
          } else copied = fallbackCopy(value);
        } catch (_) { copied = fallbackCopy(value); }
        copy.textContent = copied ? "COPIED" : "FAILED";
        copy.classList.toggle("is-copied", copied);
        copy.setAttribute("aria-label", copied ? "コードをコピーしました" : "コピーに失敗しました");
        announce(copied ? "コードをクリップボードにコピーしました" : "コピーできませんでした。コードを選択してコピーしてください。");
        window.setTimeout(() => {
          copy.textContent = "COPY";
          copy.classList.remove("is-copied");
          copy.setAttribute("aria-label", "コードをコピー");
        }, 1900);
      });
      toolbar.append(badge, copy);
      frame.insertBefore(toolbar, pre);
    });
  }

  // Japanese Standard Time clock for the editorial masthead.
  const clock = document.querySelector("[data-az-clock]");
  if (clock) {
    const updateClock = () => {
      clock.textContent = new Intl.DateTimeFormat("ja-JP", {
        timeZone: "Asia/Tokyo", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
      }).format(new Date());
    };
    updateClock();
    window.setInterval(updateClock, 1000);
  }

  // Progressive reveal; content remains visible if IntersectionObserver is unavailable.
  const revealItems = document.querySelectorAll("[data-az-reveal]");
  if (revealItems.length && "IntersectionObserver" in window &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const observer = new IntersectionObserver((entries, current) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          current.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -48px 0px", threshold: 0.08 });
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }
})();