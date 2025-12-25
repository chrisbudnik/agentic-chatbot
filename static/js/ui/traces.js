/**
 * Traces Component
 * Handles rendering of agent process traces
 */

/**
 * Create a trace element for the agent process log
 * @param {Object} traceObj - Trace object with type and content
 * @returns {HTMLElement} Trace DOM element
 */
export function createTraceElement(traceObj) {
    const el = document.createElement("div");
    el.className = `trace-item ${traceObj.type}`;

    const header = document.createElement("div");
    header.className = "trace-header";

    const details = document.createElement("div");
    details.className = "trace-details";
    details.style.display = "none";

    let label = "";
    let detailContent = "";

    switch (traceObj.type) {
        case "thought":
            label = "🤔 Thought";
            detailContent = traceObj.content;
            break;
        case "tool_call":
            label = `🔧 Calling ${traceObj.tool_name}...`;
            detailContent = JSON.stringify(traceObj.tool_args || {}, null, 2);
            break;
        case "tool_result":
            const preview = traceObj.content.length > 50
                ? traceObj.content.substring(0, 50) + "..."
                : traceObj.content;
            label = `✅ Result: ${preview}`;
            detailContent = traceObj.content;
            break;
        case "execute_callback":
            const cbType = traceObj.callback_type ? ` (${traceObj.callback_type})` : "";
            label = `🔄 Executing Callback${cbType}`;
            detailContent = traceObj.content;
            break;
        case "execute_callback_result":
            label = "✅ Callback Result";
            detailContent = traceObj.content;
            break;
        case "error":
            label = "❌ Error";
            detailContent = traceObj.content;
            break;
        default:
            label = traceObj.content;
            detailContent = traceObj.content;
    }

    header.textContent = label;
    details.textContent = detailContent;

    header.onclick = () => {
        const isHidden = details.style.display === "none";
        details.style.display = isHidden ? "block" : "none";
        header.classList.toggle("expanded", isHidden);
    };

    el.appendChild(header);
    el.appendChild(details);
    return el;
}
