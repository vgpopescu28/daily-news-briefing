(function () {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("daily-news-theme");
  if (savedTheme) {
    root.dataset.theme = savedTheme;
  }

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const current = root.dataset.theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      localStorage.setItem("daily-news-theme", next);
    });
  });

  const filterRoot = document.querySelector("[data-filter-root]");
  if (!filterRoot) {
    return;
  }

  const storyCards = Array.from(document.querySelectorAll("[data-category]"));
  const sectionNodes = Array.from(document.querySelectorAll("[data-section]"));

  filterRoot.addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter]");
    if (!button) {
      return;
    }

    const filter = button.dataset.filter;
    filterRoot.querySelectorAll("[data-filter]").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });

    storyCards.forEach((card) => {
      const visible = filter === "all" || card.dataset.category === filter;
      card.classList.toggle("is-hidden", !visible);
    });

    sectionNodes.forEach((section) => {
      const cards = section.querySelectorAll(".story-card:not(.is-hidden), .featured-card:not(.is-hidden)");
      section.classList.toggle("is-hidden", cards.length === 0);
    });
  });
})();
