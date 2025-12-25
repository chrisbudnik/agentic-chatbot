/**
 * Citations Component
 * Handles rendering of source citations
 */

/**
 * Render citations in a container
 * @param {string|Array|Object} content - Citations data
 * @param {HTMLElement} container - Container element
 */
export function renderCitations(content, container) {
    try {
        const citations = typeof content === 'string' ? JSON.parse(content) : content;

        let citationList = [];
        if (Array.isArray(citations)) {
            citationList = citations.map(c => {
                if (typeof c === 'string') return { title: c, url: c };
                return {
                    title: c.title || c.url,
                    url: c.url,
                    page_span_start: c.page_span_start,
                    page_span_end: c.page_span_end,
                };
            });
        } else if (citations && typeof citations === 'object') {
            citationList = Object.entries(citations).map(([name, url]) => ({
                title: name,
                url: url
            }));
        }

        if (citationList.length === 0) return;

        container.innerHTML = "";

        const title = document.createElement("div");
        title.className = "citations-title";
        title.textContent = "Sources:";
        container.appendChild(title);

        const list = document.createElement("ul");
        citationList.forEach(c => {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = c.url;
            a.textContent = c.title;
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            li.appendChild(a);

            const pageRange = formatPageRange(c);
            if (pageRange) {
                const meta = document.createElement("span");
                meta.className = "citation-page-range";
                meta.textContent = pageRange;
                li.appendChild(meta);
            }
            list.appendChild(li);
        });

        container.appendChild(list);
        container.style.display = "block";
    } catch (e) {
        console.error("Failed to parse citations", e);
    }
}

/**
 * Format page range for citation
 * @param {Object} citation - Citation object with page_span_start/end
 * @returns {string} Formatted page range
 */
function formatPageRange(c) {
    const start = c?.page_span_start;
    const end = c?.page_span_end;

    if (typeof start !== "number" && typeof end !== "number") return "";
    if (typeof start === "number" && typeof end === "number") {
        if (start === end) return `p. ${start}`;
        return `pp. ${start}–${end}`;
    }
    const single = (typeof start === "number") ? start : end;
    return `p. ${single}`;
}
