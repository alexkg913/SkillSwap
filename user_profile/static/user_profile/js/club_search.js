"use strict";

const clubPicker = document.getElementById("club-picker");
const clubSearch = document.getElementById("club-search");
const clubMajor = document.getElementById("id_major");
const clubList = document.getElementById("id_interests_clubs");
const clubStatus = document.getElementById("club-search-empty");

if (clubPicker && clubSearch && clubMajor && clubList && clubStatus) {
  let timer;
  let requestNumber = 0;

  function addClub(name, animate = false, delay = 0) {
    const wrapper = document.createElement("div");
    if (animate) {
      wrapper.style.setProperty("--skill-enter-delay", `${delay}ms`);
      wrapper.classList.add("club-suggestion--enter");
      wrapper.addEventListener("animationend", () => {
        wrapper.classList.remove("club-suggestion--enter");
      }, { once: true });
    }
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "interests_clubs";
    checkbox.value = name;
    checkbox.id = `club-result-${requestNumber}-${clubList.children.length}`;
    label.append(checkbox, document.createTextNode(name));
    wrapper.append(label);
    clubList.append(wrapper);
  }

  async function refresh(animate = false) {
    const current = ++requestNumber;
    const url = new URL(clubPicker.dataset.searchUrl, window.location.href);
    url.searchParams.set("major", clubMajor.value);
    url.searchParams.set("q", clubSearch.value.trim());

    try {
      const response = await fetch(url, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Club search unavailable");
      const { clubs } = await response.json();
      if (current !== requestNumber) return;

      const wanted = new Set(clubs);
      const present = new Set();
      for (const wrapper of Array.from(clubList.children)) {
        const checkbox = wrapper.querySelector('input[type="checkbox"]');
        if (!checkbox) continue;
        if (!checkbox.checked && !wanted.has(checkbox.value)) {
          wrapper.remove();
        } else {
          present.add(checkbox.value);
        }
      }
      let newSuggestions = 0;
      for (const name of clubs) {
        if (!present.has(name)) {
          addClub(name, animate, newSuggestions * 55);
          newSuggestions += 1;
          present.add(name);
        }
      }
      clubStatus.textContent = "No matching unselected clubs. Try another spelling.";
      clubStatus.hidden = !clubSearch.value.trim() || clubs.some((name) =>
        !Array.from(clubList.querySelectorAll('input[type="checkbox"]')).some(
          (checkbox) => checkbox.value === name && checkbox.checked
        )
      );
    } catch (error) {
      if (current !== requestNumber) return;
      clubStatus.textContent = "Club search is unavailable. Your selected clubs are still saved when you submit.";
      clubStatus.hidden = false;
    }
  }

  clubSearch.addEventListener("input", () => {
    ++requestNumber;
    clearTimeout(timer);
    timer = setTimeout(() => refresh(true), 250);
  });
  clubMajor.addEventListener("change", () => {
    clearTimeout(timer);
    refresh(!clubSearch.value.trim());
  });
}
