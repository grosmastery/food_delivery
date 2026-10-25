const user_id = $('#user_id').val();
const room_id = $('#room_id').val();
console.log(room_id)

const ws = new WebSocket(`ws:${window.location.host}/ws/chat/`);

ws.onopen = function () {
    ws.send(JSON.stringify({'type': 'connected', 'user_id': user_id}));
};

ws.onmessage = function (e) {
    const data = JSON.parse(e.data);
    if (data.type === 'connected') {
        const bot_message = $('<div class="sent-messages">' +
            `                   <b>Bot:</b> <span>${data.message}</span>` +
            '                </div>');
        $('#chat-view').append(bot_message);
    } else {
        const message_data = JSON.parse(data.message);
        const new_message = $('<div class="sent-messages">' +
            `                   <b>${message_data.username}:</b> <span>${message_data.text}</span>` +
            '                </div>');
        $('#chat-view').append(new_message);
    }
};

$('#send-message').click(function () {
    ws.send(JSON.stringify({
        'type': "message",
        'message': $('#message').val(),
        'user_id': user_id,
        'room_id': room_id
    }));
    $('#message').val('');
});