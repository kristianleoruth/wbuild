const themedEls = document.querySelectorAll('[data-theme]');
const switchThemeBtnIcon = document.querySelector('button.theme-btn').firstElementChild

function switchTheme() {
    let themeTo = ""
    for (el of themedEls) {
        const cur = el.getAttribute("data-theme");
        themeTo = cur == "light" ? "dark" : "light"
        el.setAttribute("data-theme", themeTo)
    }
    switchThemeBtnIcon.setAttribute("src", themeTo == "dark"? "./assets/sun.png" : "./assets/moon.png")
}