document.addEventListener("DOMContentLoaded", () => {

    function random(min, max) {
        return (Math.random() * (max - min) + min).toFixed(1);
    }

    function updateSensors() {
        const heart = document.getElementById("heart");
        const temp = document.getElementById("temp");

        if (heart) heart.innerText = random(65, 100);
        if (temp) temp.innerText = random(36.4, 37.5);
    }

    if (document.getElementById("heart") || document.getElementById("temp")) {
        setInterval(updateSensors, 2000);
        updateSensors();
    }

});






/* PAGE TRANSITION */
document.querySelectorAll("a").forEach(link => {
    if (link.href && !link.href.includes("#")) {
        link.addEventListener("click", e => {
            e.preventDefault();
            document.body.style.opacity = "0";
            setTimeout(() => window.location.href = link.href, 250);
        });
    }
});


/* SCROLL REVEAL */
const reveals = document.querySelectorAll(".reveal");
if (reveals.length) {
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add("active");
        });
    }, { threshold: 0.15 });

    reveals.forEach(el => observer.observe(el));
}


/* ACTIVE NAV */
const navLinks = document.querySelectorAll(".nav-links a");
if (navLinks.length) {
    const page = location.pathname.split("/").pop();
    navLinks.forEach(link => {
        if (link.getAttribute("href") === page) {
            link.classList.add("active");
        }
    });
}

console.log("Script connected successfully!");
