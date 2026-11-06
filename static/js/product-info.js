$(document).ready(function () {
    $('#add-to-cart').click(function (e) {
        e.preventDefault();
        let item_id = $(this).data('item_id')
        let token = $('input[name=csrfmiddlewaretoken]').val()
        let url = $('#button-form').attr("action");
        let button = $(this);
        button.prop('disabled', true);
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'item_id': item_id,
                csrfmiddlewaretoken: token,
            },
            success: function (response) {
                alertify.success(response.status)
                let badge = $('.cart-badge');
                if (badge.length) {
                    badge.text(parseInt(badge.text(), 10) + 1);
                } else {
                    $('.cart-link').append('<span class="cart-badge">1</span>');
                }
            },
            error: function () {
                console.log("error")
                alertify.error('Could not add to cart, please try again')
            },
            complete: function () {
                button.prop('disabled', false);
            }
        })
    });
})

