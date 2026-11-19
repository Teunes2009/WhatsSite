document.body.addEventListener("htmx:afterRequest", function (event) {
    if (event.detail.elt.tagName === "FORM") {
        event.detail.elt.reset();
    }
});

const MessageList = document.getElementById("MessageList");
if (MessageList) {
    MessageList.scrollTop = MessageList.scrollHeight;
}