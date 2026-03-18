let clickCount = 0;

document.addEventListener("click", (event) => {
    const button = event.target.closest("#custom-btn");
    if (!button) {
        return;
    }

    clickCount += 1;
    button.textContent = `Clicked: ${clickCount} times`;
});
