(function () {
    const key = "skillswap-appearance";
    let appearance = "dark";
    try {
        if (localStorage.getItem(key) === "light") appearance = "light";
    } catch (_) {
        // Keep the default when browser storage is unavailable.
    }
    document.documentElement.dataset.appearance = appearance;
    window.setSkillSwapAppearance = function (value) {
        appearance = value === "light" ? "light" : "dark";
        document.documentElement.dataset.appearance = appearance;
        try {
            localStorage.setItem(key, appearance);
        } catch (_) {
            // The choice still applies for this page.
        }
    };
})();
