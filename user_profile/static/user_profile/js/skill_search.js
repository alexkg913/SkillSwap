"use strict";

const picker = document.querySelector(".skill-picker");
const search = document.getElementById("skill-search");
const major = document.getElementById("id_major");
const list = document.getElementById("id_skills");
const status = document.getElementById("skill-search-empty");

if (picker && search && major && list && status) {
  let timer;
  let requestNumber = 0;

  function addSkill(name, animateSuggestion = false, delay = 0) {
    const wrapper = document.createElement("div");
    if (animateSuggestion) {
      wrapper.style.setProperty("--skill-enter-delay", `${delay}ms`);
      wrapper.classList.add("skill-suggestion--enter");
      wrapper.addEventListener("animationend", () => {
        wrapper.classList.remove("skill-suggestion--enter");
      }, { once: true });
    }
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "skills";
    checkbox.value = name;
    checkbox.id = `skill-result-${requestNumber}-${list.children.length}`;
    label.append(checkbox, document.createTextNode(name));
    wrapper.append(label);
    list.append(wrapper);
  }

  async function refresh(animateSuggestions = false) {
    const current = ++requestNumber;
    const url = new URL(picker.dataset.searchUrl, window.location.href);
    url.searchParams.set("major", major.value);
    url.searchParams.set("q", search.value.trim());

    try {
      const response = await fetch(url, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Skill search unavailable");
      const { skills } = await response.json();
      if (current !== requestNumber) return;

      const wanted = new Set(skills);
      const present = new Set();
      for (const wrapper of Array.from(list.children)) {
        const checkbox = wrapper.querySelector('input[type="checkbox"]');
        if (!checkbox) continue;
        if (!checkbox.checked && !wanted.has(checkbox.value)) {
          wrapper.remove();
        } else {
          present.add(checkbox.value);
        }
      }
      let newSuggestions = 0;
      for (const name of skills) {
        if (!present.has(name)) {
          addSkill(name, animateSuggestions, newSuggestions * 55);
          newSuggestions += 1;
          present.add(name);
        }
      }
      status.textContent = "No matching unselected skills. Try another spelling.";
      status.hidden = !search.value.trim() || skills.some((name) =>
        !Array.from(list.querySelectorAll('input[type="checkbox"]')).some(
          (checkbox) => checkbox.value === name && checkbox.checked
        )
      );
    } catch (error) {
      if (current !== requestNumber) return;
      status.textContent = "Skills search is unavailable. Your selected skills are still saved when you submit.";
      status.hidden = false;
    }
  }

  search.addEventListener("input", () => {
    ++requestNumber;
    clearTimeout(timer);
    timer = setTimeout(() => refresh(true), 250);
  });
  major.addEventListener("change", () => {
    clearTimeout(timer);
    refresh(!search.value.trim());
  });
}
