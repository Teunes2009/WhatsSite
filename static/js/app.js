const MessageList = document.getElementById("MessageList");
if (MessageList) {
    MessageList.scrollTop = MessageList.scrollHeight;
    let WasAtBottom = true;
    document.body.addEventListener("htmx:beforeRequest", function (event) {
        const MessageList = document.getElementById("MessageList");
        if (MessageList && MessageList.scrollHeight < MessageList.clientHeight+MessageList.scrollTop + 5) {
            WasAtBottom = true;
        }
    });

    document.body.addEventListener("htmx:afterSettle", function (event) {
        const MessageList = document.getElementById("MessageList");
        if (MessageList) {
            if (WasAtBottom) {
                MessageList.scrollTop = MessageList.scrollHeight;
                WasAtBottom = false;
            }
        }
    });
}

document.body.addEventListener("htmx:afterRequest", function (event) {
    if (event.detail.elt.tagName === "FORM") {
        event.detail.elt.reset();
    }
});
