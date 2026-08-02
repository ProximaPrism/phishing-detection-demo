const form = document.getElementById("connectForm");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = document.getElementById("connectButton");
    const status = document.getElementById("status");

    button.disabled = true;
    button.textContent = "Connecting...";

    status.className = "status";
    status.textContent = "";

    const request = {
        host: document.getElementById("host").value,
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
        mailbox: "INBOX"
    };

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(request)
        });

        const result = await response.json();
        if (result.success) {
            localStorage.setItem("username", result.email);

            status.classList.add("success");
            status.textContent = "Login successful, redirecting...";
            window.location.href = "/inbox";
        } else {
            status.classList.add("error");
            status.textContent = result.message;
        }
    } catch {
        status.classList.add("error");
        status.textContent = "Unable to connect to server.";
    }

    button.disabled = false;
    button.textContent = "Connect";
});