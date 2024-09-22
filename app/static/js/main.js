document.getElementById('menu-icon').addEventListener('click', () => {
    var dropdown = document.getElementById('dropdown-menu');
    dropdown.classList.toggle('show')
})

document.getElementById('price').addEventListener('show', () => {
    let count = Math.floor(Math.random(200))
    count.classList.toggle('show')
})

$(document).ready(function() {
    $('.add-to-cart-btn').click(function(e) {
        e.preventDefault();

        // Get the product ID
        var productId = $(this).data('id');

        // Make an AJAX POST request to add the product to the cart
        $.ajax({
            url: '/add_to_cart/' + productId,
            method: 'POST',
            data: { quantity: 1 },  // You can make this dynamic if you want users to input quantity
            success: function(response) {
                // Update the cart count in the header
                $('#cart-count').text(response.cart_count);
            },
            error: function() {
                alert('Failed to add product to cart. Please try again.');
            }
        });
    });
});
