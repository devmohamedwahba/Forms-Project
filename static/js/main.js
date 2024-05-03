// Collapse icon for form and reports tabs

function rotateIcon(iconId) {
    var icon = document.getElementById(iconId);

    var isExpanded = icon.getAttribute('aria-expanded') === 'true';

    if (isExpanded) {
        icon.style.transform = 'rotate(180deg)';

    } else {
        icon.style.transform = 'rotate(0deg)';
    }

    icon.setAttribute('aria-expanded', String(!isExpanded));
}

// Sidebar for Tabs and mobile
function openNav() {
    document.getElementById("mySideBar").style.marginLeft = "0";
    document.getElementById("overlay").classList.add("active");
}

function closeNav() {
    document.getElementById("mySideBar").style.marginLeft = "-250px";
    document.getElementById("overlay").classList.remove("active");
}

