document.body.addEventListener("htmx:afterRequest", function (event) {
    if (event.detail.elt.tagName === "FORM") {
        event.detail.elt.reset();
    }
});