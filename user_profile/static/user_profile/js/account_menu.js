document.addEventListener("DOMContentLoaded", () => {
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
