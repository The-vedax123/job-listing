document.addEventListener("DOMContentLoaded", function () {
    const yearEl = document.getElementById("footer-year");
    if (yearEl) {
        yearEl.textContent = new Date().getFullYear();
    }

    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            let isValid = true;
            const requiredInputs = form.querySelectorAll(
                "input[required], textarea[required], select[required]"
            );

            requiredInputs.forEach(function (input) {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add("is-invalid");
                } else {
                    input.classList.remove("is-invalid");
                }
            });

            if (!isValid) {
                event.preventDefault();
                const firstInvalid = form.querySelector(".is-invalid");
                if (firstInvalid && typeof firstInvalid.focus === "function") {
                    firstInvalid.focus();
                }
            }
        });

        form.querySelectorAll("input, textarea, select").forEach(function (el) {
            el.addEventListener("input", function () {
                el.classList.remove("is-invalid");
            });
            el.addEventListener("change", function () {
                el.classList.remove("is-invalid");
            });
        });
    });
});
