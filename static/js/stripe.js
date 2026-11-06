// Create an instance of Elements.
var elements = stripe.elements();

// Create an instance of the card Element.
var card = elements.create('card');

// Add an instance of the card Element into the `card-element` <div>.
card.mount('#card-element');

var form = document.getElementById('stripe-form');
var errorElement = document.getElementById('card-errors');

function showError(message) {
    errorElement.textContent = message || '';
}

function setLoading(isLoading) {
    document.querySelectorAll('.stripe-form button').forEach(function (button) {
        button.disabled = isLoading;
    });
}

function failed() {
    showError('Something went wrong. Please try again.');
    setLoading(false);
}

// Handle real-time validation errors from the card Element.
card.on('change', function (event) {
    showError(event.error ? event.error.message : '');
});

function postToServer(url, data) {
    var token = form.querySelector('input[name=csrfmiddlewaretoken]').value;
    return fetch(url, {
        method: 'POST',
        headers: {'X-CSRFToken': token},
        body: new URLSearchParams(data),
    }).then(function (response) {
        return response.json();
    });
}

function handleServerResponse(response) {
    if (response.redirect) {
        window.location.href = response.redirect;
        return;
    }
    if (response.requires_action) {
        stripe.handleNextAction({clientSecret: response.client_secret}).then(function (result) {
            if (result.error) {
                showError(result.error.message);
                setLoading(false);
            } else {
                postToServer(form.dataset.confirmUrl, {}).then(handleServerResponse, failed);
            }
        });
        return;
    }
    showError(response.error);
    setLoading(false);
}

// Handle form submission.
if (form.dataset.mode === 'setup') {
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        setLoading(true);
        stripe.confirmCardSetup(form.dataset.clientSecret, {payment_method: {card: card}}).then(function (result) {
            if (result.error) {
                showError(result.error.message);
                setLoading(false);
                return;
            }
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'setup_intent_id';
            input.value = result.setupIntent.id;
            form.appendChild(input);
            form.submit();
        });
    });
} else {
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        setLoading(true);
        stripe.createPaymentMethod({type: 'card', card: card}).then(function (result) {
            if (result.error) {
                showError(result.error.message);
                setLoading(false);
                return;
            }
            postToServer(window.location.pathname, {payment_method_id: result.paymentMethod.id})
                .then(handleServerResponse, failed);
        });
    });

    var savedCardForm = document.getElementById('saved-card-form');
    if (savedCardForm) {
        savedCardForm.addEventListener('submit', function (event) {
            event.preventDefault();
            setLoading(true);
            postToServer(window.location.pathname, {use_default: 'true'}).then(handleServerResponse, failed);
        });
    }

    var currentCardForm = $('.current-card-form');
    var newCardForm = $('.new-card-form');
    var useDefaultCard = document.querySelector('input[name=use_default_card]');
    if (useDefaultCard) {
        useDefaultCard.addEventListener('change', function () {
            if (this.checked) {
                newCardForm.hide();
                currentCardForm.show();
            } else {
                newCardForm.show();
                currentCardForm.hide();
            }
        });
    }
}
