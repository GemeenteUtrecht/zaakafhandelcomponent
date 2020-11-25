const onLinkClick = (node, event) => {
    if (node.classList.contains('link--disabled')) {
        event.preventDefault();
        event.stopPropagation();
        if (node.dataset.msg) {
            window.setTimeout(() => {
                alert(node.dataset.msg);
            }, 10);
        }
        return false;
    }
};

const linkNodes = document.querySelectorAll('.link');
Array.from(linkNodes).forEach(node => {
    node.addEventListener('click', (event) => onLinkClick(node, event));
});
