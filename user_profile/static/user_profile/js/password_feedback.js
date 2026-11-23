(function () {
    const password = document.getElementById("id_password");
    const confirmation = document.getElementById("id_password_confirm");
    const requirements = document.getElementById("password-requirements");
    const confirmationDetails = document.getElementById("password-confirmation");
    const matchStatus = document.getElementById("password-match-status");

    if (!password || !confirmation || !requirements || !confirmationDetails) return;

    const rules = [
        ["rule-length", value => Array.from(value).length >= 10],
        ["rule-uppercase", value => /[A-Z]/.test(value)],
        ["rule-special", value => /[^A-Za-z0-9\s]/.test(value)],
        ["rule-number", value => /[0-9]/.test(value)],
    ];

    function updateConfirmation() {
        const hasConfirmation = confirmation.value.length > 0;
        const matches = hasConfirmation && confirmation.value === password.value;
        confirmationDetails.classList.toggle("matches", matches);
        confirmationDetails.classList.toggle("mismatch", hasConfirmation && !matches);
        matchStatus.textContent = !hasConfirmation
            ? "Password confirmation"
            : matches ? "Passwords match" : "The passwords don't match";
    }

    password.addEventListener("input", () => {
        requirements.open = true;
        for (const [id, check] of rules) {
            document.getElementById(id).classList.toggle("met", check(password.value));
        }
        updateConfirmation();
    });

    confirmation.addEventListener("input", () => {
        confirmationDetails.open = true;
        updateConfirmation();
    });
})();
