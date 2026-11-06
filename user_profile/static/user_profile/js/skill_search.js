"use strict";

const search = document.getElementById("skill-search");
const list = document.getElementById("id_skills");
const emptyMessage = document.getElementById("skill-search-empty");
const showAllButton = document.getElementById("skill-show-all");

if (search && list && emptyMessage && showAllButton) {
  const options = Array.from(list.children).map((element) => ({
    element,
    checkbox: element.querySelector('input[type="checkbox"]'),
    name: element.textContent.trim().toLocaleLowerCase(),
  })).filter((option) => option.checkbox);
  const seed = document.querySelector(".skill-picker").dataset.skillSeed;
  let showAll = false;

  // A stable sample for each username; no server-side randomness or saved state.
  function hash(text) {
    let value = 2166136261;
    for (const character of text) {
      value = Math.imul(value ^ character.charCodeAt(0), 16777619);
    }
    return value >>> 0;
  }

  const examples = new Set(
    [...options]
      .sort((a, b) => hash(`${seed}:${a.name}`) - hash(`${seed}:${b.name}`))
      .slice(0, 6)
      .map((option) => option.element)
  );

  // Return only close spelling differences, including one omitted or extra letter.
  function editDistance(first, second) {
    let previous = Array.from({ length: second.length + 1 }, (_, i) => i);
    for (let i = 1; i <= first.length; i += 1) {
      const current = [i];
      for (let j = 1; j <= second.length; j += 1) {
        current[j] = Math.min(
          current[j - 1] + 1,
          previous[j] + 1,
          previous[j - 1] + (first[i - 1] === second[j - 1] ? 0 : 1)
        );
      }
      previous = current;
    }
    return previous[second.length];
  }

  function matches(name, query) {
    if (!query || name.includes(query)) return true;

    const maxDistance = query.length >= 5 ? 2 : 1;
    const words = [name, ...name.split(/\s+/)];
    return words.some((word) =>
      Math.abs(word.length - query.length) <= maxDistance &&
      editDistance(word, query) <= maxDistance
    );
  }

  function update() {
    const query = search.value.trim().toLocaleLowerCase();
    let matchCount = 0;
    for (const option of options) {
      const found = matches(option.name, query);
      if (query && found && !option.checkbox.checked) matchCount += 1;
      option.element.hidden = !option.checkbox.checked && (
        query ? !found : !showAll && !examples.has(option.element)
      );
    }
    emptyMessage.hidden = !query || matchCount > 0;
    showAllButton.hidden = Boolean(query);
    showAllButton.textContent = showAll ? "Show fewer skills" : "Show all skills";
    showAllButton.setAttribute("aria-expanded", String(showAll));
  }

  search.addEventListener("input", () => {
    showAll = false;
    update();
  });
  showAllButton.addEventListener("click", () => {
    showAll = !showAll;
    update();
  });
  list.addEventListener("change", update);
  update();
}
