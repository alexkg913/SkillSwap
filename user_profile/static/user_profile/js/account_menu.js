document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-appearance-select]").forEach((select) => {
        select.value = document.documentElement.dataset.appearance === "light" ? "light" : "dark";
        select.addEventListener("change", () => {
            window.setSkillSwapAppearance(select.value);
        });
    });
    document.querySelectorAll(".account-menu").forEach((menu) => {
        document.addEventListener("pointerdown", (event) => {
            if (menu.open && !menu.contains(event.target)) menu.open = false;
        });
        menu.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && menu.open) {
                menu.open = false;
                menu.querySelector("summary").focus();
            }
        });
    });
});
