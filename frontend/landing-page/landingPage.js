
window.onload = function() {
    console.log("JavaScript is running after full page load.");

    const ticker = document.querySelector(".ticker");
    if (ticker) {
        setInterval(() => {
            ticker.style.transform = "translateX(-100%)";
            setTimeout(() => {
                ticker.style.transform = "translateX(100%)";
            }, 5000);
        }, 10000);
    }
};