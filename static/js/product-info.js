$(document).ready(function () {
    $('#add-to-cart').click(function (e) {
        e.preventDefault();
        let item_id = $(this).data('item_id')
        let token = $('input[name=csrfmiddlewaretoken]').val()
        let url = $('#button-form').attr("action");
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'item_id': item_id,
                csrfmiddlewaretoken: token,
            },
            success: function (response) {
                alertify.success(response.status)
            },
            errors: function () {
                console.log("error")
            }
        })
    });
})

