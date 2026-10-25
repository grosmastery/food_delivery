const room_id = $('#room_id').val();
console.log(room_id)

const ws_scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${ws_scheme}://${window.location.host}/ws/chat/${room_id}/`);

function chat_line(author, text) {
    return $('<div class="sent-messages">')
        .append($('<b>').text(`${author}:`))
        .append(' ')
        .append($('<span>').text(text));
}

ws.onopen = function () {
    ws.send(JSON.stringify({'type': 'connected'}));
};

ws.onmessage = function (e) {
    const data = JSON.parse(e.data);
    if (data.type === 'connected') {
        $('#chat-view').append(chat_line('Bot', data.message));
    } else {
        const message_data = JSON.parse(data.message);
        $('#chat-view').append(chat_line(message_data.username, message_data.text));
    }
};

$('#send-message').click(function () {
    ws.send(JSON.stringify({
        'type': "message",
        'message': $('#message').val()
    }));
    $('#message').val('');
});
