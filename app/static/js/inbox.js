let offset = 0;
let limit = 10;
let loading = false;
let finishedLoading = false;
let redirecting = false;
let firstEmailOpened = false;

let currentPredictionRequest = 0;
let currentController = 0;

let activeFilter = "all";
let searchQuery = "";

let predictionRetries = new Map();
let retry_delay = 1000

function redirectToLogin() {
    if (redirecting) {
        return;
    }

    redirecting = true;
    finishedLoading = true;
    loading = false;

    localStorage.removeItem("username");
    window.location.href = "/";
}

function loadUserInfo() {
    const email = localStorage.getItem("username");
    const userElement = document.getElementById("userEmail");

    if (email) {
        userElement.textContent = email;
    } else {
        userElement.textContent = "";
    }
}


async function logout() {
    try {
        await fetch(
            "/logout",
            {
                method: "POST",
                credentials: "include"
            }
        );
    } finally {
        localStorage.removeItem("username");
        window.location.href = "/";
    }
}

async function loadEmails() {
    if (loading || finishedLoading || redirecting) {
        return false;
    }
    loading = true;

    try {
        const response = await fetch(`/emails?offset=${offset}`, {
            credentials: "include"
        });

        if (response.status === 401) {
            redirectToLogin();
            return;
        }
        if (!response.ok) {
            throw new Error("Unable to load emails.");
        }

        const emails = await response.json();
        const list = document.getElementById("emailList");

        // handle the situation if the user doesn't have any emails
        if (!emails.length) {
            finishedLoading = true;
            document.getElementById("emailPlaceholder").innerHTML = `
                <h2>No emails found</h2>
                <p>This mailbox is empty.</p>
            `;
            return true;
        }

        emails.forEach(email => {
            createEmailItem(email, list);
        });

        offset += emails.length;

        // open the newest email once
        if (!firstEmailOpened && emails.length > 0) {
            firstEmailOpened = true;

            const firstItem = list.querySelector(".email");

            if (firstItem) {
                await openEmail(emails[0], firstItem);
            }
        }

        if (emails.length < limit) {
            finishedLoading = true;
        }
        return true;
    } catch (error) {
        console.error(error);
        return false;
    } finally {
        loading = false;
    }
}

function createEmailItem(email, list) {
    const item = document.createElement("div");
    item.className = "email";

    // store email data for filtering/searching
    item.emailData = email;
    item.innerHTML = `
        <div class="email-header">
            <h3>${escapeHTML(email.subject)}</h3>
            <span class="status pending">...</span>
        </div>
        <p>
            ${escapeHTML(email.sender_display_name || email.sender_email)}
        </p>
    `;

    item.onclick = () => {
        openEmail(email, item);
    };
    list.appendChild(item);
    predictInboxItem(email, item);
}

async function predictInboxItem(email, item) {
    const badge = item.querySelector(".status");

    const attempt = predictionRetries.get(email) || 0;

    try {
        badge.className = "status pending";
        badge.textContent = attempt > 0 ? "⟳" : "...";

        const response = await fetch("/predict", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(email)
        });

        if (!response.ok) {
            throw new Error();
        }

        const result = await response.json();

        // success, remove retry counter
        predictionRetries.delete(email);

        email.prediction = result.prediction;
        email.confidence = result.confidence;
        email.analysis = result.analysis;
        email.failedPrediction = false;

        const confidence =
            (result.confidence * 100).toFixed(0);

        if (result.prediction === 1) {
            badge.className = "status phishing";
            badge.textContent = `⚠ ${confidence}%`;
        } else {
            badge.className = "status safe";
            badge.textContent = "✔";
        }
        applyFilters();

    } catch (error) {
        const nextAttempt = attempt + 1;

        predictionRetries.set(
            email,
            nextAttempt
        );

        email.prediction = null;
        email.confidence = null;
        email.analysis = null;
        email.failedPrediction = true;

        badge.className = "status pending";
        badge.textContent = "⟳";

        applyFilters();


        // Retry with increasing delay
        const delay = Math.min(
            1000 * nextAttempt,
            retry_delay
        );

        setTimeout(() => {
            predictInboxItem(
                email,
                item
            );
        }, delay);
    }
}

async function openEmail(email, element) {
    document.getElementById("emailPlaceholder").style.display = "none";
    document.getElementById("emailContent").classList.remove("hidden");

    document.querySelectorAll(".email").forEach(item => {
        item.classList.remove("active");
    });

    element.classList.add("active");

    document.getElementById("subject").textContent = email.subject;
    document.getElementById("from").textContent = `${email.sender_display_name ?? ""}<${email.sender_email}>`;
    document.getElementById("date").textContent = email.sent_datetime;
    document.getElementById("emailBody").textContent = email.body;
    document.getElementById("emailMeta").classList.remove("hidden");

    const badge = document.getElementById("prediction");
    badge.className = "badge";
    badge.innerHTML = "Analysing...";

    if (!email.failedPrediction && email.prediction !== undefined && email.prediction !== null) {

        updatePredictionBadge({
            prediction: email.prediction, confidence: email.confidence, analysis: email.analysis
        }, element);

        return;
    }
    await predictEmail(email, element);
}

async function predictEmail(email, element) {
    currentPredictionRequest++;
    const requestId = currentPredictionRequest;

    if (currentController) {
        currentController.abort();
    }

    currentController = new AbortController();

    try {
        const response = await fetch("/predict", {
            method: "POST", headers: {
                "Content-Type": "application/json"
            }, body: JSON.stringify(email), signal: currentController.signal
        });

        if (requestId !== currentPredictionRequest) return;
        if (!response.ok) throw new Error("Prediction failed.");

        const result = await response.json();
        email.prediction = result.prediction;
        email.confidence = result.confidence;
        email.analysis = result.analysis;
        email.failedPrediction = false;

        if (requestId !== currentPredictionRequest) return;

        const status = element.querySelector(".status");
        const shortConfidence = (result.confidence * 100).toFixed(0);

        if (result.prediction === 1) {
            status.className = "status phishing";
            status.textContent = `⚠ ${shortConfidence}%`;
        } else {
            status.className = "status safe";
            status.textContent = "✔";
        }

        updatePredictionBadge(result, element);

    } catch (err) {
        if (err.name === "AbortError") return;
        console.error(err);
        if (requestId !== currentPredictionRequest) return;
        setUnknownState(element);
    }
}

function setUnknownState(element) {
    element.dataset.prediction = "pending";
    element.querySelector(".status").textContent = "⟳";

    const badge = document.getElementById("prediction");

    badge.className = "badge";
    badge.innerHTML = `
        Unable to analyse.<br>
        <small>Retrying...</small>
    `;
}

function updatePredictionBadge(result, element) {
    const badge = document.getElementById("prediction");

    try {
        const confidence = (result.confidence * 100).toFixed(1);
        let explanation = "";
        if (result.prediction === 1 && result.analysis) {
            const triggerWords = (result.analysis.trigger_words || [])
                .map(word => word.trim())
                .filter(Boolean);
            const reasons = (result.analysis.reasons || [])
                .map(reason => reason.trim())
                .filter(Boolean);

            if (triggerWords.length > 0 || reasons.length > 0) {
                explanation = `
                    <div class="triggers">
                        ${triggerWords.length > 0
                    ? `<strong>Triggers:</strong> ${escapeHTML(triggerWords.join(", "))}`
                    : ""}
                        ${reasons.length > 0
                    ? `<br><strong>Reasons:</strong> ${escapeHTML(reasons.join("\n"))}`
                    : ""}
                    </div>
                `;
            }
        }

        const confidenceBar = `
            <div class="confidence-section">
                <div class="confidence-label">
                    Confidence: ${confidence}%
                </div>

                <div class="confidence-track">
                    <div 
                        class="confidence-fill ${result.prediction === 1 ? "danger" : "success"}"
                        style="width:${confidence}%">
                    </div>
                </div>
            </div>
        `;

        if (result.prediction === 1) {
            badge.className = "badge phishing";
            badge.innerHTML = `
                <div>
                    ⚠ Phishing
                </div>
                ${confidenceBar}
                ${explanation}
            `;
        } else {
            badge.className = "badge safe";

            badge.innerHTML = `
                <div>
                    ✔ Legitimate
                </div>
                ${confidenceBar}
                ${explanation}
            `;
        }

    } catch (error) {
        console.error(error);

        badge.className = "badge";
        badge.textContent = "Unable to analyse";
    }
}

function applyFilters() {
    const items = document.querySelectorAll(".email");

    items.forEach(item => {
        const email = item.emailData;

        if (!email) {
            return;
        }

        const searchableText = [
            email.subject,
            email.sender_email,
            email.sender_display_name,
            email.body
        ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

        const matchesSearch =
            searchableText.includes(
                searchQuery.trim().toLowerCase()
            );
        const status = item.querySelector(".status");

        let matchesFilter = true;

        switch (activeFilter) {
            case "phishing":
                matchesFilter =
                    status.classList.contains("phishing");
                break;

            case "safe":
                matchesFilter =
                    status.classList.contains("safe");
                break;

            case "all":
            default:
                matchesFilter = true;
        }

        item.style.display =
            matchesSearch && matchesFilter
                ? ""
                : "none";
    });
}

function setupLazyLoading() {
    const list = document.getElementById("emailList");

    list.addEventListener("scroll", () => {
        const nearBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 50;

        if (nearBottom) {
            loadEmails();
        }
    });
}


function escapeHTML(value) {
    if (!value) {
        return "";
    }

    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

window.onload = async () => {
    loadUserInfo();
    document.getElementById("logoutButton").addEventListener("click", logout);
    document.getElementById("searchBox")
        .addEventListener(
            "input",
            event => {
                searchQuery =
                    event.target.value;

                applyFilters();
            }
        );
    document.querySelectorAll(".filter")
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    document
                        .querySelectorAll(".filter")
                        .forEach(btn => {
                            btn.classList.remove(
                                "active"
                            );
                        });
                    button.classList.add(
                        "active"
                    );
                    activeFilter =
                        button.dataset.filter;
                    applyFilters();
                }
            );
        });


    const list = document.getElementById("emailList");

    setupLazyLoading();
    await loadEmails();

    // keep loading until scrolling becomes possible
    while (
        !redirecting &&
        list.scrollHeight <= list.clientHeight &&
        !finishedLoading
        ) {
        const loaded = await loadEmails();
        if (!loaded) {
            break;
        }
    }
};
