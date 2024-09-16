document.getElementById('menu-icon').addEventListener('click', () => {
    var dropdown = document.getElementById('dropdown-menu');
    dropdown.classList.toggle('show')
})

document.getElementById('price').addEventListener('show', () => {
    let count = Math.floor(Math.random(200))
    count.classList.toggle('show')
})