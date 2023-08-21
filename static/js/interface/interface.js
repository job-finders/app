
window.addEventListener("load", e => {
    const all_notifications_link = document.getElementById('notifications_see_all');
    const login_link = document.getElementById('login_link');
    const logout_link = document.getElementById('logout_link');
    const profile_link = document.getElementById('profile_link');

    all_notifications_link.addEventListener('click', e => {
        window.location.href = "/admin/notifications";
    });

    login_link.addEventListener("click", e => {
        window.location.href = "/admin/login";
    });

    logout_link.addEventListener("click", e => {
       window.location.href = "/admin/logout";
    });

    profile_link.addEventListener("click", e => {
        window.location.href = "/";
    });

});