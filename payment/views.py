from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from orders.models import Order
import braintree
from .tasks import payment_completed

# Instantiate the Braintree payment gateway
gateway = braintree.BraintreeGateway(settings.BRAINTREE_CONF)

def payment_process(request):
    order_id = request.session.get('order_id')  # Get the order ID from the session
    order = get_object_or_404(Order, id=order_id)  # Retrieve the order
    total_cost = order.get_total_cost()  # Calculate the total cost of the order

    if request.method == 'POST':
        # Retrieve the nonce from the submitted form
        nonce = request.POST.get('payment_method_nonce', None)

        # Create and submit the transaction
        result = gateway.transaction.sale({
            'amount': f'{total_cost:.2f}',  # Payment amount
            'payment_method_nonce': nonce,  # Payment method
            'options': {
                'submit_for_settlement': True  # Automatically submit for settlement
            }
        })

        if result.is_success:
            # Mark the order as paid
            order.paid = True
            # Store the transaction ID
            order.braintree_id = result.transaction.id
            order.save()
            payment_completed.delay(order.id)
            return redirect('payment:done')
        else:
            return redirect('payment:canceled')
    else:
        # Generate a client token for the Braintree form
        client_token = gateway.client_token.generate()
        return render(request, 'payment/process.html', {
            'order': order,
            'client_token': client_token
        })

def payment_done(request):
    return render(request, 'payment/done.html')

def payment_canceled(request):
    return render(request, 'payment/canceled.html')
