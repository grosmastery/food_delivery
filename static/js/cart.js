$('.delete-btn').click(function () {
    let del_item = $(this).data('item');
    let token = $('input[name=csrfmiddlewaretoken]').val();
    let url = $('#del-ele-div').attr('action');

    $.ajax({
        type: 'POST',
        url: url,
        data: {
            'del_item': del_item,
            csrfmiddlewaretoken: token,
        },
        success: function () {
            console.log('ok')
            window.location.reload(true);
        },
        errors: function () {
            console.log('not ok')
        }
    })
})

$('#clear-cart').click(function () {
    let cart_id = $(this).data('cart_id')
    let token = $('input[name=csrfmiddlewaretoken]').val();
    let url = $('#div-del-all').attr('action');
    $.ajax({
        type: 'POST',
        url: url,
        data: {
            cart_id: cart_id,
            csrfmiddlewaretoken: token,
        },
        success: function () {
            console.log('ok')
            window.location.reload(true);
        },
        errors: function () {
            console.log('not ok')
        }
    })
})