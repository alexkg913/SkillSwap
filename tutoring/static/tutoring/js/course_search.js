"use strict";

/* Searchable course picker.

   The catalog has ~960 selectable courses, far too many to render as <option>
   elements, so the box asks the server for a bounded slice as the student
   types. This mirrors the skills picker in user_profile: a debounced fetch, a
   request counter so a slow response cannot overwrite a newer one, and a
   readable message when the endpoint is unavailable.

   Two modes, both driven from the same markup contract:

     data-mode="single"  one hidden input, replaced on each pick (Find a Tutor)
     data-mode="multi"   one hidden input per pick, shown as removable chips

   The server validates every submitted code against the whole catalog, so
   nothing here is a permission or correctness check -- it only decides what
   the page offers. */

for (const picker of document.querySelectorAll(".course-picker")) {
  setupPicker(picker);
}

function setupPicker(picker) {
  const input = picker.querySelector(".course-picker__input");
  const listbox = picker.querySelector(".course-picker__listbox");
  const status = picker.querySelector(".course-picker__status");
  const values = picker.querySelector(".course-picker__values");
  const chips = picker.querySelector(".course-picker__chips");
  const searchUrl = picker.dataset.searchUrl;
  const multiple = picker.dataset.mode === "multi";

  if (!input || !listbox || !status || !values || !searchUrl) return;

  let timer;
  let requestNumber = 0;
  let options = [];
  let activeIndex = -1;

  function selectedCodes() {
    return Array.from(values.querySelectorAll("input")).map((field) => field.value);
  }

  function close() {
    listbox.hidden = true;
    listbox.replaceChildren();
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    options = [];
    activeIndex = -1;
  }

  function setActive(index) {
    const items = Array.from(listbox.children);
    if (!items.length) return;
    activeIndex = (index + items.length) % items.length;
    items.forEach((item, i) => {
      const isActive = i === activeIndex;
      item.classList.toggle("course-picker__option--active", isActive);
      item.setAttribute("aria-selected", isActive ? "true" : "false");
      if (isActive) {
        input.setAttribute("aria-activedescendant", item.id);
        item.scrollIntoView({ block: "nearest" });
      }
    });
  }

  function addChip(course) {
    const chip = document.createElement("li");
    chip.className = "course-picker__chip";

    const text = document.createElement("span");
    text.textContent = course.label;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "course-picker__chip-remove";
    remove.textContent = "\u00d7";
    remove.setAttribute("aria-label", `Remove ${course.label}`);
    remove.addEventListener("click", () => {
      chip.remove();
      const field = values.querySelector(`input[value="${cssEscape(course.code)}"]`);
      if (field) field.remove();
      announceSelection();
      input.focus();
    });

    chip.append(text, remove);
    chips.append(chip);
  }

  function announceSelection() {
    if (!multiple) return;
    const count = selectedCodes().length;
    status.textContent = count
      ? `${count} course${count === 1 ? "" : "s"} selected.`
      : "No courses selected yet.";
  }

  function choose(course) {
    if (multiple) {
      if (selectedCodes().includes(course.code)) {
        close();
        input.value = "";
        return;
      }
      const field = document.createElement("input");
      field.type = "hidden";
      field.name = values.dataset.fieldName;
      field.value = course.code;
      values.append(field);
      addChip(course);
      input.value = "";
      announceSelection();
    } else {
      let field = values.querySelector("input");
      if (!field) {
        field = document.createElement("input");
        field.type = "hidden";
        field.name = values.dataset.fieldName;
        values.append(field);
      }
      field.value = course.code;
      input.value = course.label;
      status.textContent = `${course.label} selected.`;
    }
    close();
  }

  function render(courses) {
    const taken = multiple ? new Set(selectedCodes()) : new Set();
    options = courses.filter((course) => !taken.has(course.code));

    listbox.replaceChildren();
    if (!options.length) {
      close();
      status.textContent = input.value.trim()
        ? "No matching courses. Try a course code like MAT 2022, or part of the title."
        : "";
      return;
    }

    options.forEach((course, i) => {
      const item = document.createElement("li");
      item.className = "course-picker__option";
      item.id = `${picker.id || "course-picker"}-option-${i}`;
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", "false");
      item.textContent = course.label;
      // mousedown, not click: blur would close the list first.
      item.addEventListener("mousedown", (event) => {
        event.preventDefault();
        choose(course);
      });
      listbox.append(item);
    });

    listbox.hidden = false;
    input.setAttribute("aria-expanded", "true");
    status.textContent = "";
    setActive(0);
  }

  async function refresh() {
    const query = input.value.trim();
    if (!query) {
      close();
      announceSelection();
      return;
    }

    const current = ++requestNumber;
    const url = new URL(searchUrl, window.location.href);
    url.searchParams.set("q", query);

    try {
      const response = await fetch(url, { credentials: "same-origin" });
      if (!response.ok) throw new Error("Course search unavailable");
      const { courses } = await response.json();
      if (current !== requestNumber) return;
      render(courses);
    } catch (error) {
      if (current !== requestNumber) return;
      close();
      status.textContent =
        "Course search is unavailable right now. Courses you have already selected are still saved when you submit.";
    }
  }

  input.addEventListener("input", () => {
    if (!multiple) {
      // Typing over a chosen course clears it, so the hidden value can never
      // disagree with what the box shows.
      const field = values.querySelector("input");
      if (field) field.value = "";
    }
    ++requestNumber;
    clearTimeout(timer);
    timer = setTimeout(refresh, 200);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (listbox.hidden) {
        refresh();
      } else {
        setActive(activeIndex + (event.key === "ArrowDown" ? 1 : -1));
      }
      event.preventDefault();
    } else if (event.key === "Enter") {
      if (!listbox.hidden && options[activeIndex]) {
        choose(options[activeIndex]);
        event.preventDefault();
      }
    } else if (event.key === "Escape") {
      if (!listbox.hidden) {
        close();
        event.preventDefault();
      }
    }
  });

  input.addEventListener("blur", () => {
    // Let a mousedown on an option run first.
    setTimeout(close, 120);
  });

  // Chips rendered by the server need their remove button wired up.
  for (const chip of picker.querySelectorAll(".course-picker__chip")) {
    const remove = chip.querySelector(".course-picker__chip-remove");
    const code = chip.dataset.code;
    if (!remove || !code) continue;
    remove.addEventListener("click", () => {
      chip.remove();
      const field = values.querySelector(`input[value="${cssEscape(code)}"]`);
      if (field) field.remove();
      announceSelection();
      input.focus();
    });
  }

  announceSelection();
}

function cssEscape(value) {
  return window.CSS && window.CSS.escape
    ? window.CSS.escape(value)
    : value.replace(/["\\]/g, "\\$&");
}
