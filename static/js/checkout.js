$(document).ready(function () {
    let card_btn = document.getElementById('payment-card');
    let cash_btn = document.getElementById('payment-cash');
    let bonus_coins_btn = document.getElementById('payment-bonus-coins');
    let text_id = document.getElementById('text-id');
    card_btn.setAttribute('hidden', 'hidden');
    cash_btn.setAttribute('hidden', 'hidden');
    bonus_coins_btn.setAttribute('hidden', 'hidden');
    text_id.setAttribute('hidden', 'hidden');

    $('#id_payment_choice_0').click(function () {
        card_btn.removeAttribute('hidden');
        cash_btn.setAttribute('hidden', 'hidden');
        bonus_coins_btn.setAttribute('hidden', 'hidden');
        text_id.setAttribute('hidden', 'hidden');
    });

    $('#id_payment_choice_1').change(function () {
        card_btn.setAttribute('hidden', 'hidden');
        cash_btn.removeAttribute('hidden');
        bonus_coins_btn.setAttribute('hidden', 'hidden');
        text_id.setAttribute('hidden', 'hidden');
    });

    $('#id_payment_choice_2').change(function () {
    card_btn.setAttribute('hidden', 'hidden');
    cash_btn.setAttribute('hidden', 'hidden');
    bonus_coins_btn.removeAttribute('hidden');
    text_id.removeAttribute('hidden');

    });

})

